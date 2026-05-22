#solo variables
TOKEN_ANDERCODE = "ANDERCODE"
TOKEN_META = "EAAY5YGNZBIz8BRXwA8UTEa16UrRYq3UZAoinyvHxjyXzLsaGAfimXp6qWUD4ZBlMOMywI3nTV3Oet56Ov2L697IbfXA6l8FOwpNvUoXtM0iwS8INTFrq7mpEKBB9rLq3kJXgzRQlv9Ffd2q8ZCRZC8XVYR0opra2ydz68qEfHmCBs0F9ie4AcYtYEGEpDEQZDZD"
PHONE_NUMBER_ID = "1112533955267866"
LINK_ASESOR = "https://wa.me/573118930862"
LINK_EDITORIAL = "https://wa.me/573042151025"
LINK_ALIMENTATEC ="https://wa.me/573235865867"
URL_BASE = "https://python-2-zqc5.onrender.com"
URL_RESULTADOS = "https://cib.org.co/resultados-de-laboratorio/"
SECRET_KEY = "cib_secret_2025"

HORARIO_INICIO = 7
HORARIO_FIN = 17
DIAS_ACTIVOS = [0, 1, 2, 3, 4]   # 0=Lunes ... 4=Viernes
DIAS_BLOQUEADOS = []              # e.g. [date(2025, 12, 25)]]

REQUISITOS = {
    "general": [
        "Documento de identidad vigente",
        "Orden médica si aplica"
    ],

    # ──── EXAMEN DIRECTO HONGOS ────
    "examen_directo_hongos": {
        "Uñas": [
            "No tener esmalte ni maquillaje en las uñas afectadas (3 a 5 días antes)",
            "No cortar ni limpiar la uña por lo menos 20 días antes",
            "No aplicar antitranspirantes ni cremas en el área afectada los 8 días previos",
            "No aplicar tratamientos caseros (límpido, vinagre, etc.) 8 días antes",
            "No haber tomado medicamentos antimicóticos 1 mes antes",
            "No haber aplicado tratamiento tópico para hongos 15 días antes",
            "Venir con calzado cerrado"
        ],
        "Piel": [
            "No aplicar CREMAS en el sitio de la lesión 5 días antes",
            "No aplicar TALCOS en el sitio de la lesión 5 días antes",
            "No haber tomado medicamentos antimicóticos 1 mes antes",
            "No haber aplicado tratamiento para hongos sobre la lesión 15 días antes"
        ],
        "Cuero cabelludo": [
            "No aplicar CREMAS en el sitio de la lesión 5 días antes",
            "No aplicar TALCOS en el sitio de la lesión 5 días antes",
            "No haber tomado medicamentos antimicóticos 1 mes antes",
            "No haber aplicado tratamiento para hongos sobre la lesión 15 días antes"
        ],
        "Flujo vaginal": [
            "No haberse realizado duchas vaginales 1 día antes",
            "No haber tomado medicamentos antimicóticos 15 días antes",
            "Esperar 10 días si se aplicó medicamento tópico vaginal (óvulos o cremas)",
            "Esperar mínimo 1 día si ha tenido relaciones sexuales"
        ]
    },

    # ──── HONGOS + CULTIVO ────
    "examen_directo_cultivo": {
        "Uñas": [
            "No tener esmalte ni maquillaje en las uñas afectadas (3 a 5 días antes)",
            "No cortar ni limpiar la uña por lo menos 20 días antes",
            "No aplicar antitranspirantes ni cremas en el área afectada los 8 días previos",
            "No aplicar tratamientos caseros (límpido, vinagre, etc.) 8 días antes",
            "No haber tomado medicamentos antimicóticos 1 mes antes",
            "No haber aplicado tratamiento tópico para hongos 15 días antes",
            "Venir con calzado cerrado"
        ],
        "Piel": [
            "No aplicar CREMAS en el sitio de la lesión 5 días antes",
            "No aplicar TALCOS en el sitio de la lesión 5 días antes",
            "No haber tomado medicamentos antimicóticos 1 mes antes",
            "No haber aplicado tratamiento para hongos sobre la lesión 15 días antes"
        ],
        "Cuero cabelludo": [
            "No aplicar CREMAS en el sitio de la lesión 5 días antes",
            "No aplicar TALCOS en el sitio de la lesión 5 días antes",
            "No haber tomado medicamentos antimicóticos 1 mes antes",
            "No haber aplicado tratamiento para hongos sobre la lesión 15 días antes"
        ],
        "Flujo vaginal": [
            "No haberse realizado duchas vaginales 1 día antes",
            "No haber tomado medicamentos antimicóticos 15 días antes",
            "Esperar 10 días si se aplicó medicamento tópico vaginal (óvulos o cremas)",
            "Esperar mínimo 1 día si ha tenido relaciones sexuales"
        ]
    },

    # ──── ANTÍGENOS Y SEROLOGÍAS → requieren suero ────
    "examen_galactomanano": [
        "No requiere ayuno"
    ],
    "examen_cryptococcus": [
        "No requiere ayuno"
    ],
    "examen_serologia_inmuno": [
        "No requiere ayuno"
    ],
    "examen_serologia_complemento": [
        "Requiere ayuno (única prueba de suero que lo exige)"
    ],
    "examen_igra": [
        "No requiere ayuno"
    ],

    # ──── TUBERCULINA PPD ────
    "examen_ppd": [
        "No haber recibido vacunas en las últimas 4 a 6 semanas",
        "No repetir la prueba si una anterior fue positiva",
        "No realizarse si tuvo reacción fuerte previa (necrosis, ampollas, choque anafiláctico)",
        "No tener diagnóstico de TB activa ni estar en tratamiento antituberculoso",
        "No tener una infección por TB muy antigua",
        "No tener menos de seis meses de edad",
        "No tener infecciones virales activas (sarampión, varicela)",
        "Informar si está recibiendo corticoesteroides o inmunosupresores (pueden alterar el resultado)"
    ],

    # ──── OTROS ────
    "examen_otro": [
        "Traer orden médica",
        "Consultar requisitos específicos con el laboratorio"
    ],
    "domicilio": [
        "Documento de identidad vigente",
        "Dirección completa y detallada",
        "Disponibilidad entre 7:30am y 1:00pm"
    ]
}