# Pactora CLM — Informe de Producto
### Plataforma de Gestión Inteligente de Contratos para Unergy

> **Versión:** 1.0 | **Fecha:** Marzo 2026 | **Desarrollado para:** Unergy / Grupo Suno / Solenium

---

## ¿Qué es Pactora?

**Pactora** es una plataforma web de gestión del ciclo de vida de contratos (CLM) diseñada específicamente para el portafolio de energía renovable de Unergy. Permite a los equipos legal, financiero y operativo **buscar, analizar, gestionar y auditar** contratos de manera centralizada, con inteligencia artificial integrada.

La plataforma fue construida sobre **Streamlit**, se despliega en **Streamlit Cloud** y se conecta al ecosistema Google (Drive, Sheets, OAuth) sin requerir infraestructura adicional.

---

## Arquitectura General

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PACTORA CLM                                 │
│                    (Streamlit Cloud — Web App)                      │
├──────────────┬──────────────┬──────────────┬────────────────────────┤
│   FRONTEND   │    CORE AI   │    GOOGLE    │    ALMACENAMIENTO       │
│  (Streamlit) │   (Gemini)   │    APIS      │    LOCAL / CLOUD        │
├──────────────┼──────────────┼──────────────┼────────────────────────┤
│  11 páginas  │  Gemini 2.5  │  Drive API   │  ChromaDB (vectores)   │
│  UI branding │  Flash LLM   │  Sheets API  │  Google Sheets (users) │
│  Dark mode   │  Embeddings  │  OAuth2      │  Google Drive (backup)  │
│  Responsive  │  OCR Vision  │  SA + OAuth  │  Session state (cache) │
└──────────────┴──────────────┴──────────────┴────────────────────────┘
```

---

## Flujo de Autenticación y Acceso

```mermaid
flowchart TD
    A([Usuario visita Pactora]) --> B{¿Sesión activa?}
    B -- No --> C[Pantalla de Login\nPactora by Unergy]
    C --> D[Clic: Iniciar sesión con Google]
    D --> E[Google OAuth2\nst.login]
    E --> F{¿Email autorizado?}
    F -- No --> G[⛔ Acceso Denegado\nContactar administrador]
    F -- Sí --> H{¿Qué rol tiene?}
    H -- Admin --> I[Acceso completo\n+ Panel Administración\n+ Todas las funciones]
    H -- Viewer --> J[Acceso según permisos\nasignados por admin]
    J --> K{Feature flags\npor usuario}
    K --> L[JuanMitaBot Chat]
    K --> M[Resolver con JuanMitaBot]
    K --> N[Análisis Legal]
    K --> O[Comparar Contratos]
    K --> P[Exportar Informes]
```

---

## Mapa de Navegación

```
PACTORA CLM
│
├── 🏠 PRINCIPAL
│   ├── Inicio .................. Dashboard con alertas, explorador y calendario
│   ├── 🤖 JuanMitaBot .......... Chat IA sobre contratos indexados
│   └── 🎯 Resolver ............. Análisis guiado profundo (feature-gated)
│
├── 📚 CONTRATOS
│   ├── Biblioteca .............. Visor de documentos + chat contextual
│   ├── Análisis Legal .......... Análisis de riesgo + versiones + diff
│   └── Plantillas .............. 7 plantillas para PPA, EPC, O&M, NDA...
│
├── 📊 ANÁLISIS
│   ├── Métricas ................ KPIs del portafolio + detección de riesgo
│   ├── Calendario .............. Vencimientos + hitos + eventos manuales
│   └── Gestor Normativo ........ Base de normas FNCER/CREG/MME colombianas
│
└── ⚙️ SISTEMA
    ├── Ajustes ................. Carga de documentos + diagnóstico
    └── 🔑 Administración ....... Gestión de usuarios y permisos (solo Admin)
```

---

## Módulo 1 — Inicio (Dashboard)

**Propósito:** Vista general del portafolio de contratos al entrar a la plataforma.

```
┌─────────────────────────────────────────────────────────────────────┐
│  ⚠️  ALERTAS DE CONTRATOS                                           │
│  ├── 🔴 3 contratos VENCIDOS                                        │
│  ├── 🟡 5 contratos vencen en 30 días                               │
│  └── 🟢 8 contratos vencen en 90 días                              │
├───────────────────────────┬─────────────────────────────────────────┤
│  📄 EXPLORADOR             │  📅 MINI CALENDARIO                     │
│                           │                                         │
│  Buscar: [__________]     │  ◀  Marzo 2026  ▶                       │
│                           │  Lu Ma Mi Ju Vi Sá Do                   │
│  📕 PPA_Unergy_2024.pdf   │     2  3  4  5  6  7                    │
│  📝 EPC_SolarFarm.docx    │  9 10 11 12 13 14 15 ← evento          │
│  📊 OM_Contract_Q1.xlsx   │  16 17 18 19 20 21 22                   │
│  📕 NDA_Proveedor.pdf     │  23 24 25 26 27 28 29                   │
│  [+18 contratos más]      │                                         │
├───────────────────────────┴─────────────────────────────────────────┤
│  📊 MÉTRICAS DEL WORKSPACE                                          │
│  Total contratos: 26   |   Chunks indexados: 1,847   |   Eventos: 34│
│  PDF: 18  DOCX: 5  XLSX: 2  CSV: 1                                  │
└─────────────────────────────────────────────────────────────────────┘
```

**Características:**
- Alertas automáticas de vencimiento en 3 niveles (vencido / 30 días / 90 días)
- Explorador de archivos con búsqueda por nombre
- Mini-calendario HTML con eventos coloreados por tipo
- Métricas de workspace: contratos, chunks, formatos

---

## Módulo 2 — JuanMitaBot (Chat IA)

**Propósito:** Asistente conversacional que responde preguntas sobre el portafolio de contratos en lenguaje natural.

```
┌─────────────────────────────────────────────────────────────────────┐
│  🤖 JuanMitaBot — Modo Agente                                       │
│  Agente autónomo con acceso a búsqueda semántica, perfiles,         │
│  comparación, vencimientos y resumen de portafolio                  │
│                    [🗑 Nueva conversación]                           │
├─────────────────────────────────────────────────────────────────────┤
│  [Fechas de vencimiento] [Cláusulas de penalización] [Partes]       │
│  [Obligaciones de pago]  [Fuerza mayor]              [Renovación]   │
├────────────────────────────────────────┬────────────────────────────┤
│                                        │  📄 Contratos (26)          │
│  💬 ¡Hola! Soy JuanMitaBot            │  📕 PPA_Unergy.pdf          │
│  Pregúntame sobre tus contratos        │  📝 EPC_Solar.docx          │
│  indexados. Recuerdo el contexto       │  📊 OM_Q1.xlsx              │
│  de toda la conversación.              │  [+23 más]                  │
│                                        │                             │
│                                        │  💡 Capacidades             │
│  [Escribe tu pregunta...]              │  📊 10 llamadas hoy         │
└────────────────────────────────────────┴────────────────────────────┘
```

**Modos de operación:**

| Modo | Cuándo activo | Capacidad |
|------|--------------|-----------|
| **Agente Gemini** | Con `GEMINI_API_KEY` configurada | Invoca 6 herramientas autónomamente |
| **Búsqueda semántica** | Sin API key (fallback) | Retorna fragmentos relevantes directamente |

**Herramientas del agente (Function Calling):**

```
🔍 buscar_contratos     → Búsqueda semántica en ChromaDB (k=10 chunks)
📋 obtener_perfil       → Perfil estructurado desde Google Sheets
📑 listar_contratos     → Inventario filtrado por tipo/riesgo
🔀 comparar_contratos   → Tabla comparativa lado a lado
⏰ contratos_por_vencer → Alertas de vencimiento próximo
📊 resumen_portafolio   → KPIs y estadísticas del portafolio
```

---

## Módulo 3 — Resolver con JuanMitaBot

**Propósito:** Flujo guiado de análisis contractual profundo con informe ejecutivo estructurado. Solo disponible para usuarios con el feature `resolver` habilitado.

```
┌─────────────────────────────────────────────────────────────────────┐
│  🎯 Resolver con JuanMitaBot                                        │
│  Análisis contractual profundo — JuanMitaBot te guía paso a paso   │
├────────────────────────────────────────┬────────────────────────────┤
│                                        │  ¿Cómo funciona?            │
│  ┌──────────────────────────────────┐  │  1️⃣ Describe tu consulta    │
│  │ ⚠️ Riesgos críticos             │  │  2️⃣ JuanMitaBot aclara (≤2) │
│  │ 📅 Vencimientos próximos        │  │  3️⃣ Análisis automático      │
│  │ 💰 Penalidades EPC              │  │  4️⃣ Informe ejecutivo        │
│  │ 🔀 Comparativa términos         │  │                             │
│  │ 📋 Obligaciones O&M             │  │  📄 26 contratos            │
│  │ 🔒 Cláusulas fuerza mayor       │  │  [Ver contratos]            │
│  └──────────────────────────────────┘  │                             │
│                                        │  [🗑 Nueva consulta]        │
│  [Describe tu consulta contractual…]   │                             │
└────────────────────────────────────────┴────────────────────────────┘
```

**Flujo de 3 fases del agente Resolver:**

```mermaid
sequenceDiagram
    participant U as Usuario
    participant R as Resolver
    participant A as Agente Gemini
    participant T as Herramientas

    U->>R: "Analiza riesgos en contrato PPA Fase 3"
    R->>A: Envía consulta con RESOLVER_SYSTEM_PROMPT
    A->>U: Pregunta de clarificación (máx 2)
    U->>A: "Me preocupa el riesgo económico y penalidades"
    A->>T: buscar_contratos("penalidades PPA Fase 3")
    T-->>A: 10 fragmentos relevantes
    A->>T: obtener_perfil("PPA_Fase3.pdf")
    T-->>A: Perfil estructurado (fechas, valor, partes)
    A-->>U: 📋 Informe ejecutivo estructurado
    Note over A,U: Resumen · Hallazgos · Riesgo 🟡 · Próximos pasos
```

**Estructura del informe generado:**
```
## 📋 Informe de Análisis — PPA Fase 3

### Resumen Ejecutivo
[2-3 oraciones con hallazgo principal]

### Hallazgos Clave
• Cláusula 8.3: Penalidad del 15% CAPEX por retraso en COD [Fuente: PPA_Fase3.pdf]
• Sin mecanismo de step-in en caso de incumplimiento [Fuente: PPA_Fase3.pdf]

### Nivel de Riesgo
🟡 AMARILLO — Penalidad supera el 10% CAPEX; requiere revisión

### Próximos Pasos Recomendados
• [ ] Equipo legal: revisar cláusula 8.3 para negociar tope
• [ ] Financiero: cuantificar exposición máxima
```

---

## Módulo 4 — Biblioteca de Contratos

**Propósito:** Visor de documentos con chat contextual por contrato.

```
┌─────────────────────────────────────────────────────────────────────┐
│  📚 Biblioteca                                                       │
├─────────────────────┬───────────────────────────────────────────────┤
│  LISTA              │  VISTA PREVIA + CHAT                          │
│                     │                                               │
│  📕 PPA_Unergy.pdf  │  ┌──────────────────┐  💬 Chat              │
│  [Abrir] [⚖]       │  │                  │                         │
│  📝 EPC_Solar.docx  │  │   [PDF viewer]   │  Usuario: ¿Cuáles son  │
│  [Abrir] [⚖]       │  │                  │  las partes del         │
│  📊 OM_Q1.xlsx      │  │                  │  contrato?             │
│  [Abrir] [⚖]       │  └──────────────────┘                         │
│  ...                │   Alto: [─────────]   JuanMitaBot: Las       │
│                     │                       partes son Unergy       │
│                     │                       S.A.S. como generador   │
│                     │                       y XYZ Corp como…        │
└─────────────────────┴───────────────────────────────────────────────┘
```

**Características:**
- Vista dividida: lista de contratos + preview inline
- Chat contextual por documento (historial separado por contrato)
- Botón directo a Análisis Legal (⚖)
- Soporte PDF (iframe), DOCX, Excel, imágenes

---

## Módulo 5 — Análisis Legal

**Propósito:** Análisis de riesgo, versionado de documentos y seguimiento de cambios.

```
┌─────────────────────────────────────────────────────────────────────┐
│  ⚖️  Análisis Legal                                                  │
├────────────────────────────────┬────────────────────────────────────┤
│  [Seleccionar contrato ▼]      │  Versiones: Original | Draft | Hist│
│                                │                                     │
│  ANÁLISIS DE RIESGO            │  DIFF VIEWER                        │
│  ─────────────────             │  ─────────────────                 │
│  🔴 ROJO — 2 alertas críticas  │  - Cláusula antigua                │
│  🟡 AMARILLO — 5 observaciones │  + Cláusula nueva negociada         │
│  🟢 VERDE — Cumple 8/10 items  │                                     │
│                                │  Compliance: ████████░░ 82/100     │
│  Términos legales: 14          │                                     │
│  Palabras de riesgo: 7         │  [💾 Guardar versión] [📤 Exportar] │
└────────────────────────────────┴────────────────────────────────────┘
```

---

## Módulo 6 — Métricas del Portafolio

**Propósito:** KPIs cuantitativos y cualitativos de todos los contratos indexados.

```
┌─────────────────────────────────────────────────────────────────────┐
│  📊 Métricas                                                         │
├─────────────────────────────────────────────────────────────────────┤
│  Por tipo de contrato          │  Por nivel de riesgo               │
│  ─────────────────────         │  ─────────────────────             │
│  PPA:  ████████░░  12 (46%)   │  🔴 ROJO:     ██░░░░░░  3 (12%)   │
│  EPC:  █████░░░░░   8 (31%)   │  🟡 AMARILLO: █████░░░  10 (38%)  │
│  O&M:  ███░░░░░░░   4 (15%)   │  🟢 VERDE:    ████████░  13 (50%) │
│  Otro: █░░░░░░░░░   2 (8%)    │                                     │
├─────────────────────────────────────────────────────────────────────┤
│  Montos detectados             │  Vencimientos próximos             │
│  COP: 3 contratos              │  🔴 Este mes: 2 contratos          │
│  USD: 5 contratos              │  🟡 3 meses: 5 contratos           │
│  kWh tarifa: 8 contratos       │  ✅ OK: 15 contratos               │
└─────────────────────────────────────────────────────────────────────┘
```

**Detección automática incluye:**
- Tipo de contrato por nombre/contenido (PPA, EPC, O&M, NDA, Arrendamiento, Fiducia, etc.)
- 8 categorías de riesgo: penalidades, terminación, fuerza mayor, obligaciones, renovación, confidencialidad, responsabilidad, garantías
- Valores monetarios: USD, COP, millones, tarifa/kWh, %CAPEX
- Documentos corporativos: actas, estatutos, poderes, quórum, resoluciones

---

## Módulo 7 — Calendario de Eventos

**Propósito:** Extrae, organiza y visualiza todas las fechas importantes de los contratos.

```
┌─────────────────────────────────────────────────────────────────────┐
│  📅 Calendario                                                       │
├──────────────────────────────────┬──────────────────────────────────┤
│  VISTA MENSUAL                   │  PRÓXIMOS EVENTOS                │
│                                  │                                  │
│  ◀  Marzo 2026  ▶                │  🔴 Vencimiento: 5 días          │
│  ┌─────────────────────────┐    │     PPA_Unergy.pdf               │
│  │ L  M  X  J  V  S  D    │    │                                  │
│  │ 2  3  4  5  6  7  8    │    │  🟡 Pago: 12 días                │
│  │ ●  .  .  ●  .  .  .    │    │     EPC_SolarFarm.docx           │
│  │ 9 10 11 12 13 14 15    │    │                                  │
│  │ . ●  .  .  ●  .  .     │    │  🟢 Inicio obra: 28 días         │
│  └─────────────────────────┘    │     OM_Q1_Contract.xlsx          │
├──────────────────────────────────┴──────────────────────────────────┤
│  Fuentes de eventos: Regex (18) | IA (9) | Manual (7) | Total: 34  │
└─────────────────────────────────────────────────────────────────────┘
```

**Fuentes de extracción:**

| Fuente | Método | Ejemplos de fechas detectadas |
|--------|--------|-------------------------------|
| **Regex** | Patrones `dd/mm/yyyy`, `yyyy-mm-dd` | "15/03/2026", "2026-03-15" |
| **Texto natural** | Regex español | "15 de marzo de 2026" |
| **IA (Gemini)** | Extracción semántica | "treinta días después de COD" |
| **Manual** | Formulario de usuario | Cualquier fecha + descripción |

---

## Módulo 8 — Gestor Normativo

**Propósito:** Base de datos de la normativa colombiana aplicable al sector FNCER.

```
┌─────────────────────────────────────────────────────────────────────┐
│  ⚖️  Gestor Normativo FNCER                                          │
├─────────────────────────────────────────────────────────────────────┤
│  Filtrar por: [Tipo ▼] [Aplica a ▼]   Búsqueda: [______________]   │
├─────────────────────────────────────────────────────────────────────┤
│  📜 Ley 1715/2014 — Fuentes No Convencionales de Energía Renovable  │
│     UPME · Vigente · Tags: FNCER, PPA, incentivos, exenciones       │
│     ► Art. 11: Incentivos tributarios para generación solar          │
│                                                                     │
│  📜 Resolución CREG 030/2018 — Fronteras Comerciales                │
│     CREG · Vigente · Tags: PPA, frontera, medición, liquidación      │
│     ► Art. 5: Requisitos técnicos para representación de frontera   │
│                                                                     │
│  📜 Decreto 2236/2023 — Comunidades Energéticas                     │
│     MME · Vigente · Tags: EPC, O&M, autogeneración, comunidades     │
├─────────────────────────────────────────────────────────────────────┤
│  CRUCE CON CONTRATOS  │  MONITOR NOVEDADES  │  COMPLIANCE DASHBOARD │
└─────────────────────────────────────────────────────────────────────┘
```

**Normas incluidas:** ~20 leyes, decretos y resoluciones
**Entidades:** UPME, CREG, MME, Congreso de la República
**Período cubierto:** 2014–2026

---

## Módulo 9 — Plantillas de Contratos

**Propósito:** Repositorio de plantillas estandarizadas para los tipos de contrato más comunes.

```
┌─────────────────────────────────────────────────────────────────────┐
│  📄 Plantillas                                                       │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │   PPA    │  │   EPC    │  │   O&M    │  │   Legal / NDA    │   │
│  │ #4CAF50  │  │ #2196F3  │  │ #FF9800  │  │   #9C27B0        │   │
│  │ v1.2     │  │ v2.0     │  │ v1.0     │  │   v1.1           │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│  CAMPOS DEL TEMPLATE SELECCIONADO                                   │
│  ─────────────────────────────────                                  │
│  Nombre del proyecto: [________________________]                    │
│  Capacidad instalada: [________] kWp                                │
│  Precio de energía:   [________] COP/kWh                            │
│  Fecha de inicio:     [________________________]                    │
│                                                                     │
│  [Vista previa]              [📥 Descargar DOCX personalizado]      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Módulo 10 — Ajustes y Diagnóstico

**Propósito:** Carga manual de documentos, configuración de integraciones y diagnóstico del sistema.

```
┌─────────────────────────────────────────────────────────────────────┐
│  ⚙️  Ajustes                                                         │
├─────────────────────────────────────────────────────────────────────┤
│  CARGAR DOCUMENTOS                                                  │
│  Arrastra archivos PDF, DOCX, XLSX, CSV, TXT, ZIP                   │
│  [──────────────── Soltar archivos aquí ────────────────]          │
│  ✅ PPA_Nuevo.pdf (indexado)                                         │
│  ⏳ EPC_Draft.docx (indexando...)                                    │
│                                                                     │
│  DIAGNÓSTICO DEL SISTEMA                                            │
│  ✅ Chatbot: activo     ✅ ChromaDB: 1,847 chunks                    │
│  ✅ Embeddings: ok      ✅ Drive: conectado                          │
│  ✅ Gemini: activo      ✅ Sheets: conectado                         │
│                                                                     │
│  GOOGLE DRIVE                   METADATA DE INDEXACIÓN              │
│  Carpeta raíz: configurada      Archivo       Fecha        Drive ID │
│  [🔄 Reindexar desde Drive]     PPA.pdf  2026-03-15  1BcD...        │
│  Último backup: 2026-03-15      EPC.docx 2026-03-10  2EfG...        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Módulo 11 — Panel de Administración

**Propósito:** Gestión completa de usuarios, roles y permisos granulares (solo Admin).

```
┌─────────────────────────────────────────────────────────────────────┐
│  🔑 Administración de Acceso                                         │
├─────────────────────────────────────────────────────────────────────┤
│  [👥 Usuarios]  [➕ Agregar]  [🔧 Editar permisos]  [🎛️ Funciones]   │
├─────────────────────────────────────────────────────────────────────┤
│  PERMISOS DE FUNCIONES POR USUARIO (Tab 4)                          │
│  ────────────────────────────────────────                           │
│  Usuario               │JuanMita│Resolver│Análisis│Comparar│Exportar│
│  ────────────────────────────────────────────────────────────────── │
│  maria@unergy.co       │  ✅    │  ✅    │  ✅    │  ✅    │  ✅    │
│  carlos@suno.co        │  ✅    │  ❌    │  ✅    │  ❌    │  ✅    │
│  ana@solenium.co       │  ✅    │  ✅    │  ❌    │  ✅    │  ❌    │
│  proveedor@ext.com     │  ✅    │  ❌    │  ❌    │  ❌    │  ❌    │
│                                                                     │
│  [💾 Guardar permisos de funciones]                                 │
│  Los cambios aplican al siguiente inicio de sesión del usuario.     │
└─────────────────────────────────────────────────────────────────────┘
```

**Tipos de contrato por usuario (control granular):**

| Rol | Contratos visibles | Funciones disponibles |
|-----|-------------------|----------------------|
| **Admin** | Todos (siempre) | Todas (siempre) |
| **Viewer** | Asignados por admin | Asignadas por admin |

---

## Pipeline de Indexación de Documentos

```mermaid
flowchart LR
    A[📁 Fuente] --> B{Tipo}
    B -- Manual --> C[Carga por\nusuario en\nAjustes]
    B -- Drive --> D[Auto-indexación\nen startup\nthread BG]
    C & D --> E[file_parser.py\nextract_text]
    E --> F{Formato}
    F -- PDF --> G[pypdf + pymupdf\nOCR si escaneado]
    F -- DOCX --> H[python-docx]
    F -- PPTX --> I[python-pptx]
    F -- XLSX --> J[openpyxl]
    F -- IMG --> K[Gemini Vision OCR]
    G & H & I & J & K --> L[RecursiveCharacter\nTextSplitter\n1500 chars / 300 overlap]
    L --> M[+ Summary chunk\n800 chars por doc]
    L & M --> N[all-MiniLM-L6-v2\nEmbeddings locales]
    N --> O[(ChromaDB\nchroma_db/)]
    O --> P[Backup ZIP\nGoogle Drive]
    O --> Q[Perfil LLM\nGemini extrae\nmetadatos estructurados]
    Q --> R[(Google Sheets\nCONTRACT_PROFILES)]
```

---

## Pipeline de Consulta y Respuesta

```mermaid
flowchart TD
    U([Usuario hace\nuna pregunta]) --> A[all-MiniLM-L6-v2\nEmbedding de la query]
    A --> B[ChromaDB\nsimilarity_search\nk=10 chunks]
    B --> C{LLM disponible?}
    C -- No --> D[Retorna fragmentos\nformateados directamente\nModo semántico]
    C -- Sí --> E[run_agent_turn\nGemini 2.5 Flash]
    E --> F{¿Necesita\nherramientas?}
    F -- Sí --> G[Function Calling\nbuscar / perfil / lista\ncomparar / vencer / resumen]
    G --> H[Ejecuta tool\nresultados como contexto]
    H --> E
    F -- No --> I[Genera respuesta\nen lenguaje natural]
    I --> U
```

---

## Sistema de Perfiles Permanentes (Google Sheets)

**Propósito:** Cada contrato se analiza UNA SOLA VEZ con Gemini para extraer metadatos estructurados. Los resultados se guardan permanentemente en Google Sheets, permitiendo consultas instantáneas sin re-procesar.

```
┌─ CONTRACT_PROFILES_SHEET_ID ─────────────────────────────────────────────────┐
│ drive_id │ filename    │ type │ parties     │ start    │ end      │ value_clp  │
│──────────┼─────────────┼──────┼─────────────┼──────────┼──────────┼────────── │
│ 1BcD...  │ PPA_2024    │ PPA  │ Unergy/XYZ  │ 2024-01  │ 2034-01  │ 500M       │
│ 2EfG...  │ EPC_Solar   │ EPC  │ Unergy/ABC  │ 2024-03  │ 2025-06  │ 2.000M     │
│ 3HiJ...  │ OM_Q1       │ O&M  │ Unergy/OPS  │ 2024-01  │ 2026-12  │ 120M/año   │
│...       │ ...         │ ...  │ ...         │ ...      │ ...      │ ...        │
│                                                                               │
│ + risk_level │ risk_summary │ compliance_score │ obligations_summary         │
└───────────────────────────────────────────────────────────────────────────────┘
```

**Ventaja clave:** Al reiniciar Streamlit Cloud (entorno efímero), los perfiles cargan en < 1 segundo sin re-procesar ningún documento.

---

## Integración Google Drive — Indexación Automática

```
Startup de Streamlit Cloud
         │
         ▼
_trigger_startup_index() [background thread]
         │
         ├─► Restaurar ChromaDB desde ZIP en Drive (~30s para 400 contratos)
         │
         ├─► Recorrer DRIVE_ROOT_FOLDER_ID recursivamente
         │       └─► Filtrar por SUPPORTED_MIMES (PDF, DOCX, XLSX, PPTX, PNG...)
         │
         ├─► Para cada archivo NO indexado:
         │       ├─► Descargar desde Drive
         │       ├─► extract_text_from_file()
         │       └─► vector_ingest_multiple() → ChromaDB
         │
         ├─► Si LLM disponible: extract_contract_profile() → Sheets
         │
         └─► Backup ZIP ChromaDB → Drive
```

---

## Tecnología y Dependencias Clave

| Componente | Tecnología | Notas |
|-----------|-----------|-------|
| **Framework web** | Streamlit ≥1.45.0 | Multi-page, st.navigation() |
| **LLM** | Gemini 2.5 Flash | Opcional; fallback a semántico |
| **Embeddings** | all-MiniLM-L6-v2 | Local, sin PyTorch (onnxruntime) |
| **Vector DB** | ChromaDB local | Persiste en `./chroma_db/` |
| **Auth** | Streamlit Native Auth + OAuth2 | Google Sign-In |
| **Users DB** | Google Sheets API v4 | AUTH_USERS_SHEET_ID |
| **Profiles DB** | Google Sheets API v4 | CONTRACT_PROFILES_SHEET_ID |
| **File storage** | Google Drive API | Backup ZIP + versiones |
| **PDF parsing** | pypdf + pymupdf | OCR con Gemini Vision |
| **DOCX** | python-docx | — |
| **PPTX** | python-pptx | — |
| **XLSX** | openpyxl + xlrd | — |
| **PDF export** | fpdf2 | Reportes branded Unergy |
| **Calendar UI** | streamlit-calendar | FullCalendar |
| **RAG** | LangChain community | Text splitter + Chroma wrapper |
| **Python** | 3.11 (Cloud) / 3.14 (local) | Parche pydantic v1 para 3.14 |

---

## Configuración Requerida (secrets.toml)

```toml
# Autenticación Google OAuth
[auth]
client_id     = "..."
client_secret = "..."
redirect_uri  = "https://tu-app.streamlit.app/oauth2callback"
cookie_secret = "clave-aleatoria-32-chars"

# Usuarios admin por defecto (fallback si Sheets no disponible)
[auth_config]
admin_emails           = ["admin@unergy.co"]
initial_allowed_emails = ["usuario@unergy.co"]

# Google Service Account (para Sheets y Drive)
[GOOGLE_SERVICE_ACCOUNT]
type                        = "service_account"
project_id                  = "pactora-docbrain"
private_key_id              = "..."
private_key                 = "-----BEGIN RSA PRIVATE KEY-----\n..."
client_email                = "pactora-drive@pactora-docbrain.iam.gserviceaccount.com"
# ... resto de campos SA

# IDs de recursos Google
AUTH_USERS_SHEET_ID         = "1abc...xyz"  # Sheet compartido con SA como Editor
CONTRACT_PROFILES_SHEET_ID  = "1def...uvw"  # Sheet compartido con SA como Editor
DRIVE_ROOT_FOLDER_ID        = "1ghi...rst"  # Carpeta Drive con los contratos
DRIVE_API_KEY               = "AIza..."     # Para acceso de solo lectura

# IA
GEMINI_API_KEY = "AIza..."
```

---

## Resumen de Capacidades

| Categoría | Capacidad | Estado |
|-----------|-----------|--------|
| **Ingesta** | PDF / DOCX / XLSX / PPTX / CSV / TXT / ZIP | ✅ Activo |
| **Ingesta** | OCR de imágenes (Gemini Vision) | ✅ Activo |
| **Ingesta** | Auto-indexación desde Google Drive | ✅ Activo |
| **Búsqueda** | Semántica (sin LLM, 100% local) | ✅ Siempre |
| **IA** | Chat conversacional sobre contratos | ✅ Con API key |
| **IA** | Agente con 6 herramientas (Function Calling) | ✅ Con API key |
| **IA** | Análisis guiado con informe ejecutivo | ✅ Con API key |
| **IA** | Extracción de métricas (Gemini) | ✅ Con API key |
| **IA** | OCR de PDFs escaneados (Gemini Vision) | ✅ Con API key |
| **Documentos** | Preview inline (PDF/DOCX/Excel/imágenes) | ✅ Activo |
| **Documentos** | Versionado + diff de contratos | ✅ Activo |
| **Documentos** | Exportar informes PDF branded | ✅ Activo |
| **Plantillas** | 7 plantillas (PPA, EPC, O&M, NDA...) | ✅ Activo |
| **Calendario** | Extracción automática de fechas | ✅ Activo |
| **Normativa** | Base FNCER/CREG/MME (~20 normas) | ✅ Activo |
| **Acceso** | Auth Google OAuth + whitelist | ✅ Activo |
| **Acceso** | Control granular por tipo de contrato | ✅ Activo |
| **Acceso** | Feature flags por usuario (5 funciones) | ✅ Activo |
| **Admin** | Panel de gestión de usuarios | ✅ Activo |
| **Persistencia** | ChromaDB backup/restore en Drive | ✅ Activo |
| **Persistencia** | Perfiles permanentes en Google Sheets | ✅ Activo |
| **UI** | Dark mode toggle | ✅ Activo |
| **UI** | Branding Unergy (purple #915BD8 + yellow) | ✅ Activo |

---

*Pactora CLM — Desarrollado por Unergy · Marzo 2026*
