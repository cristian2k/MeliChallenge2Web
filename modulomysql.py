import MySQLdb
from funciones import Excepcion

class ModuloDB:

    def __init__(self,mysql_cfg):
        self._db_host = mysql_cfg['host']
        self._db_name = mysql_cfg['db']
        self._db_exist = False
        try:
            self._dbol = MySQLdb.connect(host=self._db_host,
                                         user=mysql_cfg['user'],
                                         passwd=mysql_cfg['passwd'],
                                         use_unicode=True,
                                         charset='utf8mb4')
        except MySQLdb.Error as error:
            if error.args[0] == 1045:
                raise Excepcion("Error MYSQL: El usuario no tiene permisos. Código de error {1}. Descripcion: {2}"
                                .format(self._db_host, error.args[0], error.args[1]))
            else:
                raise Excepcion("Error MYSQL: Código de error {1}. Descripcion: {2}"
                                .format(self._db_host, error.args[0], error.args[1]))
        try:
            self._cursordb = self._dbol.cursor()
            self._cursordb.execute("use {0};".format(self._db_name))
            self._db_exist = True
        except MySQLdb.Error as error:
            if error.args[0] == 1049:
                print("La base {0} no existe, se creara la base {0} en el servidor {1}".format(self._db_name, self._db_host))
            else:
                raise Excepcion("Error MYSQL. Código de error {0}. Descripcion: {1}"
                                .format(error.args[0], error.args[1]))
        if not self._db_exist:
            try:
                self.crear_db()
            except Exception as error:
                raise Excepcion(error)

    def crear_db(self):
        try:
            query_creacion = "create database {0} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" \
                             "use {0};" \
                             "create table correos " \
                             "(remitente varchar(50), asunto varchar(300),fecha datetime)"\
                .format(self._db_name);
            self._cursordb.execute(query=query_creacion, args=None)
            print("La base {0} se creo exitosamente en el servidor {1}".format(self._db_name, self._db_host))
        except MySQLdb.Error as error:
            raise Excepcion("Error MYSQL: La base {0} no pudo ser creada. "
                            "Código de error {1}. Descripcion: {2}"
                            .format(self._db_name, error.args[0], error.args[1]))

    def insertar_registro(self,correo):
        try:
            query_insert = "insert into {0}.correos (remitente, asunto, fecha) " \
                           "values ('{1}','{2}','{3}');"\
                .format(self._db_name, correo.get_remitente(),correo.get_asunto(),correo.get_fecha())
            self._cursordb.execute(query=query_insert, args=None)
            self._dbol.commit()
        except MySQLdb.Error as error:
            if error.args[0] == 1062:
                raise Excepcion("Error MYSQL: Ya existe un registro igual. "
                                "No se pudo insertar el registro en la base de datos.")
            else:
                raise Excepcion("Error MYSQL: No se pudo insertar registro. "
                                "Código de error {0}. Descripcion: {1}"
                                .format(error.args[0], error.args[1]))

    def desconectar(self):
        self._cursordb.close()
        self._dbol.close()


