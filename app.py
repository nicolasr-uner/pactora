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
    
    # --- FACTORA PREMIUM CSS ---
    factora_style = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;600&display=swap');

    /* Global App Background */
    .stApp {
        background: #F8F9FA;
        font-family: 'Inter', sans-serif;
    }

    /* Factora Header & Branding */
    .factora-header {
        font-family: 'Playfair Display', serif;
        font-size: 64px;
        color: #1A2D35;
        text-align: center;
        margin-top: -30px;
        margin-bottom: 20px;
    }

    /* Sidebar Navigation Customization */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E0E0E0;
        width: 100px !important;
    }
    
    /* Nav Icons Styling */
    .nav-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 15px 0;
        cursor: pointer;
        color: #5F6368;
        transition: all 0.3s;
    }
    .nav-item:hover {
        background-color: #F1F3F4;
        color: #1A2D35;
        border-radius: 12px;
    }
    .nav-active {
        color: #915BD8;
        background-color: #F3E8FF;
        border-radius: 12px;
    }

    /* Cards Style (Widgets) */
    .factora-card {
        background: white;
        border-radius: 24px;
        padding: 25px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        border: 1px solid #F0F0F0;
        height: 100%;
        margin-bottom: 20px;
    }
    .card-title {
        font-size: 24px;
        font-weight: 600;
        color: #1A2D35;
        margin-bottom: 20px;
    }

    /* Search Bar Professionalism */
    .stTextInput>div>div>input {
        background-color: #F1F3F4 !important;
        border-radius: 50px !important;
        border: none !important;
        padding: 12px 25px !important;
        font-size: 18px !important;
    }

    /* Hide standard ST elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom Buttons */
    .stButton>button {
        border-radius: 12px !important;
        font-weight: 600 !important;
    }
    </style>
    """
    st.markdown(factora_style, unsafe_allow_html=True)
    
    # --- RENDER BRANDING ---
    st.markdown('<div class="factora-header">Factora</div>', unsafe_allow_html=True)
    # --- SIDEBAR NAVIGATION ---
    with st.sidebar:
        st.markdown('<div style="text-align: center; margin-bottom: 20px;"><img src="https://cdn-icons-png.flaticon.com/512/124/124010.png" width="40"></div>', unsafe_allow_html=True)
        nav_opt = st.radio(
            "Menú",
            ["🏠 Inicio", "📅 Calendario", "📊 Métricas", "📄 Plantillas", "⚖️ Comparativo", "🧠 Chatbot", "⚙️ Ajustes"],
            label_visibility="collapsed"
        )
        st.divider()
        
        if 'drive_root_id' in st.session_state:
            st.caption(f"☁️ Conectado: {st.session_state.folder_history[0][1]}")

    # --- MAIN CONTENT AREA ---
    if nav_opt == "🏠 Inicio":
        # Search Bar (Semantic RAG)
        st.markdown('<div style="max-width: 600px; margin: 0 auto;">', unsafe_allow_html=True)
        search_query = st.text_input("🔍 Search documents, projects or dates...", placeholder="Search...")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if search_query:
            gemini_key = st.session_state.get('gemini_api_key')
            if gemini_key:
                from core.rag_engine import query_rag
                from core.gemini_engine import configure_gemini
                configure_gemini(api_key=gemini_key)
                with st.spinner("Consultando IA..."):
                    rag_result = query_rag(search_query)
                st.info(f"🤖 **Factora Insights:**\n\n{rag_result}")

        st.write("") # Spacing

        # 2-Column Layout for Widgets
        m_col1, m_col2 = st.columns([1, 1])

        with m_col1:
            st.markdown('<div class="factora-card"><div class="card-title">Previsualización</div>', unsafe_allow_html=True)
            if 'drive_root_id' in st.session_state:
                from utils.drive_manager import get_folder_contents
                
                # Items List (Simplified for Dashboard)
                items = get_folder_contents(st.session_state.current_folder_id, api_key=st.session_state.get('drive_api_key'))
                for item in items[:6]: 
                    icon = "📁" if item['mimeType'] == 'application/vnd.google-apps.folder' else "📄"
                    i_col1, i_col2, i_col3 = st.columns([1, 6, 1])
                    with i_col1:
                        st.write(icon)
                    with i_col2:
                        if st.button(item['name'], key=f"dash_{item['id']}", use_container_width=True):
                            if item['mimeType'] == 'application/vnd.google-apps.folder':
                                st.session_state.current_folder_id = item['id']
                                st.session_state.folder_history.append((item['id'], item['name']))
                                st.rerun()
                    with i_col3:
                        if st.button("🤖", key=f"bot_dash_{item['id']}", help="Analizar con IA"):
                            with st.spinner("Leyendo..."):
                                from utils.drive_manager import download_file_to_io, get_recursive_files
                                from utils.file_parser import extract_text_from_file
                                if item['mimeType'] == 'application/vnd.google-apps.folder':
                                    files = get_recursive_files(item['id'], api_key=st.session_state.get('drive_api_key'))
                                    ingest_data = []
                                    for f in files:
                                        f_io = download_file_to_io(f['id'], api_key=st.session_state.get('drive_api_key'))
                                        if f_io: ingest_data.append((extract_text_from_file(f_io, f['name']), f['name']))
                                    if ingest_data:
                                        st.session_state.chatbot.vector_ingest_multiple(ingest_data)
                                        st.session_state.sidebar_chat_open = True
                                        st.session_state.sidebar_chat_title = item['name']
                                        st.session_state.sidebar_chat_history = []
                                        st.rerun()
                                else:
                                    f_io = download_file_to_io(item['id'], api_key=st.session_state.get('drive_api_key'))
                                    if f_io:
                                        st.session_state.chatbot.vector_ingest(extract_text_from_file(f_io, item['name']))
                                        st.session_state.sidebar_chat_open = True
                                        st.session_state.sidebar_chat_title = item['name']
                                        st.session_state.sidebar_chat_history = []
                                        st.rerun()
            else:
                st.info("Configura tu Drive en Ajustes.")
            st.markdown('</div>', unsafe_allow_html=True)

        with m_col2:
            st.markdown('<div class="factora-card"><div class="card-title">Calendario</div>', unsafe_allow_html=True)
            st.markdown('<div style="text-align: center; color: #1A2D35; font-weight: 600; padding: 10px;">Marzo 2026</div>', unsafe_allow_html=True)
            cols = st.columns(7)
            days = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
            for i, d in enumerate(days):
                cols[i].markdown(f'<div style="text-align: center; font-size: 11px; color: #5F6368;">{d}</div>', unsafe_allow_html=True)
            
            # Simulated Calendar Grid with "Events"
            calendar_data = [
                ["23","24","25","26","27","28","1"],
                ["2","3","4","5","6","7","8"],
                ["9","10","11","12","13","14","15"]
            ]
            for week in calendar_data:
                row = st.columns(7)
                for i, day in enumerate(week):
                    has_event = day in ["9", "12", "24"]
                    color = "#915BD8" if has_event else "#F8F9FA"
                    bg = "background: #F3E8FF;" if has_event else ""
                    row[i].markdown(f'<div style="text-align: center; padding: 5px; border-radius: 8px; {bg}">{day}</div>', unsafe_allow_html=True)
                    if has_event: row[i].markdown('<div style="height: 4px; width: 4px; background: #915BD8; border-radius: 50%; margin: 0 auto;"></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Bottom Widget: Actividades Recientes (Improved mimicry)
        st.markdown('<div class="factora-card" style="margin-top: 20px;"><div class="card-title">Mis Actividades Recientes</div>', unsafe_allow_html=True)
        act_cols = st.columns(4)
        with act_cols[0]:
            st.markdown('📄 **hace 5 min**<br><span style="font-size: 13px; color: #5F6368;">Editaste "Contrato Solenium"</span>', unsafe_allow_html=True)
        with act_cols[1]:
            st.markdown('📅 **hace 20 min**<br><span style="font-size: 13px; color: #5F6368;">Agregaste evento (Mar 9)</span>', unsafe_allow_html=True)
        with act_cols[2]:
            st.markdown('📂 **hace 1 hora**<br><span style="font-size: 13px; color: #5F6368;">Visualizaste "Factora.pdf"</span>', unsafe_allow_html=True)
        with act_cols[3]:
            st.markdown('🤖 **hace 3 horas**<br><span style="font-size: 13px; color: #5F6368;">Consultaste al chatbot</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    elif nav_opt == "🧠 Chatbot":
        st.header("🧠 Asistente RAG Principal")
        gemini_key = st.session_state.get('gemini_api_key')
        if not gemini_key:
            st.warning("Configura Gemini en Ajustes.")
        else:
            if 'chat_history' not in st.session_state: st.session_state.chat_history = []
            for msg in st.session_state.chat_history:
                with st.chat_message(msg['role'], avatar="🤖" if msg['role']=="assistant" else None):
                    st.markdown(msg['content'])
            u_input = st.chat_input("Pregunta sobre tus contratos...")
            if u_input:
                st.session_state.chat_history.append({'role': 'user', 'content': u_input})
                with st.chat_message('user'): st.markdown(u_input)
                with st.chat_message('assistant', avatar='🤖'):
                    ans = st.session_state.chatbot.ask_question(u_input)
                    st.markdown(ans)
                st.session_state.chat_history.append({'role': 'assistant', 'content': ans})

    elif nav_opt == "⚙️ Ajustes":
        st.header("⚙️ Configuración")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="factora-card">', unsafe_allow_html=True)
            st.subheader("🤖 Gemini API")
            if 'gemini_api_key' not in st.session_state:
                st.session_state.gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")
            g_input = st.text_input("Gemini Key", value=st.session_state.gemini_api_key, type="password")
            if st.button("Guardar Key"):
                st.session_state.gemini_api_key = g_input
                st.success("Guardado.")
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="factora-card">', unsafe_allow_html=True)
            st.subheader("☁️ Conexión Drive")
            drive_folder_id = st.text_input("ID Carpeta Raíz", value=st.session_state.get('drive_root_id', "1sF8_SuiiFdiWq_9htA-cNZP1Gp0djc4N"))
            drive_api_key = st.text_input("Drive API Key", value=st.session_state.get('drive_api_key', "AIzaSyCD7OwQcJlxz6ch8dsuM7TXaYUpZMMhXCI"), type="password")
            if st.button("Conectar Drive"):
                from utils.drive_manager import get_folder_metadata
                root_meta = get_folder_metadata(drive_folder_id, api_key=drive_api_key)
                st.session_state.drive_api_key = drive_api_key
                st.session_state.drive_root_id = drive_folder_id
                st.session_state.current_folder_id = drive_folder_id
                st.session_state.folder_history = [(drive_folder_id, root_meta.get('name', 'Raíz Pactora'))]
                st.success("Conectado con éxito.")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.divider()
        if st.button("Cerrar Sesión Pactora"):
            st.session_state.clear()
            st.rerun()

    # Renderizar el chat lateral si está abierto
    render_sidebar_chat()

if __name__ == "__main__":
    main()
