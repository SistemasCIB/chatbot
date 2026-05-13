from datetime import datetime, timedelta
import os
import requests
from msal import ConfidentialClientApplication
from dotenv import load_dotenv

load_dotenv(".env")

CLIENT_ID     = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
TENANT_ID     = os.getenv("AZURE_TENANT_ID")
ASESOR_EMAIL  = os.getenv("ASESOR_USER_ID")  # aprendizti@cib.org.co

AUTHORITY  = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES     = ["https://graph.microsoft.com/.default"]
GRAPH_BASE = f"https://graph.microsoft.com/v1.0/users/{ASESOR_EMAIL}"


def obtener_token():
    app = ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )
    result = app.acquire_token_for_client(scopes=SCOPES)
    if "access_token" not in result:
        raise Exception(f"Error obteniendo token: {result.get('error_description')}")
    return result["access_token"]


def _headers():
    return {
        "Authorization": f"Bearer {obtener_token()}",
        "Content-Type": "application/json"
    }


def crear_evento_outlook(cita):
    """Crea el evento y retorna el outlook_event_id para guardarlo en la cita."""

    # Parsear fecha + hora
    try:
        hora = cita.hora_cita.strip()  # "10:00" o "10:00 AM"
        fmt = "%Y-%m-%d %H:%M" if len(hora) == 5 else "%Y-%m-%d %I:%M %p"
        inicio = datetime.strptime(
            f"{cita.fecha_cita.strftime('%Y-%m-%d')} {hora}", fmt
        )
    except Exception as e:
        raise ValueError(f"Formato de hora inválido '{cita.hora_cita}': {e}")

    fin = inicio + timedelta(hours=1)

    evento = {
        "subject": f"Cita - {cita.paciente.nombre}",
        "start": {"dateTime": inicio.isoformat(), "timeZone": "America/Bogota"},
        "end":   {"dateTime": fin.isoformat(),    "timeZone": "America/Bogota"},
        "body": {
            "contentType": "HTML",
            "content": (
                f"<b>Paciente:</b> {cita.paciente.nombre}<br>"
                f"<b>Documento:</b> {cita.paciente.documento}<br>"
                f"<b>Teléfono:</b> {cita.paciente.telefono}<br>"
                f"<b>Tipo de examen:</b> {cita.tipo_examen}<br>"
                f"<b>Tipo de cita:</b> {cita.tipo_cita}<br>"
                f"<b>Cobertura:</b> {cita.cobertura}"
            )
        }
    }

    r = requests.post(f"{GRAPH_BASE}/events", headers=_headers(), json=evento)

    if r.status_code != 201:
        raise Exception(f"Error creando evento en Outlook: {r.status_code} {r.text}")

    return r.json().get("id")  # ← guarda esto en cita.outlook_event_id


def actualizar_evento_outlook(event_id, nuevos_datos: dict):
    """Actualiza fecha/hora u otros campos de un evento existente."""
    r = requests.patch(
        f"{GRAPH_BASE}/events/{event_id}",
        headers=_headers(),
        json=nuevos_datos
    )
    if r.status_code != 200:
        raise Exception(f"Error actualizando evento: {r.status_code} {r.text}")
    return r.json()


def eliminar_evento_outlook(event_id):
    """Elimina el evento del calendario (al rechazar una cita)."""
    r = requests.delete(
        f"{GRAPH_BASE}/events/{event_id}",
        headers=_headers()
    )
    if r.status_code not in (204, 404):
        raise Exception(f"Error eliminando evento: {r.status_code} {r.text}")


def listar_eventos_outlook(fecha_inicio=None, fecha_fin=None):
    """Lista eventos del calendario. Útil para la vista del panel."""
    params = {"$orderby": "start/dateTime", "$top": 50}
    if fecha_inicio and fecha_fin:
        params["$filter"] = (
            f"start/dateTime ge '{fecha_inicio}' and end/dateTime le '{fecha_fin}'"
        )
    r = requests.get(f"{GRAPH_BASE}/calendar/events", headers=_headers(), params=params)
    if r.status_code != 200:
        raise Exception(f"Error listando eventos: {r.status_code} {r.text}")
    return r.json().get("value", [])