import json

class Excepcion(Exception):
    pass

class Correo:

    def __init__(self,remitente,asunto,fecha):
        self._remitente = remitente
        self._asunto = asunto
        self._fecha = fecha

    def get_fecha(self):
        return self._fecha

    def get_asunto(self):
        return self._asunto

    def get_remitente(self):
        return self._remitente

def cargar_cfg():
    temp_cfg = {}
    try:
        jsonarch = open('../config.json','r',encoding='utf-8')
        temp_cfg = json.load(jsonarch)
    except FileNotFoundError:
        raise Excepcion("Error: No se encontro el archivo de configuracion, verifique que la ruta y el nombre sean correctos.")
    except Exception:
        raise Excepcion("Error: No se pudo leer el archivo de configuracion.")
    return temp_cfg

