import streamlit as st

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


def page_header(subtitle="by Unergy"):
    st.markdown(
        '<div style="font-family:Lato,sans-serif;font-weight:900;font-size:46px;'
        'color:#2C2039;text-align:center;margin-bottom:2px;">Pactora</div>'
        f'<div style="text-align:center;color:#915BD8;font-weight:600;margin-bottom:20px;">{subtitle}</div>',
        unsafe_allow_html=True
    )


def init_session_state():
    from core.rag_chatbot import RAGChatbot

    if "gemini_api_key" not in st.session_state:
        try:
            st.session_state.gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            st.session_state.gemini_api_key = ""

    if "chatbot" not in st.session_state:
        st.session_state.chatbot = RAGChatbot(api_key=st.session_state.gemini_api_key)

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


def juanmitabot_sidebar():
    """Chat lateral de JuanMitaBot mostrado en la barra lateral."""
    with st.sidebar:
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


