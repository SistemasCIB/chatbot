from models import ConfigHorario, DiasBloqueados, db, Cita, Paciente, Consentimiento, agregar_mensajes_log
from mensajes import (
    enviar_texto,
    enviar_menu,
    enviar_bienvenida,
    enviar_tipo_documento,
    mostrar_fechas_disponibles,
    enviar_tipo_cita,
    enviar_requisitos,
    enviar_fuera_horario,
    enviar_politica_datos,
    enviar_tipo_cobertura,
    enviar_pregunta_orden,
    enviar_aseguradora,
    enviar_tipo_examen,
    mostrar_horas_disponibles,
    enviar_botones_lista
)

from config import DIAS_ACTIVOS, DIAS_BLOQUEADOS, LINK_ASESOR, HORARIO_INICIO, HORARIO_FIN, URL_RESULTADOS, LINK_ALIMENTATEC, LINK_EDITORIAL, dentro_de_horario
from datetime import datetime, timedelta

from sesiones_db import SesionesDB
sesiones = SesionesDB()
MODO_HUMANO_MINUTOS = 1  # cambiar tiempo al solicitado


# =====================================================
# MODO HUMANO
# =====================================================

def verificar_modo_humano(numero):
    from models import ChatActivo

    chat = ChatActivo.query.filter_by(numero=numero, activo=True).first()
    agregar_mensajes_log(f"MODO_HUMANO | {numero} | activo={chat is not None}")
    if chat:
        return True

    sesion = sesiones.get(numero, {})
    if sesion.get("modo") != "humano":
        return False

    inicio = sesion.get("modo_humano_inicio")
    if not inicio:
        sesion["modo_humano_inicio"] = datetime.utcnow().isoformat()
        sesiones[numero] = sesion
        return True

    # modo_humano_inicio se guarda como string ISO en DB
    if isinstance(inicio, str):
        inicio = datetime.fromisoformat(inicio)

    if datetime.utcnow() - inicio >= timedelta(minutes=MODO_HUMANO_MINUTOS):
        del sesiones[numero]
        return False

    return True


# =====================================================
# CONFIRMACION DATOS
# =====================================================

def enviar_confirmacion_datos(numero):
    sesion = sesiones.get(numero) or {}
    tipo_cita = sesion.get("tipo_cita", "")
    area      = sesion.get("area", "")

    hora_linea      = f"\n📅 *Hora:* {sesion.get('hora_cita', '')}" if tipo_cita == "presencial" else ""
    domicilio_linea = f"\n🏠 *Dirección domicilio:* {sesion.get('direccion_domicilio', '')}" if tipo_cita == "domicilio" else ""

    enviar_texto(
        numero,
        "📋 *Resumen de tu solicitud*\n\n"
        f"👤 *Nombre:* {sesion.get('nombre', '')}\n"
        f"🪪 *Documento:* {sesion.get('tipo_documento', '')} {sesion.get('documento', '')}\n"
        f"🎂 *Fecha de nacimiento:* {sesion.get('fecha_nacimiento', '')}\n"
        f"📞 *Teléfono:* {sesion.get('telefono', '')}\n"
        f"📧 *Correo:* {sesion.get('correo', '')}\n"
        f"📍 *Dirección:* {sesion.get('direccion', '')}\n"
        f"🔬 *Examen:* {sesion.get('tipo_examen', '')}\n"
        f"🧪 *Tipo de muestra:* {sesion.get('tipo_muestra', '')}\n"
        f"🏥 *Tipo de cita:* {tipo_cita}\n"
        f"📆 *Fecha:* {sesion.get('fecha_cita', '')}"
        f"{hora_linea}"
        f"{domicilio_linea}\n\n"
        "¿Los datos son correctos?"
    )

    botones = [
        {"id": "confirm_ok",            "title": "✅ Todo está correcto"},
        {"id": "edit_nombre",           "title": "✏️ Cambiar nombre"},
        {"id": "edit_documento",        "title": "✏️ Cambiar documento"},
        {"id": "edit_fecha_nacimiento", "title": "✏️ Cambiar fecha de nacimiento"},
        {"id": "edit_telefono",         "title": "✏️ Cambiar teléfono"},
        {"id": "edit_correo",           "title": "✏️ Cambiar correo"},
        {"id": "edit_examen",           "title": "✏️ Cambiar examen"},
        {"id": "edit_direccion",        "title": "✏️ Cambiar dirección"},
        {"id": "edit_tipo_cita",        "title": "✏️ Cambiar tipo de cita"},
        {"id": "edit_fecha_cita",       "title": "✏️ Cambiar fecha de cita"},
    ]

    if area == "Micología":
        botones.append({"id": "edit_tipo_muestra", "title": "✏️ Cambiar tipo de muestra"})
    if tipo_cita == "domicilio":
        botones.append({"id": "edit_direccion_domicilio", "title": "✏️ Cambiar dirección domicilio"})

    enviar_botones_lista(numero, "Selecciona una opción:", "Verificar datos", botones)

    sesion["paso"] = "confirmacion"
    sesiones[numero] = sesion


# =====================================================
# BOTONES
# =====================================================

def manejar_boton(numero, opcion_id):

    if verificar_modo_humano(numero):
        return

    # -----------------------------------
    # PACIENTE / CLIENTE
    # -----------------------------------
    if opcion_id == "soy_paciente":
        enviar_politica_datos(numero)
        return

    elif opcion_id == "soy_cliente":
        enviar_texto(
            numero,
            "Estimados clientes,\n\n"
            "Les informamos que a partir de la fecha, todas las comunicaciones o solicitudes relacionadas con:\n"
            "• Estado de resultados\n"
            "• Dudas de remisiones\n"
            "• Inquietudes sobre tipos y/o requisitos de muestras\n"
            "• Información sobre días y horarios de procedimientos de laboratorio\n"
            "• Entre otros similares\n\n"
            f"Deberán realizarse exclusivamente a través de nuestra línea de WhatsApp: \n{LINK_ASESOR}\n\n"
            "Agradecemos su comprensión y colaboración para centralizar la atención y brindarles un mejor servicio.\n\n"
            "ℹ️ Otros servicios\n\n"
            "📚 Fondo editorial CIB\n"
            f"📲 {LINK_EDITORIAL}\n"
            "📧 gestorcomercial@cib.org.co\n\n"
            "🥗 Programa ALIMENTATEC\n"
            f"📲 {LINK_ALIMENTATEC}\n"
            "📧 alimentatec@cib.org.co\n\n"
            "📌 Generalidades\n"
            "📧 comunicacionesymercadeo@cib.org.co\n\n"
            "Gracias por comunicarte con nosotros💙"
        )
        return

    # -----------------------------------
    # POLITICA
    # -----------------------------------
    elif opcion_id == "acepto_datos":
        try:
            consentimiento = Consentimiento(
                numero_whatsapp=numero,
                acepto=True
            )
            db.session.add(consentimiento)
            db.session.commit()
        except:
            db.session.rollback()

        enviar_menu(numero)
        return

    elif opcion_id == "no_acepto_datos":
        enviar_texto(
            numero,
            "👋 Gracias por contactarnos.\n\n"
            "Para poder atender tu solicitud es necesario aceptar nuestra política de tratamiento de datos.\n\n"
            "Si en otro momento decides continuar, estaremos atentos para ayudarte\n\n"
            "¡Que tengas un buen día! 💙"
        )
        return

    # -----------------------------------
    # MENU
    # -----------------------------------
    elif opcion_id == "agendar":
        if not dentro_de_horario():
            enviar_fuera_horario(numero)
            return

        sesiones[numero] = {"flujo": "agendar", "paso": "buscar_documento"}
        enviar_texto(
            numero,
            "📋 Para comenzar, escribe tu número de documento de identidad sin puntos ni caracteres especiales para verificar si ya estás registrado:"
        )
        return

    elif opcion_id == "resultados":
        enviar_texto(
            numero,
            "Paso a paso para la consulta de resultados de Laboratorio\n\n"
            f"1.Ingresa en el siguiente enlace directo para la consulta de tu resultado:  \n{URL_RESULTADOS}\n\n"
            "2.Ingresa a RESULTADOS LABCORE.\n"
            "3.Ingresa en usuario: el número de identificación y en contraseña: los últimos cuatro dígitos del número de identificación\n"
            "Presiona el botón DESCARGAR RESULTADO.\n\n"
            "Muchas gracias por confiar en nosotros."
        )
        enviar_menu(numero)
        return

    elif opcion_id == "cancelar":
        sesiones[numero] = {"flujo": "cancelar", "paso": "cancelar_documento"}
        enviar_texto(
            numero,
            "Por favor escribe el número de documento asociado a la cita que deseas cancelar."
        )
        return

    elif opcion_id == "terminar":
        if numero in sesiones:
            del sesiones[numero]
        enviar_texto(numero, "Gracias por contactarnos.")
        return

    # -----------------------------------
    # TIPO DOCUMENTO
    # -----------------------------------
    elif opcion_id.startswith("tdoc_"):
        sesion = sesiones.get(numero) or {}
        sesion["tipo_documento"] = opcion_id.replace("tdoc_", "")
        sesion["paso"] = "documento"
        sesiones[numero] = sesion
        enviar_texto(
            numero,
            "Escribe tu número de documento sin puntos ni caracteres especiales:"
        )
        return

    # -----------------------------------
    # COBERTURA
    # -----------------------------------
    elif opcion_id == "cobertura_particular":
        sesion = sesiones.get(numero) or {}
        sesion["cobertura"] = "Particular"
        sesion["paso"] = "tipo_examen"
        sesiones[numero] = sesion
        enviar_tipo_examen(numero)
        return

    elif opcion_id == "cobertura_poliza":
        sesion = sesiones.get(numero) or {}
        sesion["cobertura"] = "Poliza"
        sesion["paso"] = "aseguradora"
        sesiones[numero] = sesion
        enviar_aseguradora(numero)
        return

    # -----------------------------------
    # ORDEN MÉDICA
    # -----------------------------------
    elif opcion_id == "orden_si":
        sesion = sesiones.get(numero) or {}
        sesion["paso"] = "orden"
        sesiones[numero] = sesion
        enviar_texto(
            numero,
            "📄 Adjunta la orden médica.\n\n"
            "Puedes enviarla en PDF o foto.\n"
            "Un asesor la revisará para confirmar tu cita."
        )
        return

    elif opcion_id == "orden_no":
        sesion = sesiones.get(numero) or {}
        sesion["orden"] = None
        sesion["tipo_archivo"] = None
        sesiones[numero] = sesion
        confirmar_cita(numero)
        return

    # -----------------------------------
    # ASEGURADORA
    # -----------------------------------
    elif opcion_id.startswith("seg_"):
        aseguradoras = {
            "seg_sura":     "Poliza Sura",
            "seg_coomeva":  "Coomeva",
            "seg_medplus":  "Medplus",
            "seg_bolivar":  "Seguros Bolivar",
        }
        sesion = sesiones.get(numero) or {}
        sesion["aseguradora"] = aseguradoras.get(opcion_id, opcion_id)
        sesion["paso"] = "tipo_examen"
        sesiones[numero] = sesion
        enviar_tipo_examen(numero)
        return

    # -----------------------------------
    # TIPO EXAMEN
    # -----------------------------------
    elif opcion_id.startswith("examen_"):
        sesion = sesiones.get(numero) or {}

        examenes = {
            "examen_directo_hongos":        "Directo hongos",
            "examen_directo_cultivo":       "Hongos + Cultivo",
            "examen_galactomanano":         "Galactomanan",
            "examen_cryptococcus":          "Cryptococcus",
            "examen_serologia_inmuno":      "Serologia hongos",
            "examen_serologia_complemento": "Serologia endemicos",
            "examen_serologia_completa":    "Serologia completa",
            "examen_igra":                  "IGRAs",
            "examen_ppd":                   "Tuberculina PPD",
            "examen_otro":                  "Otro examen",
        }

        if opcion_id == "examen_otro":
            sesion["area"] = "Por definir"
            sesion["examen_id"] = "examen_otro"
            sesion["paso"] = "examen_otro_texto"
            sesiones[numero] = sesion
            enviar_texto(numero, "Escribe el nombre completo del examen:")
            return

        sesion["tipo_examen"] = examenes.get(opcion_id)

        bacteriologia = ["examen_igra", "examen_ppd"]
        sesion["area"]        = "Bacteriología" if opcion_id in bacteriologia else "Micología"
        sesion["agenda_tipo"] = "bacteriologia" if opcion_id in bacteriologia else "micologia"
        sesion["examen_id"]   = opcion_id

        if opcion_id in ["examen_directo_hongos", "examen_directo_cultivo"]:
            sesion["paso"] = "tipo_muestra"
            sesiones[numero] = sesion
            enviar_botones_lista(
                numero,
                "🧪 ¿De qué tipo de muestra es el examen?",
                "Selecciona una opción",
                [
                    {"id": "muestra_unas",  "title": "Uñas"},
                    {"id": "muestra_piel",  "title": "Piel"},
                    {"id": "muestra_cuero", "title": "Cuero cabelludo"},
                    {"id": "muestra_flujo", "title": "Flujo vaginal"},
                ]
            )
            return

        sesion["paso"] = "requisitos"
        sesiones[numero] = sesion
        enviar_requisitos(numero, opcion_id, tipo_muestra=None)
        return

    # -----------------------------------
    # REQUISITOS
    # -----------------------------------
    elif opcion_id == "cumple_si":
        sesion = sesiones.get(numero) or {}
        area = sesion.get("area", "")

        if area == "Bacteriología":
            sesion["tipo_cita"]   = "presencial"
            sesion["agenda_tipo"] = "bacteriologia"
            sesion["paso"]        = "fecha"
            sesiones[numero] = sesion
            enviar_texto(numero, "ℹ️ Los exámenes de Bacteriología se realizan únicamente de forma presencial.")
            mostrar_fechas_disponibles(numero, sesiones)
        else:
            sesion["paso"] = "tipo_cita"
            sesiones[numero] = sesion
            enviar_tipo_cita(numero)
        return

    elif opcion_id == "cumple_no":
        enviar_texto(numero, "Cuando cumplas requisitos podremos ayudarte.")
        enviar_menu(numero)
        return

    # -----------------------------------
    # TIPO DE MUESTRA
    # -----------------------------------
    elif opcion_id.startswith("muestra_"):
        muestras = {
            "muestra_unas":  "Uñas",
            "muestra_piel":  "Piel",
            "muestra_cuero": "Cuero cabelludo",
            "muestra_flujo": "Flujo vaginal",
        }
        sesion = sesiones.get(numero) or {}
        sesion["tipo_muestra"] = muestras.get(opcion_id)
        sesion["agenda_tipo"]  = "micologia"
        sesion["area"]         = "Micología"
        sesion["paso"]         = "requisitos"
        sesiones[numero] = sesion
        enviar_requisitos(numero, sesion["examen_id"], sesion["tipo_muestra"])
        return

    # -----------------------------------
    # TIPO CITA
    # -----------------------------------
    elif opcion_id == "tipo_presencial":
        sesion = sesiones.get(numero) or {}
        sesion["tipo_cita"] = "presencial"
        sesion["paso"]      = "fecha"
        sesiones[numero] = sesion
        mostrar_fechas_disponibles(numero, sesiones)
        return

    elif opcion_id == "tipo_domicilio":
        sesion = sesiones.get(numero) or {}
        sesion["tipo_cita"]   = "domicilio"
        sesion["paso"]        = "fecha"
        sesion["agenda_tipo"] = "domicilio"
        sesiones[numero] = sesion
        mostrar_fechas_disponibles(numero, sesiones)
        return

    # -----------------------------------
    # FECHA
    # -----------------------------------
    elif opcion_id.startswith("fecha_"):
        sesion = sesiones.get(numero) or {}
        fecha = sesion.get("fechas", {}).get(opcion_id)
        sesion["fecha_cita"] = fecha

        if sesion.get("tipo_cita") == "presencial":
            sesion["paso"] = "hora"
            sesiones[numero] = sesion
            mostrar_horas_disponibles(numero, sesiones)
        else:
            sesion["hora_cita"] = "Por asignar"
            sesion["paso"]      = "direccion_domicilio"
            sesiones[numero] = sesion
            enviar_texto(
                numero,
                "🏠 *Dirección para domicilio*\n\n"
                "Por favor envíanos la dirección completa para la toma de la muestra:\n\n"
                "• Dirección exacta\n"
                "• Barrio\n"
                "• Municipio\n"
                "• Punto de referencia (ej: cerca a…, edificio, apartamento, casa, local…)\n"
                "• Número de teléfono de contacto"
            )
        return

    # -----------------------------------
    # HORA
    # -----------------------------------
    elif opcion_id.startswith("hora_"):
        sesion = sesiones.get(numero) or {}
        hora = sesion.get("horas", {}).get(opcion_id)
        sesion["hora_cita"] = hora
        sesion["paso"]      = "confirmacion"
        sesiones[numero] = sesion
        enviar_confirmacion_datos(numero)
        return

    # -----------------------------------
    # CONFIRMACIÓN
    # -----------------------------------
    elif opcion_id == "confirm_ok":
        sesion = sesiones.get(numero) or {}
        cobertura = sesion.get("cobertura")

        if cobertura == "Particular":
            sesion["paso"] = "tiene_orden"
            sesiones[numero] = sesion
            enviar_pregunta_orden(numero)

        elif cobertura == "Poliza":
            sesion["paso"] = "orden"
            sesiones[numero] = sesion
            enviar_texto(
                numero,
                "📄 Ahora adjunta la orden médica.\n\n"
                "Puedes enviarla en PDF o foto.\n"
                "Un asesor la revisará para confirmar tu cita."
            )

        else:
            enviar_texto(numero, "⚠️ Ocurrió un error. Por favor inicia de nuevo.")
            del sesiones[numero]
            enviar_menu(numero)
        return

    # -----------------------------------
    # EDICIÓN DE CAMPOS
    # -----------------------------------
    elif opcion_id.startswith("edit_"):
        sesion = sesiones.get(numero) or {}
        campo = opcion_id.replace("edit_", "")

        mensajes = {
            "nombre":              "Escribe tus nombres y apellidos:",
            "documento":           "Escribe tu número de documento:",
            "fecha_nacimiento":    "Escribe tu fecha de nacimiento (DD/MM/AAAA):",
            "telefono":            "Escribe tu número de teléfono:",
            "correo":              "Escribe tu correo electrónico:",
            "direccion":           "Escribe tu dirección completa:",
            "direccion_domicilio": "Escribe la dirección completa para el domicilio:",
        }

        if campo in mensajes:
            sesion["paso"] = f"editar_{campo}"
            sesiones[numero] = sesion
            enviar_texto(numero, mensajes[campo])

        elif campo == "tipo_muestra":
            sesion["paso"] = "tipo_muestra"
            sesiones[numero] = sesion
            enviar_botones_lista(
                numero,
                "🧪 ¿De qué tipo de muestra es el examen?",
                "Selecciona una opción",
                [
                    {"id": "muestra_unas",  "title": "Uñas"},
                    {"id": "muestra_piel",  "title": "Piel"},
                    {"id": "muestra_cuero", "title": "Cuero cabelludo"},
                    {"id": "muestra_flujo", "title": "Flujo vaginal"},
                ]
            )

        elif campo == "examen":
            sesion["paso"] = "tipo_examen"
            sesiones[numero] = sesion
            enviar_tipo_examen(numero)

        elif campo == "tipo_cita":
            area = sesion.get("area", "")
            if area == "Bacteriología":
                enviar_texto(numero, "ℹ️ Los exámenes de Bacteriología solo se realizan de forma presencial.")
                enviar_confirmacion_datos(numero)
            else:
                sesion["paso"] = "tipo_cita"
                sesiones[numero] = sesion
                enviar_tipo_cita(numero)

        elif campo == "fecha_cita":
            sesion["paso"] = "fecha"
            sesiones[numero] = sesion
            mostrar_fechas_disponibles(numero, sesiones)

        return


# =====================================================
# MENSAJES TEXTO
# =====================================================

def manejar_texto(numero, texto):

    if verificar_modo_humano(numero):
        return

    if numero not in sesiones:
        enviar_bienvenida(numero)
        return

    sesion = sesiones.get(numero) or {}   # ← leer UNA VEZ
    paso = sesion.get("paso")

    # -----------------------------------
    # EDICIÓN DESDE CONFIRMACIÓN
    # -----------------------------------
    if paso and paso.startswith("editar_"):
        campo = paso.replace("editar_", "")

        if campo == "fecha_nacimiento":
            try:
                fecha = datetime.strptime(texto.strip(), "%d/%m/%Y")
                sesion[campo] = fecha.strftime("%d/%m/%Y")
            except ValueError:
                enviar_texto(numero, "❌ Fecha inválida.\nUsa DD/MM/AAAA")
                return
        else:
            sesion[campo] = texto

        sesion["paso"] = "confirmacion"
        sesiones[numero] = sesion
        enviar_texto(numero, "✅ Dato actualizado correctamente.")
        enviar_confirmacion_datos(numero)
        return

    # -----------------------------------
    # BUSCAR PACIENTE POR DOCUMENTO
    # -----------------------------------
    if paso == "buscar_documento":
        paciente = Paciente.query.filter_by(documento=texto.strip()).first()

        if paciente:
            sesion["tipo_documento"]   = paciente.tipo_documento
            sesion["documento"]        = paciente.documento
            sesion["nombre"]           = paciente.nombre
            sesion["fecha_nacimiento"] = paciente.fecha_nacimiento.strftime("%d/%m/%Y") if paciente.fecha_nacimiento else ""
            sesion["telefono"]         = paciente.telefono
            sesion["correo"]           = paciente.correo
            sesion["direccion"]        = paciente.direccion
            sesion["paso"]             = "cobertura"
            sesiones[numero] = sesion
            enviar_texto(
                numero,
                f"👤 Bienvenido de nuevo, *{paciente.nombre}*.\n"
                "Usaremos tus datos registrados."
            )
            enviar_tipo_cobertura(numero)
        else:
            sesion["paso"] = "tipo_documento"
            sesiones[numero] = sesion
            enviar_texto(
                numero,
                "📋 No encontramos tu documento en nuestro sistema.\n"
                "Vamos a registrar tus datos."
            )
            enviar_tipo_documento(numero)
        return

    # -----------------------------------
    # EXAMEN OTRO
    # -----------------------------------
    if paso == "examen_otro_texto":
        sesion["tipo_examen"] = texto
        sesion["paso"]        = "requisitos"
        sesiones[numero] = sesion
        enviar_requisitos(numero, "examen_otro")
        return

    # -----------------------------------
    # DATOS PACIENTE
    # -----------------------------------
    elif paso == "documento":
        sesion["documento"] = texto
        sesion["paso"]      = "nombre"
        sesiones[numero] = sesion
        enviar_texto(
            numero,
            "Escribe tus nombres y apellidos completos tal como aparecen en tu documento de identidad:"
        )
        return

    elif paso == "nombre":
        sesion["nombre"] = texto
        sesion["paso"]   = "fecha_nacimiento"
        sesiones[numero] = sesion
        enviar_texto(numero, "Escribe tu fecha de nacimiento (DD/MM/AAAA):")
        return

    elif paso == "fecha_nacimiento":
        try:
            fecha = datetime.strptime(texto.strip(), "%d/%m/%Y")
            sesion["fecha_nacimiento"] = fecha.strftime("%d/%m/%Y")
            sesion["paso"]             = "telefono"
            sesiones[numero] = sesion
            enviar_texto(numero, "Escribe tu número de teléfono:")
        except ValueError:
            enviar_texto(
                numero,
                "❌ Fecha inválida.\n\nUsa el formato DD/MM/AAAA.\nEjemplo: 25/12/1998"
            )
        return

    elif paso == "telefono":
        sesion["telefono"] = texto
        sesion["paso"]     = "correo"
        sesiones[numero] = sesion
        enviar_texto(numero, "Escribe tu correo electrónico:")
        return

    elif paso == "correo":
        sesion["correo"] = texto
        sesion["paso"]   = "direccion"
        sesiones[numero] = sesion
        enviar_texto(numero, "📍 Por favor escribe la dirección del paciente.")
        return

    elif paso == "direccion":
        sesion["direccion"] = texto
        sesion["paso"]      = "cobertura"
        sesiones[numero] = sesion
        enviar_tipo_cobertura(numero)
        return

    # -----------------------------------
    # DIRECCIÓN DOMICILIO
    # -----------------------------------
    elif paso == "direccion_domicilio":
        sesion["direccion_domicilio"] = texto
        sesion["paso"]                = "confirmacion"
        sesiones[numero] = sesion
        enviar_confirmacion_datos(numero)
        return

    # -----------------------------------
    # FLUJO CANCELAR CITA
    # -----------------------------------
    elif paso == "cancelar_documento":
        documento = texto.strip()
        paciente = Paciente.query.filter_by(documento=documento).first()

        if not paciente:
            enviar_texto(numero, "No encontré ninguna cita con ese documento. Verifica el número e intenta de nuevo.")
            return

        citas = Cita.query.filter(
            Cita.paciente_id == paciente.id,
            Cita.estado.in_(["pendiente", "confirmada"])
        ).order_by(Cita.fecha_cita).all()

        if not citas:
            enviar_texto(numero, "No tienes citas activas para cancelar.")
            del sesiones[numero]
            enviar_menu(numero)
            return

        if len(citas) == 1:
            cita = citas[0]
            sesion["paso"]    = "cancelar_confirmar"
            sesion["cita_id"] = cita.id
            sesiones[numero] = sesion
            fecha_str = cita.fecha_cita.strftime("%d/%m/%Y %H:%M") if cita.hora_cita else cita.fecha_cita.strftime("%d/%m/%Y")
            enviar_texto(
                numero,
                f"Encontré tu cita:\n\n"
                f"📅 *Fecha:* {fecha_str}\n"
                f"🔬 *Examen:* {cita.tipo_examen}\n"
                f"🏥 *Tipo:* {cita.tipo_cita}\n\n"
                "¿Confirmas que deseas cancelarla?\n\n"
                "Responde *sí* o *no*"
            )
        else:
            sesion["paso"]     = "cancelar_elegir"
            sesion["cita_ids"] = [c.id for c in citas]
            sesiones[numero] = sesion
            lista = "\n".join(
                f"{i+1}. {c.fecha_cita.strftime('%d/%m/%Y')} — {c.tipo_examen} ({c.tipo_cita})"
                for i, c in enumerate(citas)
            )
            enviar_texto(numero, f"Tienes varias citas activas:\n\n{lista}\n\nEscribe el número de la que deseas cancelar.")
        return

    elif paso == "cancelar_elegir":
        try:
            idx      = int(texto.strip()) - 1
            cita_ids = sesion.get("cita_ids", [])
            cita     = Cita.query.get(cita_ids[idx])
            sesion["paso"]    = "cancelar_confirmar"
            sesion["cita_id"] = cita.id
            sesiones[numero] = sesion
            fecha_str = cita.fecha_cita.strftime("%d/%m/%Y %H:%M") if cita.hora_cita else cita.fecha_cita.strftime("%d/%m/%Y")
            enviar_texto(
                numero,
                f"Seleccionaste:\n\n"
                f"📅 *Fecha:* {fecha_str}\n"
                f"🔬 *Examen:* {cita.tipo_examen}\n\n"
                "¿Confirmas que deseas cancelarla?\n\n"
                "Responde *sí* o *no*"
            )
        except (ValueError, IndexError):
            enviar_texto(numero, "Por favor escribe solo el número de la cita de la lista.")
        return

    elif paso == "cancelar_confirmar":
        respuesta = texto.strip().lower()
        if respuesta in ("sí", "si", "s"):
            try:
                cita = Cita.query.get(sesion.get("cita_id"))
                cita.estado = "cancelada"
                db.session.commit()
                enviar_texto(numero, "✅ Tu cita ha sido cancelada exitosamente.")
            except Exception as e:
                db.session.rollback()
                agregar_mensajes_log(str(e))
                enviar_texto(numero, "❌ Ocurrió un error al cancelar la cita. Intenta de nuevo.")
        else:
            enviar_texto(numero, "De acuerdo, tu cita no fue cancelada.")

        del sesiones[numero]
        enviar_menu(numero)
        return

    # -----------------------------------
    # ORDEN (error si llega como texto)
    # -----------------------------------
    elif paso == "orden":
        enviar_texto(
            numero,
            "Por favor envía la orden como foto 📷 o archivo PDF 📄, no como texto."
        )
        return

    # -----------------------------------
    # POST CITA
    # -----------------------------------
    elif paso == "post_cita":
        if texto == "1":
            sesion["paso"] = "cobertura"
            sesiones[numero] = sesion
            enviar_texto(numero, "Perfecto 👍 agendaremos otra cita con los mismos datos.")
            enviar_tipo_cobertura(numero)
            return

        elif texto == "2":
            sesiones[numero] = {"flujo": "agendar", "paso": "buscar_documento"}
            enviar_texto(numero, "📋 Ingresa el documento del nuevo paciente:")
            return

        elif texto == "3":
            sesiones[numero] = {
                "modo": "humano",
                "modo_humano_inicio": datetime.utcnow().isoformat()
            }
            enviar_texto(numero, "Gracias por confiar en nosotros 💙")
            return

        elif texto == "4":
            del sesiones[numero]
            enviar_menu(numero)
            return

        else:
            enviar_texto(
                numero,
                "Por favor responde con:\n"
                "1️⃣ Mismo paciente\n"
                "2️⃣ Otro paciente\n"
                "3️⃣ No, gracias\n"
                "4️⃣ Menú principal"
            )
            return


# =====================================================
# ARCHIVOS (orden médica)
# =====================================================

def manejar_archivo(numero, media_id, tipo_mime):
    if numero not in sesiones:
        return

    sesion = sesiones.get(numero) or {}
    if sesion.get("paso") != "orden":
        return

    sesion["orden"]        = media_id
    sesion["tipo_archivo"] = tipo_mime
    sesiones[numero] = sesion
    confirmar_cita(numero)


# =====================================================
# GUARDAR CITA
# =====================================================

def confirmar_cita(numero):
    sesion = sesiones.get(numero) or {}
    try:
        fecha_texto = (sesion.get("fecha_cita") or "").strip()
        hora_texto  = (sesion.get("hora_cita") or "").strip()

        if hora_texto and hora_texto != "Por asignar":
            fecha_real = datetime.strptime(f"{fecha_texto} {hora_texto}", "%d/%m/%Y %H:%M")
        else:
            fecha_real = datetime.strptime(fecha_texto, "%d/%m/%Y")

        fecha_nacimiento_texto = (sesion.get("fecha_nacimiento") or "").strip()
        fecha_nacimiento = None
        if fecha_nacimiento_texto:
            try:
                fecha_nacimiento = datetime.strptime(fecha_nacimiento_texto, "%d/%m/%Y").date()
            except ValueError:
                enviar_texto(numero, "❌ Fecha de nacimiento inválida. Usa el formato DD/MM/AAAA.")
                return

        # Busca o crea paciente
        paciente = Paciente.query.filter_by(documento=sesion.get("documento")).first()

        if not paciente:
            paciente = Paciente(
                tipo_documento=sesion.get("tipo_documento", ""),
                documento=sesion.get("documento", ""),
                nombre=sesion.get("nombre", ""),
                fecha_nacimiento=fecha_nacimiento,
                telefono=sesion.get("telefono", ""),
                correo=sesion.get("correo", ""),
                direccion=sesion.get("direccion", ""),
                numero_whatsapp=numero
            )
            db.session.add(paciente)
            db.session.flush()
        else:
            paciente.telefono         = sesion.get("telefono", paciente.telefono)
            paciente.correo           = sesion.get("correo", paciente.correo)
            paciente.direccion        = sesion.get("direccion", paciente.direccion)
            paciente.fecha_nacimiento = fecha_nacimiento or paciente.fecha_nacimiento

        agregar_mensajes_log(
            f"DEBUG confirmar_cita | area={sesion.get('area')} | "
            f"agenda_tipo={sesion.get('agenda_tipo')} | "
            f"examen={sesion.get('tipo_examen')}"
        )

        cita = Cita(
            paciente_id=paciente.id,
            tipo_cita=sesion.get("tipo_cita", ""),
            direccion_domicilio=sesion.get("direccion_domicilio", ""),
            orden_medica=sesion.get("orden", ""),
            orden_tipo_archivo=sesion.get("tipo_archivo", ""),
            cobertura=sesion.get("cobertura", ""),
            aseguradora=sesion.get("aseguradora", ""),
            tipo_examen=sesion.get("tipo_examen", ""),
            area=sesion.get("area", ""),
            tipo_muestra=sesion.get("tipo_muestra", ""),
            fecha_cita=fecha_real,
            hora_cita=hora_texto if hora_texto and hora_texto != "Por asignar" else None,
            agenda_tipo=sesion.get("agenda_tipo", sesion.get("area", "").lower()),
            numero_whatsapp=numero,
            estado="pendiente"
        )

        db.session.add(cita)
        db.session.commit()

        enviar_texto(
            numero,
            "✅ Tu solicitud fue enviada correctamente.\n\n"
            "Tu solicitud será revisada antes de confirmar la cita.\n\n"
            "❗ Agendar y terminar este proceso no garantiza la asignación de tu cita.\n"
            "Recibirás confirmación por este medio.\n\n"
            "🕘 Horario de atención para las confirmaciones: 9:00 AM - 12:00 PM\n\n"
            "Gracias por confiar en nosotros💙\n\n"
            "¿Deseas agendar otra cita?(es necesario seleccionar una opción)\n\n"
            "1️⃣ Mismo paciente\n"
            "2️⃣ Otro paciente\n"
            "3️⃣ No, gracias"
        )

        sesion["paso"] = "post_cita"
        sesiones[numero] = sesion
        return

    except Exception as e:
        db.session.rollback()
        agregar_mensajes_log(str(e))
        enviar_texto(numero, "❌ Ocurrió un error guardando tu solicitud.")

        sesiones[numero] = {
            "modo": "humano",
            "modo_humano_inicio": datetime.utcnow().isoformat()
        }