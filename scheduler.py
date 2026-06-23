import threading
from datetime import datetime, timedelta

MENSAJES_RECORDATORIO = [
    "Hola, nuestro asesor sigue en línea esperando tu respuesta. 😊",
    "¿Sigues ahí? El asesor continúa disponible para ayudarte.",
    "Último aviso, el asesor está esperando tu respuesta.",
]

def iniciar_scheduler(app):

    # ── Job 1: recordatorio de citas por correo ──────────────────────
    def verificar_recordatorios():
        with app.app_context():
            from models import Cita, Paciente
            from email_recordatorio import enviar_recordatorio

            ahora = datetime.now()

            for dias in [1, 2]:
                inicio = (ahora + timedelta(days=dias)).replace(hour=0, minute=0, second=0, microsecond=0)
                fin    = inicio.replace(hour=23, minute=59, second=59)

                citas = Cita.query.filter(
                    Cita.fecha_cita >= inicio,
                    Cita.fecha_cita <= fin,
                    Cita.estado == 'confirmada'
                ).all()

                for cita in citas:
                    paciente = Paciente.query.get(cita.paciente_id)
                    if paciente and paciente.correo:
                        enviar_recordatorio(
                            correo_destino  = paciente.correo,
                            nombre_paciente = paciente.nombre,
                            fecha_cita      = cita.fecha_cita,
                            tipo_examen     = cita.tipo_examen,
                            dias_antes      = dias
                        )

    # ── Job 2: chats inactivos con asesor ────────────────────────────
    def verificar_chats_inactivos():
        with app.app_context():
            from models import ChatActivo, db
            from mensajes import enviar_texto

            ahora = datetime.utcnow()
            chats = ChatActivo.query.filter_by(activo=True).all()

            for chat in chats:
                if not chat.primer_mensaje_asesor:
                    continue

                referencia       = chat.ultimo_mensaje_paciente or chat.primer_mensaje_asesor
                minutos_inactivo = (ahora - referencia).total_seconds() / 60
                umbral           = 30 * (chat.recordatorios_enviados + 1)

                if minutos_inactivo < umbral:
                    continue

                if chat.recordatorios_enviados < 3:
                    enviar_texto(
                        chat.numero,
                        MENSAJES_RECORDATORIO[chat.recordatorios_enviados]
                    )
                    chat.recordatorios_enviados += 1
                    db.session.commit()
                else:
                    enviar_texto(
                        chat.numero,
                        "La sesión con el asesor ha finalizado. El asistente automático retomará la conversación."
                    )
                    db.session.delete(chat)
                    db.session.commit()

    # ── Loop principal del scheduler ─────────────────────────────────
    def loop():
        ultimo_recordatorio = None  # controla que solo corra una vez al día a las 8am

        while True:
            ahora = datetime.now()

            # Job 1: corre a las 8:00 AM una vez por día
            if ahora.hour == 8 and ahora.minute == 0:
                hoy = ahora.date()
                if ultimo_recordatorio != hoy:
                    try:
                        verificar_recordatorios()
                    except Exception as e:
                        print(f"[scheduler] Error en recordatorios: {e}")
                    ultimo_recordatorio = hoy

            # Job 2: corre cada 5 minutos
            if ahora.minute % 5 == 0 and ahora.second < 10:
                try:
                    verificar_chats_inactivos()
                except Exception as e:
                    print(f"[scheduler] Error en chats inactivos: {e}")

            # Duerme 10 segundos entre cada chequeo
            threading.Event().wait(10)

    hilo = threading.Thread(target=loop, daemon=True)
    hilo.start()
    print("Scheduler iniciado (threading)")


# ── Manual (para pruebas) ────────────────────────────────────────────
def verificar_recordatorios_manual(app):
    with app.app_context():
        from models import Cita, Paciente
        from email_recordatorio import enviar_recordatorio

        ahora = datetime.now()

        for dias in [1, 2]:
            inicio = (ahora + timedelta(days=dias)).replace(hour=0, minute=0, second=0, microsecond=0)
            fin    = (ahora + timedelta(days=dias)).replace(hour=23, minute=59, second=59, microsecond=0)

            citas = Cita.query.filter(
                Cita.fecha_cita >= inicio,
                Cita.fecha_cita <= fin,
                Cita.estado == 'confirmada'
            ).all()

            print(f"Citas encontradas para +{dias} días: {len(citas)}")

            for cita in citas:
                paciente = Paciente.query.get(cita.paciente_id)
                print(f"  → Paciente: {paciente.nombre if paciente else 'NO ENCONTRADO'}, correo: {paciente.correo if paciente else 'N/A'}")
                if paciente and paciente.correo:
                    enviar_recordatorio(
                        correo_destino  = paciente.correo,
                        nombre_paciente = paciente.nombre,
                        fecha_cita      = cita.fecha_cita,
                        tipo_examen     = cita.tipo_examen,
                        dias_antes      = dias
                    )