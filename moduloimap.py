import imaplib
import email
from datetime import datetime
from funciones import Excepcion,Correo
import threading
import multiprocessing
import time
import logging

logging.basicConfig(level=logging.FATAL, format='(%(threadName)-9s) %(message)s', )

class ModuloIMAP(threading.Thread):

    def __init__(self, config_imap, usuario, password, texto, evento):
        threading.Thread.__init__(self)
        self._evento = evento
        self._estado = {
            'estado': 'NoIniciado',
            'progreso':
                {
                'porcentage_total': '',
                'mensaje_total': '',
                'porcentage_parcial': '',
                'mensaje_parcial': ''
            }
        }
        self._mensajes = []
        self._excepciones = multiprocessing.Queue()
        self._nuevo_estado = True
        self._usuario = usuario
        self._password = password
        self._texto = texto
        self._mail = None
        try:
            if bool(config_imap['use_ssl']) == True:
                self._mail = imaplib.IMAP4_SSL(config_imap['imap_server'], int(config_imap['imap_port']))
            else:
                self._mail = imaplib.IMAP4(config_imap['imap_server'], int(config_imap['imap_port']))
        except imaplib.IMAP4.error as e:
            self.raise_excepcion("Fatal","Error conectandose al servidor de correo.")
        except imaplib.IMAP4.abort as e:
            self.raise_excepcion("Fatal","Ocurrio un error del lado del servidor.")
        except TimeoutError as e:
            self.raise_excepcion("Fatal","Tiempo de espera agotado estableciendo la conexión, verifique la dirección y el puerto.")
        except Exception as e:
            self.raise_excepcion("Fatal","Error generico inicializando modulo IMAP: " + str(e))

    def raise_excepcion(self,nivel,descripcion):
        logging.debug("raise_excepcion: " + str(nivel) + " " + str(descripcion))
        temp = {
            'nivel':nivel,
            'descripcion':descripcion
        }
        self._excepciones.put(temp)
        self._evento.set()

    def hay_excepcion(self):
        logging.debug("hay_excepcion: " + str(self._evento.is_set() and not self._excepciones.empty()))
        return self._evento.is_set() and not self._excepciones.empty()

    def get_excepcion(self):
        logging.debug("get_excepcion")
        temp = self._excepciones.get()
        if self._excepciones.empty():
            self._evento.clear()
        return temp

    def hay_nuevo_estado(self):
        logging.debug("hay_nuevo_estado: " + str(self._evento.is_set() and self._nuevo_estado))
        return self._evento.is_set() and self._nuevo_estado

    def _set_estado(self,estado='',porcentage_total='',mensaje_total='',porcentage_parcial='',mensaje_parcial=''):
        if estado:
            self._estado['estado'] = estado
        if porcentage_total:
            self._estado['progreso']['porcentage_total'] = porcentage_total
        if mensaje_total:
            self._estado['progreso']['mensaje_total'] = mensaje_total
        if porcentage_parcial:
            self._estado['progreso']['porcentage_parcial'] = porcentage_parcial
        if mensaje_parcial:
            self._estado['progreso']['mensaje_parcial'] = mensaje_parcial
        logging.debug("nuevo_estado")
        while self.hay_excepcion():
            time.sleep(0.1)
        self._nuevo_estado = True
        self._evento.set()

    def get_estado(self):
        self._nuevo_estado = False
        temp = self._estado
        self._evento.clear()
        logging.debug("get_estado: " + str(temp))
        return temp

    def get_resultado(self):
        return self._mensajes

    def run(self):
        if self._mail:
            if self.login(self._usuario, self._password):
                self.get_mensajes(self._texto)
                self.desconectar()

    def login(self,direccion,password):
        try:
            typ, data = self._mail.login(direccion,password)
            if typ != 'OK':
                self.raise_excepcion('Fatal','Error IMAP: No se pudo iniciar sesión en el servidor de correo. {0}'.format(bytes.decode(data[0])))
            else:
                return True
        except imaplib.IMAP4.error as error:
            self.raise_excepcion('Fatal', str(error))
        return False

    def get_mailboxes(self):
        carpetas_temp = []
        try:
            typ, mailboxes = self._mail.list('""','*')  # Obtengo lista de carpetas
            if typ == 'OK':
                for mailbox in mailboxes:
                    temp1, temp2, data = bytes.decode(mailbox).partition(')')
                    temp1, temp2, nombre = data.lstrip().partition(' ')
                    carpetas_temp.append(nombre)
        except Excepcion as error:
            self.raise_excepcion('Fatal','Error obteniendo lista de mailboxes. ' + str(error))
        return carpetas_temp

    def fetch_mensaje(self,num):
        try:
            typ, data = self._mail.fetch(num, 'BODY[HEADER.FIELDS (From Subject Date)]')
        except Exception as error:
            raise Excepcion("Error IMAP obteniendo mensaje: " + str(error))
        if typ == 'OK':
            try:
                mensaje = email.message_from_bytes(data[0][1])

                # Parsear remitente
                if mensaje['From']:
                    remitente_crudo = email.header.decode_header(mensaje['From'])[0]
                    if type(remitente_crudo[0]) is bytes:
                        if remitente_crudo[1] == 'unknown-8bit' or remitente_crudo[1] == None:
                            remitente = bytes(remitente_crudo[0]).decode('utf-8')
                        else:
                            remitente = bytes(remitente_crudo[0]).decode(remitente_crudo[1])
                        remitente = email.utils.parseaddr(remitente)[1]
                    else:
                        remitente = email.utils.parseaddr(remitente_crudo[0])[1]
                else:
                    remitente = '(vacio)'

                # Parsear asunto
                if mensaje['Subject']:
                    asunto_crudo = email.header.decode_header(mensaje['Subject'])[0]
                    if type(asunto_crudo[0]) is bytes:
                        if asunto_crudo[1] == 'unknown-8bit' or asunto_crudo[1] == None:
                            asunto = bytes(asunto_crudo[0]).decode('utf-8')
                        else:
                            asunto = bytes(asunto_crudo[0]).decode(asunto_crudo[1])
                            #asunto = asunto_crudo[0]
                            #para romper todo y ver que pasa
                    else:
                        asunto = asunto_crudo[0]
                    asunto = asunto.replace("'", "''")
                else:
                    asunto = '(sin asunto)'

                # Parsear fecha
                if mensaje['Date']:
                    fecha_tupla = email.utils.parsedate_tz(mensaje['Date'])
                    fecha_cruda = datetime.fromtimestamp(email.utils.mktime_tz(fecha_tupla))
                    fecha = fecha_cruda.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    fecha = datetime.fromtimestamp(0).strftime('%Y-%m-%d %H:%M:%S')
                return Correo(remitente, asunto, fecha)
            except Exception as error:
                self.raise_excepcion('Advertencia','Error IMAP parseando datos: ' + str(error))
            return None

    def get_mensajes(self,texto):
        mensajes_temp = []
        logging.debug("Obteniendo lista de mailboxs...")
        self._set_estado(estado='ObteniendoMailboxes')
        mailboxes = self.get_mailboxes()
        cantidad_mailboxes = len(mailboxes)
        logging.debug('Realizando búsqueda de correos con el texto "'+ texto +'" en el asunto y el cuerpo del correo:')
        self._set_estado(estado='EnProgreso')
        for mailbox, pos_mailbox in zip(mailboxes, range(1,cantidad_mailboxes+1)):
            logging.debug("{0}/{1} Carpeta {2}".format(pos_mailbox, cantidad_mailboxes, mailbox))
            try:
                typ, num = self._mail.select(mailbox=mailbox, readonly=True)
            except Exception as error:
                self.raise_excepcion('Advertencia',"Error IMAP accediendo mailbox: " + str(error))
            if typ == 'OK':
                try:
                    typ, data = self._mail.search(None, 'OR SUBJECT "{0}" BODY "{0}"'.format(texto))
                except Excepcion as error:
                    self.raise_excepcion('Advertencia',str(error))
                if typ == 'OK':
                    cantidad_mensajes = len(data[0].split())
                    for num, pos_mensaje in zip(data[0].split(), range(1,cantidad_mensajes+1)):
                        logging.debug("\t{0}/{1} mails procesados".format(pos_mensaje, cantidad_mensajes))
                        try:
                            mensaje_temp = self.fetch_mensaje(num)
                            mensajes_temp.append(mensaje_temp)
                        except Exception as error:
                            self.raise_excepcion('Advertencia',str(error))
                        self._set_estado(porcentage_parcial =
                                            str(int((100 / cantidad_mensajes) * pos_mensaje)),
                                         mensaje_parcial =
                                            "{0}/{1} mails procesados".format(pos_mensaje,cantidad_mensajes),
                                         porcentage_total=
                                            str(int((100 / cantidad_mailboxes) * pos_mailbox)),
                                         mensaje_total=
                                            "{0}/{1} Carpeta {2}".format(pos_mailbox, cantidad_mailboxes, mailbox))
                    if data[0] == b'':
                        self._set_estado(porcentage_total =
                                            str(int((100 / cantidad_mailboxes) * pos_mailbox)),
                                         mensaje_total =
                                            "{0}/{1} Carpeta {2}".format(pos_mailbox,cantidad_mailboxes,mailbox),
                                         porcentage_parcial=
                                            '100',
                                         mensaje_parcial=
                                            'Sin mensajes en este mailbox.')

        if self._estado['progreso']['porcentage_total'] == '100':
            self._set_estado(estado='Completado')
            self._mensajes = mensajes_temp

        logging.debug("Búsqueda terminada.")
        return mensajes_temp

    def desconectar(self):
        self._mail.logout()
