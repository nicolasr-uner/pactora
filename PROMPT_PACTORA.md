# PROMPT DE CONTEXTO — PACTORA CLM
## Prompt completo para onboarding de IA al codebase

> Usa este documento como contexto inicial cuando trabajes con cualquier IA (Claude, GPT, Gemini, etc.) en el proyecto Pactora. Cópialo completo al inicio de cada sesión.

---

```
Eres un ingeniero de software senior trabajando en PACTORA CLM, una plataforma web de gestión del ciclo de vida de contratos (Contract Lifecycle Management) construida en Python/Streamlit para Unergy, empresa colombiana de energía renovable del grupo Suno/Solenium.

═══════════════════════════════════════════════════════════════════
CONTEXTO DEL NEGOCIO
═══════════════════════════════════════════════════════════════════

Unergy gestiona un portafolio de 200-400 contratos de energía solar (PPA, EPC, O&M, SHA, NDA, Arrendamiento, Fiducia, Comunidades energéticas). Los contratos están en español, siguen la normativa CREG/MME colombiana, y sus partes son entidades como Unergy S.A.S., Suno Energy, Solenium, así como compradores de energía, constructoras EPC y operadores O&M.

El equipo que usa Pactora es pequeño (5-15 personas): abogados, financieros y operadores. Necesitan:
1. Centralizar todos los contratos en un solo lugar
2. Buscar cláusulas específicas en lenguaje natural
3. Monitorear vencimientos y alertas automáticamente
4. Analizar riesgos con IA sin re-leer cada PDF
5. Gestionar acceso por rol (admin/viewer) con restricciones por tipo de contrato

═══════════════════════════════════════════════════════════════════
STACK TÉCNICO
═══════════════════════════════════════════════════════════════════

Framework:    Streamlit ≥1.45.0 (multi-page con st.navigation / st.Page)
LLM:          Google Gemini 2.5 Flash via google-genai SDK (opcional, con fallback)
Embeddings:   ChromaDB DefaultEmbeddingFunction — all-MiniLM-L6-v2 (onnxruntime, sin PyTorch)
Vector DB:    ChromaDB local en ./chroma_db/ con LangChain como wrapper
RAG:          RecursiveCharacterTextSplitter chunk_size=1500, overlap=300, k=10
Auth:         Streamlit Native Auth (Google OAuth2) + whitelist en Google Sheets
Users DB:     Google Sheets API v4 (AUTH_USERS_SHEET_ID)
Profiles DB:  Google Sheets API v4 (CONTRACT_PROFILES_SHEET_ID)
File Storage: Google Drive API (backup ZIP de ChromaDB + versiones de documentos)
SA:           Service Account pactora-drive@pactora-docbrain.iam.gserviceaccount.com
Parsers:      pypdf, pymupdf, python-docx, python-pptx, openpyxl, xlrd, Pillow
OCR:          Gemini Vision (types.Part.from_bytes) para PNG/JPG/TIFF y PDFs escaneados
Export:       fpdf2 (reportes PDF branded Unergy)
Calendar UI:  streamlit-calendar (FullCalendar wrapper)
Python:       3.11 en Streamlit Cloud / 3.14 en local (parche pydantic v1 en app.py)
Colores:      Primary #915BD8 (purple), accent #F6FF72 (yellow), dark #2C2039

═══════════════════════════════════════════════════════════════════
ESTRUCTURA DE ARCHIVOS
═══════════════════════════════════════════════════════════════════

pactora/
├── app.py                          # Entry point: auth gate + st.navigation()
├── pages/
│   ├── inicio.py                   # Dashboard: alertas, explorador, mini-calendario, métricas
│   ├── chatbot.py                  # JuanMitaBot chat (agente + fallback semántico)
│   ├── resolver.py                 # Resolver guiado con informe ejecutivo (feature-gated)
│   ├── biblioteca.py               # Visor de documentos + chat contextual por doc
│   ├── legal.py                    # Análisis legal, versionado, diff, compliance
│   ├── metricas.py                 # KPIs del portafolio: tipos, riesgos, montos
│   ├── calendario.py               # Extracción y gestión de fechas de contratos
│   ├── normativo.py                # Base normativa colombiana FNCER/CREG/MME
│   ├── plantillas.py               # Plantillas PPA, EPC, O&M, NDA con campos custom
│   ├── ajustes.py                  # Carga docs, diagnóstico, Drive/Sheets config
│   └── admin.py                    # Panel admin: usuarios, roles, feature flags
├── core/
│   ├── rag_chatbot.py              # RAGChatbot: embeddings locales + ChromaDB
│   ├── llm_service.py              # Gemini SDK: generate_response, run_agent_turn,
│   │                               # extract_contract_metrics, analyze_risk,
│   │                               # build_portfolio_context, read/write_contract_profile
│   ├── agent_tools.py              # 6 herramientas del agente (Function Calling)
│   └── normativa_db.py             # ~20 normas colombianas hardcoded (sin API deps)
├── utils/
│   ├── shared.py                   # init_session_state, _get_chatbot(), page_header,
│   │                               # api_status_banner, _drive_status_widget, apply_styles
│   ├── auth_manager.py             # Google Sheets whitelist: is_authorized, is_admin,
│   │                               # has_feature, add_user, remove_user, update_permissions
│   ├── auth_helper.py              # get_drive_service(), get_sheets_service_sa()
│   ├── auth.py                     # get_current_user(), filter_sources_for_user()
│   ├── file_parser.py              # extract_text_from_file() para PDF/DOCX/PPTX/XLSX/img
│   ├── indexing.py                 # Background Drive indexation, ChromaDB backup/restore
│   ├── drive_manager.py            # Drive CRUD: search, download, upload
│   ├── styles.py                   # apply_styles(), dark_mode_toggle(), CSS
│   ├── preview.py                  # render_document_preview() — PDF iframe / Excel df
│   ├── export_helper.py            # Exportar análisis en PDF/DOCX
│   └── report_generator.py         # fpdf2 branded PDF generator
├── _pactora_index_metadata.json    # Metadata local: {filename: {drive_id, indexed_at,
│                                   #                 ext, profile_extracted}}
├── .streamlit/
│   ├── config.toml                 # Theme: primary #915BD8
│   └── secrets.toml                # (NO commitear) — ver secrets_template.toml
├── INFORME_PACTORA.md              # Informe de producto para humanos
├── PROMPT_PACTORA.md               # Este archivo — contexto para IA
└── requirements.txt

═══════════════════════════════════════════════════════════════════
MÓDULOS CRÍTICOS — DETALLES
═══════════════════════════════════════════════════════════════════

── app.py ──────────────────────────────────────────────────────────
Entry point de Streamlit. Hace tres cosas en orden:
1. Parche pydantic v1 para Python 3.14 (sys.version_info check)
2. Auth gate completo:
   a. Si no logueado → pantalla login + st.login("google")
   b. Si logueado pero no en whitelist → pantalla "Acceso denegado" + st.logout
   c. Si autorizado → guarda email, is_admin, permissions en session_state
3. st.navigation() con páginas condicionales:
   - "Resolver" (🎯) aparece solo si has_feature(email, "resolver")
   - "Administración" (🔑) aparece solo si is_admin

── utils/auth_manager.py ───────────────────────────────────────────
Backend de acceso basado en Google Sheets.

Sheet schema (AUTH_USERS_SHEET_ID, Sheet1!A:H):
  email | role | allowed_types | allowed_tags | features | added_at | added_by | active

Columnas JSON:
  allowed_types: ["*"] o ["PPA","EPC"] — tipos de contrato que puede ver
  features:      ["*"] o ["juanmitabot","resolver","analisis","comparar","exportar"]
  active:        "True" / "False" (soft delete)

Constantes importantes:
  FEATURES = {
    "juanmitabot": "💬 JuanMitaBot Chat",
    "resolver":    "🎯 Resolver con JuanMitaBot",
    "analisis":    "⚖️ Análisis Legal",
    "comparar":    "🔀 Comparar Contratos",
    "exportar":    "📤 Exportar Informes",
  }
  CONTRACT_TYPES = ["PPA","EPC","O&M","Arrendamiento","Compraventa",
                    "Prestación de servicios","Confidencialidad (NDA)",
                    "Consorcio / Joint Venture","Financiamiento","Otro"]
  _CACHE_TTL_SECONDS = 120  # evitar quota exhaustion

Funciones públicas:
  is_authorized(email) → bool
  is_admin(email) → bool
  has_feature(email, feature_key) → bool  # admins siempre True
  get_user_permissions(email) → dict
  get_all_users(force_reload) → list[dict]
  add_user(email, role, allowed_types, features, added_by) → (bool, str)
  remove_user(email) → (bool, str)          # soft delete (active=False)
  update_user_permissions(email, role, allowed_types, features) → (bool, str)
  _invalidate_cache() → None

Fallback: si Sheets no disponible, usa st.secrets["auth_config"]["admin_emails"]

── core/rag_chatbot.py ─────────────────────────────────────────────
Clase RAGChatbot con singleton via @st.cache_resource en shared.py.

Embeddings: _LocalEmbeddings wrappea chromadb.utils.embedding_functions.DefaultEmbeddingFunction
  → all-MiniLM-L6-v2 via onnxruntime; no requiere PyTorch

Ingesta (vector_ingest_multiple):
  1. RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=300)
  2. Summary chunk: primeros 800 chars con metadata chunk_type="summary"
  3. Chroma.from_documents() o .add_documents() según si ya existe vectorstore

Búsqueda (_retrieve_context):
  similarity_search(question, k=10, filter=filter_metadata)
  Retorna (context_text, sources_list)

Ask question flow:
  1. Si vectorstore es None → "No hay contratos indexados"
  2. _retrieve_context(question, filter_metadata)
  3. Si LLM_AVAILABLE: run_agent_turn() → si responde, retornar
  4. Fallback: retornar fragmentos formateados

── core/llm_service.py ─────────────────────────────────────────────
Centraliza toda la integración con Gemini.

Constantes:
  LLM_AVAILABLE: bool — True si GEMINI_API_KEY válida configurada
  GEMINI_MODEL = "gemini-2.5-flash" (con fallback a 2.0-flash, 1.5-flash)
  _RATE_LIMIT_MAX = 10 llamadas/minuto
  _call_count_today: int (contador diario)

System prompts:
  JUANMITA_SYSTEM_PROMPT — asistente legal conversacional para chatbot.py
  RESOLVER_SYSTEM_PROMPT — flujo guiado de 3 fases para resolver.py:
    Fase 1: Clarificación (máx 2 preguntas)
    Fase 2: Análisis con herramientas
    Fase 3: Informe ejecutivo estructurado

Funciones principales:
  generate_response(question, context, history, system_prompt) → str
  run_agent_turn(question, history, system_prompt, filter_metadata, max_iterations=6) → str|None
    → Agentic loop: function_calls → execute_tool → agregar resultados → repetir
    → _check_and_record_call() por iteración (rate limit)
  extract_contract_metrics(text, contract_type) → dict
    → {Precio, Vigencia inicio/fin, Hitos NTP/COD, Obligaciones[], Pólizas[]}
  analyze_risk(text, contract_type) → dict
    → {Nivel: ROJO/AMARILLO/VERDE, Justificacion, compliance_score: 0-100, summary, alerts[]}
  build_portfolio_context() → str
    → Lee read_contract_profiles() primero; fallback a ChromaDB stats
  detect_contract_type(filename, text="") → str (PPA/EPC/O&M/NDA/...)
  extract_contract_profile(text, filename, contract_type, drive_id) → dict
  write_contract_profile(profile) → bool (append a CONTRACT_PROFILES_SHEET_ID)
  read_contract_profiles() → list[dict]
  get_call_stats() → dict{calls_today, calls_last_minute, rate_limit_per_minute}

── core/agent_tools.py ─────────────────────────────────────────────
Implementaciones de las 6 herramientas del agente Gemini.

  buscar_contratos(query, contract_type="", max_results=8)
    → chatbot.vectorstore.similarity_search(query, k=max_results)
    → Retorna markdown con fragmentos + fuentes

  obtener_perfil(filename)
    → read_contract_profiles() + fuzzy match por nombre
    → Retorna perfil estructurado en markdown

  listar_contratos(contract_type="", risk_level="")
    → read_contract_profiles() + filtros
    → Retorna tabla markdown con inventario filtrado

  comparar_contratos(filenames: list)
    → obtener_perfil() para cada filename
    → Retorna tabla comparativa lado a lado

  contratos_por_vencer(dias=90)
    → Compara end_date de perfiles con date.today() + timedelta(dias)
    → Retorna lista de vencidos + próximos a vencer

  resumen_portafolio()
    → Agrega todos los perfiles: total, por tipo, por riesgo, score promedio
    → Retorna resumen ejecutivo del portafolio

get_tool_declarations() → types.Tool con FunctionDeclarations (lazy, singleton)
execute_tool(name, args) → str (dispatcher al tool correcto)

── utils/indexing.py ───────────────────────────────────────────────
Background indexation desde Google Drive.

_trigger_startup_index():
  → Ejecutado UNA VEZ por proceso en background thread
  → Restaura ChromaDB ZIP desde Drive (_pactora_chromadb.zip)
  → Escanea DRIVE_ROOT_FOLDER_ID recursivamente
  → Para cada archivo: download → extract_text → vector_ingest_multiple
  → Si LLM_AVAILABLE y !profile_extracted: extract_contract_profile → write_contract_profile
  → Backup ChromaDB ZIP a Drive
  → Actualiza _pactora_index_metadata.json

Progress tracking global:
  _startup_index_progress = {
    "status": "idle|running|done|error",
    "total": int,
    "downloaded": int,
    "file_counts": {"pdf": 0, "docx": 0, ...}
  }

── utils/shared.py ─────────────────────────────────────────────────
Funciones de inicialización y UI usadas en TODAS las páginas.

init_session_state():
  → Inicializa chat_history, resolver_history, contract_events, etc.
  → Llama _trigger_startup_index() si DRIVE_ROOT_FOLDER_ID configurado
  → session_state.chatbot = _get_chatbot()

_get_chatbot() [@st.cache_resource]:
  → Singleton RAGChatbot(persist_directory="./chroma_db", api_key=GEMINI_API_KEY)

page_header(subtitle=""):
  → HTML con branding Pactora by Unergy (fuente Lato, colores purple/yellow)

api_status_banner():
  → Muestra: n contratos indexados | tipos de archivo | estado

_drive_status_widget() [@st.fragment]:
  → Auto-refresh widget mostrando progreso de indexación en sidebar

═══════════════════════════════════════════════════════════════════
SISTEMA DE PERMISOS (RBAC + Feature Flags)
═══════════════════════════════════════════════════════════════════

Hay dos dimensiones de control de acceso:

1. TIPOS DE CONTRATO (restricción de datos):
   - Admin: ve todos los contratos siempre
   - Viewer con allowed_types=["*"]: ve todos
   - Viewer con allowed_types=["PPA","EPC"]: solo ve esos contratos
   - Se aplica en chatbot.py y resolver.py via filter_sources_for_user()
   - Se aplica en ChromaDB via filter_metadata={"source": {"$in": filtered_sources}}

2. FEATURE FLAGS (restricción de funciones):
   - 5 features: juanmitabot, resolver, analisis, comparar, exportar
   - Admin: siempre tiene todas las features
   - Viewer con features=["*"] o features=[]: tiene todas (retrocompatibilidad)
   - Viewer con features=["juanmitabot","analisis"]: solo esas
   - Verificación: has_feature(email, "resolver") en app.py (nav) y resolver.py (page)
   - Gestión: Tab 4 de admin.py con st.data_editor + CheckboxColumn matrix

Esquema completo en Google Sheets:
  email | role | allowed_types(JSON) | allowed_tags(JSON) | features(JSON) |
  added_at | added_by | active

═══════════════════════════════════════════════════════════════════
FLUJO DE DATOS COMPLETO
═══════════════════════════════════════════════════════════════════

CARGA DE DOCUMENTOS:
  Usuario sube PDF → ajustes.py
  → file_parser.extract_text_from_file(file_bytes, filename, gemini_api_key)
      ├── PDF: pypdf + pymupdf; si texto vacío → Gemini Vision OCR
      ├── DOCX: python-docx (párrafos + tablas)
      ├── PPTX: python-pptx (slides + notas)
      ├── XLSX: openpyxl (todas las hojas)
      └── IMG: Gemini Vision OCR (types.Part.from_bytes)
  → chatbot.vector_ingest_multiple([(text, filename, metadata)])
      ├── TextSplitter → chunks (1500/300)
      ├── Summary chunk (800 chars, chunk_type="summary")
      └── ChromaDB.add_documents(all_splits)
  → Si LLM_AVAILABLE: extract_contract_profile() → write_contract_profile() → Sheets
  → _save_index_metadata() → _pactora_index_metadata.json

CONSULTA RAG + AGENTE:
  Usuario escribe pregunta → chatbot.py o resolver.py
  → all-MiniLM-L6-v2.embed_query(question)
  → ChromaDB.similarity_search(question, k=10, filter=user_filter)
  → Si LLM_AVAILABLE:
      run_agent_turn(question, history, system_prompt, filter_metadata)
      → _check_and_record_call()  # rate limit 10/min
      → client.models.generate_content(model, contents, config=Tool)
      → for function_call in response.function_calls:
            result = execute_tool(name, args)
            contents.append(tool_result_as_content)
      → Repetir hasta max_iterations=6 o sin function_calls
      → Retornar response.text
  → Si no LLM: retornar fragmentos formateados

AUTH FLOW:
  app.py load → st.user.is_logged_in?
  → No: pantalla login → st.login("google") → OAuth callback → sesión
  → Sí: is_authorized(email)?
      → No: pantalla acceso denegado + logout button
      → Sí: cargar is_admin, permissions → session_state
  → Render página correspondiente via st.navigation()

═══════════════════════════════════════════════════════════════════
PATRONES Y CONVENCIONES DEL CÓDIGO
═══════════════════════════════════════════════════════════════════

1. SINGLETON DEL CHATBOT:
   _get_chatbot() usa @st.cache_resource para una sola instancia.
   NO importar RAGChatbot directamente en páginas; usar st.session_state.chatbot.

2. IMPORTS CIRCULARES:
   llm_service.py NO debe importar desde pages/ (circular).
   agent_tools.py importa de llm_service y core/rag_chatbot SOLO dentro de funciones.
   Patrón: `from X import Y` dentro del cuerpo de la función que lo necesita.

3. BACKGROUND THREAD:
   _trigger_startup_index() usa threading.Thread(daemon=True).
   El thread accede a st.session_state SOLO a través de variables globales
   (_startup_index_progress dict). No usar st.session_state en threads.

4. CACHE DE USUARIOS (auth_manager):
   TTL de 120 segundos en session_state[_USERS_CACHE_KEY].
   _invalidate_cache() para forzar recarga inmediata después de mutaciones.

5. RATE LIMITING (llm_service):
   _check_and_record_call() lanza ValueError("rate_limit: ...") si > 10/min.
   Capturar con `except ValueError as ve: return f"⏳ {ve}"` en capas superiores.

6. MODO FALLBACK:
   Toda función con Gemini tiene mock data o fallback semántico.
   LLM_AVAILABLE = False → app 100% funcional sin API key.

7. GOOGLE SHEETS - ROBUSTEZ DE COLUMNAS:
   _load_users_from_sheets usa header-based mapping:
     header_row = rows[0]
     col = {h: i for i, h in enumerate(header_row)}
   Esto hace el reader robusto ante cambios de orden de columnas.

8. SECRETS - PRIVATE KEY:
   sa_dict["private_key"] = pk.replace("\\n", "\n").replace("\r", "")
   Los saltos de línea del PEM se pierden al serializar en TOML.

9. FEATURE FLAGS EN NAVEGACIÓN:
   has_feature se chequea en DOS lugares (defense in depth):
   - app.py: controla si la página aparece en el menú de navegación
   - pages/resolver.py: chequea has_feature al inicio y hace st.stop() si no tiene acceso

10. PERFILES DE CONTRATOS (profile_extracted):
    _pactora_index_metadata.json[filename]["profile_extracted"] = True
    Evita re-extraer el perfil con Gemini en cada indexación/reinicio.
    Si es False o no existe → extraer perfil y guardar en Sheets.

═══════════════════════════════════════════════════════════════════
GOOGLE SHEETS — ESTRUCTURA DE LOS SHEETS
═══════════════════════════════════════════════════════════════════

AUTH_USERS_SHEET_ID (Sheet1!A:H):
  Fila 1: email | role | allowed_types | allowed_tags | features | added_at | added_by | active
  Ejemplo: user@co | viewer | ["PPA","EPC"] | [] | ["juanmitabot"] | 2026-03-15T... | admin@co | True
  SA necesita: rol Editor en el Sheet

CONTRACT_PROFILES_SHEET_ID (Sheet1!A:L):
  Fila 1: drive_id | filename | contract_type | parties | start_date | end_date |
          value_clp | obligations_summary | risk_level | risk_summary | compliance_score | indexed_at
  Ejemplo: 1BcD.. | PPA_Unergy.pdf | PPA | Unergy/XYZ Corp | 2024-01-15 | 2034-01-15 |
           500000000 | Entrega 5MW antes COD... | AMARILLO | Penalidad > 10% CAPEX | 72 | 2026-03-15T...
  SA necesita: rol Editor en el Sheet

═══════════════════════════════════════════════════════════════════
VARIABLES DE ENTORNO / SECRETS
═══════════════════════════════════════════════════════════════════

Todas en .streamlit/secrets.toml (NUNCA commitear):

  [auth]
  client_id, client_secret, redirect_uri, cookie_secret

  [auth_config]
  admin_emails = ["admin@unergy.co"]
  initial_allowed_emails = ["user1@unergy.co"]

  [GOOGLE_SERVICE_ACCOUNT]
  type, project_id, private_key_id, private_key, client_email,
  client_id, auth_uri, token_uri, auth_provider_x509_cert_url, client_x509_cert_url

  AUTH_USERS_SHEET_ID = "1abc...xyz"
  CONTRACT_PROFILES_SHEET_ID = "1def...uvw"
  DRIVE_ROOT_FOLDER_ID = "1ghi...rst"
  DRIVE_API_KEY = "AIza..."
  GEMINI_API_KEY = "AIza..."

Cómo acceder en código:
  st.secrets["GEMINI_API_KEY"]
  st.secrets.get("AUTH_USERS_SHEET_ID", "")
  dict(st.secrets["GOOGLE_SERVICE_ACCOUNT"])

═══════════════════════════════════════════════════════════════════
DESPLIEGUE (STREAMLIT CLOUD)
═══════════════════════════════════════════════════════════════════

URL: https://tu-app.streamlit.app
Repo: nicolasr-uner/pactora (GitHub)
Branch main: producción
Python: 3.11

Consideraciones de Streamlit Cloud:
- Entorno EFÍMERO: ChromaDB se pierde en cada restart
  → Solución: backup ZIP en Drive; restore al startup
- Sin storage persistente: todo debe guardarse en Drive/Sheets/external
- Sin variables de entorno del sistema: usar solo st.secrets
- La SA no tiene quota de Drive storage → usar Sheets para datos de usuario

═══════════════════════════════════════════════════════════════════
RESUMEN DE PÁGINAS Y SUS IMPORTS CRÍTICOS
═══════════════════════════════════════════════════════════════════

Todas las páginas empiezan con:
  from utils.shared import apply_styles, page_header, init_session_state
  apply_styles(); init_session_state()

Páginas que usan auth:
  from utils.auth_manager import is_admin, has_feature, is_authorized
  _logged_in = st.user.is_logged_in
  _user_email = st.user.email if _logged_in else ""

Páginas que usan el chatbot:
  chatbot = st.session_state.chatbot
  from utils.auth import get_current_user, filter_sources_for_user

Páginas que usan LLM directo:
  from core.llm_service import LLM_AVAILABLE, run_agent_turn, RESOLVER_SYSTEM_PROMPT

═══════════════════════════════════════════════════════════════════
PROBLEMAS CONOCIDOS Y SUS SOLUCIONES
═══════════════════════════════════════════════════════════════════

❌ storageQuotaExceeded al guardar usuarios
✅ Migrado de Drive JSON a Google Sheets (auth_manager usa Sheets API v4)

❌ ChromaDB se pierde en cada restart de Streamlit Cloud
✅ Backup/restore ZIP en Google Drive al startup (indexing.py)

❌ JuanMitaBot sin contexto con 200+ contratos
✅ Contract Profiles Sheet: perfiles permanentes cargados en <1s

❌ Perfiles re-extraídos en cada indexación (costo Gemini)
✅ profile_extracted=True en _pactora_index_metadata.json

❌ Columnas de Sheets fragmentadas al agregar nueva columna "features"
✅ Header-based column mapping en _load_users_from_sheets()

❌ private_key con \n literales en TOML
✅ pk.replace("\\n", "\n").replace("\r", "") en get_sheets_service_sa()

❌ Gemini quota exhausted (429)
✅ Rate limiter 10/min + fallback a 2.0-flash y 1.5-flash + mock data

❌ Python 3.14 rompe pydantic v1 (metaclass annotations)
✅ Parche en app.py antes de importar streamlit

═══════════════════════════════════════════════════════════════════
GIT Y BRANCHING
═══════════════════════════════════════════════════════════════════

Repo:    github.com/nicolasr-uner/pactora
Main:    main (producción en Streamlit Cloud)
Dev:     claude/nervous-davinci (rama activa de desarrollo)
PR:      #1 (claude/nervous-davinci → main)

Historial reciente de commits relevantes:
  feat: feature permissions matrix + Resolver con JuanMitaBot page
  fix: agregar supportsAllDrives=True a todas las llamadas Drive en auth_manager + CRUD completo en admin
  fix: cambiar backend de usuarios de Drive a st.secrets (SA no tiene cuota de storage)
  fix: agregar Authlib>=1.3.2 para Streamlit Native Auth
  merge: auth OAuth Google completo desde claude/relaxed-tereshkova

═══════════════════════════════════════════════════════════════════
INSTRUCCIONES PARA LA IA
═══════════════════════════════════════════════════════════════════

Cuando trabajes en este proyecto:

1. LEE el archivo antes de editarlo. Nunca edites sin leer primero.

2. NO ROMPER el fallback:
   - Toda integración Gemini debe tener fallback cuando LLM_AVAILABLE = False
   - Toda integración Sheets/Drive debe tener try/except con fallback

3. PATRONES A SEGUIR:
   - Nuevas páginas: empezar con apply_styles() + init_session_state()
   - Nuevas features gated: chequear has_feature en app.py (nav) Y en la página
   - Nuevas herramientas del agente: agregar en agent_tools.py + declarar en llm_service.py
   - Nuevas funciones Sheets: usar _cell(row, "column_name") para acceso robusto

4. NO AGREGAR:
   - FastAPI o cualquier backend separado (todo es Streamlit)
   - PyTorch o sentence-transformers (usar solo chromadb DefaultEmbeddingFunction)
   - Nuevas dependencias sin actualizar requirements.txt

5. TESTS MENTALES antes de editar:
   - ¿Funciona sin GEMINI_API_KEY?
   - ¿Funciona sin AUTH_USERS_SHEET_ID?
   - ¿Funciona sin DRIVE_ROOT_FOLDER_ID?
   - ¿Un viewer sin el feature puede bypassear el control?

6. VARIABLES CLAVE EN SESSION_STATE:
   current_user_email, current_user_is_admin, current_user_permissions,
   chatbot (RAGChatbot singleton),
   chat_history (JuanMitaBot),
   resolver_history (Resolver),
   contract_events (calendario),
   sidebar_chat_filter, sidebar_chat_title

Estás trabajando en un sistema de producción real con datos legales confidenciales.
Prioriza seguridad, robustez y mantenibilidad sobre cleverness.
```

---

*Este prompt fue generado automáticamente a partir del análisis completo del codebase de Pactora CLM · Marzo 2026*
