import streamlit as st

def render_sidebar_chat():
    """Renderiza el chatbot contextual en la barra lateral."""
    if st.session_state.get('sidebar_chat_open'):
        with st.sidebar:
            st.header(f"🤖 Chat: {st.session_state.sidebar_chat_title}")
            st.write("---")
            
            if 'sidebar_chat_history' not in st.session_state:
                st.session_state.sidebar_chat_history = []
            
            # Historial
            for msg in st.session_state.sidebar_chat_history:
                with st.chat_message(msg['role'], avatar="🤖" if msg['role'] == "assistant" else None):
                    st.markdown(msg['content'])
            
            # Input
            user_input = st.chat_input("Pregunta sobre este contexto...", key="sidebar_chat_input")
            if user_input:
                st.session_state.sidebar_chat_history.append({"role": "user", "content": user_input})
                with st.chat_message("user"):
                    st.markdown(user_input)
                
                with st.chat_message("assistant", avatar="🤖"):
                    with st.spinner("Pactora responde..."):
                        ans = st.session_state.chatbot.ask_question(user_input)
                        st.markdown(ans)
                st.session_state.sidebar_chat_history.append({"role": "assistant", "content": ans})

            if st.button("Cerrar Chat IA", use_container_width=True):
                st.session_state.sidebar_chat_open = False
                st.rerun()

def main():
    st.set_page_config(page_title="Pactora CLM - Unergy", layout="wide")
    
    # Inicializar chatbot global
    if 'chatbot' not in st.session_state:
        from core.rag_chatbot import RAGChatbot
        st.session_state.chatbot = RAGChatbot()
    
    # Ocultar menú de Streamlit, footer y botón Deploy (Vista Administrador)
    hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            /* Colores Unergy Custom para UI (botones primarios) */
            .stButton>button[kind='primary'] {
                background-color: #915BD8;
                color: #FDFAF7;
                border: none;
            }
            </style>
            """
    st.markdown(hide_st_style, unsafe_allow_html=True)
    
    col_title, col_tools = st.columns([4, 1])
    with col_title:
        st.title("Pactora - Unergy DocBrain")
    with col_tools:
        st.write("") # Spacing
        
        # Ocultar herramienta de ingesta nativa si ya conectó la raíz
        if 'drive_root_id' not in st.session_state:
            with st.expander("☁️ Herramienta de Conexión Drive", expanded=True):
                st.write("Configuración Inicial:")
                drive_folder_id = st.text_input("ID Carpeta Drive Raíz", value="1sF8_SuiiFdiWq_9htA-cNZP1Gp0djc4N")
                drive_api_key = st.text_input("API Key Google", value="AIzaSyCD7OwQcJlxz6ch8dsuM7TXaYUpZMMhXCI", type="password")
                if st.button("🔗 Conectar a Explorador Pactora", type="primary", use_container_width=True):
                    from utils.drive_manager import get_folder_metadata
                    with st.spinner("Conectando con Google Workspace..."):
                        root_meta = get_folder_metadata(drive_folder_id, api_key=drive_api_key)
                        st.session_state.drive_api_key = drive_api_key
                        st.session_state.drive_root_id = drive_folder_id
                        st.session_state.current_folder_id = drive_folder_id
                        st.session_state.folder_history = [(drive_folder_id, root_meta.get('name', 'Raíz Pactora'))]
                    st.rerun()
        else:
            if st.button("🔌 Desconectar Drive"):
                del st.session_state.drive_root_id
                del st.session_state.current_folder_id
                del st.session_state.folder_history
                if 'drive_api_key' in st.session_state:
                    del st.session_state.drive_api_key
                st.rerun()

    tabs = st.tabs(["🗂️ Explorador de Documentos", "🧠 Asistente RAG", "⚙️ Configuración"])
    
    with tabs[0]:
        st.header("🗂️ Explorador de Documentos")
        st.write("Visualización exacta y sincronizada 2-vías con tu Google Drive.")
        
        if 'drive_root_id' in st.session_state:
            from utils.drive_manager import get_folder_contents, create_folder, upload_file, rename_item, delete_item
            
            # --- BUSCADOR SEMÁNTICO RAG ---
            search_query = st.text_input("🔍 Buscar documento con IA (ej: 'Contrato Solenium Braya')", key="global_search")
            if search_query:
                gemini_key = st.session_state.get('gemini_api_key')
                if not gemini_key:
                    st.warning("⚠️ Configura tu Gemini API Key en la pestaña ⚙️ **Configuración** para habilitar la búsqueda semántica.")
                else:
                    from core.rag_engine import query_rag
                    from core.gemini_engine import configure_gemini
                    configure_gemini(api_key=gemini_key)
                    with st.spinner("Consultando IA..."):
                        rag_result = query_rag(search_query)
                    st.info(f"🤖 **Respuesta Pactora:**\n\n{rag_result}")
            
            # --- RENDER BREADCRUMBS ---
            st.write("---")
            nav_cols = st.columns(len(st.session_state.folder_history) + 1)
            for i, (f_id, f_name) in enumerate(st.session_state.folder_history):
                with nav_cols[i]:
                    if st.button(f"📁 {f_name}", key=f"nav_{f_id}"):
                        # Cortar historial hasta acá y navegar
                        st.session_state.folder_history = st.session_state.folder_history[:i+1]
                        st.session_state.current_folder_id = f_id
                        st.rerun()
            
            st.subheader(f"Contenido de: {st.session_state.folder_history[-1][1]}")
            
            # --- CARGAR CONTENIDOS DINÁMICO ---
            with st.spinner("Sincronizando..."):
                api_key_to_use = st.session_state.get('drive_api_key')
                items = get_folder_contents(st.session_state.current_folder_id, api_key=api_key_to_use)
            
            if not items:
                st.info("Carpeta vacía.")
            else:
                folders = [item for item in items if item['mimeType'] == 'application/vnd.google-apps.folder']
                files = [item for item in items if item['mimeType'] != 'application/vnd.google-apps.folder']
                
                # Render Carpetas Clickables
                if folders:
                    st.write("### Carpetas")
                    for folder in folders:
                        f_col1, f_col2, f_col3, f_col4 = st.columns([5, 1, 1, 1])
                        with f_col1:
                            if st.button(f"📂 {folder['name']}", key=f"enter_{folder['id']}", use_container_width=True):
                                st.session_state.current_folder_id = folder['id']
                                st.session_state.folder_history.append((folder['id'], folder['name']))
                                st.rerun()
                        with f_col2:
                            if st.button("🤖 IA", key=f"bot_f_{folder['id']}", help="Analizar contenido de carpeta"):
                                with st.spinner("Analizando carpeta y documentos..."):
                                    from utils.drive_manager import get_recursive_files, download_file_to_io
                                    from utils.file_parser import extract_text_from_file
                                    import io
                                    
                                    # Descubrimiento recursivo
                                    files_to_ingest = get_recursive_files(folder['id'], api_key=st.session_state.get('drive_api_key'))
                                    ingest_data = []
                                    for f in files_to_ingest:
                                        f_io = download_file_to_io(f['id'], api_key=st.session_state.get('drive_api_key'))
                                        if f_io:
                                            text = extract_text_from_file(f_io, f['name'])
                                            if not text.startswith("Error"):
                                                ingest_data.append((text, f['name']))
                                    
                                    if ingest_data:
                                        success, msg = st.session_state.chatbot.vector_ingest_multiple(ingest_data)
                                        if success:
                                            st.session_state.sidebar_chat_open = True
                                            st.session_state.sidebar_chat_title = folder['name']
                                            st.session_state.sidebar_chat_history = []
                                            st.success(f"Analizadas {len(ingest_data)} documentos en '{folder['name']}'")
                                        else:
                                            st.error(f"Error IA: {msg}")
                                    else:
                                        st.warning("No se encontraron documentos válidos en esta carpeta.")
                        with f_col3:
                            with st.popover("✏️"):
                                new_name = st.text_input("Nuevo Nombre", value=folder['name'], key=f"ren_f_{folder['id']}")
                                if st.button("Guardar", key=f"save_ren_f_{folder['id']}"):
                                    rename_item(folder['id'], new_name)
                                    st.rerun()
                        with f_col4:
                            with st.popover("🗑️"):
                                st.write("¿Eliminar carpeta?")
                                if st.button("Sí, borrar", type="primary", key=f"del_f_{folder['id']}"):
                                    delete_item(folder['id'])
                                    st.rerun()
                            
                # Render Archivos en Lista
                if files:
                    st.write("### Documentos")
                    for doc in files:
                        icon = "📄"
                        if 'pdf' in doc['mimeType']: icon = "📄"
                        elif 'word' in doc['mimeType']: icon = "📝"
                        
                        d_col1, d_col2, d_col3, d_col4, d_col5 = st.columns([4, 1, 1, 1, 1])
                        with d_col1:
                            st.write(f"{icon} **{doc['name']}**")
                            st.caption(f"Subido: {doc.get('createdTime', '')[:10]}")
                        with d_col2:
                            st.link_button("🔗 Ver", doc.get('webViewLink', '#'))
                        with d_col3:
                            if st.button("🤖 IA", key=f"bot_d_{doc['id']}", help="Analizar documento"):
                                with st.spinner("Leyendo documento..."):
                                    from utils.drive_manager import download_file_to_io
                                    from utils.file_parser import extract_text_from_file
                                    import io
                                    
                                    f_io = download_file_to_io(doc['id'], api_key=st.session_state.get('drive_api_key'))
                                    if f_io:
                                        text = extract_text_from_file(f_io, doc['name'])
                                        if not text.startswith("Error"):
                                            success, msg = st.session_state.chatbot.vector_ingest(text)
                                            if success:
                                                st.session_state.sidebar_chat_open = True
                                                st.session_state.sidebar_chat_title = doc['name']
                                                st.session_state.sidebar_chat_history = []
                                                st.success("Documento cargado al asistente.")
                                            else:
                                                st.error(f"Error IA: {msg}")
                                        else:
                                            st.error(text)
                                    else:
                                        st.error("No se pudo descargar el archivo.")
                        with d_col4:
                            with st.popover("✏️"):
                                new_name2 = st.text_input("Nuevo Nombre", value=doc['name'], key=f"ren_d_{doc['id']}")
                                if st.button("Guardar", key=f"save_ren_d_{doc['id']}"):
                                    rename_item(doc['id'], new_name2)
                                    st.rerun()
                        with d_col5:
                            with st.popover("🗑️"):
                                st.write("¿Mover a papelera?")
                                if st.button("Sí, borrar", type="primary", key=f"del_d_{doc['id']}"):
                                    delete_item(doc['id'])
                                    st.rerun()
            
            # --- ACCIONES BIDIRECCIONALES (ESCRITURA) ---
            st.divider()
            st.write("### ⚙️ Acciones en esta Carpeta")
            act_col1, act_col2 = st.columns(2)
            
            with act_col1:
                with st.expander("➕ Crear Nueva Carpeta"):
                    new_f_name = st.text_input("Nombre de la Carpeta")
                    if st.button("Crear en Drive", type="primary", use_container_width=True):
                        if new_f_name:
                            with st.spinner("Creando en la Nube..."):
                                create_folder(new_f_name, st.session_state.current_folder_id)
                            st.success("Carpeta Creada.")
                            st.rerun()
                        else:
                            st.error("Di un nombre.")
                            
            with act_col2:
                with st.expander("📄 Subir Documento a Drive"):
                    uploaded_file = st.file_uploader("Arrastra el contrato aquí (.pdf, .docx)", type=['pdf', 'docx'])
                    if uploaded_file and st.button("Subir e Ingestar en Pactora", type="primary", use_container_width=True):
                        with st.spinner("Subiendo de manera segura a Google Drive..."):
                            upload_file(
                                file_bytes=uploaded_file.getvalue(), 
                                filename=uploaded_file.name, 
                                parent_id=st.session_state.current_folder_id,
                                mime_type=uploaded_file.type
                            )
                        st.success("¡Documento subido y sincronizado!")
                        st.rerun()
                        
        else:
            st.info("Utiliza la herramienta '☁️ Herramienta de Conexión Drive' arriba a la derecha para iniciar la sincronización.")
    
    with tabs[1]:
        st.header("🧠 Asistente Legal Pactora")
        st.write("Chatbot conversacional con contexto estricto de los contratos que tienes subidos en Pactora.")

        gemini_key = st.session_state.get('gemini_api_key')
        if not gemini_key:
            st.warning("⚠️ Para activar el asistente, ve a ⚙️ **Configuración** e ingresa tu Gemini API Key.")
        else:
            from core.rag_chatbot import RAGChatbot
            from core.gemini_engine import configure_gemini
            configure_gemini(api_key=gemini_key)

            # Inicializar chatbot y estado de conversación
            if 'chatbot' not in st.session_state:
                st.session_state.chatbot = RAGChatbot()
            if 'chat_history' not in st.session_state:
                st.session_state.chat_history = []

            # --- PANEL DE INGESTIÓN DE CONTEXTO ---
            with st.expander("📅 Cargar Documento para Analizar", expanded=not bool(st.session_state.chat_history)):
                upload_for_rag = st.file_uploader("Sube un contrato (.pdf o .docx) para hacer preguntas sobre él", type=['pdf', 'docx'])
                if upload_for_rag:
                    if st.button("⚡ Vectorizar con IA y Cargar al Chatbot", type="primary", use_container_width=True):
                        from utils.file_parser import extract_text_from_file
                        import io
                        with st.spinner("🔍 Extrayendo texto y vectorizando con Gemini..."):
                            text = extract_text_from_file(io.BytesIO(upload_for_rag.getvalue()), upload_for_rag.name)
                            if text.startswith("Error"):
                                st.error(text)
                            else:
                                success, msg = st.session_state.chatbot.vector_ingest(text)
                                if success:
                                    st.session_state.chat_history = []
                                    st.success(f"✅ {msg}")
                                else:
                                    st.error(f"Error vectorizando: {msg}")

            # --- HISTORIAL DE CHAT ---
            if st.session_state.chat_history:
                for msg in st.session_state.chat_history:
                    role = msg['role']
                    content = msg['content']
                    if role == 'user':
                        with st.chat_message('user'):
                            st.markdown(content)
                    else:
                        with st.chat_message('assistant', avatar='🤖'):
                            st.markdown(content)

            # --- INPUT DE PREGUNTA ---
            user_question = st.chat_input("¿Qué quieres saber del contrato?")
            if user_question:
                st.session_state.chat_history.append({'role': 'user', 'content': user_question})
                with st.chat_message('user'):
                    st.markdown(user_question)
                with st.chat_message('assistant', avatar='🤖'):
                    with st.spinner("Pactora está pensando..."):
                        answer = st.session_state.chatbot.ask_question(user_question)
                    st.markdown(answer)
                st.session_state.chat_history.append({'role': 'assistant', 'content': answer})

            if st.session_state.chat_history:
                if st.button("🗑️ Limpiar Conversación"):
                    st.session_state.chat_history = []
                    st.rerun()
        
    with tabs[2]:
        st.header("⚙️ Configuración e Integraciones")
        st.write("Gestión de credenciales y conexiones a Google Workspace y Gemini.")
        
        # --- GEMINI API KEY ---
        st.subheader("🤖 Clave API de Gemini")
        st.write("Necesaria para el Asistente RAG y la búsqueda semántica.")
        
        # Auto-cargar desde secrets.toml si aún no esta en sesión
        if 'gemini_api_key' not in st.session_state:
            try:
                st.session_state.gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")
            except Exception:
                st.session_state.gemini_api_key = ""
        
        current_key = st.session_state.get('gemini_api_key', '')
        key_status = "✅ Clave activa" if current_key else "❌ Sin configurar"
        st.info(f"Estado: **{key_status}**")
        gemini_key_input = st.text_input("Gemini API Key", value=current_key, type="password", key="gemini_key_input")
        if st.button("💾 Guardar Gemini API Key", type="primary"):
            st.session_state.gemini_api_key = gemini_key_input
            st.success("✅ Clave guardada en sesión. Ya puedes usar el Asistente RAG.")
        
        st.divider()
        
        # --- GOOGLE WORKSPACE ---
        st.subheader("Estado de Conexión a Google Workspace")
        if st.button("Conectar / Verificar Credenciales de Google"):
            from utils.auth_helper import authenticate_google_apis
            try:
                creds = authenticate_google_apis()
                if creds and creds.valid:
                    st.success("¡Conexión exitosa! `token.json` generado de manera local (segura).")
                else:
                    st.warning("Credenciales detectadas pero inválidas o expiradas.")
            except FileNotFoundError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Error al conectar: {str(e)}")

    # Renderizar el chat lateral si está abierto (Independiente de pestañas)
    render_sidebar_chat()

if __name__ == "__main__":
    main()
