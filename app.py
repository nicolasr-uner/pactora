import streamlit as st

st.set_page_config(page_title="Pactora - Unergy DocBrain", page_icon="📝", layout="wide")

# Diseño de paleta Unergy
st.markdown("""
<style>
    /* Púrpura Enérgico #915BD8, Avena #FDFAF7, Amarillo Solar #F6FF72 */
    .stApp {
        background-color: #FDFAF7;
    }
</style>
""", unsafe_allow_html=True)

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
    st.write("Conexiones y credenciales.")
