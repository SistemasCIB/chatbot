"""
Corre con: python test_disponibilidad.py

Usa la misma DATABASE_URL que tu app.py (la de testing, si ya la
tienes exportada en tu entorno local). No toca WhatsApp para nada.
"""

from datetime import date, time, timedelta

# ← ajusta este import si tu archivo principal no se llama app.py
from app import app, db
from disponibilidad import validar_disponibilidad


def probar_semana(tipo_cita, area=None, origen="bot"):
    print(f"\n--- {tipo_cita} | origen={origen} | area={area} ---")
    hoy = date.today()
    dias_es = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    for i in range(14):
        dia = hoy + timedelta(days=i)
        ok, motivo = validar_disponibilidad(dia, None, tipo_cita, area=area, origen=origen)
        estado = "✅ disponible" if ok else f"❌ {motivo}"
        print(f"{dias_es[dia.weekday()]} {dia.strftime('%d/%m')} → {estado}")


def probar_hora(fecha_str, hora_str, tipo_cita, area=None, origen="bot"):
    dia = date.fromisoformat(fecha_str)
    hora = time.fromisoformat(hora_str)
    ok, motivo = validar_disponibilidad(dia, hora, tipo_cita, area=area, origen=origen)
    estado = "✅ disponible" if ok else f"❌ {motivo}"
    print(f"{fecha_str} {hora_str} ({tipo_cita}, origen={origen}) → {estado}")


if __name__ == "__main__":
    with app.app_context():
        # 1) Qué días ofrecería el BOT
        probar_semana("presencial", area="Micología", origen="bot")
        probar_semana("presencial", area="Bacteriología", origen="bot")
        probar_semana("domicilio", origen="bot")

        # 2) Qué días permite la AGENDA MANUAL
        probar_semana("presencial", area="Micología", origen="manual")
        probar_semana("presencial", area="Bacteriología", origen="manual")
        probar_semana("domicilio", origen="manual")

        # 3) Caso puntual — cambia por una fecha con un bloqueo/cupo
        probar_hora("2026-09-01", "08:00", "presencial", area="Micología", origen="bot")
        probar_hora("2026-09-01", "08:00", "presencial", area="Micología", origen="manual")