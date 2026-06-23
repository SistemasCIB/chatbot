from flask import Flask, render_template, send_from_directory, redirect, url_for
from models import db, Log, Cita, Consentimiento, Asesor, seed_examen_config
from scheduler import iniciar_scheduler
from webhook import webhook_bp
from asesor import asesor_bp
from config import SECRET_KEY, TOKEN_META
from datetime import datetime, time
from admin_routes import admin_bp, admin_requerido
import os
import requests as req_lib
from flask_sqlalchemy import SQLAlchemy
from flask import Response, stream_with_context
from admin_routes import admin_requerido

from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

#----------------------------------------------------
# Conexión a base de datos
#----------------------------------------------------

database_url = os.environ.get('DATABASE_URL', 'sqlite:///cib.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = SECRET_KEY

db.init_app(app)
app.register_blueprint(webhook_bp)
app.register_blueprint(asesor_bp)
app.register_blueprint(admin_bp)

with app.app_context():
    db.create_all()

    # Asesor por defecto
    if not Asesor.query.filter_by(usuario='test').first():
        asesor = Asesor(usuario='test', nombre='asesor test')
        asesor.set_password('cib2025')
        db.session.add(asesor)
        db.session.commit()
        print("Asesor creado: test / cib2025")

    # Config exámenes por defecto
    seed_examen_config()
    db.session.commit()


@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()

def ordenar_registros_por_fecha(registros):
    return sorted(registros, key=lambda x: x.fecha_y_hora, reverse=True)

#log de eventos y errores importantes para monitoreo 
@app.route('/')
@admin_requerido  
def index():
    registros = ordenar_registros_por_fecha(Log.query.all())
    citas = Cita.query.order_by(Cita.creada_en.desc()).all()
    consentimientos = Consentimiento.query.order_by(Consentimiento.fecha.desc()).all()
    return render_template('index.html',
        registros=registros,
        citas=citas,
        consentimientos=consentimientos
    )

@app.route('/politica')
def politica():
    return send_from_directory('static', 'politica_datos.pdf')


@app.route('/asesor/orden/<int:cita_id>')
def ver_orden(cita_id):

    cita = Cita.query.get_or_404(cita_id)

    if not cita.orden_medica:
        return "Esta cita no tiene orden médica.", 404

    ruta_local = os.path.join(
        app.root_path, 'static', 'uploads', cita.orden_medica
    )

    # Si existe localmente → sirve directo
    if os.path.exists(ruta_local):
        return redirect(
            url_for('static', filename='uploads/' + cita.orden_medica)
        )

    # Si es media_id de Meta → descargar con token y servir
    headers = {"Authorization": f"Bearer {TOKEN_META}"}

    r = req_lib.get(
        f"https://graph.facebook.com/v25.0/{cita.orden_medica}",
        headers=headers
    )

    if r.status_code != 200:
        return f"Error consultando archivo a Meta: {r.text}", 500

    url_archivo = r.json().get("url")

    if not url_archivo:
        return "No se pudo obtener la URL del archivo.", 500

    #  Descargar con token y devolver al navegador — NO hacer redirect
    archivo = req_lib.get(url_archivo, headers=headers)

    from flask import Response
    tipo_mime = cita.orden_tipo_archivo or "application/octet-stream"

    return Response(
        archivo.content,
        mimetype=tipo_mime,
        headers={
            "Content-Disposition": f"inline; filename=orden_{cita_id}"
        }
    )


@app.route("/api/citas-count")
def citas_count():
    total = Cita.query.count()
    return {"total": total}

#@app.route('/test-recordatorio')
#def test_recordatorio():
#    from scheduler import verificar_recordatorios_manual
#    verificar_recordatorios_manual(app)
#    return "Recordatorios enviados, revisa la consola"

iniciar_scheduler(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)