from flask import Blueprint, request, jsonify
from models import db, Log, agregar_mensajes_log, Mensaje
from flujos import manejar_boton, manejar_texto, manejar_archivo
from config import TOKEN_ANDERCODE
import json
import traceback

webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return verificar_token(request)
    elif request.method == 'POST':
        return recibir_mensaje(request)

def verificar_token(req):
    token = req.args.get('hub.verify_token')
    challenge = req.args.get('hub.challenge')
    if challenge and token == TOKEN_ANDERCODE:
        return challenge
    return jsonify({'error': 'Token invalido'}), 401

def recibir_mensaje(req):
    try:
        data = req.get_json()
        

        entry = data.get('entry', [])
        if not entry:
            return jsonify({'message': 'EVENT_RECEIVED'})

        changes = entry[0].get('changes', [])
        if not changes:
            return jsonify({'message': 'EVENT_RECEIVED'})

        value = changes[0].get('value', {})
        objeto_messages = value.get('messages', [])

        if objeto_messages:
            mensaje = objeto_messages[0]
            numero = mensaje['from']
            tipo = mensaje.get('type')
        if objeto_messages:
            mensaje = objeto_messages[0]
            numero = mensaje['from']
            tipo = mensaje.get('type')
            agregar_mensajes_log(f"TIPO_MENSAJE | {numero} | {tipo}")  # ← agrega aquí
            if tipo == 'interactive':
                tipo_interactive = mensaje.get('interactive', {}).get('type', '')
                if tipo_interactive == 'list_reply':
                    opcion_id = mensaje.get('interactive', {}).get('list_reply', {}).get('id', '')
                    titulo = mensaje.get('interactive', {}).get('list_reply', {}).get('title', '')
                else:
                    opcion_id = mensaje.get('interactive', {}).get('button_reply', {}).get('id', '')
                    titulo = mensaje.get('interactive', {}).get('button_reply', {}).get('title', '')

                agregar_mensajes_log(f"Boton presionado | {numero} | {titulo}")
                db.session.add(Mensaje(numero_whatsapp=numero, origen='cliente', texto=titulo, leido_asesor=False))
                db.session.commit()
                manejar_boton(numero, opcion_id)

            elif tipo == 'text':
                texto = mensaje['text']['body']
                nombre = objeto_messages[0].get('from', '')
               # obtener nombre del contacto
                contactos = value.get('contacts', [])
                nombre = contactos[0].get('profile', {}).get('name', 'Desconocido') if contactos else 'Desconocido'
               # log limpio
                agregar_mensajes_log(f"Mensaje | {nombre} | {numero} | {texto}")
                db.session.add(Mensaje(numero_whatsapp=numero, origen='cliente', texto=texto, leido_asesor=False))
                db.session.commit()
                manejar_texto(numero, texto)

            elif tipo in ['image', 'document', 'audio', 'video']:
                media = mensaje.get(tipo, {})
                media_id = media.get('id', '')
                tipo_mime = media.get('mime_type', tipo)
                agregar_mensajes_log(f"Archivo recibido | {numero} | Tipo: {tipo_mime} | Media ID: {media_id}")
                db.session.add(Mensaje(numero_whatsapp=numero, origen='cliente', texto=f'[Archivo] {tipo_mime} | {media_id}', leido_asesor=False))
                db.session.commit()
                manejar_archivo(numero, media_id, tipo_mime)
               

        return jsonify({'message': 'EVENT_RECEIVED'})
    except Exception as e:
        agregar_mensajes_log(f"ERROR WEBHOOK | {str(e)} | {traceback.format_exc()}")
        return jsonify({'message': 'EVENT_RECEIVED'})