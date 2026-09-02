from datetime import date, datetime
import os

from flask import Blueprint, jsonify, render_template, request, redirect, url_for, session
from config import get_config_horario
from dotenv import load_dotenv
from models import BloqueoAgendaFecha, Cita, ConfigHorario, DiasBloqueados, DiasPermitidosTipoCita, HorarioAsesor, Paciente, db, Asesor, Auditoria, ExamenConfig, seed_examen_config
from functools import wraps
from recaptcha import verificar_recaptcha
load_dotenv(".env")
RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY")
admin_bp = Blueprint('admin', __name__)


# =====================================================
# LOGIN REQUERIDO ADMIN
# =====================================================
def admin_requerido(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_id'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated


# =====================================================
# LOGIN
# =====================================================
@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        # Verificar reCAPTCHA primero
        token = request.form.get('g-recaptcha-response')
        if not verificar_recaptcha(token):
            error = "Verificación de seguridad fallida. Intenta de nuevo."
            return render_template('admin_login.html', error=error,
                                   site_key=RECAPTCHA_SITE_KEY)

        usuario  = request.form.get('usuario')
        password = request.form.get('password')
        admin = Asesor.query.filter_by(usuario=usuario, rol='admin').first()

        if admin and admin.check_password(password):
            session['admin_id']     = admin.id
            session['admin_nombre'] = admin.nombre
            return redirect(url_for('admin.panel'))

        error = "Credenciales incorrectas"

    return render_template('admin_login.html', error=error,
                           site_key=RECAPTCHA_SITE_KEY)


@admin_bp.route('/admin/logout')
def logout():
    session.pop('admin_id', None)
    session.pop('admin_nombre', None)
    return redirect(url_for('admin.login'))


# =====================================================
# PANEL — lista de asesores
# =====================================================
@admin_bp.route('/admin')
@admin_requerido
def panel():
    asesores = Asesor.query.filter_by(rol='asesor').order_by(Asesor.nombre).all()
    especialistas = Asesor.query.filter(
        Asesor.rol.in_(['micologia', 'bacteriologia', 'domicilio'])
    ).order_by(Asesor.nombre).all()

    config = get_config_horario()

    return render_template('admin.html',
        asesores=asesores,
        especialistas=especialistas,
        admin_nombre=session.get('admin_nombre'),
    )

@admin_bp.context_processor
def inject_admin_globals():
    config = get_config_horario()
    return dict(
        horario_inicio=config.horario_inicio,
        horario_fin=config.horario_fin,
        dias_activos=[int(d) for d in config.dias_activos.split(',')],
        dias_bloqueados=DiasBloqueados.query.order_by(DiasBloqueados.fecha).all(),
        configs=ExamenConfig.query.order_by(ExamenConfig.examen_id).all(),
    )

# =====================================================
# CREAR ASESOR
# =====================================================
@admin_bp.route('/admin/nuevo', methods=['GET', 'POST'])
@admin_requerido
def nuevo_asesor():
    error = None

    if request.method == 'POST':
        nombre   = request.form['nombre'].strip()
        usuario  = request.form['usuario'].strip()
        password = request.form['password'].strip()

        if Asesor.query.filter_by(usuario=usuario).first():
            error = "Ya existe un asesor con ese usuario."
        else:
            asesor = Asesor(
                nombre=nombre,
                usuario=usuario,
                rol='asesor',
                activo=True
            )
            asesor.set_password(password)
            db.session.add(asesor)
            db.session.commit()
            return redirect(url_for('admin.panel'))

    return render_template('admin_form_asesor.html',
        asesor=None,
        error=error,
        admin_nombre=session.get('admin_nombre')
    )

# =====================================================
# CREAR ESPECIALISTA (micología / bacteriología)
# =====================================================
@admin_bp.route('/admin/nuevo-especialista', methods=['GET', 'POST'])
@admin_requerido
def nuevo_especialista():
    error = None
    if request.method == 'POST':
        nombre   = request.form['nombre'].strip()
        usuario  = request.form['usuario'].strip()
        password = request.form['password'].strip()
        rol      = request.form['rol'].strip()   # 'micologia' o 'bacteriologia'

        if rol not in ('micologia', 'bacteriologia', 'domicilio'):
            error = "Rol inválido."
        elif Asesor.query.filter_by(usuario=usuario).first():
            error = "Ya existe un usuario con ese nombre."
        else:
            esp = Asesor(nombre=nombre, usuario=usuario, rol=rol, activo=True)
            esp.set_password(password)
            db.session.add(esp)
            db.session.commit()
            return redirect(url_for('admin.panel'))

    return render_template('admin_form_especialista.html',
        error=error,
        admin_nombre=session.get('admin_nombre')
    )

# =====================================================
# EDITAR ASESOR — ahora soporta cualquier rol
# =====================================================
@admin_bp.route('/admin/editar/<int:asesor_id>', methods=['GET', 'POST'])
@admin_requerido
def editar_asesor(asesor_id):
    asesor = Asesor.query.get_or_404(asesor_id)
    error  = None

    if request.method == 'POST':
        asesor.nombre  = request.form['nombre'].strip()
        asesor.usuario = request.form['usuario'].strip()

        # Si es especialista, el admin puede cambiar el rol
        if asesor.rol in ('micologia', 'bacteriologia', 'domicilio'):
            nuevo_rol = request.form.get('rol', '').strip()
            if nuevo_rol in ('micologia', 'bacteriologia', 'domicilio'):
                asesor.rol = nuevo_rol

        password = request.form.get('password', '').strip()
        if password:
            asesor.set_password(password)

        db.session.commit()
        return redirect(url_for('admin.panel'))

    # Reutilizar el form correcto según el rol
    template = (
        'admin_form_especialista.html'
        if asesor.rol in ('micologia', 'bacteriologia', 'domicilio')
        else 'admin_form_asesor.html'
    )

    return render_template(template,
        asesor=asesor, error=error,
        admin_nombre=session.get('admin_nombre')
    )


# =====================================================
# ACTIVAR / DESACTIVAR ASESOR
# =====================================================
@admin_bp.route('/admin/toggle/<int:asesor_id>')
@admin_requerido
def toggle_asesor(asesor_id):
    asesor = Asesor.query.get_or_404(asesor_id)
    asesor.activo = not asesor.activo
    db.session.commit()
    return redirect(url_for('admin.panel'))


# =====================================================
# ELIMINAR ASESOR
# =====================================================
@admin_bp.route('/admin/eliminar/<int:asesor_id>')
@admin_requerido
def eliminar_asesor(asesor_id):
    asesor = Asesor.query.get_or_404(asesor_id)
    db.session.delete(asesor)
    db.session.commit()
    return redirect(url_for('admin.panel'))


# =====================================================
# HISTORIAL DE UN ASESOR
# =====================================================
@admin_bp.route('/admin/historial/<int:asesor_id>')
@admin_requerido
def historial_asesor(asesor_id):
    asesor = Asesor.query.get_or_404(asesor_id)
    logs   = Auditoria.query.filter_by(asesor_id=asesor_id)\
                            .order_by(Auditoria.fecha.desc()).all()

    return render_template('admin_historial.html',
        asesor=asesor,
        logs=logs,
        admin_nombre=session.get('admin_nombre')
    )

@admin_bp.route('/admin/nuevo-admin', methods=['GET', 'POST'])
@admin_requerido
def nuevo_admin():

    if request.method == 'POST':

        nombre = request.form.get('nombre')
        usuario = request.form.get('usuario')
        password = request.form.get('password')

        existe = Asesor.query.filter_by(
            usuario=usuario
        ).first()

        if existe:
            return render_template(
                'nuevo_admin.html',
                error='El usuario ya existe'
            )

        admin = Asesor(
            nombre=nombre,
            usuario=usuario,
            rol='admin',
            activo=True
        )

        admin.set_password(password)

        db.session.add(admin)
        db.session.commit()

        return redirect(url_for('admin.panel'))

    return render_template('nuevo_admin.html')

# ==========================================
# LISTADO ADMINS
# ==========================================

@admin_bp.route('/admin/admins')
@admin_requerido
def lista_admins():

    admins = Asesor.query.filter_by(
        rol='admin'
    ).order_by(
        Asesor.creado_en.desc()
    ).all()

    return render_template(
        'admins.html',
        admins=admins,
        admin_nombre=session.get('admin_nombre')
    )

# ==========================================
# ELIMINAR ADMIN
# ==========================================

@admin_bp.route('/admin/eliminar-admin/<int:admin_id>')
@admin_requerido
def eliminar_admin(admin_id):

    admin = Asesor.query.filter_by(
        id=admin_id,
        rol='admin'
    ).first()

    if admin:
        db.session.delete(admin)
        db.session.commit()

    return redirect(
        url_for('admin.lista_admins')
    )


@admin_bp.route('/admin/horario', methods=['POST'])
@admin_requerido
def actualizar_horario():
    data = request.get_json(silent=True) or {}

    config = get_config_horario()  # garantiza que existe en BD

    # Actualizar con query directa — evita problemas de tracking
    updates = {}

    if 'horario_inicio' in data:
        updates['horario_inicio'] = int(data['horario_inicio'])
    if 'horario_fin' in data:
        updates['horario_fin'] = int(data['horario_fin'])
    if 'dias_activos' in data:
        dias = sorted([int(d) for d in data['dias_activos']])
        updates['dias_activos'] = ','.join(str(d) for d in dias)

    if updates:
        ConfigHorario.query.filter_by(id=config.id).update(updates)

    # Días bloqueados
    if 'dias_bloqueados' in data:
        DiasBloqueados.query.delete()
        for item in data['dias_bloqueados']:
            if item.get('fecha'):
                db.session.add(DiasBloqueados(
                    fecha=date.fromisoformat(item['fecha']),
                    motivo=item.get('motivo', '')
                ))

    db.session.commit()
    return jsonify({'ok': True})




@admin_bp.route('/admin/examenes')
@admin_requerido
def config_examenes():
    seed_examen_config()         
    db.session.commit()           
    configs = ExamenConfig.query.order_by(ExamenConfig.examen_id).all()
    return render_template(
        'admin_examenes.html',
        configs=configs,
        admin_nombre=session.get('admin_nombre')
    )

@admin_bp.route('/admin/examenes/guardar', methods=['POST'])
@admin_requerido
def guardar_config_examenes():
    data = request.get_json(silent=True) or {}

    for item in data.get('examenes', []):
        eid = item.get('examen_id')
        if not eid:
            continue
        cfg = ExamenConfig.query.filter_by(examen_id=eid).first()
        if not cfg:
            cfg = ExamenConfig(examen_id=eid)
            db.session.add(cfg)

        dias = sorted(set(int(d) for d in item.get('dias', []) if 0 <= int(d) <= 4))
        cfg.dias_permitidos  = ','.join(str(d) for d in dias) if dias else "1,2,3,4"
        cfg.min_anticipacion = max(1, int(item.get('min_anticipacion', 2)))
        cfg.max_por_dia      = max(0, int(item.get('max_por_dia', 0)))
        cfg.hora_inicio      = item.get('hora_inicio', '07:30')  # ← nuevo
        cfg.hora_fin         = item.get('hora_fin', '15:30')     # ← nue
    db.session.commit()
    return jsonify({'ok': True})

#nuevos endpoints para administrar la disponibilidad de citas

@admin_bp.route('/admin/horario-asesor', methods=['GET'])
@admin_requerido
def config_horario_asesor():
    horarios = HorarioAsesor.query.all()
    horarios_json = [
        {'agenda_tipo': h.agenda_tipo, 'dia_semana': h.dia_semana,
         'activo': h.activo, 'hora_inicio': h.hora_inicio, 'hora_fin': h.hora_fin}
        for h in horarios
    ]
    return render_template('horario_asesor.html', horarios=horarios_json)


@admin_bp.route('/admin/dias-tipo-cita', methods=['GET'])
@admin_requerido
def config_dias_tipo_cita():
    reglas = DiasPermitidosTipoCita.query.all()
    reglas_json = [{'tipo_cita': r.tipo_cita, 'dias_semana': r.dias_semana} for r in reglas]
    return render_template('dias_tipo_cita.html', reglas=reglas_json)


@admin_bp.route('/admin/horario-asesor/guardar', methods=['POST'])
@admin_requerido
def guardar_horario_asesor():
    data = request.get_json(silent=True) or {}
    for item in data.get('horarios', []):
        h = HorarioAsesor.query.filter_by(
            agenda_tipo=item['agenda_tipo'], dia_semana=int(item['dia_semana'])
        ).first()
        if not h:
            h = HorarioAsesor(agenda_tipo=item['agenda_tipo'], dia_semana=int(item['dia_semana']))
            db.session.add(h)
        h.activo = bool(item.get('activo', True))
        h.hora_inicio = item.get('hora_inicio')
        h.hora_fin = item.get('hora_fin')
    db.session.commit()
    return jsonify({'ok': True})


@admin_bp.route('/admin/dias-tipo-cita/guardar', methods=['POST'])
@admin_requerido
def guardar_dias_tipo_cita():
    data = request.get_json(silent=True) or {}
    for item in data.get('reglas', []):
        r = DiasPermitidosTipoCita.query.filter_by(tipo_cita=item['tipo_cita']).first()
        if not r:
            r = DiasPermitidosTipoCita(tipo_cita=item['tipo_cita'])
            db.session.add(r)
        dias = sorted(set(int(d) for d in item.get('dias', [])))
        r.dias_semana = ','.join(str(d) for d in dias)
    db.session.commit()
    return jsonify({'ok': True})


@admin_bp.route('/admin/bloqueo-fecha', methods=['GET'])
@admin_requerido
def listar_bloqueos_fecha():
    bloqueos = BloqueoAgendaFecha.query.order_by(BloqueoAgendaFecha.fecha.desc()).all()
    return render_template('bloqueo_fecha.html', bloqueos=bloqueos)


@admin_bp.route('/admin/bloqueo-fecha/crear', methods=['POST'])
@admin_requerido
def crear_bloqueo_fecha():
    data = request.get_json(silent=True) or {}

    tipo_bloqueo = data.get('tipo_bloqueo')
    if tipo_bloqueo not in ('dia_completo', 'rango_horas', 'cupo_maximo'):
        return jsonify({'ok': False, 'error': 'tipo_bloqueo inválido'}), 400

    if not data.get('fecha'):
        return jsonify({'ok': False, 'error': 'fecha es requerida'}), 400

    if not data.get('motivo'):
        return jsonify({'ok': False, 'error': 'motivo es requerido'}), 400

    tipo_cita = data.get('tipo_cita') or None
    if tipo_cita is not None and tipo_cita not in ('domicilio', 'presencial'):
        return jsonify({'ok': False, 'error': 'tipo_cita inválido'}), 400

    hora_inicio = data.get('hora_inicio')
    hora_fin = data.get('hora_fin')
    max_citas_dia = data.get('max_citas_dia')

    if tipo_bloqueo == 'rango_horas':
        if not hora_inicio or not hora_fin:
            return jsonify({'ok': False, 'error': 'hora_inicio y hora_fin son requeridas para rango_horas'}), 400
        try:
            h_ini = datetime.strptime(hora_inicio, "%H:%M").time()
            h_fin = datetime.strptime(hora_fin, "%H:%M").time()
        except ValueError:
            return jsonify({'ok': False, 'error': 'formato de hora inválido, use HH:MM'}), 400
        if h_ini >= h_fin:
            return jsonify({'ok': False, 'error': 'hora_inicio debe ser menor que hora_fin'}), 400
        # no aplican a este tipo, se descartan aunque vengan en el payload
        max_citas_dia = None

    elif tipo_bloqueo == 'cupo_maximo':
        if max_citas_dia is None:
            return jsonify({'ok': False, 'error': 'max_citas_dia es requerido para cupo_maximo'}), 400
        try:
            max_citas_dia = int(max_citas_dia)
        except (TypeError, ValueError):
            return jsonify({'ok': False, 'error': 'max_citas_dia debe ser un número entero'}), 400
        if max_citas_dia < 0:
            return jsonify({'ok': False, 'error': 'max_citas_dia no puede ser negativo'}), 400
        # no aplican a este tipo, se descartan aunque vengan en el payload
        hora_inicio = None
        hora_fin = None

    else:  # dia_completo
        # no aplican a este tipo, se descartan aunque vengan en el payload
        hora_inicio = None
        hora_fin = None
        max_citas_dia = None

    try:
        fecha_obj = date.fromisoformat(data['fecha'])
    except ValueError:
        return jsonify({'ok': False, 'error': 'formato de fecha inválido, use YYYY-MM-DD'}), 400

    b = BloqueoAgendaFecha(
        fecha=fecha_obj,
        tipo_bloqueo=tipo_bloqueo,
        tipo_cita=tipo_cita,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        max_citas_dia=max_citas_dia,
        motivo=data['motivo'],
    )
    db.session.add(b)
    db.session.commit()
    return jsonify({'ok': True, 'id': b.id})

@admin_bp.route('/admin/bloqueo-fecha/<int:bloqueo_id>/eliminar', methods=['POST'])
@admin_requerido
def eliminar_bloqueo_fecha(bloqueo_id):
    BloqueoAgendaFecha.query.filter_by(id=bloqueo_id).delete()
    db.session.commit()
    return jsonify({'ok': True})