import streamlit as st
import threading
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PACTORA] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("pactora")

# ─── Startup indexation — runs once per server process ───────────────────────
_startup_index_triggered = False
_startup_index_lock = threading.Lock()
_startup_index_progress = {
    "status": "idle",   # idle | running | complete | error
    "total": 0,
    "downloaded": 0,
    "indexed": 0,
    "last_file": "",
    "error": "",
}


def _bg_startup_index(chatbot, drive_root_id, drive_api_key):
    """Background thread: indexes all Drive contracts once on server startup."""
    prog = _startup_index_progress
    try:
        import concurrent.futures
        from utils.drive_manager import get_recursive_files, download_file_to_io
        from utils.file_parser import extract_text_from_file

        log.info("Iniciando indexacion de Drive (carpeta: %s)", drive_root_id)
        all_files = get_recursive_files(drive_root_id, api_key=drive_api_key)
        log.info("Archivos encontrados en Drive: %d", len(all_files))

        files_to_index = [f for f in all_files if f["name"] not in chatbot._indexed_sources]
        already = len(all_files) - len(files_to_index)
        if already:
            log.info("Ya indexados previamente: %d archivo(s)", already)

        if not files_to_index:
            log.info("Nada nuevo que indexar — todos los archivos ya estan en ChromaDB.")
            prog["status"] = "complete"
            return

        log.info("Archivos nuevos a indexar: %d", len(files_to_index))
        for f in files_to_index:
            log.info("  - %s", f["name"])

        prog["status"] = "running"
        prog["total"] = len(files_to_index)
        prog["downloaded"] = 0
        prog["indexed"] = 0

        # Procesar en lotes de 20 para no saturar memoria con 245 archivos
        BATCH = 20
        total_indexed = 0
        for batch_start in range(0, len(files_to_index), BATCH):
            batch = files_to_index[batch_start: batch_start + BATCH]
            log.info("Lote %d/%d — archivos %d a %d",
                     batch_start // BATCH + 1, -(-len(files_to_index) // BATCH),
                     batch_start + 1, min(batch_start + BATCH, len(files_to_index)))

            docs = []
            gemini_key = chatbot.api_key  # para extraccion de PDFs escaneados
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
                future_to_file = {ex.submit(download_file_to_io, f["id"], drive_api_key): f for f in batch}
                for future in concurrent.futures.as_completed(future_to_file, timeout=120):
                    f = future_to_file[future]
                    try:
                        fio = future.result()
                        prog["last_file"] = f["name"]
                        if fio:
                            # Pasa la Gemini key para extraer PDFs escaneados via Files API
                            txt = extract_text_from_file(fio, f["name"], gemini_api_key=gemini_key)
                            if txt and not txt.startswith("Error"):
                                # Guarda drive_id en metadata para preview directo
                                docs.append((txt, f["name"], {"drive_id": f["id"]}))
                                prog["downloaded"] += 1
                                log.info("OK (%d/%d): %s — %d chars",
                                         prog["downloaded"], prog["total"], f["name"], len(txt))
                            else:
                                prog["downloaded"] += 1
                                log.warning("Sin texto (PDF escaneado sin OCR?): %s", f["name"])
                        else:
                            prog["downloaded"] += 1
                            log.warning("Descarga vacia: %s", f["name"])
                    except concurrent.futures.TimeoutError:
                        prog["downloaded"] += 1
                        log.warning("TIMEOUT: %s — omitido", f["name"])
                    except Exception as e:
                        prog["downloaded"] += 1
                        log.warning("ERROR %s: %s", f["name"], e)

            if docs:
                log.info("Indexando lote: %d documentos a ChromaDB...", len(docs))
                chatbot.vector_ingest_multiple(docs)
                total_indexed += len(docs)
                prog["indexed"] = total_indexed
                log.info("Lote indexado. Acumulado: %d contrato(s).", total_indexed)

        log.info("Descarga completada. Total con texto valido: %d/%d", total_indexed, len(files_to_index))

        prog["status"] = "complete"
        log.info("Indexacion finalizada exitosamente.")
    except Exception as e:
        prog["status"] = "error"
        prog["error"] = str(e)[:120]
        log.error("Error fatal en indexacion: %s", e, exc_info=True)


def _trigger_startup_index(chatbot, drive_root_id, drive_api_key):
    """Launches one background indexation per server process."""
    global _startup_index_triggered
    with _startup_index_lock:
        if _startup_index_triggered:
            return
        _startup_index_triggered = True
    t = threading.Thread(
        target=_bg_startup_index,
        args=(chatbot, drive_root_id, drive_api_key),
        daemon=True
    )
    t.start()

STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Lato:wght@400;700;900&display=swap');
.stApp { background-color: #FDFAF7; font-family: 'Lato', sans-serif; color: #212121; }
section[data-testid="stSidebar"] { background-color: #2C2039 !important; }
[data-testid="stSidebar"] * { color: #FDFAF7 !important; }
.factora-card {
    background: rgba(255,255,255,0.9); border-radius: 16px; padding: 22px;
    box-shadow: 0 6px 24px rgba(145,91,216,0.07); border: 1px solid rgba(145,91,216,0.12);
    margin-bottom: 18px;
}
.card-title {
    font-size: 17px; font-weight: 900; color: #2C2039; margin-bottom: 14px;
    border-left: 4px solid #915BD8; padding-left: 10px;
}
.metric-card {
    background: white; border-radius: 12px; padding: 18px; text-align: center;
    box-shadow: 0 4px 16px rgba(145,91,216,0.08); border: 1px solid rgba(145,91,216,0.1);
}
.metric-val { font-size: 34px; font-weight: 900; color: #915BD8; }
.metric-lbl { font-size: 12px; color: #666; margin-top: 4px; }
.version-badge {
    background: #915BD8; color: white; border-radius: 4px;
    padding: 2px 8px; font-size: 11px; font-weight: 700;
}
div[data-testid="stButton"] > button {
    background-color: #915BD8 !important; color: white !important; border: none;
    border-radius: 8px; font-weight: 700; padding: 8px 20px; transition: background 0.2s;
}
div[data-testid="stButton"] > button:hover { background-color: #7a48c0 !important; }
</style>
"""


def apply_styles():
    st.markdown(STYLES, unsafe_allow_html=True)


def api_status_banner():
    """Muestra estado de Gemini API y Drive. Auto-refresca mientras indexa."""
    try:
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.get("gemini_api_key"):
                st.success("Gemini API activa", icon="✅")
            else:
                st.error("Gemini API no configurada — ve a Ajustes", icon="⚠️")
        with col2:
            if "drive_root_id" not in st.session_state:
                st.warning("Drive no conectado — ve a Ajustes", icon="⚠️")
            else:
                _drive_status_widget()
    except Exception:
        pass


@st.fragment(run_every=5)
def _drive_status_widget():
    """Fragment independiente con auto-refresh cada 5s — sobrevive navegacion."""
    p = _startup_index_progress
    try:
        n = st.session_state.chatbot.get_stats()["total_docs"]
    except Exception:
        n = 0

    if p["status"] == "running":
        total = p["total"] or 1
        done = p["downloaded"]
        pct = done / total
        st.info(
            f"Indexando contratos... **{done}/{total}** procesados  |  "
            f"Indexados en RAG: **{p['indexed']}**",
            icon="⏳"
        )
        st.progress(pct, text=f"{p['last_file'][:55]}" if p["last_file"] else "iniciando...")
    elif p["status"] == "error":
        st.warning(
            f"Drive conectado — {n} contrato(s) indexado(s). Error: {p['error']}",
            icon="⚠️"
        )
    elif p["status"] == "complete":
        st.success(f"Drive conectado — {n} contrato(s) indexado(s)", icon="✅")
    elif p["status"] == "idle":
        # Aun no arranco el hilo
        st.info("Drive conectado — iniciando indexacion...", icon="⏳")
    else:
        st.success(f"Drive conectado — {n} contrato(s)", icon="✅")


def page_header(subtitle="by Unergy"):
    st.markdown(
        '<div style="font-family:Lato,sans-serif;font-weight:900;font-size:46px;'
        'color:#2C2039;text-align:center;margin-bottom:2px;">Pactora</div>'
        f'<div style="text-align:center;color:#915BD8;font-weight:600;margin-bottom:20px;">{subtitle}</div>',
        unsafe_allow_html=True
    )


@st.cache_resource
def _get_chatbot(api_key: str):
    """Crea RAGChatbot una sola vez por proceso de servidor (cache compartido entre sesiones)."""
    from core.rag_chatbot import RAGChatbot
    try:
        return RAGChatbot(api_key=api_key)
    except Exception:
        return RAGChatbot(api_key=None)


def init_session_state():
    if "gemini_api_key" not in st.session_state:
        try:
            st.session_state.gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            st.session_state.gemini_api_key = ""

    try:
        st.session_state.chatbot = _get_chatbot(st.session_state.gemini_api_key)
    except Exception:
        from core.rag_chatbot import RAGChatbot
        st.session_state.chatbot = RAGChatbot(api_key=None)

    defaults = {
        "current_folder_id": "",
        "folder_history": [],
        "doc_versions": {},
        "chat_history": [],
        "sidebar_chat_history": [],
        "sidebar_chat_filter": None,
        "sidebar_chat_title": "",
        "drive_indexed": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # Auto-load Drive credentials from secrets if not already set in session
    if "drive_root_id" not in st.session_state:
        try:
            root_id = st.secrets.get("DRIVE_ROOT_FOLDER_ID", "")
            api_key = st.secrets.get("DRIVE_API_KEY", "")
            if root_id and api_key:
                st.session_state.drive_root_id = root_id
                st.session_state.drive_api_key = api_key
                st.session_state.current_folder_id = root_id
                st.session_state.folder_history = [(root_id, "Raiz Pactora")]
        except Exception:
            pass

    # Auto-trigger one background indexation per server process
    if (
        "drive_root_id" in st.session_state
        and st.session_state.get("drive_api_key", "") not in ("", "DEMO_KEY")
        and st.session_state.chatbot is not None
        and st.session_state.chatbot.embeddings is not None
    ):
        _trigger_startup_index(
            st.session_state.chatbot,
            st.session_state.drive_root_id,
            st.session_state.drive_api_key,
        )


def juanmitabot_sidebar():
    """Chat lateral de JuanMitaBot mostrado en la barra lateral."""
    with st.sidebar:
        # User info si hay sesion activa
        try:
            if st.user.is_logged_in:
                st.markdown(
                    f'<div style="font-size:12px;color:#F6FF72;margin-bottom:4px;">'
                    f'👤 {st.user.name}<br>'
                    f'<span style="opacity:0.7">{st.user.email}</span></div>',
                    unsafe_allow_html=True
                )
                st.button("Cerrar sesion", on_click=st.logout, key="sidebar_logout")
        except Exception:
            pass
        st.markdown("---")
        st.markdown(
            '<div style="font-weight:900;font-size:15px;color:#F6FF72;">🤖 JuanMitaBot</div>',
            unsafe_allow_html=True
        )
        ctx = st.session_state.get("sidebar_chat_title", "")
        if ctx:
            st.caption(f"Contexto: {ctx[:35]}")

        chat_container = st.container(height=280)
        with chat_container:
            for msg in st.session_state.get("sidebar_chat_history", []):
                role_icon = "🤖" if msg["role"] == "assistant" else "👤"
                st.markdown(f"**{role_icon}** {msg['content'][:300]}")
                st.markdown("---")

        user_input = st.chat_input("Pregunta a JuanMitaBot...", key="sidebar_juanmitabot")
        if user_input:
            st.session_state.sidebar_chat_history.append({"role": "user", "content": user_input})
            history_for_llm = st.session_state.sidebar_chat_history[:-1]
            with st.spinner("Analizando..."):
                ans = st.session_state.chatbot.ask_question(
                    user_input,
                    filter_metadata=st.session_state.get("sidebar_chat_filter"),
                    chat_history=history_for_llm
                )
            st.session_state.sidebar_chat_history.append({"role": "assistant", "content": ans})
            st.rerun()

        if st.session_state.get("sidebar_chat_history"):
            if st.button("Limpiar chat", key="clear_sidebar_chat"):
                st.session_state.sidebar_chat_history = []
                st.session_state.sidebar_chat_filter = None
                st.session_state.sidebar_chat_title = ""
                st.rerun()


def force_reindex():
    """Resetea el flag para permitir una nueva indexacion en background (util tras cambiar credenciales)."""
    global _startup_index_triggered
    with _startup_index_lock:
        _startup_index_triggered = False
    # Restablecer progreso
    _startup_index_progress.update({
        "status": "idle", "total": 0, "downloaded": 0,
        "indexed": 0, "last_file": "", "error": "",
    })


def run_drive_indexation(drive_root_id: str, drive_api_key: str):
    """Indexa todos los PDFs/DOCXs del Drive con timeout por archivo. Retorna (ok, msg)."""
    import concurrent.futures
    from utils.drive_manager import get_recursive_files, download_file_to_io
    from utils.file_parser import extract_text_from_file

    def _download(fid):
        return download_file_to_io(fid, api_key=drive_api_key)

    try:
        all_files = get_recursive_files(drive_root_id, api_key=drive_api_key)
        if not all_files:
            return False, "No se encontraron archivos PDF/DOCX en la carpeta."

        docs = []
        skipped = []
        files_to_index = [
            f for f in all_files
            if f["name"] not in st.session_state.chatbot._indexed_sources
        ]

        # Download up to 4 files in parallel, 30s timeout per file
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            future_to_file = {ex.submit(_download, f["id"]): f for f in files_to_index}
            for future, f in future_to_file.items():
                try:
                    fio = future.result(timeout=30)
                    if fio:
                        txt = extract_text_from_file(fio, f["name"])
                        if txt and not txt.startswith("Error"):
                            docs.append((txt, f["name"], {}))
                        else:
                            skipped.append(f["name"])
                    else:
                        skipped.append(f["name"])
                except concurrent.futures.TimeoutError:
                    skipped.append(f["name"] + " (timeout)")
                except Exception:
                    skipped.append(f["name"])

        if not docs:
            msg = "No se pudo descargar ningun archivo nuevo."
            if skipped:
                msg += f" Omitidos: {', '.join(skipped[:5])}"
            return False, msg

        ok, ingest_msg = st.session_state.chatbot.vector_ingest_multiple(docs)
        msg = f"{len(docs)} contrato(s) indexados en JuanMitaBot."
        if skipped:
            msg += f" Omitidos ({len(skipped)}): {', '.join(skipped[:3])}"
        return ok, msg

    except Exception as e:
        return False, f"Error durante indexacion: {e}"


