import os
import json
import datetime
import streamlit as st
import threading
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PACTORA] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("pactora")

CHROMADB_BACKUP_FILENAME = "_pactora_chromadb_backup.zip"
CHROMADB_DIR = "./chroma_db"
INDEX_METADATA_FILE = "./_pactora_index_metadata.json"


# ─── Index metadata helpers ───────────────────────────────────────────────────

def _load_index_metadata() -> dict:
    """Carga el archivo de metadata de indexación local."""
    try:
        if os.path.exists(INDEX_METADATA_FILE):
            with open(INDEX_METADATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        log.warning("[meta] Error cargando metadata: %s", e)
    return {}


def _save_index_metadata(meta: dict):
    """Guarda el archivo de metadata de indexación local."""
    try:
        with open(INDEX_METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning("[meta] Error guardando metadata: %s", e)

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
    "file_counts": {},  # {"pdf": 12, "docx": 5, "xlsx": 3, ...}
}


def _restore_chromadb_from_drive(drive_root_id: str) -> bool:
    """Download + extract ChromaDB backup zip from Drive. Returns True if restored."""
    import zipfile
    try:
        from utils.auth_helper import get_drive_service
        service = get_drive_service()
        if not service:
            log.info("[restore] Sin servicio Drive — omitiendo restore.")
            return False

        query = (
            f"name='{CHROMADB_BACKUP_FILENAME}' and "
            f"'{drive_root_id}' in parents and trashed=false"
        )
        result = service.files().list(
            q=query, fields="files(id, modifiedTime)",
            supportsAllDrives=True, includeItemsFromAllDrives=True
        ).execute()
        found = result.get("files", [])
        if not found:
            log.info("[restore] No hay backup de ChromaDB en Drive.")
            return False

        file_id = found[0]["id"]
        log.info("[restore] Descargando backup ChromaDB (id: %s)...", file_id[:20])

        from utils.drive_manager import _do_download
        zip_io = _do_download(service, file_id)

        # Verificar integridad del ZIP antes de extraer
        try:
            with zipfile.ZipFile(zip_io, "r") as zf:
                bad = zf.testzip()
                if bad:
                    log.error("[restore] ZIP corrupto — primer archivo dañado: %s", bad)
                    return False
                zip_io.seek(0)
                zf.extractall(".")
        except zipfile.BadZipFile as bz:
            log.error("[restore] ZIP no válido: %s", bz)
            return False

        log.info("[restore] ChromaDB restaurado desde Drive.")
        return True
    except Exception as e:
        log.error("[restore] Error al restaurar ChromaDB: %s", e)
        return False


def _backup_chromadb_to_drive(drive_root_id: str) -> bool:
    """Zip ./chroma_db/ and upload to Drive root folder. Returns True if successful."""
    import zipfile
    import io
    try:
        if not os.path.exists(CHROMADB_DIR):
            log.warning("[backup] chroma_db no existe — nada que hacer backup.")
            return False

        from utils.auth_helper import get_drive_service
        from googleapiclient.http import MediaIoBaseUpload

        service = get_drive_service()
        if not service:
            log.warning("[backup] Sin servicio Drive — backup omitido.")
            return False

        # Zip the chroma_db directory in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, files in os.walk(CHROMADB_DIR):
                for fname in files:
                    filepath = os.path.join(root, fname)
                    arcname = os.path.relpath(filepath, ".")
                    zf.write(filepath, arcname)
        zip_size = zip_buffer.tell()
        zip_buffer.seek(0)
        log.info("[backup] ZIP creado: %.1f MB", zip_size / 1024 / 1024)

        media = MediaIoBaseUpload(zip_buffer, mimetype="application/zip", resumable=True)

        # Check if backup already exists → update; else → create
        query = (
            f"name='{CHROMADB_BACKUP_FILENAME}' and "
            f"'{drive_root_id}' in parents and trashed=false"
        )
        existing = service.files().list(
            q=query, fields="files(id)",
            supportsAllDrives=True, includeItemsFromAllDrives=True
        ).execute().get("files", [])

        if existing:
            service.files().update(
                fileId=existing[0]["id"], media_body=media,
                supportsAllDrives=True
            ).execute()
            log.info("[backup] Backup actualizado en Drive.")
        else:
            service.files().create(
                body={"name": CHROMADB_BACKUP_FILENAME, "parents": [drive_root_id]},
                media_body=media, fields="id",
                supportsAllDrives=True
            ).execute()
            log.info("[backup] Backup creado en Drive.")

        return True
    except Exception as e:
        log.error("[backup] Error al hacer backup ChromaDB: %s", e)
        return False


def _bg_startup_index(api_key, drive_root_id, drive_api_key):
    """Background thread: indexes all Drive contracts once on server startup."""
    # Siempre obtener el chatbot del cache para garantizar que es la misma
    # instancia que usa st.session_state.chatbot (evita el bug de "0 contratos")
    chatbot = _get_chatbot()
    prog = _startup_index_progress
    try:
        import concurrent.futures
        try:
            from utils.drive_manager import get_recursive_files, download_file_to_io
            from utils.file_parser import extract_text_from_file
        except (ImportError, KeyError) as _ie:
            log.error("Modulos no disponibles (hot-reload race): %s — abortando", _ie)
            prog["status"] = "error"
            prog["error"] = f"Import error: {_ie}"
            return

        # ── Cargar metadata de indexación local ─────────────────────────────
        index_meta = _load_index_metadata()

        # ── Intentar restaurar ChromaDB desde backup de Drive ───────────────
        restored = _restore_chromadb_from_drive(drive_root_id)
        if restored:
            chatbot._initialize_vectorstore()
            try:
                stats = chatbot.get_stats()
                chatbot._indexed_sources = stats.get("sources", [])
                log.info("[restore] Vectorstore recargado: %d docs, %d fuentes",
                         stats["total_docs"], len(chatbot._indexed_sources))
            except Exception as re:
                log.warning("[restore] No se pudieron cargar sources: %s", re)
        else:
            # Sin backup de ChromaDB — poblar _indexed_sources desde metadata JSON local
            # para evitar re-indexar archivos cuyo texto ya se descartó (e.g. scanned PDFs)
            if index_meta:
                for fname in index_meta:
                    if fname not in chatbot._indexed_sources:
                        chatbot._indexed_sources.append(fname)
                log.info("[restore] _indexed_sources poblados desde metadata JSON: %d entradas",
                         len(chatbot._indexed_sources))
        # ────────────────────────────────────────────────────────────────────

        log.info("Iniciando indexacion de Drive (carpeta: %s)", drive_root_id)
        all_files = get_recursive_files(drive_root_id, api_key=drive_api_key)
        log.info("Archivos encontrados en Drive: %d", len(all_files))

        # Differential: omitir archivos ya registrados en metadata JSON
        # (sobrevive reinicios incluso sin backup de ChromaDB)
        files_to_index = [
            f for f in all_files
            if f["name"] not in chatbot._indexed_sources
            and f["name"] not in index_meta
        ]
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
        prog["file_counts"] = {}

        # Procesar en lotes de 20 para no saturar memoria con 245 archivos
        BATCH = 20
        BACKUP_EVERY = 50  # backup parcial cada N documentos indexados
        total_indexed = 0

        def _ext_from_name(name: str) -> str:
            parts = name.rsplit(".", 1)
            return parts[-1].lower() if len(parts) > 1 else "otro"

        for batch_start in range(0, len(files_to_index), BATCH):
            batch = files_to_index[batch_start: batch_start + BATCH]
            log.info("Lote %d/%d — archivos %d a %d",
                     batch_start // BATCH + 1, -(-len(files_to_index) // BATCH),
                     batch_start + 1, min(batch_start + BATCH, len(files_to_index)))

            docs = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
                future_to_file = {
                    ex.submit(download_file_to_io, f["id"], drive_api_key, f.get("mimeType")): f
                    for f in batch
                }
                for future in concurrent.futures.as_completed(future_to_file, timeout=120):
                    f = future_to_file[future]
                    try:
                        fio = future.result()
                        prog["last_file"] = f["name"]
                        if fio:
                            txt = extract_text_from_file(fio, f["name"])
                            if txt and not txt.startswith("Error"):
                                # Guarda drive_id en metadata para preview directo
                                docs.append((txt, f["name"], {"drive_id": f["id"]}))
                                prog["downloaded"] += 1
                                # Conteo por extensión
                                ext = _ext_from_name(f["name"])
                                prog["file_counts"][ext] = prog["file_counts"].get(ext, 0) + 1
                                # Registrar en metadata JSON local
                                index_meta[f["name"]] = {
                                    "drive_id": f["id"],
                                    "indexed_at": datetime.datetime.utcnow().isoformat(),
                                    "size": f.get("size", 0),
                                    "ext": ext,
                                }
                                log.info("OK (%d/%d): %s — %d chars",
                                         prog["downloaded"], prog["total"], f["name"], len(txt))
                            elif txt and txt.startswith("Error"):
                                prog["downloaded"] += 1
                                prog["error"] = f"{f['name']}: {txt[:100]}"
                                log.warning("Error extraccion %s: %s", f["name"], txt[:100])
                            else:
                                prog["downloaded"] += 1
                                prog["error"] = f"{f['name']}: sin texto (PDF escaneado sin OCR)"
                                log.warning("Sin texto: %s", f["name"])
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
                ok, ingest_msg = chatbot.vector_ingest_multiple(docs)
                if ok:
                    total_indexed += len(docs)
                    prog["indexed"] = total_indexed
                    log.info("Lote indexado. Acumulado: %d contrato(s).", total_indexed)
                    # Persistir metadata JSON inmediatamente
                    _save_index_metadata(index_meta)
                    # Backup parcial cada BACKUP_EVERY documentos
                    if total_indexed % BACKUP_EVERY == 0:
                        log.info("[backup] Backup parcial en checkpoint: %d docs", total_indexed)
                        _backup_chromadb_to_drive(drive_root_id)
                else:
                    log.error("Error al indexar lote: %s", ingest_msg)

        log.info("Descarga completada. Total con texto valido: %d/%d", total_indexed, len(files_to_index))

        # Actualizar prog["indexed"] con el conteo REAL de ChromaDB
        try:
            real_count = chatbot.get_stats()["total_docs"]
            prog["indexed"] = real_count
            log.info("Verificacion ChromaDB: %d documentos en vectorstore.", real_count)
        except Exception as e:
            log.warning("No se pudo verificar ChromaDB: %s", e)

        # ── Guardar backup de ChromaDB en Drive para sobrevivir reinicios ───
        if prog["indexed"] > 0:
            log.info("[backup] Guardando ChromaDB en Drive...")
            _backup_chromadb_to_drive(drive_root_id)
        # ────────────────────────────────────────────────────────────────────

        prog["status"] = "complete"
        log.info("Indexacion finalizada exitosamente. Total en ChromaDB: %d", prog["indexed"])
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
    api_key = chatbot.api_key if chatbot else None
    t = threading.Thread(
        target=_bg_startup_index,
        args=(api_key, drive_root_id, drive_api_key),
        daemon=True
    )
    t.start()

STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Lato:wght@400;700;900&display=swap');
.stApp { background-color: #FDFAF7; font-family: 'Lato', sans-serif; color: #212121; }
section[data-testid="stSidebar"] { background-color: #2C2039 !important; }
[data-testid="stSidebar"] * { color: #FDFAF7 !important; }
/* Chat input en sidebar: fondo y texto legibles */
[data-testid="stSidebar"] [data-testid="stChatInput"] textarea,
[data-testid="stSidebar"] [data-testid="stChatInput"] input {
    color: #1a1a2e !important;
    background-color: #f0eaf8 !important;
}
[data-testid="stSidebar"] [data-testid="stChatInput"] {
    background-color: #f0eaf8 !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-testid="stChatInput"] textarea::placeholder {
    color: #7a6a9a !important;
}
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
    """Muestra estado del bot, contratos indexados y desglose por tipo."""
    try:
        try:
            n = st.session_state.chatbot.get_stats()["total_docs"]
        except Exception:
            n = 0
        counts = _startup_index_progress.get("file_counts", {})
        if n > 0:
            if counts:
                counts_str = "  |  ".join(
                    f"{ext.upper()}: {c}" for ext, c in sorted(counts.items()) if c > 0
                )
                st.success(f"✅  {n} contrato(s) indexado(s) — {counts_str} — JuanMitaBot listo")
            else:
                st.success(f"{n} contrato(s) indexado(s) — JuanMitaBot listo", icon="✅")
        else:
            st.info("Sin contratos indexados — ve a **Ajustes** para cargar documentos", icon="📄")
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
        pct = min(done / total, 1.0)
        st.info(
            f"Indexando contratos... **{done}/{total}** procesados  |  "
            f"Indexados en RAG: **{p['indexed']}**",
            icon="⏳"
        )
        st.progress(pct, text=f"{p['last_file'][:55]}" if p["last_file"] else "iniciando...")
    elif p["status"] == "error":
        st.warning(
            f"Drive conectado — {p['indexed']} contrato(s) indexado(s). Error: {p['error']}",
            icon="⚠️"
        )
    elif p["status"] == "complete":
        count = p["indexed"] if p["indexed"] > 0 else n
        counts = p.get("file_counts", {})
        if counts:
            counts_str = "  |  ".join(
                f"{ext.upper()}: {c}" for ext, c in sorted(counts.items()) if c > 0
            )
            st.success(f"Drive conectado — {count} contrato(s)  •  {counts_str}", icon="✅")
        else:
            st.success(f"Drive conectado — {count} contrato(s) indexado(s)", icon="✅")
    elif p["status"] == "idle":
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
def _get_chatbot(_unused=None):
    """Crea RAGChatbot una sola vez por proceso de servidor (cache compartido entre sesiones)."""
    from core.rag_chatbot import RAGChatbot
    try:
        return RAGChatbot()
    except Exception as e:
        log.error("[shared] Error creando RAGChatbot: %s", e)
        return RAGChatbot()


def init_session_state():
    try:
        st.session_state.chatbot = _get_chatbot()
    except Exception:
        from core.rag_chatbot import RAGChatbot
        st.session_state.chatbot = RAGChatbot()

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

    # Auto-trigger one background indexation per server process (solo si Drive configurado)
    if (
        "drive_root_id" in st.session_state
        and st.session_state.get("drive_api_key", "") not in ("", "DEMO_KEY")
        and st.session_state.chatbot is not None
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
            '<div style="font-weight:900;font-size:15px;color:#F6FF72;">💬 JuanMitaBot</div>'
            '<div style="font-size:11px;color:#c9b8e8;margin-bottom:6px;">Pregunta sobre tus contratos</div>',
            unsafe_allow_html=True
        )
        ctx = st.session_state.get("sidebar_chat_title", "")
        if ctx:
            st.caption(f"📄 {ctx[:35]}")

        history = st.session_state.get("sidebar_chat_history", [])
        chat_container = st.container(height=260)
        with chat_container:
            if not history:
                st.markdown(
                    '<div style="color:#9d87c0;font-size:12px;text-align:center;margin-top:80px;">'
                    'Escribe tu pregunta abajo<br>y presiona Enter ↵</div>',
                    unsafe_allow_html=True
                )
            for msg in history[-6:]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        user_input = st.chat_input("Escribe tu pregunta...", key="sidebar_juanmitabot")
        if user_input:
            st.session_state.sidebar_chat_history.append({"role": "user", "content": user_input})
            history_for_llm = st.session_state.sidebar_chat_history[:-1]
            try:
                with st.spinner("Buscando..."):
                    ans = st.session_state.chatbot.ask_question(
                        user_input,
                        filter_metadata=st.session_state.get("sidebar_chat_filter"),
                        chat_history=history_for_llm
                    )
            except Exception as _e:
                ans = f"⚠️ Error interno: {_e}"
                log.error("[sidebar] ask_question falló: %s", _e, exc_info=True)
            st.session_state.sidebar_chat_history.append({"role": "assistant", "content": ans})
            st.rerun()

        if history:
            if st.button("🗑 Limpiar chat", key="clear_sidebar_chat", width="stretch"):
                st.session_state.sidebar_chat_history = []
                st.session_state.sidebar_chat_filter = None
                st.session_state.sidebar_chat_title = ""
                st.rerun()


def render_document_preview(source_name: str, height: int = 660):
    """
    Renderiza previsualización enriquecida para un documento indexado.
    Orden de intentos:
      1. PDF bytes en _file_cache (subidos en sesión actual) → base64 iframe
      2. drive_id en metadata de ChromaDB:
         - PDF → embed Google Drive viewer (/preview) sin descarga
         - Otros → descarga + render (imagen, Excel, CSV)
      3. Texto de chunks del vectorstore → div scrollable (sin textarea amarillo)
    """
    import io as _io

    fname_lower = source_name.lower()

    # 1. PDF en caché de sesión (subido manualmente en esta sesión)
    cached_pdf = st.session_state.get("_file_cache", {}).get(source_name)
    if cached_pdf and fname_lower.endswith(".pdf"):
        import base64 as _b64
        b64_pdf = _b64.b64encode(cached_pdf).decode()
        st.markdown(
            f'<iframe src="data:application/pdf;base64,{b64_pdf}" '
            f'width="100%" height="{height}" '
            f'style="border:1px solid #e0d4f7;border-radius:8px;"></iframe>',
            unsafe_allow_html=True
        )
        st.download_button("⬇ Descargar PDF", data=cached_pdf,
                           file_name=source_name, mime="application/pdf",
                           key=f"dl_pdf_prev_{source_name}")
        return

    # 2. Buscar drive_id en metadata de ChromaDB
    drive_id = None
    try:
        cb = st.session_state.get("chatbot")
        if cb and cb.vectorstore:
            result = cb.vectorstore.get(include=["metadatas"])
            for m in result.get("metadatas", []):
                if m and m.get("source") == source_name and m.get("drive_id"):
                    drive_id = m["drive_id"]
                    break
    except Exception:
        pass

    if drive_id:
        if fname_lower.endswith(".pdf"):
            # 2a. PDF desde Drive — embed directo vía Google Viewer (sin descarga)
            import streamlit.components.v1 as _components
            embed_url = f"https://drive.google.com/file/d/{drive_id}/preview"
            _components.iframe(embed_url, height=height, scrolling=True)
            # Botón de descarga bajo demanda vía service account
            dl_cache_key = f"_drive_dl_{drive_id}"
            dl_bytes = st.session_state.get(dl_cache_key)
            if dl_bytes:
                st.download_button("⬇ Descargar PDF", data=dl_bytes,
                                   file_name=source_name, mime="application/pdf",
                                   key=f"dl_pdf_drv_{drive_id}")
            else:
                if st.button("⬇ Descargar PDF", key=f"dl_drv_btn_{drive_id}"):
                    with st.spinner("Descargando desde Drive..."):
                        try:
                            from utils.drive_manager import download_file_to_io
                            fio = download_file_to_io(drive_id)
                            if fio:
                                st.session_state[dl_cache_key] = fio.read()
                                st.rerun()
                        except Exception as _e:
                            st.error(f"Error al descargar: {_e}")
            return

        # 2b. Archivo no-PDF desde Drive — descargar y renderizar
        cache_key = f"_drive_preview_{drive_id}"
        file_bytes = st.session_state.get(cache_key)
        if file_bytes is None:
            with st.spinner(f"Cargando {source_name} desde Drive..."):
                try:
                    from utils.drive_manager import download_file_to_io
                    fio = download_file_to_io(drive_id)
                    if fio:
                        file_bytes = fio.read()
                        st.session_state[cache_key] = file_bytes
                except Exception as _e:
                    log.warning("[preview] Error descargando %s: %s", source_name, _e)

        if file_bytes:
            if any(fname_lower.endswith(e) for e in (".png", ".jpg", ".jpeg")):
                st.image(file_bytes, caption=source_name, use_container_width=True)
                return
            elif fname_lower.endswith(".tiff") or fname_lower.endswith(".tif"):
                try:
                    from PIL import Image
                    img = Image.open(_io.BytesIO(file_bytes))
                    st.image(img, caption=source_name, use_container_width=True)
                except Exception:
                    st.info("Formato TIFF — descarga el archivo para verlo.")
                st.download_button("⬇ Descargar imagen", data=file_bytes,
                                   file_name=source_name, key=f"dl_img_drv_{drive_id}")
                return
            elif fname_lower.endswith(".xlsx"):
                try:
                    import pandas as _pd
                    df = _pd.read_excel(_io.BytesIO(file_bytes), nrows=200)
                    st.dataframe(df, use_container_width=True, height=height)
                    st.download_button("⬇ Descargar Excel", data=file_bytes,
                                       file_name=source_name, key=f"dl_xlsx_drv_{drive_id}")
                    return
                except Exception as _e:
                    st.warning(f"No se pudo mostrar como tabla: {_e}")
            elif fname_lower.endswith(".csv"):
                try:
                    import pandas as _pd
                    import io as _io2
                    df = _pd.read_csv(_io2.StringIO(file_bytes.decode("utf-8", errors="replace")), nrows=200)
                    st.dataframe(df, use_container_width=True, height=height)
                    return
                except Exception as _e:
                    st.warning(f"No se pudo mostrar como tabla: {_e}")

    # 3. Fallback: texto de chunks — div scrollable con tipografía legible
    try:
        cb = st.session_state.get("chatbot")
        if cb and cb.vectorstore:
            result = cb.vectorstore.get(include=["documents", "metadatas"])
            chunks = [d for d, m in zip(result.get("documents", []), result.get("metadatas", []))
                      if m and m.get("source") == source_name]
            if chunks:
                full_text = "\n\n─────────────────────\n\n".join(chunks)
                safe_text = full_text[:30000].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                st.markdown(
                    f'<div style="height:{height}px;overflow-y:auto;padding:20px 24px;'
                    f'background:#ffffff;border:1px solid #e0e0e0;border-radius:8px;'
                    f'font-family:\'Georgia\',serif;font-size:13.5px;line-height:1.75;'
                    f'color:#212121;white-space:pre-wrap;">{safe_text}</div>',
                    unsafe_allow_html=True
                )
                st.download_button("⬇ Exportar texto", data=full_text.encode("utf-8"),
                                   file_name=f"{source_name}_texto.txt", mime="text/plain",
                                   key=f"dl_txt_prev_{source_name}")
                return
    except Exception:
        pass

    st.info("Sin previsualización disponible para este documento.")


def force_reindex(chatbot=None):
    """Resetea el flag y limpia _indexed_sources para re-indexar todos los archivos."""
    global _startup_index_triggered
    with _startup_index_lock:
        _startup_index_triggered = False
    _startup_index_progress.update({
        "status": "idle", "total": 0, "downloaded": 0,
        "indexed": 0, "last_file": "", "error": "",
    })
    # Limpiar lista de fuentes para que el thread procese todos los archivos
    if chatbot is not None:
        chatbot._indexed_sources = []


def run_drive_indexation(drive_root_id: str, drive_api_key: str):
    """Indexa todos los documentos soportados del Drive con timeout por archivo. Retorna (ok, msg)."""
    import concurrent.futures
    from utils.drive_manager import get_recursive_files, download_file_to_io
    from utils.file_parser import extract_text_from_file

    def _download(fid, mime=None):
        return download_file_to_io(fid, api_key=drive_api_key, mime_type=mime)

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
            future_to_file = {ex.submit(_download, f["id"], f.get("mimeType")): f for f in files_to_index}
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


