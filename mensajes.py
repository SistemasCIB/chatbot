import http.client
import json
from config import TOKEN_META, PHONE_NUMBER_ID, LINK_ASESOR, HORARIO_INICIO, HORARIO_FIN, REQUISITOS
from models import agregar_mensajes_log, db, Cita

def enviar_request(data):
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
            "body": {"text": "En que podemos ayudarte hoy?"},
            "action": {
                "button": "Ver opciones",
                "sections": [{
                    "title": "Menu principal",
                    "rows": [
                        {"id": "agendar",    "title": "Agendar Cita",       "description": "Programa una nueva cita"},
                        {"id": "resultados", "title": "Ver Resultados",      "description": "Consulta el estado o entrega de tus resultados"},
                        {"id": "otros",      "title": "Otros servicios",     "description": "Informacion sobre nuestros servicios"},
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
🗓️ Martes a jueves: 7:30 a.m. a 3:30 p.m.
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
                    f"{horario}\n\n"
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
    from models import Cita

    DIAS_ES = [
        "Lunes", "Martes", "Miércoles",
        "Jueves", "Viernes", "Sábado", "Domingo"
    ]

    tipo = sesiones[numero]["tipo_cita"]
    hoy = datetime.now()

    dias = []
    fechas_guardar = {}

    # =====================================================
    # 🏥 PRESENCIAL
    # Máximo 17 citas de martes a viernes
    # maximo 9 citas los viernes 
    # Desde 2 días en adelante
    # =====================================================
    if tipo == "presencial":

        dia = hoy + timedelta(days=2)

        while len(dias) < 3:

            if 1 <= dia.weekday() <= 4:   # martes a viernes
                es_viernes = (dia.weekday() == 4)
                cupo_maximo = 9 if es_viernes else 17
                
                ocupadas = Cita.query.filter(
                    db.func.date(Cita.fecha_cita) == dia.date(),
                    Cita.estado.in_(["pendiente", "confirmada"]),
                    Cita.tipo_cita == "presencial"
                ).count()
                agregar_mensajes_log(f"[DEBUG] {dia.date()} → ocupadas={ocupadas}")

                # Si aún hay cupos
                if ocupadas < cupo_maximo:

                    texto = (
                        f"{DIAS_ES[dia.weekday()]} "
                        f"{dia.strftime('%d/%m/%Y')}"
                    )

                    dias.append(texto)
                    fechas_guardar[f"fecha_{len(dias)}"] = dia.strftime("%d/%m/%Y")

            dia += timedelta(days=1)

    # =====================================================
    # 🏠 DOMICILIO
    # Solo miércoles
    # Máximo 6 por día
    # Desde 8 días en adelante
    # =====================================================
    else:

        inicio = hoy + timedelta(days=8)
        fin = hoy + timedelta(days=30)

        dia = inicio

        while dia <= fin and len(dias) < 3:

            if dia.weekday() == 2:   # miércoles

                ocupadas = Cita.query.filter(
                    db.func.date(Cita.fecha_cita) == dia.date(),
                    Cita.estado.in_(["pendiente", "confirmada"]),
                    Cita.tipo_cita == "domicilio"
                ).count()

                if ocupadas < 6:

                    texto = (
                        f"{DIAS_ES[dia.weekday()]} "
                        f"{dia.strftime('%d/%m/%Y')}"
                    )

                    dias.append(texto)
                    fechas_guardar[f"fecha_{len(dias)}"] = dia.strftime("%d/%m/%Y")

            dia += timedelta(days=1)

    # =====================================================
    # BOTONES WHATSAPP
    # =====================================================
    botones = []

    for i, texto in enumerate(dias):

        botones.append({
            "type": "reply",
            "reply": {
                "id": f"fecha_{i+1}",
                "title": texto[:20]
            }
        })

    sesiones[numero]["fechas"] = fechas_guardar

    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": "Selecciona una fecha disponible:"
            },
            "action": {
                "buttons": botones[:3]
            }
        }
    }

    enviar_request(data)

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
    # -----------------------------------

    ocupadas = db.session.query(Cita.hora_cita).filter(
        db.func.date(Cita.fecha_cita) == fecha_dt.date(),
        Cita.tipo_cita == "presencial",
        Cita.estado.in_(["pendiente", "confirmada"])
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

    # Dividir en secciones de máx 10
    secciones = []
    if rows[:10]:
        secciones.append({
            "title": "Mañana",
            "rows": rows[:10]
        })
    if rows[10:]:
        secciones.append({
            "title": "Tarde",
            "rows": rows[10:]
        })

  
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "🕐 Selecciona una hora disponible:"},
            "action": {
                "button": "Ver horas",
                "sections": secciones
            }
        }
    }

    enviar_request(data)
    if len(rows) > 10:
         data2 = {
           "messaging_product": "whatsapp",
           "recipient_type": "individual",
           "to": numero,
           "type": "interactive",
           "interactive": {
              "type": "list",
              "body": {"text": "🕐 Más horarios disponibles:"},
              "action": {
                 "button": "Ver más",
                 "sections": [{
                    "title": "Horas adicionales",
                    "rows": rows[10:]
                }]
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
    enviar_texto(numero,
        f"Nuestros asesores estan disponibles de lunes a viernes "
        f"de {HORARIO_INICIO}am a {HORARIO_FIN}pm.\n\n"
        f"Por favor contactanos en ese horario. ¡Gracias!"
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
                    "🔹 Póliza: Atención por aseguradora.\n\n"
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
                            "title": "Poliza"
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
                                "description": "No incluye plan complementario"
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
                                "title": "Hongos + Cultivo",
                                "description": "Micosis superficiales y subcutaneas"
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