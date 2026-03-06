import streamlit as st
from utils.auth_helper import authenticate_google_apis

st.set_page_config(page_title="Pactora - Unergy DocBrain", page_icon="📝", layout="wide")

st.title("Pactora - Unergy DocBrain")

tab_dashboard, tab_ingest, tab_rag, tab_config = st.tabs([
    "📊 Dashboard", 
    "📂 Ingesta y Análisis", 
    "💬 Chatbot RAG", 
    "⚙️ Configuración"
])

with tab_dashboard:
    st.header("Dashboard Comercial")
    st.write("Vista sobre métricas de riesgo y matrices de tiempo.")

with tab_ingest:
    st.header("Human-in-the-Loop y Extracción")
    st.write("Carga de contratos (.docx, Drive) para revisión.")

with tab_rag:
    st.header("Asistente RAG Legal")
    st.write("Consulta y semáforo de riesgo CREG / BMA.")

with tab_config:
    st.header("Autenticación")
    st.write("Inicia sesión de forma segura para conectar con **Google Drive** (Ingesta Read-Only) y **Calendar** (Agendamiento).")
    
    if st.button("Conectar con Google Workspace"):
        with st.spinner("Autenticando..."):
            services = authenticate_google_apis()
            if services:
                st.session_state['google_services'] = services
                st.success("¡Autenticación exitosa! Ya puedes cargar documentos o sincronizar eventos.")
    
    if 'google_services' in st.session_state:
        st.info("Estado: 🟢 Conectado de forma segura.")
