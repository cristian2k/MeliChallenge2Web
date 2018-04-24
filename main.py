import funciones
import moduloimap
import modulomysql
import getpass
import threading

#Cargo configuración desde archivo JSON
try:
    configuracion = funciones.cargar_cfg()
    if configuracion['imap_cfg']:
        config_imap = configuracion['imap_cfg']
    else:
        raise Exception('No existe sección imap_cfg en archivo de configuración')
    if configuracion['mysql_cfg']:
        config_mysql = configuracion['mysql_cfg']
    else:
        raise Exception('No existe sección mysql_cfg en archivo de configuración')
except Exception as error:
    print(error)
    quit()

#Obtengo dirección de correo y contraseña
direccion = input('Dirección de correo: ')
password = getpass.getpass('Ingrese su contraseña para ' + direccion + ':')
palabra = input('Palabra a buscar [devops]: ') or 'devops'

#Intento conectarme a la base de datos para asegurarme que esto funciona antes de iniciar el proceso de búsqueda
try:
    obj_db = modulomysql.ModuloDB(config_mysql)
except Exception as error:
    print(error.args[0])
    quit()

#Inicio proceso
try:
    evento = threading.Event()
    obj_mail = moduloimap.ModuloIMAP(config_imap, direccion, password, palabra,evento)
    if obj_mail:
        obj_mail.start()
        proceso = True
        while proceso:
            evento.wait(timeout=0.1)
            while obj_mail.hay_excepcion():
                excepcion = obj_mail.get_excepcion()
                if excepcion['nivel'] == 'Advertencia':
                    print("\t"+excepcion['descripcion'])
                if excepcion['nivel'] == 'Fatal':
                    raise funciones.Excepcion(excepcion['descripcion'])
            while obj_mail.hay_nuevo_estado():
                estado = obj_mail.get_estado()
                if estado['estado'] == 'NoIniciado':
                    print('Iniciando...')
                elif estado['estado'] == 'ObteniendoMailboxes':
                    print('Obteniendo lista de mailboxes para la búsqueda...')
                elif estado['estado'] == 'EnProgreso':
                    mensaje = "Procesando: {0}% de progreso total. {1}% de progreso parcial - {2}".format(
                        estado['progreso']['porcentage_total'],
                        estado['progreso']['porcentage_parcial'],
                        estado['progreso']['mensaje_parcial'])
                    print(mensaje)
                elif estado['estado'] == 'Completado':
                    proceso = False
                    print('El proceso de obtención de correos termino.')
                    mensajes = obj_mail.get_resultado()

except Exception as error:
    print(str(error))
    quit()

#Guardo mensajes obtenidos
print('Guardando mensajes en base de datos.')
for mensaje in mensajes:
    try:
        print('Guardando. Fecha: ' + str(mensaje.get_fecha()) +
              '\t Asunto: ' + mensaje.get_asunto() +
              '\t De: ' + mensaje.get_remitente())
        obj_db.insertar_registro(mensaje)
    except Exception as error:
        print(str(error))
        quit()

