import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

OUTLOOK_EMAIL    = os.getenv('OUTLOOK_EMAIL', 'aprendizti@cib.org.co')
OUTLOOK_PASSWORD = os.getenv('OUTLOOK_PASSWORD', 'higuita_29')

def enviar_recordatorio(correo_destino, nombre_paciente, fecha_cita, tipo_examen, dias_antes):
    if not correo_destino:
        return False

    asunto = f"Recordatorio: Su cita es {'mañana' if dias_antes == 1 else 'en 2 días'}"

    cuerpo = f"""
    <html>
    <body style="margin:0; padding:0; background-color:#f4f6f9; font-family:Arial, sans-serif;">

    <div style="max-width:600px; margin:30px auto; background:#ffffff;
                border-radius:12px; overflow:hidden;
                box-shadow:0 2px 8px rgba(0,0,0,0.08);">

        <!-- Encabezado -->
        <div style="background:#005792; padding:25px; text-align:center;">
            <h2 style="color:white; margin:0;">
                Recordatorio de Cita
            </h2>
        </div>

        <!-- Contenido -->
        <div style="padding:35px; color:#333;">

            <p style="font-size:16px;">
                Estimado/a <strong>{nombre_paciente}</strong>,
            </p>

            <p style="line-height:1.6;">
                Le recordamos que tiene una cita programada
                <strong style="color:#005792;">
                    {'mañana' if dias_antes == 1 else 'en 2 días'}
                </strong>.
            </p>

            <!-- Caja de información -->
            <div style="
                background:#f8fafc;
                border-left:5px solid #005792;
                padding:18px;
                border-radius:8px;
                margin:20px 0;
            ">
                <p style="margin:8px 0;">
                    📅 <strong>Fecha:</strong>
                    {fecha_cita.strftime('%d/%m/%Y %H:%M')}
                </p>

                <p style="margin:8px 0;">
                    🧪 <strong>Examen:</strong>
                    {tipo_examen}
                </p>
            </div>

            <p style="line-height:1.6;">
                Por favor llegue <strong>10 minutos antes</strong> de su cita.
            </p>

            <p style="line-height:1.6;">
                Si necesita cancelar o reprogramar, comuníquese con nosotros con anticipación.
            </p>

        </div>

        <!-- Footer -->
        <div style="
            background:#f1f3f5;
            text-align:center;
            padding:18px;
            color:#666;
            font-size:13px;
        ">
            <strong>CIB - Centro de Infectología y Bacteriología</strong><br>
            Este es un mensaje automático.
        </div>

    </div>

    </body>
    </html>
    """
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = asunto
        msg['From']    = OUTLOOK_EMAIL
        msg['To']      = correo_destino
        msg.attach(MIMEText(cuerpo, 'html'))

        with smtplib.SMTP('smtp.office365.com', 587) as server:
            server.starttls()
            server.login(OUTLOOK_EMAIL, OUTLOOK_PASSWORD)
            server.sendmail(OUTLOOK_EMAIL, correo_destino, msg.as_string())

        print(f"Recordatorio enviado a {correo_destino}")
        return True

    except Exception as e:
        print(f"Error enviando correo a {correo_destino}: {e}")
        return False