from datetime import timedelta
from models import DiasBloqueados

def fecha_bloqueada(fecha):

    bloqueo = DiasBloqueados.query.filter_by(
        fecha=fecha.date()
    ).first()

    return bloqueo is not None

def fecha_disponible(fecha, examen_config):

    # -----------------------------------
    # NO fines de semana
    # -----------------------------------
    if fecha.weekday() in [5, 6]:
        return False

    # -----------------------------------
    # NO festivos
    # -----------------------------------
    if fecha_bloqueada(fecha):
        return False

    # -----------------------------------
    # DÍAS PERMITIDOS
    # -----------------------------------
    dias = [
        int(x)
        for x in examen_config.dias_permitidos.split(",")
    ]

    if fecha.weekday() not in dias:
        return False

    # -----------------------------------
    # VALIDAR RETORNO
    # -----------------------------------
    if examen_config.requiere_retorno:

        retorno = fecha + timedelta(
            hours=examen_config.horas_retorno
        )

        # si retorno cae fin de semana
        if retorno.weekday() in [5, 6]:
            return False

        # si retorno cae festivo
        if fecha_bloqueada(retorno):
            return False

    return True