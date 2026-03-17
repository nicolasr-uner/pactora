import streamlit as st
from utils.shared import apply_styles, page_header, init_session_state

apply_styles()
init_session_state()
page_header()

st.markdown("## Ajustes")
st.caption("Configura tu workspace: carga contratos, gestiona el índice y conecta integraciones externas.")

# ─── Banner de seguridad — sin autenticación de usuarios ──────────────────────
try:
    _user_auth_active = st.user.is_logged_in
except Exception:
    _user_auth_active = False  # st.user no disponible en esta versión o sin auth configurada

if not _user_auth_active:
    st.warning(
        "**⚠️ App sin autenticación de usuarios activa.** "
        "Cualquier persona con la URL puede acceder a todos los contratos y configuraciones. "
        "Configura Streamlit Auth en `.streamlit/secrets.toml` para proteger la aplicación en producción.",
        icon="🔒"
    )

# ─── Diagnóstico del sistema ──────────────────────────────────────────────────
with st.expander("🔧 Diagnóstico del sistema", expanded=False):
    diag_cols = st.columns(2)
    with diag_cols[0]:
        # Chatbot
        cb = st.session_state.get("chatbot")
        if cb is None:
            st.error("❌ Chatbot no inicializado")
        else:
            st.success("✅ Chatbot inicializado")
            emb_ok = cb.embeddings is not None
            st.write(f"{'✅' if emb_ok else '❌'} Embeddings: {'cargados' if emb_ok else 'NO disponibles'}")
            vs_ok = cb.vectorstore is not None
            st.write(f"{'✅' if vs_ok else '⚠️'} Vectorstore: {'conectado' if vs_ok else 'no inicializado (normal si aún no hay contratos)'}")
            try:
                _s = cb.get_stats()
                st.write(f"✅ ChromaDB: {_s['total_docs']} contrato(s), {_s['total_chunks']} chunks")
            except Exception as _e:
                st.write(f"❌ ChromaDB get_stats: {_e}")

    with diag_cols[1]:
        # Librerías
        for lib, name in [("pypdf", "pypdf"), ("PyPDF2", "PyPDF2"), ("docx", "python-docx"),
                          ("pptx", "python-pptx"), ("chromadb", "chromadb"),
                          ("langchain_community", "langchain-community"),
                          ("fitz", "pymupdf"), ("openpyxl", "openpyxl")]:
            try:
                __import__(lib)
                st.write(f"✅ {name}")
            except ImportError as _ie:
                st.write(f"❌ {name}: {_ie}")

    # Metadata JSON de indexación
    try:
        from utils.shared import _load_index_metadata
        _imeta = _load_index_metadata()
        if _imeta:
            with st.expander(f"📋 Metadata de indexación ({len(_imeta)} entradas)", expanded=False):
                import pandas as _pd_diag
                _meta_rows = [
                    {
                        "Archivo": k,
                        "Extensión": v.get("ext", "?").upper(),
                        "Indexado": v.get("indexed_at", "")[:10],
                        "Drive ID": v.get("drive_id", "")[:20] + "…" if v.get("drive_id") else "—",
                    }
                    for k, v in _imeta.items()
                ]
                st.dataframe(_pd_diag.DataFrame(_meta_rows), use_container_width=True, hide_index=True)
    except Exception:
        pass

    if st.button("🧪 Test embeddings", key="diag_emb"):
        try:
            cb = st.session_state.chatbot
            vec = cb.embeddings.embed_query("prueba de embeddings")
            st.success(f"Embeddings OK — vector dim: {len(vec)}")
        except Exception as _e:
            st.error(f"Error en embeddings: {_e}")

st.markdown("---")

# ─── Sección 1: Cargar contratos ──────────────────────────────────────────────
sec1_hrow = st.columns([9, 1])
sec1_hrow[0].markdown("### 📂 Cargar Contratos")
with sec1_hrow[1].popover("ℹ️"):
    st.markdown(
        "Sube tus contratos en formato **PDF** o **DOCX** para indexarlos localmente. "
        "También puedes subir un **ZIP** con múltiples archivos.\\n\\n"
        "Los archivos se procesan localmente — no se envían a ningún servidor externo."
    )

st.caption("Sube contratos desde tu computador: PDF, DOCX, XLSX, XLS, CSV, TXT. Para una carpeta completa: comprímela en ZIP.")

uploaded_files = st.file_uploader(
    "Selecciona archivos",
    type=["pdf", "docx", "xlsx", "xls", "csv", "txt", "zip"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)

if uploaded_files:
    import io as _io, zipfile

    expanded = []
    for uf in uploaded_files:
        if uf.name.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(_io.BytesIO(uf.read())) as zf:
                    for entry in zf.namelist():
                        if entry.lower().endswith((".pdf", ".docx", ".xlsx", ".xls", ".csv", ".txt")) and not entry.startswith("__MACOSX"):
                            fname = entry.split("/")[-1]
                            expanded.append((fname, _io.BytesIO(zf.read(entry))))
                st.info(f"ZIP **{uf.name}**: {len(expanded)} archivo(s) extraído(s)")
            except Exception as e:
                st.error(f"No se pudo abrir {uf.name}: {e}")
        else:
            raw_bytes = uf.read()
            # Cachear bytes del PDF para previsualización (máx 10 MB)
            if uf.name.lower().endswith(".pdf") and len(raw_bytes) <= 10 * 1024 * 1024:
                if "_file_cache" not in st.session_state:
                    st.session_state["_file_cache"] = {}
                st.session_state["_file_cache"][uf.name] = raw_bytes
            expanded.append((uf.name, _io.BytesIO(raw_bytes)))

    already = set(st.session_state.chatbot._indexed_sources)
    new_files = [(name, fio) for name, fio in expanded if name not in already]
    skipped = [name for name, _ in expanded if name in already]

    if skipped:
        st.info(f"Ya indexados (se omiten): {', '.join(skipped)}")

    if new_files:
        st.write(f"**{len(new_files)} archivo(s) nuevos listos para indexar:**")
        for name, _ in new_files[:10]:
            st.write(f"  • {name}")
        if len(new_files) > 10:
            st.write(f"  … y {len(new_files) - 10} más")

        if st.button("📥 Indexar archivos cargados", type="primary", width="stretch"):
            from utils.file_parser import extract_text_from_file

            docs = []
            errors = []

            with st.status("Procesando archivos...", expanded=True) as _status:
                for name, fio in new_files:
                    st.write(f"📄 {name}...")
                    try:
                        txt = extract_text_from_file(fio, name)
                    except Exception as ex:
                        txt = f"Error: {ex}"
                    if txt and not txt.startswith("Error"):
                        docs.append((txt, name, {}))
                    else:
                        reason = txt[:120] if txt else "sin texto (PDF escaneado o imagen sin OCR)"
                        errors.append(f"**{name}**: {reason}")

                for e in errors:
                    st.warning(e)

                if docs:
                    st.write("Indexando en ChromaDB...")
                    ok, msg = st.session_state.chatbot.vector_ingest_multiple(docs)
                    if ok:
                        stats_result = st.session_state.chatbot.get_stats()
                        _status.update(
                            label=f"✅ {len(docs)} archivo(s) indexados — Total: {stats_result['total_docs']}",
                            state="complete",
                            expanded=False
                        )
                        st.rerun()
                    else:
                        _status.update(label="❌ Error al indexar en ChromaDB", state="error")
                        st.error(f"Error al indexar en ChromaDB: {msg}")
                else:
                    _status.update(label="⚠️ Sin texto extraíble", state="error")
                    st.error(
                        "⚠️ Ningún archivo produjo texto extraíble. "
                        "Asegúrate de que los PDFs tengan texto seleccionable (no sean imágenes escaneadas)."
                    )
    else:
        st.info("Todos los archivos seleccionados ya están indexados.")

# ─── Sección 2: Contratos indexados ───────────────────────────────────────────
st.markdown("---")
sec2_hrow = st.columns([9, 1])
sec2_hrow[0].markdown("### 📋 Contratos Indexados")
with sec2_hrow[1].popover("ℹ️"):
    st.markdown(
        "Lista de todos los contratos actualmente en el índice local (ChromaDB). "
        "Puedes limpiar el índice completo si necesitas empezar de cero.\\n\\n"
        "⚠️ Limpiar el índice eliminará todos los contratos y no se puede deshacer."
    )

stats = st.session_state.chatbot.get_stats()

if stats["total_docs"] > 0:
    st.success(f"**{stats['total_docs']} contrato(s)** indexados y listos para búsqueda.")
    with st.expander(f"Ver contratos ({len(stats['sources'])})"):
        for src in stats["sources"]:
            ext = src.lower().split(".")[-1] if "." in src else ""
            icon = "📄" if ext == "pdf" else "📝" if ext == "docx" else "📁"
            st.write(f"{icon} {src}")
        st.markdown("---")
        if st.button("🗑 Limpiar todos los contratos indexados", type="secondary"):
            import shutil, os
            chroma_dir = "./chroma_db"
            if os.path.exists(chroma_dir):
                shutil.rmtree(chroma_dir)
            from utils.shared import _get_chatbot
            _get_chatbot.clear()
            st.session_state.chatbot = _get_chatbot()
            st.success("ChromaDB limpiado. Vuelve a cargar los contratos.")
            st.rerun()
else:
    st.info("No hay contratos indexados aún. Carga archivos en la sección de arriba.")

# ─── Sección 3: Google Drive ──────────────────────────────────────────────────
st.markdown("---")
sec3_hrow = st.columns([9, 1])
sec3_hrow[0].markdown("### ☁️ Google Drive")
with sec3_hrow[1].popover("ℹ️"):
    st.markdown(
        "Conecta una carpeta de Google Drive para indexar contratos automáticamente.\n\n"
        "Configura `DRIVE_ROOT_FOLDER_ID`, `DRIVE_API_KEY` y `GOOGLE_SERVICE_ACCOUNT` "
        "en **App Settings → Secrets** de Streamlit Cloud."
    )

_drive_root_id = st.session_state.get("drive_root_id", "")
_drive_api_key = st.session_state.get("drive_api_key", "")
_drive_configured = bool(_drive_root_id and _drive_api_key and _drive_api_key != "DEMO_KEY")

if _drive_configured:
    _stats_drive = st.session_state.chatbot.get_stats()
    st.success(
        f"✅ **Drive conectado** — Carpeta: `{_drive_root_id[:28]}...` · "
        f"{_stats_drive['total_docs']} contrato(s) indexado(s)",
        icon="☁️"
    )

    from utils.shared import _drive_status_widget
    _drive_status_widget()

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        if st.button("🔍 Probar conexión", width="stretch", key="drive_test_btn"):
            with st.spinner("Conectando con Drive..."):
                try:
                    from utils.drive_manager import get_folder_contents
                    contents = get_folder_contents(_drive_root_id, api_key=_drive_api_key)
                    files = [f for f in (contents or []) if f.get("mimeType") != "application/vnd.google-apps.folder"][:3]
                    if files:
                        st.success(f"✅ Conexión exitosa. Primeros archivos en la carpeta:")
                        for f in files:
                            st.write(f"  • {f.get('name', '?')}")
                    else:
                        st.info("Conexión exitosa — carpeta vacía o solo subcarpetas.")
                except Exception as _e:
                    st.error(f"❌ Error al conectar: {_e}")

    with col_d2:
        if st.button("🔄 Re-indexar desde Drive", width="stretch", key="drive_reindex_btn", type="primary"):
            from utils.shared import force_reindex, _trigger_startup_index
            force_reindex(st.session_state.chatbot)
            _trigger_startup_index(
                st.session_state.chatbot,
                _drive_root_id,
                _drive_api_key,
            )
            st.success("Re-indexación iniciada en segundo plano.")
            st.rerun()
else:
    st.info(
        "**Drive no configurado.** Para conectar Google Drive, añade estos secrets en "
        "**Streamlit Cloud → App Settings → Secrets**:\n\n"
        "```toml\n"
        "DRIVE_ROOT_FOLDER_ID = \"tu_folder_id\"\n"
        "DRIVE_API_KEY = \"tu_api_key\"\n\n"
        "[GOOGLE_SERVICE_ACCOUNT]\n"
        "type = \"service_account\"\n"
        "# ... resto del JSON de la cuenta de servicio\n"
        "```",
        icon="☁️"
    )

# ─── Sección 4: Gemini API ─────────────────────────────────────────────────────
st.markdown("---")
sec4_hrow = st.columns([9, 1])
sec4_hrow[0].markdown("### 🤖 Gemini API")
with sec4_hrow[1].popover("ℹ️"):
    st.markdown(
        "Gemini potencia a JuanMitaBot con respuestas inteligentes, análisis de riesgo, "
        "comparación de contratos y extracción de fechas.\n\n"
        "Configura `GEMINI_API_KEY` en **App Settings → Secrets** de Streamlit Cloud. "
        "Obtén tu clave gratis en [aistudio.google.com](https://aistudio.google.com/apikey)."
    )

from core.llm_service import LLM_AVAILABLE, get_call_stats, _GEMINI_MODEL, _GEMINI_FALLBACK_MODEL

if LLM_AVAILABLE:
    _gstats = get_call_stats()
    col_g1, col_g2 = st.columns([3, 1])
    with col_g1:
        st.success(f"✅ **Gemini activo** — modelo `{_GEMINI_MODEL}` · fallback `{_GEMINI_FALLBACK_MODEL}`", icon="🤖")
    with col_g2:
        if st.button("🧪 Probar conexión", width="stretch", key="gemini_test_btn"):
            with st.spinner("Probando Gemini..."):
                from core.llm_service import test_gemini_connection
                _ok, _msg = test_gemini_connection()
                if _ok:
                    st.success(f"✅ {_msg}")
                else:
                    st.error(f"❌ {_msg}")

    # Cadena de modelos activa
    _model_chain = _gstats.get("model_chain", [_gstats.get("primary_model", "?")])
    _chain_labels = {"gemini-2.5-flash": "~20 req/día", "gemini-2.0-flash": "~1,500 req/día", "gemini-1.5-flash": "cuota alta"}
    _chain_html = " → ".join(
        f'<span style="background:#915BD8;color:white;border-radius:4px;padding:2px 7px;font-size:11px;margin:0 2px">'
        f'{m} <span style="opacity:.7">({_chain_labels.get(m,"")})</span></span>'
        for m in _model_chain
    )
    st.markdown(
        f"**Cadena de modelos** (se usa el primero disponible, baja al siguiente si quota agotada):<br>{_chain_html}",
        unsafe_allow_html=True,
    )
    st.caption("Cuando gemini-2.5-flash agota sus ~20 req/día, se pasa automáticamente a gemini-2.0-flash (1,500 req/día), y luego a gemini-1.5-flash.")

    # Contador de uso
    _calls_today = _gstats["calls_today"]
    _calls_min = _gstats["calls_last_minute"]
    _rate_max = _gstats["rate_limit_per_minute"]
    _c1, _c2, _c3 = st.columns(3)
    with _c1:
        st.metric("Llamadas hoy", _calls_today, help="Se resetea a medianoche (contador en memoria, no persiste entre reinicios).")
    with _c2:
        st.metric("Llamadas último minuto", f"{_calls_min}/{_rate_max}", help=f"Límite interno: {_rate_max} llamadas/minuto para proteger la quota.")
    with _c3:
        # Quota estimada: si < 20 → puede estar en gemini-2.5-flash, si > 20 → en gemini-2.0-flash
        _quota_pct = min(100, int(_calls_today / 15))  # referencia: 1500 req/día
        st.metric("Quota usada (ref. 1,500/día)", f"{_quota_pct}%", help="Estimado sobre gemini-2.0-flash (1,500 req/día). Los primeros ~20 van sobre gemini-2.5-flash.")
else:
    st.warning(
        "**⚫ Gemini no configurado** — JuanMitaBot funciona en modo búsqueda semántica local.\n\n"
        "Para activar respuestas generadas por IA, añade en **Streamlit Cloud → App Settings → Secrets**:\n\n"
        "```toml\nGEMINI_API_KEY = \"AIzaSy...\"\n```\n\n"
        "Obtén tu clave gratuita en [aistudio.google.com/apikey](https://aistudio.google.com/apikey).",
        icon="🤖"
    )

# ─── Sección 5: Cerrar sesión ──────────────────────────────────────────────────
st.markdown("---")
sec5_hrow = st.columns([9, 1])
sec5_hrow[0].markdown("### ⚙️ Sesión")
with sec5_hrow[1].popover("ℹ️"):
    st.markdown(
        "Limpia todos los datos de la sesión actual (contratos cargados, historial de búsqueda, eventos). "
        "El índice de ChromaDB **no se borra** con esta acción — solo el estado de la sesión."
    )

col_ses1, col_ses2 = st.columns([3, 1])
with col_ses1:
    st.caption("Reinicia la sesión de Pactora. El índice local de contratos se mantiene.")
with col_ses2:
    if st.button("Cerrar sesión", width="stretch"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
