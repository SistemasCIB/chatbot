from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

def iniciar_scheduler(app):
    scheduler = BackgroundScheduler(timezone='America/Bogota')

    def verificar_recordatorios():
        with app.app_context():
            from models import Cita, Paciente
            from email_recordatorio import enviar_recordatorio

            ahora = datetime.now()

            for dias in [1, 2]:
                inicio = ahora + timedelta(days=dias)
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

    # Ejecuta todos los días a las 8:00 AM
    scheduler.add_job(verificar_recordatorios, 'cron', hour=8, minute=0)
    scheduler.start()
    print("Scheduler de recordatorios iniciado")
    return scheduler
def verificar_recordatorios_manual(app):
    with app.app_context():
        from models import Cita, Paciente
        from email_recordatorio import enviar_recordatorio
        from datetime import datetime, timedelta

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