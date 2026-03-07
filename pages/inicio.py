import streamlit as st
import threading
from utils.shared import apply_styles, page_header, init_session_state, juanmitabot_sidebar, api_status_banner

apply_styles()
init_session_state()

page_header()
api_status_banner()

# ─── Indexacion en segundo plano ─────────────────────────────────────────────
# Modulo-level dict compartido entre sesiones (mismo proceso del servidor)
if "_bg_index_status" not in st.session_state:
    st.session_state._bg_index_status = {}


def _bg_index_folder(folder_id, api_key, chatbot, status_ref):
    """Corre en hilo de fondo: descarga e indexa archivos de la carpeta."""
    try:
        from utils.drive_manager import get_folder_contents, download_file_to_io
        from utils.file_parser import extract_text_from_file
        import concurrent.futures

        items = get_folder_contents(folder_id, api_key=api_key)
        files = [
            i for i in items
            if i["mimeType"] != "application/vnd.google-apps.folder"
            and i["name"] not in chatbot._indexed_sources
        ]
        if not files:
            status_ref[folder_id] = "done:0"
            return

        docs = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            futures = {ex.submit(download_file_to_io, f["id"], api_key): f for f in files}
            for future, f in futures.items():
                try:
                    fio = future.result(timeout=30)
                    if fio:
                        txt = extract_text_from_file(fio, f["name"])
                        if txt and not txt.startswith("Error"):
                            docs.append((txt, f["name"], {}))
                except Exception:
                    pass

        if docs:
            chatbot.vector_ingest_multiple(docs)
        status_ref[folder_id] = f"done:{len(docs)}"
    except Exception as e:
        status_ref[folder_id] = f"error:{str(e)[:80]}"


def _trigger_bg_index(folder_id, api_key, chatbot):
    """Lanza indexacion en segundo plano si no esta ya corriendo."""
    status = st.session_state._bg_index_status
    if status.get(folder_id) in (None,) and api_key and api_key != "DEMO_KEY":
        status[folder_id] = "running"
        t = threading.Thread(
            target=_bg_index_folder,
            args=(folder_id, api_key, chatbot, status),
            daemon=True
        )
        t.start()


# ─── Barra de busqueda global ─────────────────────────────────────────────────
search_query = st.text_input(
    "buscar",
    placeholder="Buscar en contratos indexados... Ej: clausulas de terminacion, fecha de vencimiento",
    label_visibility="collapsed"
)
if search_query:
    with st.spinner("JuanMitaBot consultando contratos..."):
        ans = st.session_state.chatbot.ask_question(search_query)
    st.info(f"**JuanMitaBot:**\n\n{ans}")

c1, c2 = st.columns(2)

# ─── Explorador de Archivos ──────────────────────────────────────────────────
with c1:
    st.markdown('<div class="factora-card"><div class="card-title">Explorador de Archivos</div>', unsafe_allow_html=True)

    if "drive_root_id" not in st.session_state:
        st.info("Conecta tu Google Drive en Ajustes para explorar archivos.")
    else:
        from utils.drive_manager import get_folder_contents, download_file_to_io
        from utils.file_parser import extract_text_from_file
        import concurrent.futures

        drive_api_key = st.session_state.get("drive_api_key", "")
        is_demo = drive_api_key == "DEMO_KEY"
        current_folder = st.session_state.current_folder_id

        # Auto-indexar carpeta actual en segundo plano
        if not is_demo:
            _trigger_bg_index(current_folder, drive_api_key, st.session_state.chatbot)

        # Estado de indexacion de fondo
        bg_status = st.session_state._bg_index_status.get(current_folder)
        if bg_status == "running":
            st.caption("⏳ Indexando archivos de esta carpeta en segundo plano...")
        elif bg_status and bg_status.startswith("done:"):
            n = bg_status.split(":")[1]
            if n != "0":
                st.caption(f"✅ {n} archivo(s) indexado(s) en esta carpeta.")

        # Breadcrumb
        history = st.session_state.folder_history
        if history:
            breadcrumb = " > ".join(name for _, name in history)
            st.caption(f"📍 {breadcrumb}")
        if len(history) > 1:
            if st.button("← Volver", key="back_btn", type="secondary"):
                history.pop()
                st.session_state.current_folder_id = history[-1][0]
                st.rerun()

        if is_demo and "mock_items" in st.session_state:
            items = st.session_state.mock_items
        else:
            items = get_folder_contents(current_folder, api_key=drive_api_key)

        for item in items[:20]:
            is_folder = item["mimeType"] == "application/vnd.google-apps.folder"
            icon = "📁" if is_folder else "📄"
            is_indexed = (not is_folder) and (item["name"] in st.session_state.chatbot._indexed_sources)

            row = st.columns([1, 6, 1, 1])
            row[0].write(icon + (" ✓" if is_indexed else ""))

            if row[1].button(item["name"], key=f"f_{item['id']}", use_container_width=True):
                if is_folder:
                    st.session_state.current_folder_id = item["id"]
                    st.session_state.folder_history.append((item["id"], item["name"]))
                    st.rerun()

            if not is_folder:
                if row[2].button("👁", key=f"prev_{item['id']}", help="Previsualizar"):
                    toggle_key = f"show_preview_{item['id']}"
                    st.session_state[toggle_key] = not st.session_state.get(toggle_key, False)

            help_txt = "Analizar con JuanMitaBot" if is_folder else "Preguntar a JuanMitaBot"
            if row[3].button("🤖", key=f"ia_{item['id']}", help=help_txt):
                if not is_folder and not is_demo and not is_indexed:
                    with st.spinner(f"Indexando {item['name']}..."):
                        try:
                            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                                fio = ex.submit(download_file_to_io, item["id"], drive_api_key).result(timeout=25)
                            if fio:
                                txt = extract_text_from_file(fio, item["name"])
                                if txt and not txt.startswith("Error"):
                                    st.session_state.chatbot.vector_ingest(txt, filename=item["name"])
                        except Exception:
                            pass
                st.session_state.sidebar_chat_title = item["name"]
                st.session_state.sidebar_chat_history = []
                st.session_state.sidebar_chat_filter = None if is_folder else {"source": item["name"]}
                st.rerun()

            # Vista previa inline usando visor nativo de Drive
            if not is_folder and st.session_state.get(f"show_preview_{item['id']}", False):
                with st.expander(f"Vista previa: {item['name']}", expanded=True):
                    if not is_demo:
                        # Iframe con el visor de Drive (funciona para archivos compartidos)
                        embed_url = f"https://drive.google.com/file/d/{item['id']}/preview"
                        st.components.v1.iframe(embed_url, height=520, scrolling=True)
                        # Texto indexado adicional si esta en RAG
                        if is_indexed:
                            try:
                                all_docs = st.session_state.chatbot.vectorstore.get(
                                    include=["documents", "metadatas"]
                                )
                                chunks = [
                                    d for d, m in zip(all_docs.get("documents", []), all_docs.get("metadatas", []))
                                    if m and m.get("source") == item["name"]
                                ]
                                if chunks:
                                    with st.expander("Texto en JuanMitaBot"):
                                        st.text("\n\n".join(chunks[:2])[:1000])
                            except Exception:
                                pass
                    else:
                        st.caption("Vista previa no disponible en modo demo.")

    st.markdown("</div>", unsafe_allow_html=True)

# ─── Estado del Workspace ────────────────────────────────────────────────────
with c2:
    st.markdown('<div class="factora-card"><div class="card-title">Estado del Workspace</div>', unsafe_allow_html=True)

    stats = st.session_state.chatbot.get_stats()
    m1, m2 = st.columns(2)
    m1.markdown(
        f'<div class="metric-card"><div class="metric-val">{stats["total_docs"]}</div>'
        '<div class="metric-lbl">Contratos indexados</div></div>',
        unsafe_allow_html=True
    )
    m2.markdown(
        f'<div class="metric-card"><div class="metric-val">{stats["total_chunks"]}</div>'
        '<div class="metric-lbl">Fragmentos en RAG</div></div>',
        unsafe_allow_html=True
    )

    if stats["sources"]:
        st.caption("Contratos disponibles para JuanMitaBot:")
        for s in stats["sources"][:10]:
            st.markdown(f"- {s}")
    else:
        if "drive_root_id" in st.session_state:
            st.info("Abre una carpeta del Drive para que JuanMitaBot indexe los contratos automaticamente.")
        else:
            st.caption("Conecta Google Drive en Ajustes para que JuanMitaBot pueda leer los contratos.")

    st.markdown("</div>", unsafe_allow_html=True)

juanmitabot_sidebar()
