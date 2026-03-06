import streamlit as st

def main():
    st.set_page_config(page_title="Pactora CLM - Unergy", layout="wide")
    st.title("Pactora - Unergy DocBrain")
    
    tabs = st.tabs(["Dashboard Comercial", "Ingesta y Análisis Legal", "Asistente RAG", "Configuración"])
    
    with tabs[0]:
        st.header("Dashboard Comercial")
        st.write("Visualización de métricas, rentabilidad e informes Investor-Ready.")
    
    with tabs[1]:
        st.header("Ingesta y Análisis Legal")
        st.write("Carga de contratos, extracción y clasificación de riesgos (Semáforo CREG).")
        
    with tabs[2]:
        st.header("Asistente Legal RAG")
        st.write("Consultas conversacionales con contexto estricto de los documentos cargados.")
        
    with tabs[3]:
        st.header("Configuración e Integraciones")
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
