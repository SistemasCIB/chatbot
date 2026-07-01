from datetime import date
import http.client
import json
import os
from config import DIAS_ACTIVOS, LINK_ASESOR, HORARIO_INICIO, HORARIO_FIN, REQUISITOS, get_config_horario

from models import agregar_mensajes_log, db, Cita, Mensaje 

from dotenv import load_dotenv
load_dotenv(".env")
TOKEN_META = os.getenv("TOKEN_META")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

def _enviar_texto_simple(numero, mensaje):
    """Envío de emergencia — no llama a enviar_request para evitar recursión."""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {TOKEN_META}'
    }
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "text",
        "text": {"preview_url": False, "body": mensaje}
    }
    connection = http.client.HTTPSConnection('graph.facebook.com')
    try:
        connection.request('POST', f'/v25.0/{PHONE_NUMBER_ID}/messages', json.dumps(data), headers)
        connection.getresponse().read()
    except:
        pass
    finally:
        connection.close()

def enviar_request(data, numero=None):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {TOKEN_META}'
    }
    connection = http.client.HTTPSConnection('graph.facebook.com')
    try:
        connection.request('POST', f'/v25.0/{PHONE_NUMBER_ID}/messages', json.dumps(data), headers)
        response = connection.getresponse()
        body = response.read()
        if response.status != 200:
            agregar_mensajes_log(f"Error envio | {response.status} {response.reason} | {body.decode('utf-8', errors='replace')}")

            # ── NUEVO: avisar al usuario si tenemos su número ──
            if numero:
                _enviar_texto_simple(numero, "⚠️ Ocurrió un error técnico. Por favor escribe *hola* para reiniciar.")

    except Exception as e:
        agregar_mensajes_log(f"Error envio: {str(e)}")
    finally:
        connection.close()

def enviar_texto(numero, mensaje, origen='bot'):  
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "text",
        "text": {"preview_url": False, "body": mensaje}
    }
    enviar_request(data, numero=numero)
    
    try:
        db.session.add(Mensaje(numero_whatsapp=numero, origen=origen, texto=mensaje))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        agregar_mensajes_log(f"Error guardando mensaje: {str(e)}")


def enviar_menu(numero):
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "¿En qué te podemos ayudar?"},
            "action": {
                "button": "Ver opciones",
                "sections": [{
                    "title": "Menu principal",
                    "rows": [
                        {"id": "agendar",    "title": "Agendar Cita",       "description": "Programa una nueva cita"},
                        {"id": "resultados", "title": "Ver Resultados",      "description": "Consulta el estado o entrega de tus resultados"},
                        {"id": "cancelar",   "title": "Cancelar Cita",      "description": "Cancelar una cita programada"},
                        {"id": "terminar",   "title": "Finalizar",           "description": "Terminar la conversacion"}
                    ]
                }]
            }
        }
    }
    enviar_request(data, numero=numero) 

def enviar_bienvenida(numero):
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": (
                    "👋¡Bienvenido(a) a la Corporación para Investigaciones Biológicas (CIB)!\n\n"
                    "Somos un laboratorio especializado en diagnóstico, investigación, servicios en salud y otros servicios 🧪\n\n"
                    "Estamos aquí para ayudarte con:\n"
                    "• Agendamiento de citas\n"
                    "• Consulta de resultados\n"
                    "• Información sobre nuestros servicios\n\n"
                    "📌 Para brindarte una mejor atención, sigue las opciones que te indicaremos a continuación.\n\n"
                    "¡Gracias por confiar en nosotros! 💙\n\n"
                    "Por favor, elige una opción e indícanos si eres:\n\n"
                    "🔹 Paciente: persona que necesita un examen, agendar cita o consultar resultados para sí mismo o un familiar.\n\n"
                    "🔹 Cliente: empresa o profesional (IPS, médico, laboratorio, aseguradora) con convenio o solicitud institucional."
                )
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "soy_paciente",
                            "title": "Soy Paciente"      
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "soy_cliente",
                            "title": "Soy Cliente"       
                        }
                    }
                ]
            }
        }
    }
    enviar_request(data, numero=numero)

def enviar_politica_datos(numero):
    from config import URL_BASE

    enviar_texto(
        numero,
        "📄 Protección de datos personales\n\n"
        "Tus datos serán tratados conforme a la Ley 1581 de 2012 y el Decreto 1377 de 2013.\n"
        "Serán usados únicamente para la prestación de nuestros servicios de salud.\n\n"
        "Consulta nuestra política aquí:\n"
        f"{URL_BASE}/politica"
    )

    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": "¿Autorizas el tratamiento de tus datos personales?"
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "acepto_datos",
                            "title": "Si acepto"        
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "no_acepto_datos",
                            "title": "No acepto"          
                        }
                    }
                ]
            }
        }
    }
    enviar_request(data, numero=numero)

def enviar_tipo_cita(numero):
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": """¿Qué tipo de cita necesitas?

🏥 *Atención presencial*
🗓️ Martes a jueves: 7:30 a.m. a 3:30 p.m.
🗓️ Viernes: 7:30 a.m. a 11:30 a.m.
❌ No se atiende fines de semana ni festivos.

🏠 *Atención a domicilio*
🗓️ Este servicio se realiza únicamente los días miércoles en el horario  7:30 a.m. a 1:00 p.m.
📌 Ten en cuenta: la toma de muestra puede realizarse en cualquier momento dentro de este rango y se verifica cobertura.

¿Cómo deseas tu cita?👇"""
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "tipo_presencial",
                            "title": "Presencial"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "tipo_domicilio",
                            "title": "Domicilio"
                        }
                    }
                ]
            }
        }
    }
    enviar_request(data, numero=numero)

def enviar_requisitos(numero, tipo, tipo_muestra=None):

    datos = REQUISITOS.get(tipo, REQUISITOS["general"])

    # EXÁMENES CON TIPO DE MUESTRA
    if isinstance(datos, dict):

        requisitos = datos.get(tipo_muestra, [])

    else:
        requisitos = datos

    lista = "\n".join([f"- {r}" for r in requisitos])



    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text":
                    f"RECUERDE:\n\n"
                    f"{lista}\n\n"
                    f"⚠️ Confirmación de requisitos\n"
                    f"Es muy importante que respondas correctamente para evitar errores o perder la cita.\n"
                    f"Si no cumples con los requisitos anteriormente mencionados."
                    f"(ayuno, documento de identidad, orden médica u otros que apliquen),"
                    f"no se podrá tomar la muestra el día de la cita.\n\n"
                    f"¿Cumples con estos requisitos?"
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "cumple_si",
                            "title": "Si, cumplo"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "cumple_no",
                            "title": "No cumplo"
                        }
                    }
                ]
            }
        }
    }

    enviar_request(data, numero=numero)

def mostrar_fechas_disponibles(numero, sesiones):
    from datetime import datetime, timedelta
    from models import Cita, ExamenConfig
    from festivos import es_festivo

    DIAS_ES = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]

    sesion   = sesiones[numero]
    tipo     = sesion["tipo_cita"]
    examen_id = sesion.get("examen_id") or _examen_a_id(sesion.get("tipo_examen", ""))
    hoy      = datetime.now().date()

    # Cargar config del examen (o valores por defecto)
    ecfg = ExamenConfig.query.filter_by(examen_id=examen_id).first()
    if ecfg:
        dias_permitidos  = ecfg.dias_lista()
        min_anticipacion = ecfg.min_anticipacion
    else:
        dias_permitidos  = [0, 1, 2, 3, 4]   # lunes-vie
        min_anticipacion = 2

    # Días bloqueados por admin (como conjunto de fechas)
    from models import DiasBloqueados
    bloqueados_admin = {
        r.fecha for r in DiasBloqueados.query.all()
    }

    dias             = []
    fechas_guardar   = {}

    # ── PRESENCIAL ────────────────────────────────────────
    if tipo == "presencial":
        area = sesion.get("area", "Micología")
        dia  = hoy + timedelta(days=min_anticipacion)

        #  después de calcular dia:
        if dia.weekday() == 5:          # sábado → lunes
            dia += timedelta(days=2)
        elif dia.weekday() == 6:        # domingo → lunes
            dia += timedelta(days=1)

        if hoy.weekday() == 4:          # hoy es viernes → mínimo miércoles
            while dia.weekday() < 2:    # saltar lunes(0) y martes(1)
                dia += timedelta(days=1)

        while len(dias) < 3:
            wd = dia.weekday()

            # 1) Día de la semana permitido para este examen
            if wd not in dias_permitidos:
                dia += timedelta(days=1)
                continue

            # 2) No es fin de semana (por si el admin habilitó sábado en otro examen)
            if wd >= 5:
                dia += timedelta(days=1)
                continue

            # 3) No es festivo
            if es_festivo(dia):
                dia += timedelta(days=1)
                continue

            # 4) No está bloqueado por admin
            if dia in bloqueados_admin:
                dia += timedelta(days=1)
                continue

            # 5) Validación especial tuberculina/PPD:
            #    el día de lectura (dia + 3 días hábiles laborables) no debe
            #    caer en festivo, fin de semana ni día bloqueado.
            if examen_id == "examen_ppd":
                lectura = _dia_lectura_ppd(dia, bloqueados_admin, dias_permitidos)
                if lectura is None:
                    dia += timedelta(days=1)
                    continue

            # 6) Cupos
            es_viernes  = (wd == 4)
            if ecfg and ecfg.max_por_dia > 0:
                cupo_maximo = ecfg.max_por_dia
            else:
                cupo_maximo = 9 if es_viernes else 17
            ocupadas = Cita.query.filter(
                db.func.date(Cita.fecha_cita) == dia,
                Cita.estado.in_(["pendiente", "confirmada"]),
                Cita.tipo_cita == "presencial",
                Cita.area == area
            ).count()

            if ocupadas < cupo_maximo:
                texto = f"{DIAS_ES[wd]} {dia.strftime('%d/%m/%Y')}"
                dias.append(texto)
                fechas_guardar[f"fecha_{len(dias)}"] = dia.strftime("%d/%m/%Y")

            dia += timedelta(days=1)

    # ── DOMICILIO ─────────────────────────────────────────
    else:
        inicio = hoy + timedelta(days=8)
        fin    = hoy + timedelta(days=30)
        dia    = inicio

        while dia <= fin and len(dias) < 3:
            wd = dia.weekday()

            if wd != 2:          # solo miércoles
                dia += timedelta(days=1)
                continue

            if es_festivo(dia) or dia in bloqueados_admin:
                dia += timedelta(days=1)
                continue

            ocupadas = Cita.query.filter(
                db.func.date(Cita.fecha_cita) == dia,
                Cita.estado.in_(["pendiente", "confirmada"]),
                Cita.tipo_cita == "domicilio"
            ).count()

            if ocupadas < 6:
                texto = f"{DIAS_ES[wd]} {dia.strftime('%d/%m/%Y')}"
                dias.append(texto)
                fechas_guardar[f"fecha_{len(dias)}"] = dia.strftime("%d/%m/%Y")

            dia += timedelta(days=1)

    # ── Botones WhatsApp ──────────────────────────────────
    sesiones[numero]["fechas"] = fechas_guardar

    if not dias:
        enviar_texto(
            numero,
            "❌ No hay fechas disponibles en los próximos días. "
            "Por favor contáctanos directamente."
        )
        return

    botones = [
        {"type": "reply", "reply": {"id": f"fecha_{i+1}", "title": t[:20]}}
        for i, t in enumerate(dias)
    ]

    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "Selecciona una fecha disponible:"},
            "action": {"buttons": botones[:3]}
        }
    }
    enviar_request(data, numero=numero) 


# ── Helpers privados ──────────────────────────────────────

def _examen_a_id(nombre: str) -> str:
    """Fallback: intenta mapear nombre legible → id."""
    mapa = {
        "Tuberculina PPD": "examen_ppd",
        "IGRAs":           "examen_igra",
    }
    return mapa.get(nombre, "examen_otro")


def _dia_lectura_ppd(fecha_aplicacion, bloqueados_admin, dias_permitidos) -> date | None:
    from festivos import es_festivo
    from datetime import timedelta

    # Lectura exacta: aplicación + 3 días calendario
    lectura = fecha_aplicacion + timedelta(days=3)

    if (
        lectura.weekday() >= 5            # fin de semana
        or lectura.weekday() not in dias_permitidos  # ← día no habilitado por admin
        or es_festivo(lectura)
        or lectura in bloqueados_admin
    ):
        return None

    return lectura

def mostrar_horas_disponibles(numero, sesiones):
    from models import Cita, ExamenConfig
    from datetime import datetime

    fecha = sesiones[numero].get("fecha_cita")

    agregar_mensajes_log(
        f"DEBUG mostrar_horas_disponibles | fecha_cita={repr(fecha)}"
    )

    fecha_dt = datetime.strptime(fecha, "%d/%m/%Y")

    es_viernes = (fecha_dt.weekday() == 4)
    area = sesiones[numero].get("area", "Micología")
    examen_id = sesiones[numero].get("examen_id") or _examen_a_id(
        sesiones[numero].get("tipo_examen", "")
    )
    
    # Cargar config del examen
    ecfg = ExamenConfig.query.filter_by(examen_id=examen_id).first()
    h_ini = ecfg.hora_inicio if ecfg else "07:30"
    h_fin = ecfg.hora_fin    if ecfg else "15:30"

    # Generar todas las horas en intervalos de 30 min dentro del rango
    todas = []
    t = datetime.strptime(h_ini, "%H:%M")
    tope = datetime.strptime(h_fin, "%H:%M")
    while t <= tope:
        todas.append(t.strftime("%H:%M"))
        t = t.replace(minute=t.minute + 30) if t.minute == 0 else t.replace(hour=t.hour + 1, minute=0)

    # Viernes: solo hasta 11:30 si el rango lo permite
    if es_viernes:
        tope_viernes = datetime.strptime("11:30", "%H:%M")
        todas = [h for h in todas if datetime.strptime(h, "%H:%M") <= tope_viernes]

    # Horas ocupadas para esta fecha y área
    ocupadas = db.session.query(Cita.hora_cita).filter(
        db.func.date(Cita.fecha_cita) == fecha_dt.date(),
        Cita.tipo_cita == "presencial",
        Cita.area == area,
        Cita.estado.in_(["pendiente", "confirmada"])
    ).all()
    ocupadas = [h[0] for h in ocupadas]

    libres = [h for h in todas if h not in ocupadas]
    # ... resto igual

    if not libres:
        enviar_texto(
            numero,
            "❌ Ya no hay horarios disponibles para esa fecha.\nSelecciona otra fecha."
        )
        mostrar_fechas_disponibles(numero, sesiones)
        return

    # -----------------------------------
    # Guardar opciones
    # -----------------------------------
    sesiones[numero]["horas"] = {
        f"hora_{i+1}": hora for i, hora in enumerate(libres)
    }

    rows = []
    for i, hora in enumerate(libres):
        rows.append({
            "id": f"hora_{i+1}",
            "title": hora,
            "description": ""
        })

    # Max 10 filas por sección
# Guardar opciones
    sesiones[numero]["horas"] = {
        f"hora_{i+1}": hora for i, hora in enumerate(libres)
    }
    rows_am = []
    rows_pm = []

    for i, hora in enumerate(libres):
        hora_dt = datetime.strptime(hora, "%H:%M")
        entry = {"id": f"hora_{i+1}", "title": hora, "description": ""}
        if hora_dt.hour < 12:
            rows_am.append(entry)
        else:
            rows_pm.append(entry)

    # Primer mensaje: AM
    if rows_am:
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": numero,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": "🕐 Horarios de la mañana:"},
                "action": {
                    "button": "Ver horas AM",
                    "sections": [{"title": "Mañana", "rows": rows_am}]
                }
            }
        }
        enviar_request(data, numero=numero) 

    # Segundo mensaje: PM
    if rows_pm:
        data2 = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": numero,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": "🕐 Horarios de la tarde:"},
                "action": {
                    "button": "Ver horas PM",
                    "sections": [{"title": "Tarde", "rows": rows_pm}]
                }
            }
        }
        enviar_request(data2, numero=numero)

def enviar_tipo_documento(numero):
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "Selecciona el tipo de documento de identificacion:"},
            "action": {
                "button": "Ver tipos",
                "sections": [{
                    "title": "Tipo de documento",
                    "rows": [
                        {"id": "tdoc_CC",   "title": "CC",   "description": "Cedula de ciudadania"},
                        {"id": "tdoc_TI",   "title": "TI",   "description": "Tarjeta de identidad"},
                        {"id": "tdoc_CE",   "title": "CE",   "description": "Cedula de extranjeria"},
                        {"id": "tdoc_PPT",  "title": "PPT",  "description": "Permiso de proteccion temporal"},
                        {"id": "tdoc_RC",   "title": "RC",   "description": "Registro civil"},
                        {"id": "tdoc_Otro", "title": "Otro", "description": "Otro tipo de documento"}
                    ]
                }]
            }
        }
    }
    enviar_request(data, numero=numero)

def enviar_fuera_horario(numero):
    from models import DiasBloqueados  # evitar import circular si aplica
    
    config = get_config_horario()
    
    dias_activos = [int(d) for d in (config.dias_activos or "0,1,2,3,4").split(',')]
    nombres_dias = ["lunes", "martes", "miércoles", "jueves",
                    "viernes", "sábado", "domingo"]
    dias_str = ", ".join(nombres_dias[i] for i in dias_activos)

    inicio = config.horario_inicio
    fin    = config.horario_fin

    sufijo_inicio = "am" if inicio < 12 else "pm"
    sufijo_fin    = "am" if fin    < 12 else "pm"
    h_inicio = inicio if inicio <= 12 else inicio - 12
    h_fin    = fin    if fin    <= 12 else fin    - 12

    # Verificar si hoy está bloqueado y agregar motivo
    from datetime import date
    hoy = date.today()
    dia_bloqueado = DiasBloqueados.query.filter_by(fecha=hoy).first()

    if dia_bloqueado and dia_bloqueado.motivo:
        razon = f"Hoy no hay atención: {dia_bloqueado.motivo}.\n\n"
    else:
        razon = ""

    enviar_texto(numero,
        f"{razon}"
        f"Nuestros asesores están disponibles los días {dias_str} "
        f"de {h_inicio}{sufijo_inicio} a {h_fin}{sufijo_fin}.\n\n"
        f"Por favor contáctanos en ese horario. ¡Gracias!"
    )



def enviar_tipo_cobertura(numero):
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": (
                    "💳 Tipo de cobertura\n\n"
                    "Para tu cita indícanos:\n\n"
                    "🔹 Particular: Pagas directamente el valor del examen.\n"
                    "🔹 Aseguradora: Atención por Póliza/Prepagada\n\n"
                    "Nota: no se tienen convenios con EPS/EAPB\n\n"
                    "Selecciona una opción:"
                )
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "cobertura_particular",
                            "title": "Particular"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "cobertura_poliza",
                            "title": "Aseguradora"
                        }
                    }
                ]
            }
        }
    }
    enviar_request(data, numero=numero)

def enviar_pregunta_orden(numero):
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": "📋 ¿Tienes orden médica?\n\nIndícanos si cuentas con una orden para adjuntarla."
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "orden_si",
                            "title": "Sí, tengo orden"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "orden_no",
                            "title": "No tengo orden"
                        }
                    }
                ]
            }
        }
    }
    enviar_request(data, numero=numero)

def enviar_aseguradora(numero):
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {
                "text": (
                    "🏥 Selecciona tu aseguradora:\n\n"
                    "💳 Importante:\n"
                    "Según tu tipo de cobertura, es posible que debas "
                    "realizar un copago al momento del servicio."
                )
            },
            "action": {
                "button": "Ver opciones",
                "sections": [
                    {
                        "title": "Aseguradoras",
                        "rows": [
                            {
                                "id": "seg_sura",
                                "title": "Poliza Sura",
                                "description": "Sin plan complementario"
                            },
                            {
                                "id": "seg_coomeva",
                                "title": "Coomeva",
                                "description": "Medicina prepagada"
                            },
                            {
                                "id": "seg_medplus",
                                "title": "Medplus",
                                "description": "Seleccionar cobertura"
                            },
                            {
                                "id": "seg_bolivar",
                                "title": "Seguros Bolivar",
                                "description": "Seleccionar cobertura"
                            }
                        ]
                    }
                ]
            }
        }
    }
    enviar_request(data, numero=numero)


def enviar_tipo_examen(numero):
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {
                "text": (
                    "🧪 Tipo de examen o muestra\n\n"
                    "Indícanos el examen que necesitas:"
                )
            },
            "action": {
                "button": "Ver examenes",
                "sections": [
                    {
                        "title": "Exámenes disponibles",
                        "rows": [
                            {
                                "id": "examen_directo_hongos",
                                "title": "Directo para hongos",
                                "description": "Fresco o KOH"
                            },
                            {
                                "id": "examen_directo_cultivo",
                                "title": "Directo+Cultivo hongos",
                                "description": "uñas, piel, cuero cabelludo, flujo vaginal"
                            },
                            {
                                "id": "examen_galactomanano",
                                "title": "Antigeno galactomanan",
                                "description": "Aspergillus (PLATELIA)"
                            },
                            {
                                "id": "examen_cryptococcus",
                                "title": "Antigeno cryptococcus",
                                "description": "Lateral Flow Assay(LFA)"
                            },
                            {
                                "id": "examen_serologia_inmuno",
                                "title": "Serologia hongos",
                                "description": "Inmunodifusión"
                            },
                            {
                                "id": "examen_serologia_complemento",
                                "title": "Serologia endemicos",
                                "description": "Fijación complemento"
                            },

                            {
                                "id": "examen_serologia_completa",
                                "title": "Serologia completa",
                                "description": "Prueba de serología completa"
                            },

                            {
                                "id": "examen_igra",
                                "title": "IGRAs",
                                "description": "Ensayo de liberación de Interferón Gamma QuantiFERON-TB"
                            },
                            {
                                "id": "examen_ppd",
                                "title": "Tuberculina PPD",
                                "description": "Test Mantoux"
                            },
                            {
                                "id": "examen_otro",
                                "title": "Otro examen",
                                "description": "Escribir manualmente"
                            }
                        ]
                    }
                ]
            }
        }
    }
    enviar_request(data, numero=numero)    

def enviar_botones_lista(numero, texto, footer, opciones):

    rows = []
    for op in opciones[:10]:
        rows.append({
            "id": op["id"],
            "title": op["title"][:24]
        })

    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {
                "text": texto
            },
            "footer": {
                "text": footer
            },
            "action": {
                "button": "Ver opciones",
                "sections": [
                    {
                        "title": "Opciones disponibles",
                        "rows": rows
                    }
                ]
            }
        }
    }

    enviar_request(data, numero=numero)