"""
shared.py — Funciones centrales de Pactora CLM.
Contiene: init_session_state, page_header, api_status_banner,
          _drive_status_widget, juanmitabot_sidebar.

Re-exporta desde submodulos para compatibilidad con imports existentes:
  - apply_styles, dark_mode_toggle  ← utils/styles.py
  - render_document_preview         ← utils/preview.py
  - _load_index_metadata, _save_index_metadata, _startup_index_progress,
    _trigger_startup_index, force_reindex, run_drive_indexation ← utils/indexing.py
"""
import logging

import streamlit as st

# ─── Re-exports para compatibilidad ───────────────────────────────────────────
from utils.styles import apply_styles, dark_mode_toggle, STYLES, DARK_STYLES  # noqa: F401
from utils.preview import render_document_preview  # noqa: F401
from utils.indexing import (  # noqa: F401
    _load_index_metadata,
    _save_index_metadata,
    _startup_index_progress,
    _trigger_startup_index,
    force_reindex,
    run_drive_indexation,
    _restore_chromadb_from_drive,
    _backup_chromadb_to_drive,
    CHROMADB_BACKUP_FILENAME,
    CHROMADB_DIR,
    INDEX_METADATA_FILE,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PACTORA] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("pactora")


# ─── Chatbot singleton ────────────────────────────────────────────────────────

@st.cache_resource
def _get_chatbot(_unused=None):
    """Crea RAGChatbot una sola vez por proceso de servidor (cache compartido entre sesiones)."""
    from core.rag_chatbot import RAGChatbot
    try:
        return RAGChatbot()
    except Exception as e:
        log.error("[shared] Error creando RAGChatbot: %s", e)
        return RAGChatbot()


# ─── Session state ────────────────────────────────────────────────────────────

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
        "sidebar_chat_history": [],   # mantenido por compatibilidad
        "sidebar_chat_filter": None,
        "sidebar_chat_title": "",
        "drive_indexed": False,
        "dark_mode": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # Auto-load Drive credentials desde secrets
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

    # Auto-trigger indexación en background (una sola vez por proceso)
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


# ─── UI helpers ───────────────────────────────────────────────────────────────

def page_header(subtitle="by Unergy"):
    st.markdown(
        '<div style="font-family:Lato,sans-serif;font-weight:900;font-size:46px;'
        'text-align:center;margin-bottom:2px;" class="pactora-title">Pactora</div>'
        f'<div style="text-align:center;font-weight:600;margin-bottom:20px;" class="pactora-sub">{subtitle}</div>',
        unsafe_allow_html=True,
    )


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
    """Fragment con auto-refresh cada 5 s — muestra progreso de indexación Drive."""
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
            icon="⏳",
        )
        st.progress(pct, text=f"{p['last_file'][:55]}" if p["last_file"] else "iniciando...")
    elif p["status"] == "error":
        st.warning(
            f"Drive conectado — {p['indexed']} contrato(s) indexado(s). Error: {p['error']}",
            icon="⚠️",
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

    ocr_failed = p.get("ocr_quota_failed", 0)
    if ocr_failed > 0:
        st.warning(
            f"⚠️ **{ocr_failed} documento(s) sin indexar** — cuota de Gemini Vision agotada. "
            "Se indexarán en el próximo reinicio cuando la cuota se renueve (medianoche PT).",
            icon="🔴",
        )


# ─── Sidebar de JuanMitaBot ───────────────────────────────────────────────────

def juanmitabot_sidebar():
    """Chat lateral de JuanMitaBot en la barra lateral — comparte historial con la página principal."""
    with st.sidebar:
        try:
            from utils.auth import get_current_user
            u = get_current_user()
            if getattr(st, "user", None) and getattr(st.user, "is_logged_in", False) and u:
                role_badge = "👑 Admin" if u.get("role") == "admin" else "👤 Visor"
                st.markdown(
                    f'<div style="font-size:12px;color:#F6FF72;margin-bottom:4px;">'
                    f'{role_badge} — {u.get("name")}<br>'
                    f'<span style="opacity:0.7">{u.get("email")}</span></div>',
                    unsafe_allow_html=True,
                )
                if hasattr(st, "logout"):
                    st.button("Cerrar sesion", on_click=st.logout, key="sidebar_logout")
            elif getattr(st, "user", None) and getattr(st.user, "is_logged_in", False):
                st.markdown(
                    f'<div style="font-size:12px;color:#F6FF72;margin-bottom:4px;">'
                    f'👤 {getattr(st.user, "name", "Usuario")}<br>'
                    f'<span style="opacity:0.7">{getattr(st.user, "email", "")}</span></div>',
                    unsafe_allow_html=True,
                )
                if hasattr(st, "logout"):
                    st.button("Cerrar sesion", on_click=st.logout, key="sidebar_logout")
        except Exception:
            pass
        st.markdown("---")
        # Badge de alertas de vencimiento (se actualiza desde inicio.py)
        _n_alertas = st.session_state.get("_alertas_total", 0)
        if _n_alertas > 0:
            st.markdown(
                f'<div style="background:#e53935;color:white;border-radius:8px;'
                f'padding:6px 12px;margin-bottom:8px;font-size:12px;font-weight:700;'
                f'text-align:center;">🔔 {_n_alertas} alerta(s) de vencimiento</div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            '<div style="font-weight:900;font-size:15px;color:#F6FF72;">💬 JuanMitaBot</div>'
            '<div style="font-size:11px;color:#c9b8e8;margin-bottom:6px;">Pregunta sobre tus contratos</div>',
            unsafe_allow_html=True,
        )
        ctx = st.session_state.get("sidebar_chat_title", "")
        if ctx:
            st.caption(f"📄 {ctx[:35]}")

        # Historia compartida con la página principal (chat_history)
        history = st.session_state.get("chat_history", [])
        chat_container = st.container(height=260)
        with chat_container:
            if not history:
                st.markdown(
                    '<div style="color:#9d87c0;font-size:12px;text-align:center;margin-top:80px;">'
                    'Escribe tu pregunta abajo<br>y presiona Enter ↵</div>',
                    unsafe_allow_html=True,
                )
            for msg in history[-6:]:
                with st.chat_message(msg["role"]):
                    content = msg["content"]
                    if msg["role"] == "assistant" and len(content) > 400:
                        st.markdown(content[:380] + "… *(ver completo en JuanMitaBot)*")
                    else:
                        st.markdown(content)

        user_input = st.chat_input("Escribe tu pregunta...", key="sidebar_juanmitabot")
        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            history_for_llm = st.session_state.chat_history[-7:-1]
            try:
                with st.spinner("Buscando..."):
                    ans = st.session_state.chatbot.ask_question(
                        user_input,
                        filter_metadata=st.session_state.get("sidebar_chat_filter"),
                        chat_history=history_for_llm,
                    )
            except Exception as _e:
                ans = f"⚠️ Error interno: {_e}"
                log.error("[sidebar] ask_question falló: %s", _e, exc_info=True)
            st.session_state.chat_history.append({"role": "assistant", "content": ans})
            st.rerun()

        if history:
            if st.button("🗑 Limpiar chat", key="clear_sidebar_chat", width="stretch"):
                st.session_state.chat_history = []
                st.session_state.sidebar_chat_filter = None
                st.session_state.sidebar_chat_title = ""
                st.rerun()
