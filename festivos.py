"""
Festivos fijos y móviles de Colombia.
Ley Emiliani: festivos que no caen en lunes se trasladan
al siguiente lunes (excepto los marcados como fijos).
"""
from datetime import date, timedelta

def _siguiente_lunes(d: date) -> date:
    """Desplaza d al lunes siguiente si no es lunes."""
    dias = (7 - d.weekday()) % 7
    return d if dias == 0 else d + timedelta(days=dias)

def _pascua(year: int) -> date:
    """Algoritmo de Butcher para calcular el Domingo de Pascua."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19*a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2*e + 2*i - h - k) % 7
    m = (a + 11*h + 22*l) // 451
    month = (h + l - 7*m + 114) // 31
    day   = ((h + l - 7*m + 114) % 31) + 1
    return date(year, month, day)

def festivos_colombia(year: int) -> set:
    pascua   = _pascua(year)
    festivos = set()

    # ── Fijos (no se trasladan) ──────────────────────────
    fijos = [
        date(year, 1,  1),   # Año nuevo
        date(year, 5,  1),   # Día del Trabajo
        date(year, 7,  20),  # Independencia
        date(year, 8,  7),   # Boyacá
        date(year, 12, 8),   # Inmaculada Concepción
        date(year, 12, 25),  # Navidad
    ]
    festivos.update(fijos)

    # ── Ley Emiliani (traslado al siguiente lunes) ───────
    emiliani = [
        date(year, 1,  6),   # Reyes Magos
        date(year, 3,  19),  # San José
        date(year, 6,  29),  # San Pedro y San Pablo
        date(year, 8,  15),  # Asunción
        date(year, 10, 12),  # Día de la Raza
        date(year, 11, 1),   # Todos los Santos
        date(year, 11, 11),  # Independencia Cartagena
    ]
    for d in emiliani:
        festivos.add(_siguiente_lunes(d))

    # ── Relativos a Pascua ───────────────────────────────
    relativos = {
        -3:  "Jueves Santo",
        -2:  "Viernes Santo",
        39:  "Ascensión",
        60:  "Corpus Christi",
        68:  "Sagrado Corazón",
    }
    for delta, _ in relativos.items():
        d = pascua + timedelta(days=delta)
        # Ascensión, Corpus y Sagrado Corazón → Ley Emiliani
        if delta in (39, 60, 68):
            d = _siguiente_lunes(d)
        festivos.add(d)

    return festivos


# Cache por año para no recalcular en cada iteración
_cache: dict[int, set] = {}

def es_festivo(d: date) -> bool:
    if d.year not in _cache:
        _cache[d.year] = festivos_colombia(d.year)
    return d in _cache[d.year]