import streamlit as st

def render_sidebar_chat():
    """Renderiza el chatbot contextual en la barra lateral."""
    if st.session_state.get('sidebar_chat_open'):
        with st.sidebar:
            st.header(f"🤖 JuanMa: {st.session_state.sidebar_chat_title}")
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
                    with st.spinner("JuanMa responde..."):
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
    
    # --- UNERGY / FACTORA BRANDING CSS ---
    unergy_style = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Lato:wght@400;700;900&display=swap');

    /* Global App Structure */
    .stApp {
        background-color: #FDFAF7; /* Avena background (Light) */
        font-family: 'Lato', sans-serif;
        color: #212121; /* Púrpura Profundo -> Dynamic Dark Text for Light BG */
    }
    
    /* Dynamic Contrast Classes */
    .contrast-dark { color: #FFFFFF !important; }
    .contrast-light { color: #212121 !important; }

    /* Top-Right Static Navigation */
    .top-nav {
        position: fixed;
        top: 20px;
        right: 40px;
        z-index: 1000;
        display: flex;
        gap: 20px;
        background: rgba(255, 255, 255, 0.8);
        padding: 10px 20px;
        border-radius: 30px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        backdrop-filter: blur(5px);
    }
    .top-nav a {
        text-decoration: none;
        color: #915BD8;
        font-weight: 700;
        font-size: 18px;
    }

    /* Factora Header -> Pactora by Unergy */
    .pactora-header {
        font-family: 'Lato', sans-serif;
        font-weight: 900;
        font-size: 56px;
        color: #2C2039;
        text-align: center;
        margin-top: -40px;
        padding-bottom: 5px;
        letter-spacing: -2px;
    }
    .pactora-tagline {
        text-align: center;
        color: #915BD8;
        font-weight: 600;
        margin-bottom: 30px;
        font-size: 18px;
    }

    /* Sidebar Navigation Customization */
    section[data-testid="stSidebar"] {
        background-color: #2C2039 !important; /* Púrpura Profundo Sidebar */
        border-right: none;
        width: 250px !important; /* Increased width for accessibility */
    }
    
    /* Increased Sidebar Legibility */
    [data-testid="stSidebar"] * {
        font-size: 1.1rem !important;
    }
    
    [data-testid="stSidebarNav"] {
        background-color: transparent !important;
    }
    .stRadio > div {
        background-color: transparent !important;
    }
    label[data-testid="stWidgetLabel"] {
        color: #FDFAF7 !important;
        font-weight: 700;
    }

    /* Cards Style (Glassmorphism + Unergy touch) */
    .factora-card {
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(8px);
        border-radius: 20px;
        padding: 24px;
        box-shadow: 0 8px 32px 0 rgba(145, 91, 216, 0.05);
        border: 1px solid rgba(145, 91, 216, 0.1);
        height: 100%;
        margin-bottom: 20px;
        transition: transform 0.2s, border-color 0.2s;
    }
    .factora-card:hover {
        transform: translateY(-4px);
        border-color: #915BD8;
    }
    
    .card-title {
        font-size: 20px;
        font-weight: 900;
        color: #2C2039;
        margin-bottom: 18px;
        border-left: 5px solid #915BD8;
        padding-left: 12px;
    }

    /* Search Bar Customization */
    .stTextInput>div>div>input {
        background-color: white !important;
        border-radius: 12px !important;
        border: 1px solid #E0E0E0 !important;
        padding: 10px 20px !important;
        color: #2C2039 !important;
        font-family: 'Lato', sans-serif !important;
    }
    .stTextInput>div>div>input:focus {
        border-color: #915BD8 !important;
        box-shadow: 0 0 0 2px rgba(145, 91, 216, 0.2) !important;
    }

    /* Custom Buttons (Unergy Purple) */
    .stButton>button {
        background-color: #915BD8 !important;
        color: #FDFAF7 !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 10px 20px !important;
        font-weight: 700 !important;
        font-family: 'Lato', sans-serif !important;
    }
    .stButton>button:hover {
        background-color: #2C2039 !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(145, 91, 216, 0.3) !important;
    }

    /* Utility */
    .stCaption {
        color: #915BD8 !important;
        font-weight: 700 !important;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """
    st.markdown(unergy_style, unsafe_allow_html=True)
    
    # --- RENDER TOP NAV ---
    st.markdown("""
        <div class="top-nav">
            <a href="#inicio">🏠 Inicio</a>
            <a href="#chatbot">🧠 JuanMa</a>
            <a href="#ajustes">⚙️ Ajustes</a>
        </div>
    """, unsafe_allow_html=True)
    
    # --- RENDER BRANDING ---
    st.markdown('<div class="pactora-header">Pactora</div>', unsafe_allow_html=True)
    st.markdown('<div class="pactora-tagline">by Unergy</div>', unsafe_allow_html=True)
    # --- SIDEBAR NAVIGATION ---
    with st.sidebar:
        # st.markdown('<div style="text-align: center; margin-bottom: 20px;"><img src="https://cdn-icons-png.flaticon.com/512/124/124010.png" width="40"></div>', unsafe_allow_html=True) # Facebook Logo Removed
        nav_opt = st.radio(
            "Menú",
            ["🏠 Inicio", "📅 Calendario", "📊 Métricas", "📄 Plantillas", "⚖️ Análisis Legal", "🧠 Chatbot", "⚙️ Ajustes"],
            label_visibility="collapsed"
        )
        st.divider()
        
        if 'drive_root_id' in st.session_state:
            st.caption(f"☁️ Conectado: {st.session_state.folder_history[0][1]}")
            
        st.divider()
        st.session_state.agent_active = st.toggle("🤖 Activar Agente (JuanMa)", value=st.session_state.get('agent_active', False))
        if st.session_state.agent_active:
            st.success("Agente habilitado: JuanMa está listo para actuar.")

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

    elif nav_opt == "📅 Calendario":
        st.header("📅 Calendario Operativo Pactora")
        
        # View Selector
        view_mode = st.radio("Filtro de Vista", ["Diario", "Semanal", "Mensual", "Anual"], horizontal=True)
        
        st.markdown('<div class="factora-card">', unsafe_allow_html=True)
        st.subheader(f"Vista: {view_mode}")
        
        if view_mode == "Mensual":
            # Better Monthly View
            st.markdown('<div style="text-align: center; color: #915BD8; font-weight: 800; font-size: 24px; margin-bottom: 20px;">Marzo 2026</div>', unsafe_allow_html=True)
            cols = st.columns(7)
            days_header = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            for i, d in enumerate(days_header):
                cols[i].markdown(f'<div style="text-align: center; font-weight: 700; color: #2C2039; border-bottom: 2px solid #F3E8FF; padding-bottom: 10px;">{d}</div>', unsafe_allow_html=True)
            
            weeks = [
                [{"d": "23", "u": None}, {"d": "24", "u": None}, {"d": "25", "u": None}, {"d": "26", "u": "Rojo"}, {"d": "27", "u": None}, {"d": "28", "u": None}, {"d": "1", "u": None}],
                [{"d": "2", "u": None}, {"d": "3", "u": "Verde"}, {"d": "4", "u": None}, {"d": "5", "u": "Amarillo"}, {"d": "6", "u": None}, {"d": "7", "u": None}, {"d": "8", "u": None}],
                [{"d": "9", "u": "Rojo"}, {"d": "10", "u": None}, {"d": "11", "u": None}, {"d": "12", "u": "Amarillo"}, {"d": "13", "u": None}, {"d": "14", "u": None}, {"d": "15", "u": None}]
            ]
            
            for week in weeks:
                row = st.columns(7)
                for i, day_data in enumerate(week):
                    day = day_data["d"]
                    urgency = day_data["u"]
                    bg = "background: rgba(145, 91, 216, 0.05);" if urgency else ""
                    border = f"border-top: 4px solid {'#FF4B4B' if urgency=='Rojo' else '#FFAA00' if urgency=='Amarillo' else '#28A745' if urgency=='Verde' else 'transparent'};"
                    
                    row[i].markdown(f"""
                    <div style="height: 100px; padding: 10px; border-radius: 8px; {bg} {border} margin: 2px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
                        <span style="font-weight: 800; color: #2C2039;">{day}</span>
                        {f'<div style="font-size: 10px; margin-top: 10px; color: #5F6368;">Hito: {urgency}</div>' if urgency else ''}
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info(f"Integrando visualización interactiva para el modo {view_mode}...")
            st.image("https://via.placeholder.com/800x400.png?text=Interactive+Draggable+Calendar+Mode", caption="Componente Movible en Desarrollo")
            
        st.markdown('</div>', unsafe_allow_html=True)

    elif nav_opt == "📊 Métricas":
        st.header("📊 Métricas y Rendimiento Contractual")
        
        # Simulated Metrics Dashboard
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Contratos Totales", "24", "+2")
        with col2:
            st.metric("Score Promedio CREG", "88%", "-3%")
        with col3:
            st.metric("Pólizas por Vencer", "5", "Urgente")
            
        st.write("---")
        
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            st.markdown('<div class="factora-card">', unsafe_allow_html=True)
            st.subheader("Distribución por Tipo")
            import pandas as pd
            chart_data = pd.DataFrame({
                'Tipo': ['PPA', 'EPC', 'OyM', 'NDA', 'MOU'],
                'Cantidad': [8, 5, 4, 4, 3]
            })
            st.bar_chart(chart_data.set_index('Tipo'))
            st.markdown('</div>', unsafe_allow_html=True)
            
        with m_col2:
            st.markdown('<div class="factora-card">', unsafe_allow_html=True)
            st.subheader("Nivel de Riesgo (Semáforo)")
            risk_data = pd.DataFrame({
                'Nivel': ['Bajo (Verde)', 'Medio (Amarillo)', 'Alto (Rojo)'],
                'Contratos': [15, 6, 3]
            })
            st.area_chart(risk_data.set_index('Nivel'))
            st.markdown('</div>', unsafe_allow_html=True)

    elif nav_opt == "📄 Plantillas":
        st.header("📄 Gestión de Plantillas Maestras")
        
        # Template Tools
        t_col1, t_col2 = st.columns([1, 1])
        with t_col1:
            st.markdown('<div class="factora-card">', unsafe_allow_html=True)
            st.subheader("Cargar Nueva Plantilla")
            uploaded_template = st.file_uploader("Subir archivo (.docx)", type=["docx"])
            if uploaded_template:
                st.success("Plantilla cargada con éxito.")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with t_col2:
            st.markdown('<div class="factora-card">', unsafe_allow_html=True)
            st.subheader("Buscador de Plantillas")
            search_t = st.text_input("🔍 Buscar por nombre o tipo...", placeholder="PPA, EPC...")
            st.markdown('</div>', unsafe_allow_html=True)
            
        st.write("---")
        
        # Template List
        st.subheader("Biblioteca de Plantillas")
        templates = [
            {"name": "PPA_Standard_Unergy_V2.docx", "type": "PPA", "last": "2024-02-01"},
            {"name": "EPC_Construction_Solar_v4.docx", "type": "EPC", "last": "2024-01-15"},
            {"name": "NDA_General_Legal.docx", "type": "NDA", "last": "2023-11-20"},
        ]
        
        for t in templates:
            with st.expander(f"📄 {t['name']} ({t['type']})"):
                st.write(f"**Última actualización:** {t['last']}")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button(f"Previsualizar {t['name']}", key=f"pre_{t['name']}"):
                        st.info("Generando previsualización...")
                        st.markdown("> [!NOTE]\n> Esta es una vista previa de la estructura del documento PPA...")
                with c2:
                    st.download_button(f"Descargar {t['name']}", data=b"Contenido simulado", file_name=t['name'], key=f"dl_{t['name']}")

    elif nav_opt == "⚖️ Análisis Legal":
        st.header("⚖️ Ingeniería Legal & Semáforo de Riesgo")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown('<div class="factora-card">', unsafe_allow_html=True)
            st.subheader("Subir para Análisis")
            contract_type = st.selectbox("Tipo de Contrato", ["PPA", "EPC", "OyM", "Arriendo", "Representación Frontera", "MOU", "NDA", "Investment Agreement"])
            uploaded_file = st.file_uploader("Documento del Contrato (.docx)", type=["docx"], key="legal_uploader")
            run_analysis = st.button("Ejecutar Análisis de Riesgo", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        if run_analysis:
            if uploaded_file:
                from core.risk_assessor import analyze_legal_risk
                from utils.file_parser import extract_text_from_file
                import io
                
                with st.spinner("Pactora analizando riesgos y cumplimiento CREG..."):
                    text = extract_text_from_file(io.BytesIO(uploaded_file.getvalue()), uploaded_file.name)
                    report = analyze_legal_risk(text, contract_type)
                
                if "error" in report:
                    st.error(report["error"])
                else:
                    with c2:
                        st.markdown(f"### Score de Cumplimiento: **{report.get('compliance_score', 0)}%**")
                        st.write(report.get("summary", ""))
                        st.write("---")
                        
                        for risk in report.get("risks", []):
                            level = risk.get("level", "Verde")
                            color = "#FF4B4B" if level == "Rojo" else "#FFAA00" if level == "Amarillo" else "#28A745"
                            icon = "🔴" if level == "Rojo" else "🟡" if level == "Amarillo" else "🟢"
                            
                            st.markdown(f"""
                            <div style="background: white; border-left: 10px solid {color}; padding: 15px; border-radius: 12px; margin-bottom: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
                                <h4 style="margin:0; color: {color};">{icon} {risk.get('clause', 'Análisis de Cláusula')}</h4>
                                <p style="margin: 8px 0; color: #2C2039; font-size: 1.05em;">{risk.get('reason', '')}</p>
                                <div style="background: #F8F9FA; padding: 8px; border-radius: 8px; border: 1px dashed #DDD;">
                                    <span style="color: #5F6368; font-size: 0.9em;"><b>Acción Recomendada:</b> {risk.get('action', 'N/A')}</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Botón de Sincronización si es una póliza con fecha
                            if "Poliza" in risk.get('clause', '') and "vencimiento" in risk.get('reason', '').lower():
                                import re
                                date_match = re.search(r'\d{4}-\d{2}-\d{2}', risk.get('reason', ''))
                                if date_match:
                                    date_str = date_match.group()
                                    if st.button(f"📅 Sincronizar {risk.get('clause')} ({date_str})", key=f"sync_{risk.get('clause')}_{date_str}"):
                                        from utils.calendar_manager import create_contract_event
                                        res = create_contract_event(risk.get('clause'), risk.get('reason'), date_str)
                                        if "error" in res:
                                            st.error(f"Error: {res['error']}")
                                        else:
                                            st.success(f"✅ Sincronizado: [Ver en Calendario]({res['link']})")
            else:
                st.warning("⚠️ Por favor, carga un documento primero.")

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
            u_input = st.chat_input("Pregunta a JuanMa sobre tus contratos...")
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
