from datetime import date

from flask import Blueprint, jsonify, render_template, request, redirect, url_for, session
from config import get_config_horario
from models import Cita, ConfigHorario, DiasBloqueados, Paciente, db, Asesor, Auditoria, ExamenConfig
from functools import wraps

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
        usuario  = request.form.get('usuario')
        password = request.form.get('password')

        # Admin tiene un usuario especial con rol='admin' en la tabla Asesor
        admin = Asesor.query.filter_by(usuario=usuario, rol='admin').first()

        if admin and admin.check_password(password):
            session['admin_id']     = admin.id
            session['admin_nombre'] = admin.nombre
            return redirect(url_for('admin.panel'))

        error = "Credenciales incorrectas"

    return render_template('admin_login.html', error=error)


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
        Asesor.rol.in_(['micologia', 'bacteriologia'])
    ).order_by(Asesor.nombre).all()

    config = get_config_horario()

    return render_template('admin.html',
        asesores=asesores,
        especialistas=especialistas,
        admin_nombre=session.get('admin_nombre'),
        horario_inicio=config.horario_inicio,
        horario_fin=config.horario_fin,
        dias_activos=[int(d) for d in config.dias_activos.split(',')],
        dias_bloqueados=DiasBloqueados.query.order_by(DiasBloqueados.fecha).all(),
        configs=ExamenConfig.query.order_by(ExamenConfig.examen_id).all(),  # ← esta línea
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

        if rol not in ('micologia', 'bacteriologia'):
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
        if asesor.rol in ('micologia', 'bacteriologia'):
            nuevo_rol = request.form.get('rol', '').strip()
            if nuevo_rol in ('micologia', 'bacteriologia'):
                asesor.rol = nuevo_rol

        password = request.form.get('password', '').strip()
        if password:
            asesor.set_password(password)

        db.session.commit()
        return redirect(url_for('admin.panel'))

    # Reutilizar el form correcto según el rol
    template = (
        'admin_form_especialista.html'
        if asesor.rol in ('micologia', 'bacteriologia')
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

    db.session.commit()
    return jsonify({'ok': True})