from datetime import datetime, timedelta
from email_recordatorio import enviar_recordatorio

enviar_recordatorio(
    correo_destino  = "correaisabella097@gmail.com",
    nombre_paciente = "Paciente de Prueba",
    fecha_cita      = datetime.now() + timedelta(days=1),
    tipo_examen     = "Micología",
    dias_antes      = 1
)