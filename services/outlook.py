import datetime
import os
import requests

from msal import ConfidentialClientApplication
from dotenv import load_dotenv

load_dotenv(".env")

CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
TENANT_ID = os.getenv("AZURE_TENANT_ID")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

SCOPES = ["https://graph.microsoft.com/.default"]

GRAPH_URL = "https://graph.microsoft.com/v1.0/users/Sistemas@cib.org.co/events"

def obtener_token():

    app = ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )

    result = app.acquire_token_for_client(
        scopes=SCOPES
    )

    return result['access_token']

def crear_evento_outlook(cita):

    token = obtener_token()

    inicio = datetime.strptime(
        f"{cita.fecha_cita.strftime('%Y-%m-%d')} {cita.hora_cita}",
        '%Y-%m-%d %H:%M'
    )

    fin = inicio + datetime.timedelta(hours=1)

    evento = {

        "subject": f"Cita - {cita.paciente.nombre}",

        "start": {
            "dateTime": inicio.isoformat(),
            "timeZone": "America/Bogota"
        },

        "end": {
            "dateTime": fin.isoformat(),
            "timeZone": "America/Bogota"
        },

        "body": {
            "contentType": "HTML",
            "content": f"""
                Paciente: {cita.paciente.nombre}<br>
                Documento: {cita.paciente.documento}<br>
                Teléfono: {cita.paciente.telefono}<br>
                Tipo examen: {cita.tipo_examen}
            """
        }
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        GRAPH_URL,
        headers=headers,
        json=evento
    )

    return response.json()

print("CLIENT:", CLIENT_ID)
print("TENANT:", TENANT_ID)