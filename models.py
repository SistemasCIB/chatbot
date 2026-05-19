from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha_y_hora = db.Column(db.DateTime, default=datetime.utcnow)
    texto = db.Column(db.TEXT)

class Paciente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo_documento = db.Column(db.String(20))
    documento = db.Column(db.String(50), unique=True, index=True)
    nombre = db.Column(db.String(100))
    telefono = db.Column(db.String(20))
    correo = db.Column(db.String(100))
    numero_whatsapp = db.Column(db.String(20))
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    citas = db.relationship('Cita', backref='paciente', lazy=True)

class Cita(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'))  
    tipo_cita = db.Column(db.String(20))
    direccion_domicilio = db.Column(db.String(300))
    orden_medica = db.Column(db.String(500))
    orden_tipo_archivo = db.Column(db.String(50))
    cobertura = db.Column(db.String(50))
    aseguradora = db.Column(db.String(100))
    tipo_examen = db.Column(db.String(300))
    area = db.Column(db.String(50), nullable=True)
    tipo_muestra = db.Column(db.String(50))
    fecha_cita = db.Column(db.DateTime)
    hora_cita = db.Column(db.String(20),nullable=True)
    agenda_tipo = db.Column(db.String(50), default='')
    numero_whatsapp = db.Column(db.String(20))
    estado = db.Column(db.String(20), default='pendiente')
    creada_en = db.Column(db.DateTime, default=datetime.utcnow)
    outlook_event_id = db.Column(db.String(255))

class Consentimiento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_whatsapp = db.Column(db.String(20))
    acepto = db.Column(db.Boolean)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

class Asesor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(50), unique=True)
    nombre = db.Column(db.String(100))
    password_hash = db.Column(db.Text, nullable=False)
    rol = db.Column(db.String(20), default='asesor')        # ← nuevo
    activo = db.Column(db.Boolean, default=True)            # ← nuevo
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

def agregar_mensajes_log(texto):
    try:
        nuevo_registro = Log(texto=str(texto))
        db.session.add(nuevo_registro)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error log: {str(e)}")

class Admin(db.Model):

    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)

    nombre = db.Column(db.String(100), nullable=False)

    usuario = db.Column(db.String(50), unique=True, nullable=False)

    correo = db.Column(db.String(120), unique=True)

    password_hash = db.Column(db.String(255), nullable=False)

    activo = db.Column(db.Boolean, default=True)

    creado_en = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # =====================================
    # PASSWORD
    # =====================================

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password
        )        

class Conversacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_whatsapp = db.Column(db.String(20), unique=True)
    modo = db.Column(db.String(20), default='bot')   # bot / humano
    vence_humano = db.Column(db.DateTime, nullable=True)
    actualizada = db.Column(db.DateTime, default=datetime.utcnow)


class Auditoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asesor_id = db.Column(db.Integer)
    asesor_nombre = db.Column(db.String(100))
    accion = db.Column(db.String(50))
    cita_id = db.Column(db.Integer, nullable=True)
    detalle = db.Column(db.Text)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)        

class ChatActivo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True)
    asesor_id = db.Column(db.Integer)
    asesor_nombre = db.Column(db.String(100))
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    vence_en = db.Column(db.DateTime)