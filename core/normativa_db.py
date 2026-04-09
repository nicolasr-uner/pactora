"""
normativa_db.py — Base de datos normativa FNCER / Generación Distribuida para Unergy.
Fuente estática (hardcoded). No requiere base de datos ni scraping en tiempo real.
Países: Colombia, Ecuador, México, Brasil. v2.0 — multi-país.
"""
from __future__ import annotations
from typing import List, Dict, Any

_VERSION = "2.0.0-multi-pais"  # cache-bust: no borrar

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


# ─── Datos regulatorios por país ──────────────────────────────────────────────

NORMATIVA_ECUADOR: List[Dict[str, Any]] = [
    {
        "id": "lose_2015_ec", "tipo": "Ley", "numero": "LOSE", "año": 2015,
        "nombre": "Ley Orgánica del Sector Eléctrico (LOSE)",
        "titulo": "Marco regulatorio del sector eléctrico ecuatoriano",
        "entidad": "Asamblea Nacional del Ecuador", "fecha": "2015-01-16", "estado": "Vigente",
        "url": "https://www.regulacionelectrica.gob.ec",
        "resumen": "Define el marco institucional del sector eléctrico. Crea la ARCERNNR como ente regulador. Establece las actividades de generación, transmisión, distribución y comercialización. Promueve el desarrollo de energías renovables.",
        "articulos_clave": [
            {"articulo": "Art. 3", "tema": "Principios del sector eléctrico"},
            {"articulo": "Art. 10", "tema": "Creación de la ARCERNNR"},
            {"articulo": "Art. 63", "tema": "Autogeneración y generación distribuida"},
        ],
        "aplica_a": ["PPA", "EPC", "O&M", "Autogeneración"],
        "tags": ["LOSE", "ARCERNNR", "sector_eléctrico", "Ecuador"],
    },
    {
        "id": "res_arcernnr_019_2021_ec", "tipo": "Resolución ARCERNNR", "numero": "019/21", "año": 2021,
        "nombre": "Resolución ARCERNNR Nro. 019/21",
        "titulo": "Regulación para la generación fotovoltaica y renovable en Ecuador",
        "entidad": "ARCERNNR", "fecha": "2021-08-30", "estado": "Vigente",
        "url": "https://www.regulacionelectrica.gob.ec",
        "resumen": "Establece los procedimientos para la conexión de generación fotovoltaica distribuida. Define tarifa de excedentes (net billing). Límites: hasta 1MW para usuarios regulados y hasta 10MW para no regulados.",
        "articulos_clave": [
            {"articulo": "Art. 4", "tema": "Límites de potencia para autogeneración"},
            {"articulo": "Art. 8", "tema": "Tarifa de excedentes — net billing"},
            {"articulo": "Art. 12", "tema": "Procedimiento de conexión a la red"},
        ],
        "aplica_a": ["PPA", "EPC", "Autogeneración", "GD"],
        "tags": ["ARCERNNR", "fotovoltaico", "net_billing", "GD", "Ecuador"],
    },
    {
        "id": "plan_maestro_ec", "tipo": "Plan Nacional", "numero": "PME 2031", "año": 2023,
        "nombre": "Plan Maestro de Electricidad 2031",
        "titulo": "Planificación de la expansión del sistema eléctrico ecuatoriano",
        "entidad": "Ministerio de Energía y Minas Ecuador", "fecha": "2023-06-01", "estado": "Vigente",
        "url": "https://www.energiayrecursosnaturales.gob.ec",
        "resumen": "Planificación de expansión de generación y transmisión al 2031. Meta: 80% de generación renovable. Incluye proyectos solares y eólicos a gran escala. Define prioridades de inversión en FNCER.",
        "articulos_clave": [
            {"articulo": "Cap. 4", "tema": "Expansión de generación renovable"},
            {"articulo": "Cap. 7", "tema": "Proyectos solares y eólicos prioritarios"},
        ],
        "aplica_a": ["PPA", "EPC"],
        "tags": ["PME", "planificación", "renovables", "Ecuador"],
    },
    {
        "id": "contrato_concesion_ec", "tipo": "Reglamento", "numero": "Reg. 1274", "año": 2020,
        "nombre": "Reglamento para Contratos de Concesión de Energía Renovable",
        "titulo": "Marco contractual para concesiones de generación renovable en Ecuador",
        "entidad": "ARCERNNR", "fecha": "2020-11-15", "estado": "Vigente",
        "url": "https://www.regulacionelectrica.gob.ec",
        "resumen": "Define las condiciones para contratos de concesión de proyectos de generación con FNCER. Establece garantías, plazos (hasta 20 años), indexación tarifaria y condiciones de terminación.",
        "articulos_clave": [
            {"articulo": "Art. 5", "tema": "Plazos de concesión (hasta 20 años)"},
            {"articulo": "Art. 9", "tema": "Garantías de cumplimiento"},
            {"articulo": "Art. 15", "tema": "Indexación tarifaria"},
        ],
        "aplica_a": ["PPA", "SHA"],
        "tags": ["concesión", "renovables", "contratos", "Ecuador"],
    },
]

NORMATIVA_MEXICO: List[Dict[str, Any]] = [
    {
        "id": "lte_2015_mx", "tipo": "Ley", "numero": "LTE", "año": 2015,
        "nombre": "Ley de Transición Energética (LTE)",
        "titulo": "Marco para el desarrollo de energías limpias en México",
        "entidad": "Congreso de la Unión", "fecha": "2015-12-24", "estado": "Vigente",
        "url": "https://www.dof.gob.mx",
        "resumen": "Establece metas de energías limpias: 35% al 2024, 43% al 2030. Define los certificados de energías limpias (CEL). Regula la generación limpia distribuida y los contratos de cobertura eléctrica. SENER como ente rector.",
        "articulos_clave": [
            {"articulo": "Art. 3", "tema": "Definiciones de energía limpia y renovable"},
            {"articulo": "Art. 16", "tema": "Certificados de Energías Limpias (CEL)"},
            {"articulo": "Art. 22", "tema": "Generación limpia distribuida"},
        ],
        "aplica_a": ["PPA", "EPC", "Tax Partnership"],
        "tags": ["LTE", "CEL", "transición_energética", "México"],
    },
    {
        "id": "cre_contrato_cobertura_mx", "tipo": "Resolución CRE", "numero": "RES/203/2022", "año": 2022,
        "nombre": "Resolución CRE RES/203/2022",
        "titulo": "Contratos de cobertura eléctrica y PPA en mercado eléctrico mayorista",
        "entidad": "Comisión Reguladora de Energía (CRE)", "fecha": "2022-03-10", "estado": "Vigente",
        "url": "https://www.gob.mx/cre",
        "resumen": "Regula los contratos de cobertura eléctrica (equivalente al PPA en el mercado mayorista). Define las condiciones de precio, plazo, garantías financieras y procedimiento de registro ante el CENACE. Plazo máximo: 25 años.",
        "articulos_clave": [
            {"articulo": "Art. 5", "tema": "Condiciones de precio y plazo"},
            {"articulo": "Art. 11", "tema": "Garantías financieras requeridas"},
            {"articulo": "Art. 18", "tema": "Registro de contratos ante el CENACE"},
        ],
        "aplica_a": ["PPA", "SHA"],
        "tags": ["CRE", "PPA", "cobertura_eléctrica", "CENACE", "México"],
    },
    {
        "id": "gdbt_cfe_mx", "tipo": "Tarifa", "numero": "GDBT", "año": 2023,
        "nombre": "Tarifa GDBT — Generación Distribuida Baja Tensión",
        "titulo": "Esquema de generación distribuida y net metering en México",
        "entidad": "CFE / SENER", "fecha": "2023-01-01", "estado": "Vigente",
        "url": "https://www.cfe.mx",
        "resumen": "Regula la generación distribuida hasta 500kW en baja tensión. Define el esquema de medición neta (net metering) con créditos de energía. Contratos de interconexión de hasta 10 años con CFE. Aplica para autoconsumo con excedentes.",
        "articulos_clave": [
            {"articulo": "Cláusula 3", "tema": "Límite de 500kW para GDBT"},
            {"articulo": "Cláusula 7", "tema": "Medición neta y créditos de energía"},
            {"articulo": "Cláusula 12", "tema": "Contrato de interconexión — plazo"},
        ],
        "aplica_a": ["EPC", "O&M", "Autogeneración"],
        "tags": ["CFE", "net_metering", "GD", "México"],
    },
    {
        "id": "res_cenace_mx", "tipo": "Resolución CENACE", "numero": "DIR-001/2023", "año": 2023,
        "nombre": "Directiva CENACE DIR-001/2023",
        "titulo": "Operación del mercado eléctrico mayorista para generadores renovables",
        "entidad": "CENACE", "fecha": "2023-05-20", "estado": "Vigente",
        "url": "https://www.cenace.gob.mx",
        "resumen": "Establece las reglas de participación de generadores renovables en el mercado spot. Define los perfiles de generación esperada, penalidades por desvíos y el tratamiento de la energía en el mercado de balance.",
        "articulos_clave": [
            {"articulo": "Cap. 3", "tema": "Perfiles de generación esperada"},
            {"articulo": "Cap. 5", "tema": "Penalidades por desvíos de generación"},
        ],
        "aplica_a": ["PPA", "EPC"],
        "tags": ["CENACE", "mercado_mayorista", "renovables", "México"],
    },
]

NORMATIVA_BRASIL: List[Dict[str, Any]] = [
    {
        "id": "lei_14300_2022_br", "tipo": "Lei", "numero": "14.300", "año": 2022,
        "nombre": "Lei 14.300 de 2022",
        "titulo": "Marco Legal da Micro e Minigeração Distribuída",
        "entidad": "Congresso Nacional", "fecha": "2022-01-06", "estado": "Vigente",
        "url": "https://www.planalto.gov.br",
        "resumen": "Consolida o marco regulatório da geração distribuída no Brasil. Define micro (até 75kW) e minigeração (75kW a 5MW). Estabelece o sistema de compensação de energia (net metering avançado). Garante direitos dos consumidores-geradores. Prazo de transição até 2045.",
        "articulos_clave": [
            {"articulo": "Art. 2", "tema": "Definições de micro e minigeração"},
            {"articulo": "Art. 7", "tema": "Sistema de compensação de energia elétrica"},
            {"articulo": "Art. 15", "tema": "Geração compartilhada e autoconsumo remoto"},
        ],
        "aplica_a": ["PPA", "EPC", "O&M", "Autogeneração"],
        "tags": ["marco_legal", "GD", "net_metering", "minigeração", "Brasil"],
    },
    {
        "id": "ren_aneel_1000_2021_br", "tipo": "Resolução ANEEL", "numero": "1000", "año": 2021,
        "nombre": "Resolução Normativa ANEEL 1000/2021",
        "titulo": "Condições gerais de fornecimento de energia elétrica",
        "entidad": "ANEEL", "fecha": "2021-12-07", "estado": "Vigente",
        "url": "https://www.aneel.gov.br",
        "resumen": "Consolida as regras de acesso e conexão ao sistema de distribuição. Define procedimentos para geração distribuída, prazos de conexão e requisitos técnicos. Estabelece penalidades para distribuidoras que atrasem conexões de GD.",
        "articulos_clave": [
            {"articulo": "Art. 185", "tema": "Acesso de micro e minigeração à rede"},
            {"articulo": "Art. 192", "tema": "Prazo máximo de conexão (65 dias)"},
            {"articulo": "Art. 201", "tema": "Requisitos técnicos de medição"},
        ],
        "aplica_a": ["EPC", "O&M", "Autogeneração"],
        "tags": ["ANEEL", "GD", "conexão", "distribuição", "Brasil"],
    },
    {
        "id": "ppa_mercado_livre_br", "tipo": "Resolução ANEEL", "numero": "876", "año": 2020,
        "nombre": "Resolução ANEEL 876/2020 — Mercado Livre",
        "titulo": "Contratos de compra de energia no Ambiente de Contratação Livre (ACL)",
        "entidad": "ANEEL", "fecha": "2020-03-11", "estado": "Vigente",
        "url": "https://www.aneel.gov.br",
        "resumen": "Regula os contratos bilaterais de energia no mercado livre (ACL). Define condições para PPAs de longo prazo entre geradores e consumidores livres. Prazo mínimo: 1 ano. Registro obrigatório na CCEE.",
        "articulos_clave": [
            {"articulo": "Art. 3", "tema": "Tipos de contratos no ACL"},
            {"articulo": "Art. 8", "tema": "Prazo e condições dos contratos PPA"},
            {"articulo": "Art. 14", "tema": "Registro obrigatório na CCEE"},
        ],
        "aplica_a": ["PPA", "SHA"],
        "tags": ["PPA", "ACL", "mercado_livre", "CCEE", "Brasil"],
    },
    {
        "id": "ccee_regras_br", "tipo": "Regras CCEE", "numero": "REH 2.166", "año": 2023,
        "nombre": "Regras de Comercialização CCEE — REH 2.166/2023",
        "titulo": "Regras do mercado de comercialização de energia elétrica",
        "entidad": "CCEE", "fecha": "2023-09-15", "estado": "Vigente",
        "url": "https://www.ccee.org.br",
        "resumen": "Define as regras de liquidação financeira do mercado spot (PLD). Estabelece procedimentos de medição e apuração. Regula a contabilização de contratos de energia e penalidades por exposição involuntária ao spot.",
        "articulos_clave": [
            {"articulo": "Cap. 4", "tema": "Liquidação financeira e PLD"},
            {"articulo": "Cap. 7", "tema": "Apuração e contabilização de contratos"},
        ],
        "aplica_a": ["PPA"],
        "tags": ["CCEE", "PLD", "mercado_spot", "liquidação", "Brasil"],
    },
]

# Novedades por país
NOVEDADES_COLOMBIA = NOVEDADES  # alias para compatibilidad

NOVEDADES_ECUADOR: List[Dict[str, Any]] = [
    {
        "fecha": "2025-03-15", "entidad": "ARCERNNR", "pais": "Ecuador",
        "titulo": "ARCERNNR amplía límite de generación distribuida a 2MW",
        "resumen": "La nueva regulación eleva el límite de potencia para generación fotovoltaica distribuida de 1MW a 2MW para usuarios no regulados, facilitando proyectos industriales.",
        "impacto": "alto",
        "impacto_unergy": "Abre oportunidades para proyectos industriales solares en Ecuador. Revisar contratos EPC y PPA para actualizar límites de potencia.",
        "url": "https://www.regulacionelectrica.gob.ec",
    },
    {
        "fecha": "2024-11-20", "entidad": "Ministerio de Energía", "pais": "Ecuador",
        "titulo": "Plan de expansión renovable 2025-2030 — Ecuador suma 3GW de solar",
        "resumen": "Ecuador anuncia plan para agregar 3GW de energía solar al 2030, con licitaciones anuales de 500MW. Se establecen contratos PPA de 20 años con el Estado.",
        "impacto": "alto",
        "impacto_unergy": "Oportunidad significativa para participar en licitaciones. Preparar propuestas EPC y PPA para el mercado ecuatoriano.",
        "url": "https://www.energiayrecursosnaturales.gob.ec",
    },
    {
        "fecha": "2024-08-10", "entidad": "ARCERNNR", "pais": "Ecuador",
        "titulo": "Nueva tarifa de excedentes (net billing) actualizada",
        "resumen": "ARCERNNR actualiza la tarifa de remuneración de excedentes fotovoltaicos. Se adopta el modelo de net billing con precio horario del mercado, reemplazando el precio fijo anterior.",
        "impacto": "medio",
        "impacto_unergy": "Revisar modelos financieros de proyectos con autoconsumo y excedentes en Ecuador.",
        "url": "https://www.regulacionelectrica.gob.ec",
    },
]

NOVEDADES_MEXICO: List[Dict[str, Any]] = [
    {
        "fecha": "2025-02-28", "entidad": "CRE", "pais": "México",
        "titulo": "CRE aprueba nuevos contratos de cobertura para renovables — plazo hasta 25 años",
        "resumen": "La CRE modifica las bases para contratos de cobertura eléctrica, extendiendo el plazo máximo a 25 años y simplificando el proceso de registro ante el CENACE para proyectos renovables.",
        "impacto": "alto",
        "impacto_unergy": "Mayor certeza para estructurar PPAs de largo plazo en México. Actualizar plantillas contractuales.",
        "url": "https://www.gob.mx/cre",
    },
    {
        "fecha": "2024-12-05", "entidad": "SENER", "pais": "México",
        "titulo": "SENER publica plan de expansión solar 2025 — 8GW de nueva capacidad",
        "resumen": "La Secretaría de Energía anuncia convocatoria para 8GW de energía solar distribuida entre 2025 y 2027. Se priorizan proyectos en estados del norte del país.",
        "impacto": "alto",
        "impacto_unergy": "Oportunidad de entrada al mercado mexicano. Analizar viabilidad de proyectos EPC en estados prioritarios.",
        "url": "https://www.gob.mx/sener",
    },
    {
        "fecha": "2024-09-18", "entidad": "CFE", "pais": "México",
        "titulo": "CFE actualiza tarifas de interconexión para generación distribuida",
        "resumen": "CFE publica actualización de las tarifas GDBT y GDMTO para generación distribuida. Se incluyen nuevas condiciones para proyectos de almacenamiento con baterías (BESS).",
        "impacto": "medio",
        "impacto_unergy": "Revisar proyecciones financieras para proyectos GD en México. Explorar oportunidades con BESS.",
        "url": "https://www.cfe.mx",
    },
]

NOVEDADES_BRASIL: List[Dict[str, Any]] = [
    {
        "fecha": "2025-03-01", "entidad": "ANEEL", "pais": "Brasil",
        "titulo": "ANEEL reduce prazo de conexão de minigeração para 30 dias",
        "resumen": "Nueva regulación de ANEEL establece que las distribuidoras deben conectar proyectos de minigeração distribuída en máximo 30 días (antes 65 días). Se incluyen multas automáticas por incumplimiento.",
        "impacto": "alto",
        "impacto_unergy": "Mejora el cronograma de proyectos EPC en Brasil. Actualizar planes de implementación.",
        "url": "https://www.aneel.gov.br",
    },
    {
        "fecha": "2025-01-15", "entidad": "CCEE", "pais": "Brasil",
        "titulo": "CCEE abre mercado livre para consumidores acima de 500kW",
        "resumen": "La CCEE amplía el acceso al mercado libre de energía para consumidores con demanda superior a 500kW (antes 1MW). Abre el mercado a ~30.000 nuevos potenciales compradores de PPAs renovables.",
        "impacto": "alto",
        "impacto_unergy": "Expansión significativa del mercado PPA en Brasil. Oportunidad para estructurar contratos con nuevos clientes industriales.",
        "url": "https://www.ccee.org.br",
    },
    {
        "fecha": "2024-10-22", "entidad": "ANEEL", "pais": "Brasil",
        "titulo": "Marco Legal GD (Lei 14.300) — regulamentação completa em vigor",
        "resumen": "Entra en vigor la reglamentación completa de la Ley 14.300/2022. Se confirman las regras de compensación de energía hasta 2045 y los procedimientos para geração compartilhada.",
        "impacto": "medio",
        "impacto_unergy": "Certeza jurídica para proyectos GD en Brasil. Marco estable para estructurar PPAs de largo plazo.",
        "url": "https://www.aneel.gov.br",
    },
]

# Mapa de acceso centralizado por país
NORMATIVA_POR_PAIS = {
    "🇨🇴 Colombia": NORMATIVA,
    "🇪🇨 Ecuador":  NORMATIVA_ECUADOR,
    "🇲🇽 México":   NORMATIVA_MEXICO,
    "🇧🇷 Brasil":   NORMATIVA_BRASIL,
}
NOVEDADES_POR_PAIS = {
    "🇨🇴 Colombia": NOVEDADES,
    "🇪🇨 Ecuador":  NOVEDADES_ECUADOR,
    "🇲🇽 México":   NOVEDADES_MEXICO,
    "🇧🇷 Brasil":   NOVEDADES_BRASIL,
}


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
