import streamlit as st

def main():
    st.set_page_config(page_title="Pactora CLM - Unergy", layout="wide")
    
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
            
            # --- BUSCADOR GENERAL ---
            search_query = st.text_input("🔍 Buscar documento (ej: 'Contrato Solenium Braya')", key="global_search")
            if search_query:
                st.info(f"Buscador Inteligente (RAG) en construcción. Búsqueda semántica para: '{search_query}'")
            
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
                                st.session_state.rag_context = folder['id']
                                st.success("Contexto RAG configurado para esta carpeta. Ve a la pestaña 'Asistente RAG'.")
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
                                st.session_state.rag_context = doc['id']
                                st.success("Contexto RAG configurado para este documento. Ve a la pestaña 'Asistente RAG'.")
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
        st.header("🧠 Asistente Legal RAG")
        st.write("Consultas conversacionales con contexto estricto de los documentos cargados.")
        
    with tabs[2]:
        st.header("⚙️ Configuración e Integraciones")
        st.write("Gestión de conexiones a Google Drive y Calendar.")
        
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

if __name__ == "__main__":
    main()
