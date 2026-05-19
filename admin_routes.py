from flask import Blueprint, render_template, request, redirect, url_for, session
from models import db, Asesor, Auditoria
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
    asesores      = Asesor.query.filter_by(rol='asesor').order_by(Asesor.nombre).all()
    especialistas = Asesor.query.filter(
        Asesor.rol.in_(['micologia', 'bacteriologia'])
    ).order_by(Asesor.nombre).all()

    return render_template('admin.html',
        asesores=asesores,
        especialistas=especialistas,
        admin_nombre=session.get('admin_nombre')
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