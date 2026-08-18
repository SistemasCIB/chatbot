import os

from flask import Blueprint, request, jsonify
from dotenv import load_dotenv
from models import db, Log, agregar_mensajes_log, Mensaje
from flujos import manejar_boton, manejar_texto, manejar_archivo
import json
load_dotenv(".env")

TOKEN_ANDERCODE = os.getenv("TOKEN_ANDERCODE")

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
    data = None
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

        if not objeto_messages:
            # Puede ser un status update (delivered/read/sent/failed) u otro evento, se ignora
            return jsonify({'message': 'EVENT_RECEIVED'})

        mensaje = objeto_messages[0]
        numero = mensaje.get('from')
        tipo = mensaje.get('type')

        if not numero:
            agregar_mensajes_log(f"Mensaje sin 'from' ignorado | payload: {json.dumps(mensaje)}")
            return jsonify({'message': 'EVENT_RECEIVED'})

        agregar_mensajes_log(f"TIPO_MENSAJE | {numero} | {tipo}")

        if tipo == 'interactive':
            interactive = mensaje.get('interactive', {})
            tipo_interactive = interactive.get('type', '')
            if tipo_interactive == 'list_reply':
                opcion_id = interactive.get('list_reply', {}).get('id', '')
                titulo = interactive.get('list_reply', {}).get('title', '')
            else:
                opcion_id = interactive.get('button_reply', {}).get('id', '')
                titulo = interactive.get('button_reply', {}).get('title', '')

            agregar_mensajes_log(f"Boton presionado | {numero} | {titulo}")
            db.session.add(Mensaje(numero_whatsapp=numero, origen='cliente', texto=titulo, leido_asesor=False))
            db.session.commit()
            manejar_boton(numero, opcion_id)

        elif tipo == 'text':
            texto = mensaje.get('text', {}).get('body', '')

            contactos = value.get('contacts', [])
            nombre = contactos[0].get('profile', {}).get('name', 'Desconocido') if contactos else 'Desconocido'

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
        payload_str = json.dumps(data) if data else 'sin payload'
        agregar_mensajes_log(f"Error: {str(e)} | payload: {payload_str}")
        return jsonify({'message': 'EVENT_RECEIVED'})