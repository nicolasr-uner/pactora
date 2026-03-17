"""
normativa_db.py — Base de datos normativa FNCER / Generación Distribuida para Unergy.
Fuente estática (hardcoded). No requiere base de datos ni scraping en tiempo real.
"""
from __future__ import annotations
from typing import List, Dict, Any

NORMATIVA: List[Dict[str, Any]] = [
    {
        "id": "ley_1715_2014",
        "tipo": "Ley",
        "numero": "1715",
        "año": 2014,
        "nombre": "Ley 1715 de 2014",
        "titulo": "Regulación de la integración de energías renovables no convencionales al Sistema Energético Nacional",
        "entidad": "Congreso de la República",
        "fecha": "2014-05-13",
        "estado": "Vigente",
        "url": "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=57353",
        "resumen": "Marco general para la promoción de FNCER. Establece incentivos tributarios (Art. 11-14): deducción del 50% de inversiones en renta, exclusión de IVA, exención arancelaria, depreciación acelerada. Define autogeneración a pequeña escala y generación distribuida. Crea el FENOGE.",
        "articulos_clave": [
            {"articulo": "Art. 5", "tema": "Definición de Generación Distribuida"},
            {"articulo": "Art. 8", "tema": "Promoción de autogeneración a pequeña escala"},
            {"articulo": "Art. 11", "tema": "Incentivo: deducción en renta del 50%"},
            {"articulo": "Art. 12", "tema": "Incentivo: exclusión de IVA"},
            {"articulo": "Art. 13", "tema": "Incentivo: exención arancelaria"},
            {"articulo": "Art. 14", "tema": "Incentivo: depreciación acelerada (5 años)"},
        ],
        "aplica_a": ["PPA", "EPC", "O&M", "Tax Partnership"],
        "tags": ["FNCER", "incentivos_tributarios", "autogeneración", "generación_distribuida"],
    },
    {
        "id": "ley_2099_2021",
        "tipo": "Ley",
        "numero": "2099",
        "año": 2021,
        "nombre": "Ley 2099 de 2021",
        "titulo": "Ley de Transición Energética",
        "entidad": "Congreso de la República",
        "fecha": "2021-07-10",
        "estado": "Vigente",
        "url": "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=166326",
        "resumen": "Amplía y modifica la Ley 1715. Extiende incentivos tributarios al hidrógeno verde y azul. Crea el marco para comunidades energéticas. Establece metas de capacidad instalada renovable. Refuerza rol de UPME en planeación.",
        "articulos_clave": [
            {"articulo": "Art. 7", "tema": "Extensión incentivos a hidrógeno verde"},
            {"articulo": "Art. 45", "tema": "Comunidades energéticas (primera mención)"},
        ],
        "aplica_a": ["PPA", "EPC", "Tax Partnership"],
        "tags": ["FNCER", "transición_energética", "hidrógeno_verde", "comunidades_energéticas"],
    },
    {
        "id": "ley_2294_2023",
        "tipo": "Ley",
        "numero": "2294",
        "año": 2023,
        "nombre": "Ley 2294 de 2023",
        "titulo": "Plan Nacional de Desarrollo 2022-2026",
        "entidad": "Congreso de la República",
        "fecha": "2023-05-19",
        "estado": "Vigente",
        "resumen": "Artículo 235 establece marco para comunidades energéticas. Promueve democratización del acceso a energía limpia. Vinculado a ODS 7.",
        "articulos_clave": [
            {"articulo": "Art. 235", "tema": "Comunidades energéticas — marco legal"},
        ],
        "aplica_a": ["Comunidades Energéticas", "PPA"],
        "tags": ["PND", "comunidades_energéticas", "democratización_energía"],
    },
    {
        "id": "decreto_2236_2023",
        "tipo": "Decreto",
        "numero": "2236",
        "año": 2023,
        "nombre": "Decreto 2236 de 2023",
        "titulo": "Reglamentación de Comunidades Energéticas",
        "entidad": "Ministerio de Minas y Energía",
        "fecha": "2023-12-22",
        "estado": "Vigente",
        "resumen": "Reglamenta Art. 235 de la Ley 2294. Define comunidades energéticas como asociaciones para generación, comercialización y uso eficiente con FNCER. Establece parámetros técnicos y de sostenibilidad.",
        "articulos_clave": [
            {"articulo": "Art. 2.2.9.1.2", "tema": "Definición de Comunidad Energética"},
            {"articulo": "Art. 2.2.9.1.3", "tema": "Actividades permitidas"},
        ],
        "aplica_a": ["Comunidades Energéticas"],
        "tags": ["comunidades_energéticas", "reglamentación"],
    },
    {
        "id": "decreto_929_2023",
        "tipo": "Decreto",
        "numero": "929",
        "año": 2023,
        "nombre": "Decreto 929 de 2023",
        "titulo": "Modificación régimen de autogeneración",
        "entidad": "Ministerio de Minas y Energía",
        "fecha": "2023-06-09",
        "estado": "Vigente",
        "resumen": "Exención de cobro de energía reactiva para AGPE con FNCER (parágrafo 2, Art. 4). Modifica condiciones de autogeneración a pequeña escala.",
        "articulos_clave": [
            {"articulo": "Art. 4, par. 2", "tema": "Exención energía reactiva para AGPE FNCER"},
        ],
        "aplica_a": ["PPA", "O&M", "Autogeneración"],
        "tags": ["autogeneración", "AGPE", "energía_reactiva"],
    },
    {
        "id": "res_creg_030_2018",
        "tipo": "Resolución CREG",
        "numero": "030",
        "año": 2018,
        "nombre": "Resolución CREG 030 de 2018",
        "titulo": "Regulación de autogeneración a pequeña escala y generación distribuida",
        "entidad": "CREG",
        "fecha": "2018-02-26",
        "estado": "Vigente (modificada por Res. 174/2021)",
        "url": "https://gestornormativo.creg.gov.co/gestor/entorno/docs/resolucion_creg_0030_2018.htm",
        "resumen": "Regula mecanismos de conexión, medición bidireccional, créditos de energía y comercialización para AGPE y GD. Define fórmula de remuneración de excedentes. Establece límite de 1MW (AGPE) y procedimiento de conexión.",
        "articulos_clave": [
            {"articulo": "Art. 5", "tema": "Créditos de energía (medición bidireccional)"},
            {"articulo": "Art. 7", "tema": "Fórmula de remuneración de excedentes"},
            {"articulo": "Art. 15", "tema": "Beneficios: 50% de pérdidas técnicas evitadas"},
            {"articulo": "Art. 19", "tema": "GD en Zonas No Interconectadas"},
        ],
        "aplica_a": ["PPA", "EPC", "O&M", "Autogeneración", "GD"],
        "tags": ["CREG", "autogeneración", "generación_distribuida", "créditos_energía", "medición_bidireccional"],
    },
    {
        "id": "res_creg_038_2018",
        "tipo": "Resolución CREG",
        "numero": "038",
        "año": 2018,
        "nombre": "Resolución CREG 038 de 2018",
        "titulo": "Regulación de actividades de autogeneración en el SIN y ZNI",
        "entidad": "CREG",
        "fecha": "2018-03-22",
        "estado": "Vigente",
        "resumen": "Complementa la Res. 030. Define procedimiento de conexión para GD y AGPE. Establece reglas de medición y balance para autogeneradores conectados al SDL.",
        "articulos_clave": [
            {"articulo": "Art. 3", "tema": "Procedimiento de conexión GD"},
            {"articulo": "Art. 8", "tema": "Reglas de medición y balance SDL"},
        ],
        "aplica_a": ["PPA", "EPC", "Autogeneración", "GD"],
        "tags": ["CREG", "conexión", "SIN", "ZNI"],
    },
    {
        "id": "res_creg_174_2021",
        "tipo": "Resolución CREG",
        "numero": "174",
        "año": 2021,
        "nombre": "Resolución CREG 174 de 2021",
        "titulo": "Modificaciones a la regulación de GD y AGPE",
        "entidad": "CREG",
        "fecha": "2021-12-23",
        "estado": "Vigente",
        "resumen": "Modifica reglas de comercialización para GD. Establece que GD puede vender al comercializador integrado. Actualiza fórmula de precio de venta. Define alternativas de entrega de excedentes para AGPE con y sin FNCER.",
        "articulos_clave": [
            {"articulo": "Art. 22 (mod.)", "tema": "Comercialización de GD"},
            {"articulo": "Art. 23 (mod.)", "tema": "Alternativas de excedentes de AGPE"},
        ],
        "aplica_a": ["PPA", "GD", "Autogeneración"],
        "tags": ["CREG", "comercialización", "excedentes", "GD"],
    },
    {
        "id": "res_creg_101_072_2025",
        "tipo": "Resolución CREG",
        "numero": "101 072",
        "año": 2025,
        "nombre": "Resolución CREG 101 072 de 2025",
        "titulo": "Regulación de Comunidades Energéticas",
        "entidad": "CREG",
        "fecha": "2025-04-06",
        "estado": "Vigente",
        "resumen": "Armoniza regulación para integración de comunidades energéticas al SIN. Define Autogeneración Colectiva (AGRC) y Generación Distribuida Colectiva (GDC). Límite de 5MW por comunidad. Dispersión limitada al mismo SDL y mercado de comercialización. Crea RUCE (Registro Único de Comunidades Energéticas). Habilita al menos 1GW adicional de FNCER.",
        "articulos_clave": [
            {"articulo": "Art. 3", "tema": "Definiciones (AGRC, GDC, Comunidad Energética)"},
            {"articulo": "Art. 18", "tema": "Capacidad instalada por usuario"},
            {"articulo": "Art. 19", "tema": "Porcentaje de distribución de excedentes"},
            {"articulo": "Art. 21", "tema": "Tratamiento de excedentes"},
        ],
        "aplica_a": ["Comunidades Energéticas", "PPA", "GD"],
        "tags": ["CREG", "comunidades_energéticas", "AGRC", "GDC", "RUCE"],
    },
    {
        "id": "res_creg_101_070_2025",
        "tipo": "Resolución CREG",
        "numero": "101 070",
        "año": 2025,
        "nombre": "Resolución CREG 101 070 de 2025",
        "titulo": "Actualización de reglas de conexión al SIN",
        "entidad": "CREG",
        "fecha": "2025-02-19",
        "estado": "Vigente",
        "resumen": "Permite uso de activos de conexión de Usuarios No Regulados para conectar generación y demanda al SIN. Flexibiliza negociación de tarifas por uso de infraestructura privada. Agiliza conexión de proyectos renovables.",
        "articulos_clave": [
            {"articulo": "Art. 4", "tema": "Uso de activos privados para conexión SIN"},
            {"articulo": "Art. 7", "tema": "Negociación de tarifas de infraestructura"},
        ],
        "aplica_a": ["EPC", "PPA", "GD"],
        "tags": ["CREG", "conexión", "SIN", "activos_privados"],
    },
    {
        "id": "res_upme_281_2015",
        "tipo": "Resolución UPME",
        "numero": "281",
        "año": 2015,
        "nombre": "Resolución UPME 281 de 2015",
        "titulo": "Límite máximo de potencia para AGPE",
        "entidad": "UPME",
        "fecha": "2015-06-25",
        "estado": "Vigente",
        "resumen": "Define límite máximo de potencia para autogeneración a pequeña escala en 1MW.",
        "articulos_clave": [
            {"articulo": "Art. 1", "tema": "Límite 1MW para AGPE"},
        ],
        "aplica_a": ["Autogeneración", "EPC"],
        "tags": ["UPME", "AGPE", "límite_potencia"],
    },
    {
        "id": "res_upme_501_2024",
        "tipo": "Resolución UPME",
        "numero": "501",
        "año": 2024,
        "nombre": "Resolución UPME 501 de 2024",
        "titulo": "Límites de potencia y dispersión para comunidades energéticas",
        "entidad": "UPME",
        "fecha": "2024-10-15",
        "estado": "Vigente",
        "resumen": "Establece límite de 5MW para AGRC y GDC. La dispersión se limita al mismo SDL y mercado de comercialización.",
        "articulos_clave": [
            {"articulo": "Art. 2", "tema": "Límite 5MW para AGRC/GDC"},
            {"articulo": "Art. 4", "tema": "Restricción de dispersión al mismo SDL"},
        ],
        "aplica_a": ["Comunidades Energéticas"],
        "tags": ["UPME", "comunidades_energéticas", "límite_potencia", "dispersión"],
    },
    {
        "id": "res_mme_40136_2024",
        "tipo": "Resolución MME",
        "numero": "40136",
        "año": 2024,
        "nombre": "Resolución MME 40136 de 2024",
        "titulo": "Creación del RUCE (Registro Único de Comunidades Energéticas)",
        "entidad": "Ministerio de Minas y Energía",
        "fecha": "2024-07-12",
        "estado": "Vigente",
        "resumen": "Crea el Registro Único de Comunidades Energéticas (RUCE) con base en el Decreto 2236 de 2023. Establece los requisitos de inscripción y funcionamiento.",
        "articulos_clave": [
            {"articulo": "Art. 3", "tema": "Requisitos de inscripción en el RUCE"},
            {"articulo": "Art. 7", "tema": "Funcionamiento y actualización del registro"},
        ],
        "aplica_a": ["Comunidades Energéticas"],
        "tags": ["MME", "RUCE", "comunidades_energéticas", "registro"],
    },
]

# Novedades regulatorias recientes (feed estático)
NOVEDADES: List[Dict[str, Any]] = [
    {
        "fecha": "2025-04-06",
        "entidad": "CREG",
        "titulo": "Resolución CREG 101 072 de 2025 — Comunidades Energéticas",
        "resumen": "Regula la integración de comunidades energéticas al SIN. Define AGRC y GDC, crea el RUCE y habilita hasta 1GW adicional de FNCER.",
        "impacto": "alto",
        "impacto_unergy": "Abre mercado de comunidades energéticas para Unergy. Requiere adaptar contratos PPA para incluir cláusulas de AGRC/GDC.",
        "url": "",
    },
    {
        "fecha": "2025-02-19",
        "entidad": "CREG",
        "titulo": "Resolución CREG 101 070 de 2025 — Conexión al SIN con activos privados",
        "resumen": "Flexibiliza el uso de activos privados de UNR para conectar proyectos renovables al SIN.",
        "impacto": "medio",
        "impacto_unergy": "Facilita conexión de proyectos EPC. Revisar contratos de uso de infraestructura.",
        "url": "",
    },
    {
        "fecha": "2024-10-15",
        "entidad": "UPME",
        "titulo": "Resolución UPME 501 de 2024 — Límites comunidades energéticas",
        "resumen": "Establece límite de 5MW por comunidad y restricción de dispersión al mismo SDL.",
        "impacto": "medio",
        "impacto_unergy": "Delimita el tamaño de proyectos de comunidades energéticas. Dimensionar portafolios acordemente.",
        "url": "",
    },
    {
        "fecha": "2024-07-12",
        "entidad": "MME",
        "titulo": "Resolución MME 40136 de 2024 — Creación del RUCE",
        "resumen": "Establece el Registro Único de Comunidades Energéticas con sus requisitos de inscripción.",
        "impacto": "alto",
        "impacto_unergy": "Unergy debe inscribirse en el RUCE para operar proyectos de comunidades energéticas.",
        "url": "",
    },
    {
        "fecha": "2023-12-22",
        "entidad": "MME",
        "titulo": "Decreto 2236 de 2023 — Reglamentación Comunidades Energéticas",
        "resumen": "Primera reglamentación detallada de comunidades energéticas en Colombia.",
        "impacto": "alto",
        "impacto_unergy": "Marco legal base para todos los proyectos de comunidades energéticas de Unergy.",
        "url": "",
    },
]


def get_normativa_for_contract_type(contract_type: str) -> List[Dict[str, Any]]:
    """Filtra la normativa relevante para un tipo de contrato dado."""
    ct = contract_type.upper()
    return [n for n in NORMATIVA if any(ct in a.upper() for a in n.get("aplica_a", []))]


def get_normativa_summary_for_prompt(contract_type: str) -> str:
    """Genera un resumen de normativa aplicable para incluir en prompts de análisis de riesgo."""
    normas = get_normativa_for_contract_type(contract_type)
    if not normas:
        normas = NORMATIVA[:5]  # fallback: primeras 5 normas
    lines = ["Normativa aplicable al contrato (Colombia — FNCER):"]
    for n in normas:
        arts = ", ".join(a["articulo"] for a in n.get("articulos_clave", [])[:3])
        lines.append(f"- {n['nombre']}: {n['resumen'][:120]}. Arts. clave: {arts}")
    return "\n".join(lines)


def search_normativa(query: str) -> List[Dict[str, Any]]:
    """Búsqueda simple por texto en nombre, resumen y tags."""
    q = query.lower()
    return [
        n for n in NORMATIVA
        if q in n["nombre"].lower()
        or q in n["resumen"].lower()
        or any(q in t.lower() for t in n.get("tags", []))
        or q in n.get("titulo", "").lower()
    ]
