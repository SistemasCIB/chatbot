from datetime import date
import http.client
import json
from config import DIAS_ACTIVOS, TOKEN_META, PHONE_NUMBER_ID, LINK_ASESOR, HORARIO_INICIO, HORARIO_FIN, REQUISITOS, get_config_horario

from models import agregar_mensajes_log, db, Cita

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

def enviar_texto(numero, mensaje):
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "text",
        "text": {"preview_url": False, "body": mensaje}
    }
    enviar_request(data)

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
    enviar_request(data)

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
                    "👋 ¡Bienvenido(a) a la Corporación para Investigaciones Biológicas (CIB)!\n\n"
                    "Somos un laboratorio especializado en diagnóstico, investigación y servicios en salud 🧪\n\n"
                    "Podemos ayudarte con:\n"
                    "- Agendar citas\n"
                    "- Consulta de resultados\n"
                    "- Información sobre nuestros servicios\n\n"
                    "📌 Sigue las opciones que te indicaremos a continuación.\n\n"
                    "¡Gracias por confiar en nosotros! 💙\n\n"
                    "Por favor indícanos quién eres:\n\n"
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
    enviar_request(data)

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
    enviar_request(data)

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

🏥 *Presencial*
🗓️ lunes a jueves: 7:30 a.m. a 3:30 p.m.
🗓️ Viernes: 7:30 a.m. a 11:30 a.m.

🏠 *Domicilio*
🗓️ Solo miércoles: 7:30 a.m. a 1:00 p.m.

Selecciona una opción 👇"""
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
    enviar_request(data)

def enviar_requisitos(numero, tipo, tipo_muestra=None):

    datos = REQUISITOS.get(tipo, REQUISITOS["general"])

    # EXÁMENES CON TIPO DE MUESTRA
    if isinstance(datos, dict):

        requisitos = datos.get(tipo_muestra, [])

    else:
        requisitos = datos

    lista = "\n".join([f"- {r}" for r in requisitos])

    horario = (
        f"Horario de atencion: "
        f"Lunes a viernes de {HORARIO_INICIO}am a {HORARIO_FIN}pm"
    )

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

    enviar_request(data)

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
                lectura = _dia_lectura_ppd(dia, bloqueados_admin)
                if lectura is None:
                    dia += timedelta(days=1)
                    continue

            # 6) Cupos
            es_viernes  = (wd == 4)
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
    enviar_request(data)


# ── Helpers privados ──────────────────────────────────────

def _examen_a_id(nombre: str) -> str:
    """Fallback: intenta mapear nombre legible → id."""
    mapa = {
        "Tuberculina PPD": "examen_ppd",
        "IGRAs":           "examen_igra",
    }
    return mapa.get(nombre, "examen_otro")


def _dia_lectura_ppd(fecha_aplicacion, bloqueados_admin) -> date | None:
    """
    Devuelve la fecha de lectura de la tuberculina (72 h ≈ 3 días hábiles
    desde la aplicación), o None si esa fecha cae en festivo/bloqueado/finde.
    Busca hasta 7 días hacia adelante para encontrar una lectura válida.
    """
    from festivos import es_festivo
    from datetime import timedelta

    # La lectura DEBE ser exactamente 72 h después (día + 3 calendario).
    # Si ese día no es hábil, la cita NO es apta — no se ofrece.
    lectura = fecha_aplicacion + timedelta(days=3)

    if (
        lectura.weekday() >= 5          # fin de semana
        or es_festivo(lectura)
        or lectura in bloqueados_admin
    ):
        return None

    return lectura

def mostrar_horas_disponibles(numero, sesiones):
    from models import Cita
    from datetime import datetime

    fecha = sesiones[numero]["fecha_cita"]
    fecha_dt = datetime.strptime(fecha, "%d/%m/%Y")

    es_viernes = (fecha_dt.weekday() == 4)
    # horas los viernes
    if es_viernes:
        horas = [
            "07:30",
            "08:00",
            "08:30",
            "09:00",
            "09:30",
            "10:00",
            "10:30",
            "11:00",
            "11:30"
        ]
    else:
        horas = [
            "07:30",
            "08:00",
            "08:30",
            "09:00",
            "09:30",
            "10:00",
            "10:30",
            "11:00",
            "11:30",
            "12:00",
            "12:30",
            "13:00",
            "13:30",
            "14:00",            
            "14:30",
            "15:00",    
            "15:30"   
        ]

    # -----------------------------------
    # Horas ocupadas (pendiente o confirmada)
    # CAMBIO:
    # horas ocupadas SOLO para la misma área
    # =====================================================

    area = sesiones[numero].get(
        "area",
        "Micología"
    )

    ocupadas = db.session.query(
        Cita.hora_cita
    ).filter(

        db.func.date(Cita.fecha_cita) == fecha_dt.date(),

        Cita.tipo_cita == "presencial",

        # =====================================================
        # CAMBIO:
        # separar horarios por área
        # =====================================================
        Cita.area == area,

        Cita.estado.in_([
            "pendiente",
            "confirmada"
        ])

    ).all()

    ocupadas = [h[0] for h in ocupadas]

    # -----------------------------------
    # Solo libres
    # -----------------------------------
    libres = [h for h in horas if h not in ocupadas]

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
        enviar_request(data)

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
        enviar_request(data2)  

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
    enviar_request(data)

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
    enviar_request(data)


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
                    "🏥 Seleccione su aseguradora:\n\n"
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
                                "description": "Sin complementario"
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
    enviar_request(data)


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
                                "title": "fresco o KOH + Cultivo",
                                "description": "Examen directo y cultivo para hongos de micosis superficiales y subcutáneas"
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
    enviar_request(data)    

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

    enviar_request(data)