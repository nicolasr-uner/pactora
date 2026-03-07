# Pactora by Unergy

Sistema de gestión de contratos (CLM) con RAG conversacional, construido sobre Streamlit y Google Gemini.

---

## Que hace

- **JuanMitaBot**: chatbot legal que responde preguntas sobre los contratos indexados, cita fuentes y clasifica riesgos con semáforo ROJO / AMARILLO / VERDE
- **Explorador de Drive**: navega la carpeta corporativa de contratos directamente desde la app
- **Análisis legal**: análisis de cláusulas, comparación de contratos, extracción de riesgos
- **Métricas**: estadísticas de contratos (tipos, valores, fechas, riesgos)
- **Calendario**: extracción automática de fechas clave desde los contratos
- **Plantillas**: generación y gestión de plantillas de contratos

---

## Arquitectura

```
app.py                  ← Entrada principal (st.navigation)
pages/
  inicio.py             ← Explorador de Google Drive
  chatbot.py            ← Chat completo con JuanMitaBot
  legal.py             ← Análisis y comparación de contratos
  metricas.py          ← Dashboard de métricas
  calendario.py        ← Calendario de fechas contractuales
  plantillas.py        ← Gestión de plantillas
  ajustes.py           ← Configuración, diagnóstico, re-indexación
core/
  rag_chatbot.py       ← RAGChatbot: embeddings + ChromaDB + Gemini
utils/
  shared.py            ← Estado compartido, indexación en background, backup/restore
  drive_manager.py     ← Descarga y listado de archivos de Drive
  auth_helper.py       ← Autenticación (Service Account + OAuth2)
  file_parser.py       ← Extracción de texto (pypdf, python-docx, Gemini OCR)
```

### Pipeline de indexación

1. Al arrancar, el hilo de fondo (`_bg_startup_index`) intenta restaurar ChromaDB desde `_pactora_chromadb_backup.zip` en Drive
2. Si no hay backup, descarga todos los PDF/DOCX de la carpeta raíz de Drive (recursivo) en lotes de 20 con 4 workers en paralelo
3. Extrae texto con pypdf/python-docx; para PDFs escaneados usa Gemini OCR
4. Indexa en ChromaDB con embeddings `models/embedding-001` (Google Generative AI)
5. Al terminar, comprime `./chroma_db/` y sube el backup a Drive — así cada reinicio restaura en segundos

---

## Configuración

### Requisitos

- Python 3.10+
- Cuenta de Google Cloud con las APIs habilitadas:
  - Google Drive API
  - Generative Language API (Gemini)

### Variables de entorno / Secrets

En Streamlit Cloud: **App Settings → Secrets**. Localmente: `.streamlit/secrets.toml` (gitignoreado).

```toml
GEMINI_API_KEY = "tu_gemini_api_key"
DRIVE_ROOT_FOLDER_ID = "id_de_la_carpeta_raiz_en_drive"
DRIVE_API_KEY = "tu_google_drive_api_key"

[GOOGLE_SERVICE_ACCOUNT]
type = "service_account"
project_id = "tu-proyecto-id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "nombre-sa@tu-proyecto.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/nombre-sa%40tu-proyecto.iam.gserviceaccount.com"
```

### Configurar la Cuenta de Servicio (Service Account)

La API Key solo sirve para listar archivos públicos. Para descargar contratos privados se necesita una SA:

1. Google Cloud Console → IAM → Cuentas de servicio → Crear (`pactora-drive`)
2. Pestaña Claves → Agregar clave → JSON → descargar
3. En Google Drive: compartir la carpeta raíz con el `client_email` de la SA como **Editor**
4. Pegar los campos del JSON en Streamlit Secrets (ver plantilla arriba)

> El campo `client_x509_cert_url` se construye así:
> `https://www.googleapis.com/robot/v1/metadata/x509/{client_email_url_encoded}`

---

## Instalación local

```bash
git clone https://github.com/nicolasr-uner/pactora.git
cd pactora
pip install -r requirements.txt
# Crear .streamlit/secrets.toml con tus credenciales
streamlit run app.py
```

---

## Deploy en Streamlit Cloud

1. Push al repositorio de GitHub
2. Streamlit Cloud detecta el push y redespliega automáticamente
3. En **App Settings → Secrets**: pegar el bloque TOML completo
4. Al primer arranque: indexa todos los contratos (~5-10 min dependiendo del volumen)
5. Al terminar: crea `_pactora_chromadb_backup.zip` en la carpeta raíz de Drive
6. Reinicios siguientes: restaura el backup en ~30 segundos

---

## Diagnóstico

En la página **Ajustes** hay tres herramientas:

| Herramienta | Qué hace |
|---|---|
| Probar descarga + extracción | Verifica SA → descarga el primer archivo → extrae texto |
| Re-indexar en background | Fuerza re-indexación completa desde Drive |
| Debug: estado interno | Muestra conteo en ChromaDB, progreso del hilo, errores |

---

## Stack técnico

| Capa | Tecnología |
|---|---|
| Frontend | Streamlit 1.55+ |
| LLM | Google Gemini 2.0 Flash |
| Embeddings | `models/embedding-001` (Google Generative AI) |
| Vector store | ChromaDB (persistido en `./chroma_db/`) |
| Drive | Google Drive API v3 + Service Account |
| Extracción PDF | pypdf + Gemini OCR (fallback para escaneados) |
| Extracción DOCX | python-docx |
