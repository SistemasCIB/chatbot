from functools import wraps

from flask import Blueprint, flash, render_template, request, redirect, url_for, session, jsonify
from models import DiasBloqueados, db, Cita, Asesor, Auditoria, ChatActivo, Paciente, Mensaje, agregar_mensajes_log
from datetime import date, datetime, timedelta
from mensajes import enviar_texto
from config import HORARIO_INICIO, HORARIO_FIN,  get_config_horario
import io, csv, os
from flask import Response
from werkzeug.utils import secure_filename
from recaptcha import verificar_recaptcha
from services.outlook import crear_evento_outlook, eliminar_evento_outlook, listar_eventos_outlook
from recaptcha import verificar_recaptcha

from dotenv import load_dotenv
load_dotenv(".env")
RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY")
asesor_bp = Blueprint('asesor', __name__)


@asesor_bp.route('/asesor/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Verificar reCAPTCHA primero
        token = request.form.get('g-recaptcha-response')
        if not verificar_recaptcha(token):
            return render_template('login.html',
                                   error='Verificación de seguridad fallida.',
                                   site_key=RECAPTCHA_SITE_KEY)

        usuario  = request.form.get('usuario', '').strip()
        password = request.form.get('password', '').strip()
        asesor = Asesor.query.filter_by(usuario=usuario, activo=True).first()

        if asesor and asesor.check_password(password):
            session['asesor_id']     = asesor.id
            session['asesor_nombre'] = asesor.nombre
            session['asesor_rol']    = asesor.rol

            if asesor.rol == 'micologia':
                return redirect(url_for('asesor.calendario_micologia'))
            elif asesor.rol == 'bacteriologia':
                return redirect(url_for('asesor.calendario_bacteriologia'))
            else:
                return redirect(url_for('asesor.panel'))

        return render_template('login.html',
                               error='Usuario o contraseña incorrectos',
                               site_key=RECAPTCHA_SITE_KEY)

    return render_template('login.html', site_key=RECAPTCHA_SITE_KEY)

def login_requerido(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('asesor_id'):
            return redirect(url_for('asesor.login'))
        asesor = Asesor.query.get(session.get('asesor_id'))
        if not asesor or not asesor.activo:
            session.clear()
            return redirect(url_for('asesor.login'))

        return f(*args, **kwargs)
    
    return decorated

def rol_requerido(*roles_permitidos):
    """Uso: @rol_requerido('asesor', 'micologia')"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'asesor_id' not in session:
                return redirect(url_for('asesor.login'))
            rol_actual = session.get('asesor_rol', 'asesor')
            if rol_actual not in roles_permitidos:
                return render_template('sin_permiso.html'), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

@asesor_bp.route('/asesor')
@login_requerido
def panel():
    documento = request.args.get('documento', '').strip()
    query = Cita.query.join(Paciente)

    if documento:
        query = query.filter(Paciente.documento.ilike(f"%{documento}%"))

    citas = query.order_by(Cita.creada_en.desc()).all()
    config = get_config_horario()

    chats_activos = {chat.numero for chat in ChatActivo.query.filter_by(activo=True).all()}
    for cita in citas:

        cita.chat_activo = cita.numero_whatsapp in chats_activos

        cita.total_mensajes = Mensaje.query.filter_by(
            numero_whatsapp=cita.numero_whatsapp
        ).count()

        cita.mensajes_nuevos = Mensaje.query.filter_by(
            numero_whatsapp=cita.numero_whatsapp,
            origen='cliente',
            leido_asesor=False
        ).count()
        
    return render_template(
        'asesor.html',
        citas=citas,
        asesor_nombre=session.get('asesor_nombre'),
        documento_filtro=documento
    )



@asesor_bp.route('/asesor/horario', methods=['POST'])
@login_requerido
def actualizar_horario():
    data = request.get_json(silent=True) or {}

    config = get_config_horario()

    # Horas
    if 'horario_inicio' in data:
        config.horario_inicio = int(data['horario_inicio'])
    if 'horario_fin' in data:
        config.horario_fin = int(data['horario_fin'])

    # Días activos — opcional, si no viene no se toca
    if 'dias_activos' in data:
        dias = [int(d) for d in data['dias_activos']]
        config.dias_activos = ','.join(str(d) for d in sorted(dias))

    # Días bloqueados — opcional
    if 'dias_bloqueados' in data:
        DiasBloqueados.query.delete()
        for item in data['dias_bloqueados']:
            db.session.add(DiasBloqueados(
                fecha=date.fromisoformat(item['fecha']),
                motivo=item.get('motivo', '')
            ))

    db.session.commit()
    return jsonify({'ok': True})

@asesor_bp.route('/asesor/confirmar/<int:cita_id>')
@login_requerido
def confirmar_cita(cita_id):
    cita = Cita.query.get(cita_id)
    if cita:
        cita.estado = 'confirmada'

        # Crear evento en Outlook solo si no existe aún
        if not cita.outlook_event_id:
            try:
                event_id = crear_evento_outlook(cita)   # retorna el ID directamente
                cita.outlook_event_id = event_id
            except Exception as e:
                print(f"[Outlook] Error creando evento: {e}")
                # No bloquea la confirmación si Outlook falla

        db.session.commit()

        log = Auditoria(
            asesor_id=session['asesor_id'],
            asesor_nombre=session['asesor_nombre'],
            accion='confirmo',
            cita_id=cita.id,
            detalle=f'Confirmó cita de {cita.paciente.documento} - {cita.paciente.nombre}'
        )
        db.session.add(log)
        db.session.commit()

        enviar_texto(cita.numero_whatsapp,
            f"✅ Cita confirmada\n\n"
            f"Hola {cita.paciente.nombre}\n"
            f"Hemos recibido y verificado toda tu información.\n"
            f"Tu cita ha sido confirmada y programada de la siguiente manera:\n"
            f"Modalidad: {cita.tipo_cita.capitalize()}\n"
            f"Fecha: {cita.fecha_cita}\n"
            f"Hora: {cita.hora_cita}\n\n"
            f"📌 Por favor ten en cuenta:\n"
            f"• Presentar tu documento de identidad\n"
            f"• Traer la orden médica (si aplica)\n"
            f"• Llegar 15 minutos antes de la cita\n\n"
            f"⚠️ Muy importante:\n"
            f"Debes cumplir con todos los requisitos del examen.\n\n"
            f"De lo contrario, no será posible tomar la muestra y deberás reagendar tu cita.\n\n"
            f"Te esperamos y agradecemos por confiar en nosotros 💙"
        )
    return redirect(url_for('asesor.panel'))


@asesor_bp.route('/asesor/rechazar/<int:cita_id>')
@login_requerido
def rechazar_cita(cita_id):
    cita = Cita.query.get(cita_id)
    if cita:
        # Eliminar evento de Outlook si existe
        if cita.outlook_event_id:
            try:
                eliminar_evento_outlook(cita.outlook_event_id)
                cita.outlook_event_id = None
            except Exception as e:
                print(f"[Outlook] Error eliminando evento: {e}")

        cita.estado = 'rechazada'
        db.session.commit()

        log = Auditoria(
            asesor_id=session['asesor_id'],
            asesor_nombre=session['asesor_nombre'],
            accion='rechazo',
            cita_id=cita.id,
            detalle=f'Rechazó cita de {cita.paciente.documento} - {cita.paciente.nombre}'
        )
        db.session.add(log)
        db.session.commit()

        enviar_texto(cita.numero_whatsapp,
            f"👋 Gracias por comunicarte con nosotros.\n\n"
            f"En este momento no fue posible continuar con tu solicitud de cita.\n\n"
            f"Si más adelante deseas retomarla o completar la información, estaremos atentos para ayudarte por este medio\n\n"
            f"¡Que tengas un buen día! 💙"
        )
    return redirect(url_for('asesor.panel'))

# ==========================================
# CITA CUMPLIDA
# ==========================================

@asesor_bp.route('/asesor/cumplida/<int:cita_id>')
@login_requerido
def marcar_cumplida(cita_id):

    cita = Cita.query.get(cita_id)

    if cita:

        cita.estado = 'cumplida'

        db.session.commit()

        # ---------------------------------
        # AUDITORÍA
        # ---------------------------------

        log = Auditoria(
            asesor_id=session['asesor_id'],
            asesor_nombre=session['asesor_nombre'],
            accion='cumplida',
            cita_id=cita.id,
            detalle=(
                f'Marcó como cumplida la cita de '
                f'{cita.paciente.documento} - '
                f'{cita.paciente.nombre}'
            )
        )

        db.session.add(log)
        db.session.commit()

        # ---------------------------------
        # WHATSAPP
        # ---------------------------------

        enviar_texto(
            cita.numero_whatsapp,
            f"✅ Tu cita fue registrada como completada.\n\n"
            f"Gracias por confiar en CIB 💙"
        )

    return redirect(url_for('asesor.panel'))


# ==========================================
# CITA NO CUMPLIDA
# ==========================================

@asesor_bp.route('/asesor/no_cumplio/<int:cita_id>')
@login_requerido
def marcar_no_cumplio(cita_id):

    cita = Cita.query.get(cita_id)

    if cita:

        cita.estado = 'no cumplio'

        db.session.commit()

        log = Auditoria(
            asesor_id=session['asesor_id'],
            asesor_nombre=session['asesor_nombre'],
            accion='no cumplio',
            cita_id=cita.id,
            detalle=(
                f'Marcó como no cumplida la cita de '
                f'{cita.paciente.documento} - '
                f'{cita.paciente.nombre}'
            )
        )

        db.session.add(log)
        db.session.commit()

        enviar_texto(
            cita.numero_whatsapp,
            f"⚠️ Tu cita fue registrada como no asistida.\n\n"
            f"Si deseas reagendar, estaremos atentos para ayudarte."
        )

    return redirect(url_for('asesor.panel'))

@asesor_bp.route('/asesor/trazabilidad')
@login_requerido
def trazabilidad():

    citas = Cita.query.filter(
        Cita.estado.in_([
            'cumplida',
            'no cumplio'
        ])
    ).order_by(
        Cita.fecha_cita.desc()
    ).all()

    return render_template(
        'trazabilidad.html',
        citas=citas,
        asesor_nombre=session.get('asesor_nombre')
    )  
@asesor_bp.route('/asesor/exportar')
@login_requerido
def exportar_excel():

    citas = Cita.query.order_by(Cita.creada_en.desc()).all()

    output = io.StringIO()

    writer = csv.writer(
        output,
        delimiter=';',
        quoting=csv.QUOTE_MINIMAL
    )

    writer.writerow([
        'ID',
        'Nombre',
        'Documento',
        'Telefono',
        'Tipo',
        'Orden Médica',
        'Área',
        'Fecha',
        'Hora',
        'WhatsApp',
        'Estado',
        'Registrada'
    ])

    for c in citas:

        writer.writerow([
            c.id,
            c.paciente.nombre,
            str(c.paciente.documento),
            str(c.paciente.telefono),
            c.tipo_cita,
            c.orden_medica or '',
            c.area or '',
            c.fecha_cita.strftime('%d/%m/%Y') if c.fecha_cita else '',
            str(c.hora_cita),
            str(c.numero_whatsapp),
            c.estado,
            c.creada_en.strftime('%d/%m/%Y %H:%M')
        ])

    csv_data = output.getvalue()
    output.close()

    return Response(
        '\ufeff' + csv_data,  # Corrige tildes en Excel
        mimetype='text/csv; charset=utf-8',
        headers={
            "Content-Disposition": "attachment; filename=citas_cib.csv"
        }
    )


@asesor_bp.route('/asesor/nueva', methods=['GET', 'POST'])
@login_requerido
def nueva_cita():

    if request.method == 'POST':

        archivo = request.files.get('orden_medica')
        nombre_archivo = ''

        if archivo and archivo.filename != '':
            nombre_archivo = secure_filename(archivo.filename)
            ruta = os.path.join('static/uploads', nombre_archivo)
            archivo.save(ruta)

        # CORREGIR FECHA
        fecha_cita = datetime.strptime(
            request.form['fecha_cita'],
            '%Y-%m-%d'
        )

        paciente = Paciente.query.filter_by(documento=request.form['documento']).first()
        if not paciente:
            paciente = Paciente(
                nombre=request.form['nombre'],
                tipo_documento=request.form['tipo_documento'],
                documento=request.form['documento'],
                fecha_nacimiento=datetime.strptime(request.form['fecha_nacimiento'], '%Y-%m-%d') if request.form.get('fecha_nacimiento') else None,
                telefono=request.form['telefono'],
                correo=request.form.get('correo', ''),
            )
            db.session.add(paciente)
            db.session.commit()

        cita = Cita(
            paciente_id=paciente.id,
            tipo_cita=request.form['tipo_cita'],
            direccion_domicilio=request.form.get('direccion_domicilio', ''),
            cobertura=request.form.get('cobertura', ''),
            aseguradora=request.form.get('aseguradora', ''),
            tipo_examen=request.form.get('tipo_examen', ''),
            tipo_muestra=request.form.get('tipo_muestra', ''),
            agenda_tipo=request.form.get('agenda_tipo', ''),
            area=(
                    "Bacteriología"
                    if request.form.get('tipo_examen') in [
                        'IGRAs',
                        'Tuberculina PPD'
                    ]
                    else 'Micología'
                ),  
            orden_medica=nombre_archivo,
            fecha_cita=fecha_cita,
            hora_cita=request.form['hora_cita'],
            numero_whatsapp=request.form['telefono'],
            estado=request.form['estado']
        )
        db.session.add(cita)
        db.session.commit()

        log = Auditoria(
            asesor_id=session['asesor_id'],
            asesor_nombre=session['asesor_nombre'],
            accion='creo_manual',
            cita_id=cita.id,
            detalle=f'Creó cita manual para {cita.paciente.documento} - {cita.paciente.nombre}'
        )

        db.session.add(log)
        db.session.commit()
        if cita.estado == 'confirmada' and not cita.outlook_event_id:
            try:
                cita.outlook_event_id = crear_evento_outlook(cita)
                db.session.commit()
            except Exception as e:
                print(f"[Outlook] Error en cita manual: {e}")        

        return redirect(url_for('asesor.panel'))

    return render_template('form_cita.html', cita=None)


@asesor_bp.route('/asesor/editar/<int:cita_id>', methods=['GET', 'POST'])
@login_requerido
def editar_cita(cita_id):

    cita = Cita.query.get_or_404(cita_id)
    paciente = cita.paciente  # ← clave con tu nuevo modelo

    if request.method == 'POST':


        # datos del paciente
        paciente.nombre = request.form['nombre']
        paciente.tipo_documento = request.form['tipo_documento']
        paciente.documento = request.form['documento']
        paciente.fecha_nacimiento = datetime.strptime(request.form['fecha_nacimiento'], '%Y-%m-%d') if request.form.get('fecha_nacimiento') else None
        paciente.telefono = request.form['telefono']
        paciente.correo = request.form.get('correo', '')
        paciente.direccion = request.form.get('direccion', '')
        paciente.numero_whatsapp = request.form['telefono']

        # datos de la cita
        cita.tipo_cita = request.form['tipo_cita']
        cita.direccion_domicilio = request.form.get('direccion_domicilio', '')
        cita.cobertura = request.form.get('cobertura', '')
        cita.aseguradora = request.form.get('aseguradora', '')
        cita.tipo_examen = request.form.get('tipo_examen', '')
        cita.tipo_muestra = request.form.get('tipo_muestra', '')
        cita.agenda_tipo = request.form.get('agenda_tipo', '')

        # =====================================================
        # CAMBIO:
        # clasificación automática
        # =====================================================

        cita.area = (
            "Bacteriología"
            if request.form.get('tipo_examen') in [
                'IGRAs',
                'Tuberculina PPD'
            ]
            else 'Micología'
        )

        # Fecha
        cita.fecha_cita = datetime.strptime(
            request.form['fecha_cita'],
            '%Y-%m-%d'
        )

        cita.hora_cita = request.form['hora_cita']
        cita.estado = request.form['estado']
        cita.numero_whatsapp = request.form['telefono']

        # =========================
        # ARCHIVO ORDEN MÉDICA
        # =========================
        archivo = request.files.get('orden_medica')

        if archivo and archivo.filename != '':
            nombre_archivo = secure_filename(archivo.filename)
            ruta = os.path.join('static/uploads', nombre_archivo)
            archivo.save(ruta)

            cita.orden_medica = nombre_archivo
            cita.orden_tipo_archivo = archivo.content_type  # ← opcional pero recomendado

        db.session.commit()


        log = Auditoria(
            asesor_id=session['asesor_id'],
            asesor_nombre=session['asesor_nombre'],
            accion='editó',
            cita_id=cita.id,
            detalle=f'Editó cita de {paciente.documento} - {paciente.nombre}'
        )

        db.session.add(log)
        db.session.commit()

        return redirect(url_for('asesor.panel'))

    return render_template('form_cita.html', cita=cita)

@asesor_bp.route('/asesor/historial')
@login_requerido
def historial():

    logs = Auditoria.query.order_by(Auditoria.fecha.desc()).all()

    return render_template(
        'historial.html',
        logs=logs,
        asesor_nombre=session.get('asesor_nombre')
    )
@asesor_bp.route('/asesor/buscar_paciente')
def buscar_paciente():
    documento = request.args.get('documento')

    paciente = Paciente.query.filter_by(documento=documento).first()

    if paciente:
        return jsonify({
            'nombre': paciente.nombre,
            'tipo_documento': paciente.tipo_documento,
            'telefono': paciente.telefono
        })

    return jsonify({})

def _ocupar_chat(numero):
    """Crea o reactiva el ChatActivo para este número. Se llama tanto al
    'tomar' un chat explícitamente como al simplemente abrir la conversación."""
    chat = ChatActivo.query.filter_by(numero=numero).first()

    if not chat:
        chat = ChatActivo(
            numero=numero,
            asesor_id=session['asesor_id'],
            asesor_nombre=session['asesor_nombre'],
            activo=True,
            vence_en=datetime.utcnow() + timedelta(hours=24),
            primer_mensaje_asesor=datetime.utcnow()
        )
        db.session.add(chat)
    else:
        chat.activo = True
        chat.asesor_id = session['asesor_id']
        chat.asesor_nombre = session['asesor_nombre']
        chat.vence_en = datetime.utcnow() + timedelta(hours=24)
        chat.primer_mensaje_asesor = datetime.utcnow()

    db.session.commit()
    return chat


@asesor_bp.route('/asesor/tomar_chat/<int:cita_id>')
@login_requerido
def tomar_chat(cita_id):
    cita = Cita.query.get_or_404(cita_id)
    _ocupar_chat(cita.numero_whatsapp)
    return redirect(url_for('asesor.ver_chat', cita_id=cita_id))


from flask import request  # asegúrate de tenerlo importado

@asesor_bp.route('/asesor/liberar_chat/<int:cita_id>')
@login_requerido
def liberar_chat(cita_id):

    cita = Cita.query.get_or_404(cita_id)
    chat = ChatActivo.query.filter_by(numero=cita.numero_whatsapp).first()

    if chat:
        db.session.delete(chat)
        db.session.commit()

    origen = request.args.get('origen')
    if origen == 'bandeja':
        return redirect(url_for('asesor.bandeja'))  # ajusta el nombre si tu endpoint se llama distinto

    return redirect(url_for('asesor.panel'))


# =====================================================
# CALENDARIO
# =====================================================
@asesor_bp.route('/asesor/calendario')
@asesor_bp.route('/asesor/calendario/<area>')
@login_requerido
def calendario(area=None):
    return render_template(
        'asesor_calendario.html',
        asesor_nombre=session.get('asesor_nombre'),
        asesor_rol=session.get('asesor_rol', 'asesor'),   
        agenda_fija=None,                                  # asesor ve todo
        area=area or ''
    )


# CALENDARIO MICOLOGÍA (rol: micologia) — solo micología

@asesor_bp.route('/asesor/calendario/micologia')
@login_requerido
@rol_requerido('micologia')
def calendario_micologia():
    return render_template(
        'asesor_calendario.html',
        asesor_nombre=session.get('asesor_nombre'),
        asesor_rol='micologia',
        agenda_fija='micologia'   # filtro bloqueado al template
    ) 

# CALENDARIO BACTERIOLOGÍA (rol: bacteriologia) — solo bacteriología

@asesor_bp.route('/asesor/calendario/bacteriologia')
@login_requerido
@rol_requerido('bacteriologia')
def calendario_bacteriologia():
    return render_template(
        'asesor_calendario.html',
        asesor_nombre=session.get('asesor_nombre'),
        asesor_rol='bacteriologia',
        agenda_fija='bacteriologia'
    )

@asesor_bp.route('/asesor/eventos')
@login_requerido
def eventos_calendario():

    rol_actual   = session.get('asesor_rol', 'asesor')
    agenda_filtro = request.args.get('agenda', '')

    # Si el rol es micologia o bacteriologia, forzar su agenda
    # sin importar lo que venga por query param
    if rol_actual == 'micologia':
        agenda_filtro = 'micologia'
    elif rol_actual == 'bacteriologia':
        agenda_filtro = 'bacteriologia'

    query = Cita.query.filter(Cita.fecha_cita.isnot(None))

    if agenda_filtro == 'micologia':
        query = query.filter(Cita.agenda_tipo == 'micologia')
    elif agenda_filtro == 'bacteriologia':
        query = query.filter(Cita.agenda_tipo == 'bacteriologia')
    elif agenda_filtro == 'domicilio':
        query = query.filter(Cita.tipo_cita == 'domicilio')

    citas = query.all()

    eventos = []

    for cita in citas:

        color = '#f39c12'

        if cita.estado == 'confirmada':
            color = '#27ae60'

        elif cita.estado in (
            'rechazada',
            'cancelada'
        ):
            color = '#e74c3c'

        # =====================================================
        # CAMBIO:
        # DOMICILIOS SIN HORA
        # =====================================================

        if cita.tipo_cita == "domicilio":

            eventos.append({

                'id': cita.id,

                'title':
                    f"🏠 {cita.paciente.nombre}",

                'start':
                    cita.fecha_cita.date().isoformat(),

                'allDay': True,

                'color': '#9b59b6',

                'extendedProps': {
                    'estado': cita.estado,
                    'telefono': cita.numero_whatsapp,
                    'paciente': cita.paciente.nombre,
                    'tipo_examen': cita.tipo_examen or '',
                    'agenda': cita.agenda_tipo or 'domicilio',
                    'area': cita.area or '',
                    'direccion': cita.direccion_domicilio,
                    'correo': cita.paciente.correo or'',
                    'tipo': 'domicilio'
                }
            })

            continue

        # =====================================================
        # PRESENCIAL
        # =====================================================

        try:

            hora = cita.hora_cita.strip()

            hora_obj = datetime.strptime(
                hora,
                "%H:%M"
            ).time()

            inicio = datetime.combine(
                cita.fecha_cita.date(),
                hora_obj
            )

            fin = inicio + timedelta(hours=1)

        except Exception:
            continue

        # =====================================================
        # COLOR POR ÁREA
        # =====================================================

        if cita.area == "Micología":
            color_area = "#4f8ef7"

        elif cita.area == "Bacteriología":
            color_area = "#16a085"

        else:
            color_area = color

        eventos.append({

            'id': cita.id,

            'title':
                f"{cita.paciente.nombre} — {cita.tipo_examen}",

            'start': inicio.isoformat(),

            'end': fin.isoformat(),

            'color': color_area,

            'extendedProps': {
                'estado': cita.estado,
                'telefono': cita.numero_whatsapp,
                'paciente': cita.paciente.nombre,
                'tipo_examen': cita.tipo_examen or '',
                'agenda': cita.agenda_tipo or cita.area or '',
                'area': cita.area or '',
                'correo': cita.paciente.correo or '',
                'direccion': cita.direccion_domicilio or '',   # ← AGREGAR
                'tipo': 'presencial'
            }
        })

    return jsonify(eventos)

#Cambiar contraseña

@asesor_bp.route('/asesor/cambiar-password')
@login_requerido
def vista_cambiar_password():

    return render_template(
        'cambiar_password.html',
        asesor_nombre=session.get('asesor_nombre')
    )

@asesor_bp.route(
    '/asesor/guardar-password',
    methods=['POST']
)
@login_requerido
def guardar_nueva_password():

    asesor = Asesor.query.get(
        session['asesor_id']
    )

    actual = request.form.get('actual')

    nueva = request.form.get('nueva')

    confirmar = request.form.get('confirmar')

    # =====================================
    # VALIDAR PASSWORD ACTUAL
    # =====================================

    if not asesor.check_password(actual):

        flash('La contraseña actual es incorrecta')

        return redirect(
            url_for('asesor.vista_cambiar_password')
        )

    # =====================================
    # VALIDAR COINCIDENCIA
    # =====================================

    if nueva != confirmar:

        flash('Las contraseñas no coinciden')

        return redirect(
            url_for('asesor.vista_cambiar_password')
        )

    # =====================================
    # ACTUALIZAR
    # =====================================

    asesor.set_password(nueva)

    db.session.commit()

    flash('Contraseña actualizada correctamente')

    return redirect(url_for('asesor.panel'))

@asesor_bp.route('/asesor/logout')
def logout():
    session.pop('asesor_id', None)
    session.pop('asesor_nombre', None)
    session.pop('asesor_rol', None)        # ← limpiar el rol también
    return redirect(url_for('asesor.login'))


@asesor_bp.route('/asesor/chat/<int:cita_id>', methods=['GET', 'POST'])
@login_requerido
def ver_chat(cita_id):
    cita = Cita.query.get_or_404(cita_id)
    numero = cita.numero_whatsapp

    _ocupar_chat(numero)   # ← aquí se "ocupa" el chat al abrirlo

    Mensaje.query.filter_by(
        numero_whatsapp=numero,
        origen='cliente',
        leido_asesor=False
    ).update({
        'leido_asesor': True
    })

    db.session.commit()

    if request.method == 'POST':
        texto = request.form.get('mensaje', '').strip()
        if texto:
            enviar_texto(numero, texto, origen='asesor')

        return redirect(url_for('asesor.ver_chat', cita_id=cita_id))

    mensajes = Mensaje.query.filter_by(numero_whatsapp=numero).order_by(Mensaje.id.asc()).all()

    return render_template('chat.html', cita=cita, mensajes=mensajes)

@asesor_bp.route('/asesor/chat_mensajes_count/<int:cita_id>')
@login_requerido
def chat_mensajes_count(cita_id):

    cita = Cita.query.get_or_404(cita_id)

    nuevos = Mensaje.query.filter_by(
        numero_whatsapp=cita.numero_whatsapp,
        origen='cliente',
        leido_asesor=False
    ).count()

    return jsonify({
        'nuevos': nuevos
    })

@asesor_bp.route('/asesor/media/<media_id>')
@login_requerido
def ver_media(media_id):
    from config import TOKEN_META
    import requests as req_lib
    from flask import Response

    headers = {"Authorization": f"Bearer {TOKEN_META}"}

    # 1. Obtener URL del archivo
    r = req_lib.get(f"https://graph.facebook.com/v25.0/{media_id}", headers=headers)
    if r.status_code != 200:
        return "Error obteniendo archivo", 500

    url_archivo = r.json().get("url")
    mime_type = r.json().get("mime_type", "application/octet-stream")

    if not url_archivo:
        return "URL no disponible", 500

    # 2. Descargar y servir
    archivo = req_lib.get(url_archivo, headers=headers)
    return Response(
        archivo.content,
        mimetype=mime_type,
        headers={"Content-Disposition": f"inline; filename={media_id}"}
    )

@asesor_bp.route('/asesor/chat/<int:cita_id>/enviar_media', methods=['POST'])
@login_requerido
def enviar_media(cita_id):
    from config import TOKEN_META, PHONE_NUMBER_ID
    import requests as req_lib

    cita = Cita.query.get_or_404(cita_id)
    numero = cita.numero_whatsapp
    archivo = request.files.get('archivo')

    if not archivo:
        return redirect(url_for('asesor.ver_chat', cita_id=cita_id))

    mime_type = archivo.mimetype

    # 1. Subir archivo a Meta
    headers = {"Authorization": f"Bearer {TOKEN_META}"}
    upload = req_lib.post(
        f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/media",
        headers=headers,
        files={"file": (archivo.filename, archivo.read(), mime_type)},
        data={"messaging_product": "whatsapp", "type": mime_type}
    )

    if upload.status_code != 200:
        agregar_mensajes_log(f"Error subiendo media: {upload.text}")
        return redirect(url_for('asesor.ver_chat', cita_id=cita_id))

    media_id = upload.json().get("id")

    # 2. Determinar tipo para WhatsApp API
    if 'image' in mime_type:
        tipo_wa = 'image'
    elif 'audio' in mime_type:
        tipo_wa = 'audio'
    elif 'video' in mime_type:
        tipo_wa = 'video'
    else:
        tipo_wa = 'document'

    # 3. Enviar mensaje con archivo
    from mensajes import enviar_request
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": tipo_wa,
        tipo_wa: {"id": media_id}
    }
    enviar_request(payload, numero=numero)

    # 4. Guardar en BD
    db.session.add(Mensaje(
        numero_whatsapp=numero,
        origen='asesor',
        texto=f'[Archivo] {mime_type} | {media_id}'
    ))
    db.session.commit()

    return redirect(url_for('asesor.ver_chat', cita_id=cita_id))

@asesor_bp.route('/asesor/chat_total/<int:cita_id>')
@login_requerido
def chat_total(cita_id):

    cita = Cita.query.get_or_404(cita_id)

    total = Mensaje.query.filter_by(
        numero_whatsapp=cita.numero_whatsapp
    ).count()

    return jsonify({
        'total': total
    })

@asesor_bp.route('/asesor/bandeja')
@login_requerido
def bandeja():
    from sqlalchemy import func
    from datetime import datetime

    numeros = [n[0] for n in db.session.query(Mensaje.numero_whatsapp).distinct().all()]

    bandeja = []
    for numero in numeros:
        cita = Cita.query.filter_by(numero_whatsapp=numero).order_by(Cita.creada_en.desc()).first()
        ultimo_msg = Mensaje.query.filter_by(numero_whatsapp=numero).order_by(Mensaje.fecha.desc()).first()
        nuevos = Mensaje.query.filter_by(numero_whatsapp=numero, origen='cliente', leido_asesor=False).count()
        chat_activo = ChatActivo.query.filter_by(numero=numero, activo=True).first()

        asesor_actual = session.get('asesor_nombre')
        ocupado_por_mi = chat_activo and chat_activo.asesor_nombre == asesor_actual

        bandeja.append({
            'numero': numero,
            'cita': cita,
            'ultimo_msg': ultimo_msg,
            'nuevos': nuevos,
            'ocupado': chat_activo is not None,
            'ocupado_por_mi': ocupado_por_mi,
            'ocupado_por': chat_activo.asesor_nombre if chat_activo else None,
        })

    bandeja.sort(
        key=lambda item: item['ultimo_msg'].fecha if item['ultimo_msg'] else datetime.min,
        reverse=True
    )

    return render_template('bandeja.html', bandeja=bandeja, asesor_nombre=session.get('asesor_nombre'))