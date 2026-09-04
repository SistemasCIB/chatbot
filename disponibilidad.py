from datetime import datetime, time as time_cls
from models import db, Cita, HorarioAsesor, DiasPermitidosTipoCita, BloqueoAgendaFecha


def _to_time(s):
    """'14:30' -> time(14, 30). None-safe."""
    if not s:
        return None
    return datetime.strptime(s, "%H:%M").time()


def _agenda_de(tipo_cita, area):
    """Deriva agenda_tipo a partir de tipo_cita/area, igual que ya hace el código
    existente (Micología / Bacteriología / domicilio)."""
    if tipo_cita == "domicilio":
        return "domicilio"
    if area == "Bacteriología":
        return "bacteriologia"
    return "micologia"


def validar_disponibilidad(fecha, hora, tipo_cita, area=None, origen="manual"):
    """
    fecha: date
    hora: time o None (None solo válido para domicilio)
    tipo_cita: 'domicilio' | 'presencial'
    area: 'Micología' | 'Bacteriología' | None (requerido si tipo_cita == 'presencial')
    origen: 'bot' | 'manual' — solo afecta qué valida (Dominio 2 se salta si origen == 'bot')

    Retorna: (ok: bool, motivo: str | None)
    """
    dia_semana = fecha.weekday()
    agenda_tipo = _agenda_de(tipo_cita, area)

    # ---- Dominio 3: días de semana permitidos por tipo de cita ----
    regla_dias = DiasPermitidosTipoCita.query.filter_by(tipo_cita=tipo_cita).first()
    if regla_dias and dia_semana not in regla_dias.dias_lista():
        dias_es = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        permitidos = ", ".join(dias_es[d] for d in regla_dias.dias_lista())
        return False, f"Solo se agenda {tipo_cita} los días: {permitidos}."

    # ---- Dominio 4: bloqueos/cupos por fecha puntual ----
    bloqueos = BloqueoAgendaFecha.query.filter_by(fecha=fecha).all()
    for b in bloqueos:
        if b.tipo_cita is not None and b.tipo_cita != tipo_cita:
            continue  # este bloqueo no aplica a este tipo de cita

        if b.tipo_bloqueo == 'dia_completo':
            return False, b.motivo or "Fecha no disponible."

        if b.tipo_bloqueo == 'rango_horas' and hora is not None:
            h_ini, h_fin = _to_time(b.hora_inicio), _to_time(b.hora_fin)
            if h_ini and h_fin and h_ini <= hora <= h_fin:
                return False, b.motivo or "Horario no disponible."

        if b.tipo_bloqueo == 'cupo_maximo' and b.max_citas_dia is not None:
            filtros = [
                db.func.date(Cita.fecha_cita) == fecha,
                Cita.estado.in_(["pendiente", "confirmada"]),
                Cita.tipo_cita == tipo_cita,
            ]
            ocupadas = Cita.query.filter(*filtros).count()
            if ocupadas >= b.max_citas_dia:
                return False, b.motivo or "Cupo lleno para esta fecha."

    # ---- Dominio 2: horario de agenda MANUAL por agenda_tipo/día (no aplica al bot) ----
    if origen == "manual":
        h_asesor = HorarioAsesor.query.filter_by(
            agenda_tipo=agenda_tipo, dia_semana=dia_semana
        ).first()
        if h_asesor:
            if not h_asesor.activo:
                return False, f"Este día no está habilitado para agendar citas en la agenda de {agenda_tipo}."
            if hora is not None:
                h_ini, h_fin = _to_time(h_asesor.hora_inicio), _to_time(h_asesor.hora_fin)
                if h_ini and h_fin and not (h_ini <= hora <= h_fin):
                    return False, f"Ese día solo se agenda de {h_asesor.hora_inicio} a {h_asesor.hora_fin}."

    return True, None


def citas_restantes(fecha, tipo_cita):
    """Para el bot: cuántos cupos quedan ese día según Dominio 4 (cupo_maximo).
    Retorna None si no hay límite definido (sin tope explícito)."""
    b = BloqueoAgendaFecha.query.filter_by(
        fecha=fecha, tipo_bloqueo='cupo_maximo'
    ).filter(
        db.or_(BloqueoAgendaFecha.tipo_cita == tipo_cita, BloqueoAgendaFecha.tipo_cita.is_(None))
    ).first()
    if not b or b.max_citas_dia is None:
        return None
    ocupadas = Cita.query.filter(
        db.func.date(Cita.fecha_cita) == fecha,
        Cita.estado.in_(["pendiente", "confirmada"]),
        Cita.tipo_cita == tipo_cita,
    ).count()
    return max(0, b.max_citas_dia - ocupadas)