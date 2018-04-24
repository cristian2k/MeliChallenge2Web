from flask import Flask, flash, redirect, render_template, request, session, json
import os, datetime
import funciones
import moduloimap
import modulomysql
import threading
import random

def output_doble(texto):
    flash(texto)
    print(datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] + " " + texto)

app = Flask(__name__)
obj_mail = {}
evento = {}

try:
    configuracion = funciones.cargar_cfg()
except Exception as error:
    output_doble(str(error))
    quit()
config_imap = configuracion['imap_cfg']
config_mysql = configuracion['mysql_cfg']
try:
    obj_db = modulomysql.ModuloDB(config_mysql)
except Exception as error:
    output_doble(error.args[0])


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/progreso', methods=['GET'])
def get_progreso():
    if obj_mail[session['id']]:
        return json.jsonify(obj_mail[session['id']].get_estado()),200,{'ContentType':'application/json'}
    else:
        return "El proceso no se ha iniciado.",204

@app.route('/terminar', methods=['GET'])
def terminar():
    if obj_mail[session['id']]:
        if obj_mail[session['id']].get_estado()['estado'] == 'Completado':
            mensajes = obj_mail[session['id']].get_resultado()
            for mensaje in mensajes:
                try:
                    obj_db.insertar_registro(mensaje)
                    print("Insertando mensaje ... " + mensaje.get_asunto())
                except Exception as error:
                    print(str(error))
            del obj_mail[session['id']]
            return "Proceso completado",200
    return "El proceso no esta completo aún. Aguarde a que termine el proceso.",204


@app.route('/inicio', methods=['POST'])
def inicio():
    if request.method == 'POST':
        values = request.get_json()
        if values:
            random.seed()
            session['id'] = values['palabra'] + str(random.randint(1000000,10000000))
            global obj_mail
            global evento
            evento[session['id']] = threading.Event()
            obj_mail[session['id']] = moduloimap.ModuloIMAP(config_imap,
                                             values['username'],
                                             values['password'],
                                             values['palabra'],
                                             evento[session['id']])
            if obj_mail[session['id']]:
                obj_mail[session['id']].start()
                evento[session['id']].wait()
                while obj_mail[session['id']].hay_excepcion():
                    excepcion = obj_mail[session['id']].get_excepcion()
                    if excepcion['nivel'] == 'Fatal':
                        return json.dumps(excepcion),401,{'ContentType': 'application/json'}
                return json.dumps({'success': True}),200,{'ContentType': 'application/json'}
        else:
            return json.dumps({'success':False}),400,{'ContentType':'application/json'}

if __name__ == "__main__":
 app.secret_key = os.urandom(12)
 app.run(debug=False)