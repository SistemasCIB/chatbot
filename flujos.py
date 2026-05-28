from models import ConfigHorario, DiasBloqueados, db, Cita,Paciente, Consentimiento, agregar_mensajes_log
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
    enviar_aseguradora,
    enviar_tipo_examen,
    mostrar_horas_disponibles,
    enviar_botones_lista
)

from config import DIAS_ACTIVOS, DIAS_BLOQUEADOS, LINK_ASESOR, HORARIO_INICIO, HORARIO_FIN, URL_RESULTADOS, LINK_ALIMENTATEC, LINK_EDITORIAL, dentro_de_horario
from datetime import datetime, timedelta

sesiones = {}
MODO_HUMANO_MINUTOS = 3 # cambiar tiempo al solicitado



# =====================================================
# MODO HUMANO
# =====================================================

def verificar_modo_humano(numero):
    sesion = sesiones.get(numero, {})

    if sesion.get("modo") != "humano":
        return False

    inicio = sesion.get("modo_humano_inicio")

    if not inicio:
        sesiones[numero]["modo_humano_inicio"] = datetime.utcnow()
        return True

    if datetime.utcnow() - inicio >= timedelta(minutes=MODO_HUMANO_MINUTOS):
        del sesiones[numero]
        return False

    return True


# =====================================================
# BOTONES
# =====================================================
def enviar_confirmacion_datos(numero):
    sesion = sesiones[numero]

    tipo_cita = sesion.get("tipo_cita", "")
    hora_linea = f"\n📅 *Hora:* {sesion.get('hora_cita', '')}" if tipo_cita == "presencial" else ""
    domicilio_linea = f"\n🏠 *Dirección domicilio:* {sesion.get('direccion_domicilio', '')}" if tipo_cita == "domicilio" else ""

    enviar_texto(
        numero,
        "📋 *Resumen de tu solicitud*\n\n"
        f"👤 *Nombre:* {sesion.get('nombre', '')}\n"
        f"🪪 *Documento:* {sesion.get('tipo_documento', '')} {sesion.get('documento', '')}\n"
        f"📞 *Teléfono:* {sesion.get('telefono', '')}\n"
        f"📧 *Correo:* {sesion.get('correo', '')}\n"
        f"🔬 *Examen:* {sesion.get('tipo_examen', '')}\n"
        f"🧪 *Tipo de muestra:*{sesion.get('tipo_muestra','')}\n"
        f"🏥 *Tipo de cita:* {tipo_cita}\n"
        f"📆 *Fecha:* {sesion.get('fecha_cita', '')}"
        f"{hora_linea}"
        f"{domicilio_linea}\n\n"
        "¿Los datos son correctos?"
    )

    enviar_botones_lista(
        numero,
        "Selecciona una opción:",
        "Verificar datos",
        [
            {"id": "confirm_ok",           "title": "✅ Todo está correcto"},
            {"id": "edit_nombre",          "title": "✏️ Cambiar nombre"},
            {"id": "edit_documento",       "title": "✏️ Cambiar documento"},
            {"id": "edit_telefono",        "title": "✏️ Cambiar teléfono"},
            {"id": "edit_correo",          "title": "✏️ Cambiar correo"},
            {"id": "edit_examen",          "title": "✏️ Cambiar examen"},
            {"id": "edit_tipo_muestra",    "title": "✏️ Cambiar tipo de muestra"},
            {"id": "edit_tipo_cita",       "title": "✏️ Cambiar tipo de cita"},
            {"id": "edit_fecha",           "title": "✏️ Cambiar fecha"},   
            {"id": "edit_direccion_domicilio", "title": "✏️ Cambiar dirección domicilio"}
            
        ]
    )
    sesiones[numero]["paso"] = "confirmacion"

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
            "• Inquietudes sobre tipos y/o requisitos de muestrass\n"
            "• Información sobre días y horarios de procedimientos de laboratorio\n"
            "• Entre otros similares\n\n"
            f"Deberán realizarse exclusivamente a través de nuestra línea de WhatsApp: \n{LINK_ASESOR}\n\n"
            "ℹ️ Otros servicios\n\n"
            "📚 Fondo editorial CIB\n"
            f"📲 {LINK_EDITORIAL}\n"
            "📧 gestorcomercial@cib.org.co\n\n"
            "🥗 Programa ALIMENTATEC\n"
            f"📲 {LINK_ALIMENTATEC}\n"
            "📧 alimentatec@cib.org.co\n\n"
            "📌 Generalidades\n"
            "📧 comunicacionesymercadeo@cib.org.co\n\n"
            "Agradecemos su comprensión y colaboración para centralizar la atención y brindarles un mejor servicio."

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

        #primero busca si ya es un paciente existente
        sesiones[numero] = {
            "flujo": "agendar",
            "paso": "buscar_documento"
        }
        enviar_texto(
            numero,
            "📋 Para comenzar, escribe tu número de documento de identidad sin puntos ni caracteres especiales para verificar si ya estás registrado:"
        )    

        return

    elif opcion_id == "resultados":
        enviar_texto(
            numero,
            "Paso a paso para la consulta de resultados de Laboratorio:\n\n"
            f"1. Ingresa en el siguiente enlace directo para la consulta de su resultado: \n{URL_RESULTADOS}\n\n"
            "2. Ingresa a RESULTADOS LABCORE.\n"
            "3. Ingresa en usuario: el número de identificación y en contraseña: los ultimos cuatro digitos del número de identificación.\n"
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
    # PASO 1 - DATOS PACIENTE: tipo documento
    # -----------------------------------
    elif opcion_id.startswith("tdoc_"):

        sesiones[numero]["tipo_documento"] = opcion_id.replace("tdoc_", "")
        sesiones[numero]["paso"] = "documento"

        enviar_texto(
            numero,
            "Escribe tu número de documento sin puntos ni caracteres especiales:"
        )
        return

    # -----------------------------------
    # PASO 2 - COBERTURA: después de correo
    # -----------------------------------
    elif opcion_id == "cobertura_particular":

        sesiones[numero]["cobertura"] = "Particular"
        sesiones[numero]["paso"] = "tipo_examen"

        enviar_tipo_examen(numero)
        return

    elif opcion_id == "cobertura_poliza":

        sesiones[numero]["cobertura"] = "Poliza"
        sesiones[numero]["paso"] = "aseguradora"

        enviar_aseguradora(numero)
        return

    # -----------------------------------
    # ASEGURADORA
    # -----------------------------------
    elif opcion_id.startswith("seg_"):

        sesiones[numero]["aseguradora"] = opcion_id
        sesiones[numero]["paso"] = "tipo_examen"

        enviar_tipo_examen(numero)
        return

    # -----------------------------------
    # PASO 3 - TIPO EXAMEN: después de cobertura
    # -----------------------------------
    elif opcion_id.startswith("examen_"):

        examenes = {
            "examen_directo_hongos": "Examen directo para hongos",
            "examen_directo_cultivo": "Hongos + Cultivo",
            "examen_galactomanano": "Antigeno galactomanan",
            "examen_cryptococcus": "Antigeno cryptococcus",
            "examen_serologia_inmuno": "Serologia hongos",
            "examen_serologia_complemento": "Serologia endemicos",
            "examen_serologia_completa": "Serologia completa",
            "examen_igra": "IGRAs",
            "examen_ppd": "Tuberculina PPD"
        }

        if opcion_id == "examen_otro":
            sesiones[numero]["area"] = "Por definir" 
            sesiones[numero]["paso"] = "examen_otro_texto"

            enviar_texto(
                numero,
                "Escribe el nombre completo del examen:"
            )
            return

        sesiones[numero]["tipo_examen"] = examenes.get(opcion_id)
        # Clasificación automática por área
        bacteriologia = ["examen_igra", "examen_ppd"]
        sesiones[numero]["area"] = "Bacteriología" if opcion_id in bacteriologia else "Micología" 
        sesiones[numero]["agenda_tipo"] = "bacteriologia" if opcion_id in bacteriologia else "micologia"       
        sesiones[numero]["agenda_tipo"] = "domicilio"

        # SOLO PARA HONGOS
        if opcion_id in [
            "examen_directo_hongos",
            "examen_directo_cultivo"
        ]:

            sesiones[numero]["examen_id"] = opcion_id
            sesiones[numero]["paso"] = "tipo_muestra"

            enviar_botones_lista(
                numero,
                "🧪 ¿De qué tipo de muestra es el examen?",
                "Selecciona una opción",
                [
                    {
                        "id": "muestra_unas",
                        "title": "Uñas"
                    },
                    {
                        "id": "muestra_piel",
                        "title": "Piel"
                    },
                    {
                        "id": "muestra_cuero",
                        "title": "Cuero cabelludo"
                    },
                    {
                        "id": "muestra_flujo",
                        "title": "Flujo vaginal"
                    }
                ]
            )

            return


        # RESTO DE EXÁMENES → flujo normal
        sesiones[numero]["paso"] = "requisitos"

        enviar_requisitos(numero, opcion_id, tipo_muestra=None)

        return

    # -----------------------------------
    # PASO 4 - REQUISITOS: después de examen
    # -----------------------------------
    elif opcion_id == "cumple_si":
        # FLUJO: después de requisitos → tipo_cita
        sesiones[numero]["paso"] = "tipo_cita"

        enviar_tipo_cita(numero)
        return
    elif opcion_id == "cumple_no":
        enviar_texto(
            numero,
            "Cuando cumplas requisitos podremos ayudarte."
        )
        enviar_menu(numero)
        return
   
    # -----------------------------------
    # TIPO DE MUESTRA
    # -----------------------------------
    elif opcion_id.startswith("muestra_"):

        muestras = {
            "muestra_unas": "Uñas",
            "muestra_piel": "Piel",
            "muestra_cuero": "Cuero cabelludo",
            "muestra_flujo": "Flujo vaginal"
        }

        sesiones[numero]["tipo_muestra"] = muestras.get(opcion_id)

        # =========================================
        # CAMBIO NUEVO
        # AGENDA AUTOMÁTICA MICOLÓGICA
        # =========================================

        sesiones[numero]["agenda_tipo"] = "micologia"

        sesiones[numero]["area"] = "Micología"

        sesiones[numero]["paso"] = "requisitos"

        enviar_requisitos(
            numero,
            sesiones[numero]["examen_id"],
            sesiones[numero]["tipo_muestra"]
        )

        return

    # -----------------------------------
    # PASO 5 - TIPO CITA: después de requisitos
    # -----------------------------------
    elif opcion_id == "tipo_presencial":

        sesiones[numero]["tipo_cita"] = "presencial"
        # FLUJO: después de tipo_cita → fecha
        sesiones[numero]["paso"] = "fecha"

        mostrar_fechas_disponibles(numero, sesiones)
        return

    elif opcion_id == "tipo_domicilio":

        sesiones[numero]["tipo_cita"] = "domicilio"
        # FLUJO: después de tipo_cita → fecha
        sesiones[numero]["paso"] = "fecha"
        sesiones[numero]["agenda_tipo"] = "domicilio"

        mostrar_fechas_disponibles(numero, sesiones)
        return

    # -----------------------------------
    # PASO 6 - FECHA: después de tipo_cita
    # -----------------------------------
    elif opcion_id.startswith("fecha_"):

        fecha = sesiones[numero]["fechas"].get(opcion_id)

        sesiones[numero]["fecha_cita"] = fecha
        if sesiones[numero]["tipo_cita"] == "presencial":
            sesiones[numero]["paso"] = "hora"
            mostrar_horas_disponibles(numero, sesiones)
           
            return
        else:    
        ## Si es domicilio no pide hora
           sesiones[numero]["hora_cita"] = None
           sesiones[numero]["paso"] = "direccion_domicilio"

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
    # PASO 7 - HORA
    # -----------------------------------
    elif opcion_id.startswith("hora_"):

        hora = sesiones[numero]["horas"].get(opcion_id)

        sesiones[numero]["hora_cita"] = hora
        sesiones[numero]["paso"] = "confirmacion"

        enviar_confirmacion_datos(numero)

        return
    # -----------------------------------
    # CONFIRMACIÓN Y EDICIÓN DE DATOS
    # -----------------------------------
    elif opcion_id == "confirm_ok":
        sesiones[numero]["paso"] = "orden"
        enviar_texto(
            numero,
            "📄 Ahora adjunta la orden médica.\n\n"
            "Puedes enviarla en PDF o foto.\n"
            "Un asesor la revisará para confirmar tu cita."
        )
        return

    elif opcion_id.startswith("edit_"):
        campo = opcion_id.replace("edit_", "")

        mensajes = {
            "nombre":    "Escribe tus nombres y apellidos:",
            "documento": "Escribe tu número de documento:",
            "telefono":  "Escribe tu número de teléfono:",
            "correo":    "Escribe tu correo electrónico:",
        }

        if campo in mensajes:
            sesiones[numero]["paso"] = f"editar_{campo}"
            enviar_texto(numero, mensajes[campo])

        elif campo == "examen":
            sesiones[numero]["paso"] = "tipo_examen"
            enviar_tipo_examen(numero)

        elif campo == "tipo_cita":
            sesiones[numero]["paso"] = "tipo_cita"
            enviar_tipo_cita(numero)

        elif campo == "fecha":
            sesiones[numero]["paso"] = "fecha"
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

    sesion = sesiones[numero]
    paso = sesion.get("paso")

    # -----------------------------------
    # EDICIÓN DESDE CONFIRMACIÓN
    # -----------------------------------
    if paso and paso.startswith("editar_"):
        campo = paso.replace("editar_", "")
        sesiones[numero][campo] = texto
        sesiones[numero]["paso"] = "confirmacion"
        enviar_texto(numero, f"✅ Dato actualizado correctamente.")
        enviar_confirmacion_datos(numero)
        return    

    # -----------------------------------
    # BUSCAR PACIENTE POR DOCUMENTO
    # -----------------------------------
    if paso == "buscar_documento":
        from models import Paciente

        paciente = Paciente.query.filter_by(documento=texto.strip()).first()

        if paciente:
            # Paciente encontrado — cargar datos y saltar al flujo
            sesiones[numero]["tipo_documento"] = paciente.tipo_documento
            sesiones[numero]["documento"]      = paciente.documento
            sesiones[numero]["nombre"]         = paciente.nombre
            sesiones[numero]["telefono"]       = paciente.telefono
            sesiones[numero]["correo"]         = paciente.correo
            sesiones[numero]["paso"]           = "cobertura"

            enviar_texto(
                numero,
                f"👤 Bienvenido de nuevo, *{paciente.nombre}*.\n"
                f"Usaremos tus datos registrados."
            )
            enviar_tipo_cobertura(numero)

        else:
            # Paciente nuevo — pedir datos completos
            sesiones[numero]["paso"] = "tipo_documento"
            enviar_tipo_documento(numero)

        return

    # -----------------------------------
    # EXAMEN OTRO
    # -----------------------------------
    if paso == "examen_otro_texto":
        sesiones[numero]["tipo_examen"] = texto
        # FLUJO: después de examen otro → requisitos
        sesiones[numero]["paso"] = "requisitos"       

        enviar_requisitos(numero, "examen_otro")
        return

    # -----------------------------------
    # DATOS PACIENTE: número de documento
    # -----------------------------------
    elif paso == "documento":
        sesiones[numero]["documento"] = texto
        sesiones[numero]["paso"] = "nombre"

        enviar_texto(
            numero,
            "Escribe tus nombres y apellidos completos tal como aparecen en tu documento de identidad:"
        )
        return

    # -----------------------------------
    # DATOS PACIENTE: nombre
    # -----------------------------------
    elif paso == "nombre":
        sesiones[numero]["nombre"] = texto
        sesiones[numero]["paso"] = "telefono"

        enviar_texto(
            numero,
            "Escribe tu número de teléfono :"
        )
        return

    # -----------------------------------
    # DATOS PACIENTE: teléfono
    # -----------------------------------
    elif paso == "telefono":
        sesiones[numero]["telefono"] = texto
        sesiones[numero]["paso"] = "correo"

        enviar_texto(
            numero,
            "Escribe tu correo electrónico:"
        )
        return

    # -----------------------------------
    # DATOS PACIENTE: correo
    # -----------------------------------
    elif paso == "correo":
        sesiones[numero]["correo"] = texto
        sesiones[numero]["paso"] = "cobertura"

        enviar_tipo_cobertura(numero)
        return

 
   
    # -----------------------------------
    #DIRECION DOMICILIO
    # -----------------------------------
    elif paso == "direccion_domicilio":
        sesiones[numero]["direccion_domicilio"] = texto
        sesiones[numero]["paso"] = "confirmacion"
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

        citas = Cita.query.filter_by(
            paciente_id=paciente.id,
            estado="pendiente"
        ).order_by(Cita.fecha_cita).all()

        if not citas:
            enviar_texto(numero, "No tienes citas activas para cancelar.")
            del sesiones[numero]
            enviar_menu(numero)
            return

        if len(citas) == 1:
            cita = citas[0]
            sesiones[numero]["paso"]    = "cancelar_confirmar"
            sesiones[numero]["cita_id"] = cita.id
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
            sesiones[numero]["paso"]     = "cancelar_elegir"
            sesiones[numero]["cita_ids"] = [c.id for c in citas]
            lista = "\n".join(
                f"{i+1}. {c.fecha_cita.strftime('%d/%m/%Y')} — {c.tipo_examen} ({c.tipo_cita})"
                for i, c in enumerate(citas)
            )
            enviar_texto(numero, f"Tienes varias citas activas:\n\n{lista}\n\nEscribe el número de la que deseas cancelar.")
        return

    elif paso == "cancelar_elegir":
        try:
            idx      = int(texto.strip()) - 1
            cita_ids = sesiones[numero]["cita_ids"]
            cita     = Cita.query.get(cita_ids[idx])
            sesiones[numero]["paso"]    = "cancelar_confirmar"
            sesiones[numero]["cita_id"] = cita.id
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
                cita = Cita.query.get(sesiones[numero]["cita_id"])
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
    # ORDEN (captura por texto — error)
    # -----------------------------------
    elif paso == "orden":
        enviar_texto(
            numero,
            "Por favor envía la orden como foto 📷 o archivo PDF 📄, no como texto."
        )
        return

    # -----------------------------------
    # POST CITA (re-agendar)
    # -----------------------------------
    elif paso == "post_cita":

        if texto == "1":
            # MISMO PACIENTE
            sesiones[numero]["paso"] = "cobertura"

            enviar_texto(
                numero,
                "Perfecto 👍 agendaremos otra cita con los mismos datos."
            )

            enviar_tipo_cobertura(numero)
            return

        elif texto == "2":
            # OTRO PACIENTE
            sesiones[numero] = {
                "flujo": "agendar",
                "paso": "buscar_documento"
            }

            enviar_texto(
                numero,
                "📋 Ingresa el documento del nuevo paciente:"
            )
            return

        elif texto == "3":
            # TERMINAR
            enviar_texto(
                numero,
                "Gracias por confiar en nosotros 💙"
            )

            sesiones[numero] = {
                "modo": "humano",
                "modo_humano_inicio": datetime.utcnow()
            }
            return
        
        elif texto == "4":
            enviar_menu(numero)
            sesiones[numero] = {}
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

def manejar_archivo(numero, media_id, tipo_mime):
    if numero not in sesiones:
        return
    if sesiones[numero].get("paso") != "orden":
        return

    sesiones[numero]["orden"] = media_id
    sesiones[numero]["tipo_archivo"] = tipo_mime
    confirmar_cita(numero)




# =====================================================
# GUARDAR CITA
# =====================================================

def confirmar_cita(numero):
    sesion = sesiones.get(numero, {})
    try:
        from datetime import datetime

        # ---------------------------------
        # FECHA
        # ---------------------------------
        fecha_texto = sesion.get("fecha_cita", "").strip()
        hora_texto = sesion.get("hora_cita", "").strip()

        if hora_texto:
            fecha_real = datetime.strptime(
                f"{fecha_texto} {hora_texto}",
                "%d/%m/%Y %H:%M"
            )
        else:
            fecha_real = datetime.strptime(
                fecha_texto,
                "%d/%m/%Y"
            )

        # ---------------------------------
        # PACIENTE — busca o crea
        # ---------------------------------
        paciente = Paciente.query.filter_by(
            documento=sesion.get("documento")
        ).first()

        if not paciente:
            paciente = Paciente(
                tipo_documento=sesion.get("tipo_documento", ""),
                documento=sesion.get("documento", ""),
                nombre=sesion.get("nombre", ""),
                telefono=sesion.get("telefono", ""),
                correo=sesion.get("correo", ""),
                numero_whatsapp=numero
            )
            db.session.add(paciente)
            db.session.flush()  # obtiene paciente.id sin commit

        # ---------------------------------
        # CITA
        # ---------------------------------
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
            hora_cita=hora_texto if hora_texto else None,
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
            "Agendar y terminar este proceso no garantiza la cita inmediata.\n"
            "Recibirás confirmación por este medio.\n\n"
            " 🕘 Horario de atención: 9:00 AM - 12:00 PM\n\n"
            "Gracias por confiar en nosotros💙\n\n"

            "¿Deseas agendar otra cita?(es necesario seleccionar una opción)\n\n"
            "1️⃣ Mismo paciente\n" 
            "2️⃣ Otro paciente\n"
            "3️⃣ No, gracias"
        )
        sesiones[numero]["paso"] = "post_cita"
        return

    except Exception as e:
        db.session.rollback()
        agregar_mensajes_log(str(e))

        enviar_texto(
            numero,
            "❌ Ocurrió un error guardando tu solicitud."
        )

    sesiones[numero] = {
        "modo": "humano",
        "modo_humano_inicio": datetime.utcnow()
    }
