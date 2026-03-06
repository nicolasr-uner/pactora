import streamlit as st
import pandas as pd
from core.gemini_engine import process_contract, extract_text_from_docx
from core.risk_analyzer import analyze_risk
from core.rag_chatbot import RAGChatbot
from utils.calendar_sync import create_calendar_event
from utils.export_helper import generate_investor_report

# Unergy Brand Colors
COLOR_PURPLE = "#915BD8"
COLOR_DEEP_PURPLE = "#2C2039"
COLOR_OAT = "#FDFAF7"
COLOR_YELLOW = "#F6FF72"
COLOR_RED = "#FF4B4B"
COLOR_GREEN = "#28a745"

# Initialize Chatbot in session state
if 'chatbot' not in st.session_state:
    st.session_state['chatbot'] = RAGChatbot()

def main():
    st.set_page_config(page_title="Pactora - DocBrain", page_icon="📄", layout="wide")
    
    # Custom CSS for Unergy Branding (Fonts and Exact Colors)
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Lato:wght@400;700;900&display=swap');
    
    * {{
        font-family: 'Lato', 'Open Sans', 'Roboto', sans-serif !important;
    }}
    
    .stApp {{
        background-color: {COLOR_OAT};
        color: {COLOR_DEEP_PURPLE};
    }}
    
    h1, h2, h3, h4, h5, h6 {{
        /* Using Lato Extra Bold as fallback for Forma DJR Display */
        font-family: 'Lato', sans-serif !important;
        font-weight: 900 !important;
        color: {COLOR_DEEP_PURPLE} !important;
    }}
    
    /* Primary buttons (Púrpura Enérgico) */
    .stButton>button {{
        background-color: {COLOR_PURPLE};
        color: {COLOR_OAT} !important;
        border-radius: 8px;
        border: none;
        font-weight: 700 !important;
        padding: 12px 24px;
        transition: background-color 0.3s ease;
    }}
    
    .stButton>button:hover {{
        background-color: #7A45C0; /* Variación más oscura sugerida en la guía */
        color: white !important;
    }}
    
    /* Highlighting/Accents with Amarillo Solar */
    .stAlert {{
        background-color: rgba(246, 255, 114, 0.2) !important;
        color: {COLOR_DEEP_PURPLE} !important;
        border-left: 4px solid {COLOR_YELLOW} !important;
    }}
    
    /* Tables styling */
    .stDataFrame {{
        font-family: 'Lato', sans-serif !important;
    }}
    
    /* Links styling */
    a {{
        color: {COLOR_PURPLE} !important;
    }}
    </style>
    """, unsafe_allow_html=True)
    
    st.title("Pactora: Unergy DocBrain")
    
    tabs = st.tabs(["Dashboard Comercial", "Carga e Ingesta Legal", "Chatbot RAG"])
    
    with tabs[0]:
        st.header("Dashboard Comercial y Legal")
        
        if 'approved_metrics' in st.session_state and 'risk_data' in st.session_state:
            metrics_df = st.session_state['approved_metrics']
            risk = st.session_state['risk_data']
            policies_df = st.session_state.get('approved_policies', pd.DataFrame())
            
            # Filtros de Vista
            st.subheader("Filtros de Portfolio")
            col_filter_1, col_filter_2 = st.columns(2)
            with col_filter_1:
                filtro_tipo = st.selectbox("Filtrar por Tipo de Contrato", ["Todos", st.session_state.get('last_contract_type', 'PPA')])
            with col_filter_2:
                filtro_riesgo = st.selectbox("Filtrar por Nivel de Riesgo", ["Todos", "ROJO", "AMARILLO", "VERDE"])
                
            st.divider()
                
            # Use columns to create a clean dashboard feel
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Contratos Procesados", "1" if filtro_tipo == "Todos" or filtro_tipo == st.session_state.get('last_contract_type') else "0")
            with col2:
                nivel = risk.get("Nivel", "VERDE")
                color = COLOR_GREEN if nivel == "VERDE" else (COLOR_YELLOW if nivel == "AMARILLO" else COLOR_RED)
                if (filtro_riesgo == "Todos" or filtro_riesgo == nivel):
                    st.markdown(f"### Riesgo Actual: <span style='color:{color};'>{nivel}</span>", unsafe_allow_html=True)
                else:
                    st.markdown("### Riesgo Actual: N/A", unsafe_allow_html=True)
            with col3:
                polizas_count = len(policies_df) if not policies_df.empty else 0
                st.metric("Pólizas Activas (Acumulado)", polizas_count)
                
            st.divider()
            
            col_rep1, col_rep2 = st.columns(2)
            with col_rep1:
                st.subheader("Reporte de Due Diligence (Completo)")
                # Simple Dictionary mock based on DataFrame for report generation
                metrics_dict = {row["Campo"]: row["Valor Sugerido"] for _, row in metrics_df.iterrows()}
                policies_list = policies_df.to_dict('records') if not policies_df.empty else []
                contract_type = st.session_state.get('last_contract_type', 'PPA (Default)')
                
                report_md = generate_investor_report(contract_type, metrics_dict, policies_list, risk)
                
                st.download_button(
                    label="⬇️ Descargar Informe Due Diligence (.md)",
                    data=report_md,
                    file_name=f"Informe_{contract_type.replace(' ', '_')}.md",
                    mime="text/markdown"
                )
            with col_rep2:
                st.subheader("Avisos y Riesgos Legales")
                st.write("Descarga únicamente el análisis de riesgo y compliance para el comité.")
                
                # Crear un mini-reporte solo de riesgos
                alertas_text = "\\n".join([f"- {a}" for a in risk.get('Alertas', [])])
                risk_md = f"# Reporte de Riesgo: {contract_type}\\n\\n## Nivel CREG/BMA: {nivel}\\n\\n**Justificación:**\\n{risk.get('Justificacion', 'N/A')}\\n\\n**Alertas Críticas:**\\n{alertas_text}"
                st.download_button(
                    label="⚠️ Descargar Alertas de Riesgo (.txt)",
                    data=risk_md,
                    file_name=f"Riesgos_{contract_type.replace(' ', '_')}.txt",
                    mime="text/plain"
                )
            
            with st.expander("Ver Vista Previa del Informe de Due Diligence"):
                st.markdown(report_md)
                
        else:
            st.info("No hay datos aprobados todavía. Para poblar este dashboard, carga y aprueba un documento legal en la siguiente pestaña.")
    
    with tabs[1]:
        st.header("Ingesta de Contratos (Human-in-the-Loop)")
        st.write("Sube un contrato en formato `.docx` para extraer automáticamente sus datos críticos y evaluar riesgos (Semáforo CREG).")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            contract_type = st.selectbox(
                "Tipo de Contrato",
                ["PPA", "EPC", "OyM", "Representación de Frontera", "Arriendo", "Fiducia", "SHA", "NDA", "MOU", "Termsheet"]
            )
            
            uploaded_file = st.file_uploader("Subir Documento (.docx)", type=["docx"])
            
            if uploaded_file is not None:
                # Store the file in session state so we can redownload it
                st.session_state['current_file_bytes'] = uploaded_file.getvalue()
                st.session_state['current_file_name'] = uploaded_file.name
                
                st.info(f"📄 Archivo cargado: **{uploaded_file.name}**")
                
                st.download_button(
                    label="⬇️ Descargar Archivo Original",
                    data=st.session_state['current_file_bytes'],
                    file_name=st.session_state['current_file_name'],
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            
            if st.button("Procesar y Analizar Riesgo") and uploaded_file is not None:
                with st.spinner('Extrayendo texto y analizando con Gemini 1.5 Pro...'):
                    # 1. Extract text
                    file_bytes = uploaded_file.read()
                    text_content = extract_text_from_docx(file_bytes)
                    
                    if text_content:
                        # Pass string content to session state for chatbot
                        st.session_state['current_contract_text'] = text_content
                        st.session_state['chatbot_ready'] = False # Will reset chatbot
                        st.session_state['last_contract_type'] = contract_type
                        
                        # 2. Process Extraction
                        extracted_data = process_contract(text_content, contract_type)
                        # 3. Process Risk
                        risk_data = analyze_risk(text_content, contract_type)
                        
                        if "error" in extracted_data:
                            st.error(f"Error en extracción: {extracted_data['error']}")
                        elif "error" in risk_data:
                            st.error(f"Error en riesgo: {risk_data['error']}")
                        else:
                            st.success("¡Extracción y Análisis completados!")
                            st.session_state['extracted_data'] = extracted_data
                            st.session_state['risk_data'] = risk_data
                            
                            # Auto-vectorize in the background for RAG
                            with st.spinner('Vectorizando contrato en ChromaDB para el Chatbot...'):
                                success, msg = st.session_state['chatbot'].vector_ingest(text_content)
                                if success:
                                    st.session_state['chatbot_ready'] = True
                                else:
                                    st.error(f"Vectorización falló: {msg}")
                                    
                    else:
                        st.error("No se pudo extraer texto del documento.")
                        
        with col2:
            st.subheader("Validación y Semáforo de Riesgo")
            
            if 'risk_data' in st.session_state:
                risk = st.session_state['risk_data']
                nivel = risk.get("Nivel", "VERDE")
                color = COLOR_GREEN if nivel == "VERDE" else (COLOR_YELLOW if nivel == "AMARILLO" else COLOR_RED)
                
                st.markdown(f"### Riesgo Regulatorio/Comercial: <span style='color:{color}; font-weight:bold;'>{nivel}</span>", unsafe_allow_html=True)
                st.write(f"**Justificación:** {risk.get('Justificacion', '')}")
                alertas = risk.get('Alertas', [])
                if alertas:
                    st.warning("⚠️ Alertas Críticas:")
                    for alerta in alertas:
                        st.write(f"- {alerta}")
                st.divider()

            if 'extracted_data' in st.session_state:
                data = st.session_state['extracted_data']
                
                flat_metrics = {
                    "Campo": ["Precio", "Vigencia", "Hitos", "Obligaciones"],
                    "Valor Sugerido": [
                        data.get("Precio", ""),
                        data.get("Vigencia", ""),
                        data.get("Hitos", ""),
                        data.get("Obligaciones", "")
                    ]
                }
                st.write("**Métricas Críticas**")
                df_metrics = pd.DataFrame(flat_metrics)
                edited_metrics = st.data_editor(df_metrics, use_container_width=True, hide_index=True)
                
                st.write("**Pólizas y Garantías Detectadas**")
                policies = data.get("Polizas", [])
                if policies and isinstance(policies, list):
                    df_policies = pd.DataFrame(policies)
                    edited_policies = st.data_editor(df_policies, use_container_width=True, hide_index=True, num_rows="dynamic")
                else:
                    st.info("No se detectaron pólizas.")
                    df_policies = pd.DataFrame(columns=["Tipo", "Valor", "Vencimiento"])
                    edited_policies = st.data_editor(df_policies, use_container_width=True, hide_index=True, num_rows="dynamic")
                
                col_save, col_calendar = st.columns(2)
                with col_save:
                    if st.button("Aprobar y Guardar Datos"):
                        st.success("Datos guardados y validados por el equipo legal.")
                        st.session_state['approved_metrics'] = edited_metrics
                        st.session_state['approved_policies'] = edited_policies
                        
                with col_calendar:
                    if st.button("Sincronizar Pólizas con Google Calendar"):
                        if not edited_policies.empty:
                            success_count = 0
                            for index, row in edited_policies.iterrows():
                                if pd.notnull(row['Vencimiento']) and str(row['Vencimiento']).strip() != "":
                                    # Create Calendar Logic
                                    summary = f"Renovación Póliza {row.get('Tipo', 'Desconocida')}"
                                    desc = f"Póliza por {row.get('Valor', 'NaN')} vence el {row['Vencimiento']}. Sincronizado por Pactora DocBrain."
                                    res = create_calendar_event(summary, desc, str(row['Vencimiento']))
                                    if res:
                                        success_count += 1
                                        
                            if success_count > 0:
                                st.success(f"{success_count} evento(s) creado(s) con recordatorios automáticos.")
                            else:
                                st.warning("No se crearon eventos. Asegúrate de que las fechas tengan el formato YYYY-MM-DD.")
                        else:
                            st.warning("No hay pólizas para sincronizar.")
                        
            else:
                st.info("Aún no se ha procesado ningún documento.")
        
    with tabs[2]:
        st.header("Chatbot RAG Contractual")
        st.write("Consulta detalles específicos sobre el contrato ingresado actualmente.")
        
        # Enhanced validation for Chatbot and Vectorization state
        is_ready = st.session_state.get('chatbot_ready', False)
        has_text = 'current_contract_text' in st.session_state
        
        if is_ready and has_text:
            if "messages" not in st.session_state:
                st.session_state.messages = []

            # Display chat history
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # Input for new question
            if prompt := st.chat_input("Ej: ¿Cuál es la penalidad por retraso en el COD?"):
                st.chat_message("user").markdown(prompt)
                st.session_state.messages.append({"role": "user", "content": prompt})
                
                with st.chat_message("assistant"):
                    with st.spinner("Buscando en el contrato y generando respuesta..."):
                        try:
                            response = st.session_state['chatbot'].ask_question(prompt)
                            st.markdown(response)
                            st.session_state.messages.append({"role": "assistant", "content": response})
                        except Exception as e:
                            error_msg = f"Hubo un error al consultar la IA: {str(e)}"
                            st.error(error_msg)
                            st.session_state.messages.append({"role": "assistant", "content": error_msg})
        elif has_text and not is_ready:
            st.warning("El documento se ha subido pero su procesamiento vectorial falló o está pendiente. Vuelve a analizarlo en la pestaña de Ingesta.")
        else:
            st.info("👋 ¡Hola! Para hablar conmigo, primero debes subir y procesar un contrato en la pestaña 'Carga e Ingesta Legal'.")

if __name__ == "__main__":
    main()
