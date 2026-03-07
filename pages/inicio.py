import streamlit as st
from utils.shared import apply_styles, page_header, init_session_state, juanmitabot_sidebar, api_status_banner

apply_styles()
init_session_state()

page_header()
api_status_banner()

# Barra de busqueda global
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

        # Breadcrumb
        history = st.session_state.folder_history
        if history:
            breadcrumb = " > ".join(name for _, name in history)
            st.caption(f"Ubicacion: {breadcrumb}")
        if len(history) > 1:
            if st.button("Volver", key="back_btn", type="secondary"):
                history.pop()
                st.session_state.current_folder_id = history[-1][0]
                st.rerun()

        if is_demo and "mock_items" in st.session_state:
            items = st.session_state.mock_items
        else:
            items = get_folder_contents(
                st.session_state.current_folder_id,
                api_key=drive_api_key
            )

        for item in items[:20]:
            is_folder = item["mimeType"] == "application/vnd.google-apps.folder"
            icon = "📁" if is_folder else "📄"
            is_indexed = (not is_folder) and (item["name"] in st.session_state.chatbot._indexed_sources)

            row = st.columns([1, 6, 1, 1])
            row[0].write(icon)

            if row[1].button(item["name"], key=f"f_{item['id']}", use_container_width=True):
                if is_folder:
                    st.session_state.current_folder_id = item["id"]
                    st.session_state.folder_history.append((item["id"], item["name"]))
                    st.rerun()

            # Boton de previsualizacion (solo archivos)
            if not is_folder:
                preview_key = f"prev_{item['id']}"
                if row[2].button("👁", key=preview_key, help="Previsualizar contrato"):
                    toggle_key = f"show_preview_{item['id']}"
                    st.session_state[toggle_key] = not st.session_state.get(toggle_key, False)

            help_txt = "Analizar con JuanMitaBot" if is_folder else "Preguntar a JuanMitaBot sobre este archivo"
            if row[3].button("🤖", key=f"ia_{item['id']}", help=help_txt):
                # Para archivos: indexar si no esta indexado aun (con timeout de 25s)
                if not is_folder and not is_demo:
                    chatbot = st.session_state.chatbot
                    if item["name"] not in chatbot._indexed_sources:
                        with st.spinner(f"Indexando {item['name']}..."):
                            try:
                                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                                    future = ex.submit(download_file_to_io, item["id"], drive_api_key)
                                    fio = future.result(timeout=25)
                                if fio:
                                    txt = extract_text_from_file(fio, item["name"])
                                    if txt and not txt.startswith("Error"):
                                        chatbot.vector_ingest(txt, filename=item["name"])
                            except concurrent.futures.TimeoutError:
                                st.warning(f"Timeout al descargar {item['name']}. Intenta desde Ajustes.")
                            except Exception as e:
                                st.warning(f"No se pudo indexar: {e}")

                # Para carpetas: solo abrir chat con contexto general (no descarga masiva)
                st.session_state.sidebar_chat_title = item["name"]
                st.session_state.sidebar_chat_history = []
                st.session_state.sidebar_chat_filter = (
                    None if is_folder else {"source": item["name"]}
                )
                st.rerun()

            # Vista previa inline si el toggle esta activo
            if not is_folder and st.session_state.get(f"show_preview_{item['id']}", False):
                with st.expander(f"Vista previa: {item['name']}", expanded=True):
                    if is_indexed:
                        try:
                            all_docs = st.session_state.chatbot.vectorstore.get(
                                include=["documents", "metadatas"]
                            )
                            docs = all_docs.get("documents", [])
                            metas = all_docs.get("metadatas", [])
                            chunks = [
                                d for d, m in zip(docs, metas)
                                if m and m.get("source") == item["name"]
                            ]
                            preview_text = "\n\n".join(chunks[:2]) if chunks else "(sin texto disponible)"
                            st.text(preview_text[:800] + ("..." if len(preview_text) > 800 else ""))
                        except Exception:
                            st.caption("No se pudo cargar la vista previa.")
                    elif not is_demo:
                        with st.spinner(f"Descargando {item['name']}..."):
                            try:
                                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                                    future = ex.submit(download_file_to_io, item["id"], drive_api_key)
                                    fio = future.result(timeout=25)
                                if fio:
                                    txt = extract_text_from_file(fio, item["name"])
                                    st.text(txt[:800] + ("..." if len(txt) > 800 else ""))
                                else:
                                    st.caption("No se pudo descargar el archivo.")
                            except concurrent.futures.TimeoutError:
                                st.caption("Timeout al descargar.")
                            except Exception as e:
                                st.caption(f"Error: {e}")
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
            st.info("JuanMitaBot esta indexando los contratos del Drive. Ve a Ajustes si el proceso no comenzo.")
        else:
            st.caption("Conecta Google Drive en Ajustes para que JuanMitaBot pueda leer los contratos.")

    st.markdown("</div>", unsafe_allow_html=True)

# JuanMitaBot chat en sidebar
juanmitabot_sidebar()
