import streamlit as st
import os

# --- HELPER FUNCTIONS ---
def render_side_chat_panel(panel_col):
    """Renderiza el chatbot contextual en una columna lateral derecha."""
    with panel_col:
        st.markdown(f"""
        <div style="background: white; padding: 20px; border-radius: 20px; box-shadow: -5px 0 15px rgba(0,0,0,0.05); height: 85vh; border-left: 2px solid #915BD8;">
            <h3 style="color: #2C2039; margin-top: 0;">🧠 JuanMa Contextual</h3>
            <p style="font-size: 0.8em; color: #915BD8;"><b>Documento:</b> {st.session_state.get('sidebar_chat_title', 'Contexto')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Historial del chat lateral
        chat_container = st.container(height=500)
        with chat_container:
            if 'sidebar_chat_history' not in st.session_state:
                st.session_state.sidebar_chat_history = []
            for msg in st.session_state.sidebar_chat_history:
                with st.chat_message(msg['role'], avatar="🤖" if msg['role'] == "assistant" else None):
                    st.markdown(msg['content'])

        # Input
        user_input = st.chat_input("Pregunta sobre este archivo...", key="side_panel_input")
        if user_input:
            st.session_state.sidebar_chat_history.append({"role": "user", "content": user_input})
            st.rerun()

        # Respuesta diferida para mostrar el mensaje de carga en el contenedor correcto
        if st.session_state.sidebar_chat_history and st.session_state.sidebar_chat_history[-1]["role"] == "user":
            last_query = st.session_state.sidebar_chat_history[-1]["content"]
            with chat_container:
                with st.chat_message("assistant", avatar="🤖"):
                    with st.spinner("Analizando..."):
                        filter_meta = st.session_state.get('sidebar_chat_filter')
                        ans = st.session_state.chatbot.ask_question(last_query, filter_metadata=filter_meta)
                        st.markdown(ans)
            st.session_state.sidebar_chat_history.append({"role": "assistant", "content": ans})
            st.rerun()

        if st.button("Cerrar Chat IA", use_container_width=True):
            st.session_state.sidebar_chat_open = False
            st.rerun()

def main():
    st.set_page_config(page_title="Pactora CLM - Unergy", layout="wide")
    
    # --- SESSION STATE INITIALIZATION ---
    if 'gemini_api_key' not in st.session_state:
        st.session_state.gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")
        
    if 'chatbot' not in st.session_state:
        from core.rag_chatbot import RAGChatbot
        st.session_state.chatbot = RAGChatbot(api_key=st.session_state.gemini_api_key)

    if 'current_folder_id' not in st.session_state:
        st.session_state.current_folder_id = st.session_state.get('drive_root_id', "1sF8_SuiiFdiWq_9htA-cNZP1Gp0djc4N")
    if 'folder_history' not in st.session_state:
        st.session_state.folder_history = [(st.session_state.current_folder_id, "Raíz Pactora")]
    if 'sidebar_chat_open' not in st.session_state:
        st.session_state.sidebar_chat_open = False
    
    # --- STYLES ---
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Lato:wght@400;700;900&display=swap');
    .stApp { background-color: #FDFAF7; font-family: 'Lato', sans-serif; color: #212121; }
    .top-nav { position: fixed; top: 20px; right: 40px; z-index: 1000; display: flex; gap: 20px; background: rgba(255, 255, 255, 0.8); padding: 10px 20px; border-radius: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); backdrop-filter: blur(5px); }
    .top-nav a { text-decoration: none; color: #915BD8; font-weight: 700; font-size: 18px; }
    .pactora-header { font-family: 'Lato', sans-serif; font-weight: 900; font-size: 56px; color: #2C2039; text-align: center; margin-top: -40px; }
    .pactora-tagline { text-align: center; color: #915BD8; font-weight: 600; margin-bottom: 30px; }
    section[data-testid="stSidebar"] { background-color: #2C2039 !important; width: 250px !important; }
    [data-testid="stSidebar"] * { color: #FDFAF7 !important; }
    .factora-card { background: rgba(255, 255, 255, 0.8); border-radius: 20px; padding: 24px; box-shadow: 0 8px 32px 0 rgba(145, 91, 216, 0.05); border: 1px solid rgba(145, 91, 216, 0.1); margin-bottom: 20px; }
    .card-title { font-size: 20px; font-weight: 900; color: #2C2039; margin-bottom: 18px; border-left: 5px solid #915BD8; padding-left: 12px; }
    </style>
    """, unsafe_allow_html=True)
    
    # --- SIDEBAR NAVIGATION ---
    with st.sidebar:
        nav_opt = st.radio(
            "Menú",
            ["🏠 Inicio", "📅 Calendario", "📊 Métricas", "📄 Plantillas", "⚖️ Análisis Legal", "🧠 Chatbot", "⚙️ Ajustes"],
            label_visibility="collapsed"
        )
        st.divider()
        if 'drive_root_id' in st.session_state:
            st.caption(f"☁️ Conectado: {st.session_state.get('drive_root_name', 'Drive')}")
        st.session_state.agent_active = st.toggle("🤖 Activar Agente (JuanMa)", value=st.session_state.get('agent_active', False))

    # --- LAYOUT LOGIC ---
    if st.session_state.get('sidebar_chat_open'):
        col_main, col_side = st.columns([2.5, 1])
    else:
        col_main = st.container()
        col_side = None

    with col_main:
        # Top Nav & Branding
        st.markdown('<div class="top-nav"><a href="#inicio">🏠 Inicio</a><a href="#chatbot">🧠 JuanMa</a><a href="#ajustes">⚙️ Ajustes</a></div>', unsafe_allow_html=True)
        st.markdown('<div class="pactora-header">Pactora</div><div class="pactora-tagline">by Unergy</div>', unsafe_allow_html=True)

        if nav_opt == "🏠 Inicio":
            st.markdown('<div style="max-width: 600px; margin: 0 auto;">', unsafe_allow_html=True)
            search_query = st.text_input("🔍 Buscar en todo el workspace...", placeholder="Ej: Cláusulas de terminación en Suno Solar")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if search_query:
                with st.spinner("JuanMa consultando..."):
                    ans = st.session_state.chatbot.ask_question(search_query)
                st.info(f"🤖 **JuanMa Insights:**\n\n{ans}")

            c1, c2 = st.columns(2)
            with c1:
                st.markdown('<div class="factora-card"><div class="card-title">Explorador de Archivos</div>', unsafe_allow_html=True)
                if 'drive_root_id' in st.session_state:
                    from utils.drive_manager import get_folder_contents
                    
                    if st.session_state.get('drive_api_key') == "DEMO_KEY" and 'mock_items' in st.session_state:
                        items = st.session_state.mock_items
                    else:
                        items = get_folder_contents(st.session_state.current_folder_id, api_key=st.session_state.get('drive_api_key'))
                    
                    for item in items[:10]:
                        icon = "📁" if item['mimeType'] == 'application/vnd.google-apps.folder' else "📄"
                        row = st.columns([1, 8, 1])
                        row[0].write(icon)
                        if row[1].button(item['name'], key=f"f_{item['id']}", use_container_width=True):
                            if item['mimeType'] == 'application/vnd.google-apps.folder':
                                st.session_state.current_folder_id = item['id']
                                st.session_state.folder_history.append((item['id'], item['name']))
                                st.rerun()
                        if row[2].button("🤖", key=f"ia_{item['id']}", help="Preguntar sobre este contexto"):
                            st.session_state.sidebar_chat_open = True
                            st.session_state.sidebar_chat_title = item['name']
                            st.session_state.sidebar_chat_history = []
                            st.session_state.sidebar_chat_filter = {"file_id": item['id']} if item['mimeType'] != 'application/vnd.google-apps.folder' else {"folder_id": item['id']}
                            st.rerun()
                else:
                    st.info("Conecta tu Drive en Ajustes.")
                st.markdown('</div>', unsafe_allow_html=True)
            
            with c2:
                st.markdown('<div class="factora-card"><div class="card-title">Calendario</div>', unsafe_allow_html=True)
                # (Minified calendar logic)
                st.write("Marzo 2026")
                st.image("https://via.placeholder.com/300x150?text=Mini+Calendar")
                st.markdown('</div>', unsafe_allow_html=True)

        elif nav_opt == "📅 Calendario":
            st.header("📅 Calendario Operativo")
            view = st.radio("Vista", ["Mensual", "Semanal", "Diario"], horizontal=True)
            st.info(f"Mostrando vista {view}...")

        elif nav_opt == "📊 Métricas":
            st.header("📊 Métricas de Cumplimiento")
            import pandas as pd
            df = pd.DataFrame({"Proyecto": ["Suno", "Pactora", "Unergy"], "Score": [85, 92, 78]})
            st.bar_chart(df.set_index("Proyecto"))

        elif nav_opt == "📄 Plantillas":
            st.header("📄 Biblioteca de Plantillas")
            st.write("PPA_Standard_V2.docx")
            st.button("Descargar .docx")

        elif nav_opt == "⚖️ Análisis Legal":
            st.header("⚖️ Análisis de Riesgos")
            up = st.file_uploader("Subir contrato")
            if up: st.success("Documento cargado.")

        elif nav_opt == "🧠 Chatbot":
            st.header("🧠 JuanMa - Asistente Global")
            if 'chat_history' not in st.session_state: st.session_state.chat_history = []
            for m in st.session_state.chat_history:
                with st.chat_message(m['role']): st.markdown(m['content'])
            prompt = st.chat_input("Dime algo...")
            if prompt:
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                with st.chat_message("user"): st.markdown(prompt)
                with st.chat_message("assistant"):
                    res = st.session_state.chatbot.ask_question(prompt)
                    st.markdown(res)
                st.session_state.chat_history.append({"role": "assistant", "content": res})

        elif nav_opt == "⚙️ Ajustes":
            st.header("⚙️ Ajustes")
            k = st.text_input("Gemini API Key", value=st.session_state.gemini_api_key, type="password")
            if st.button("Guardar"):
                st.session_state.gemini_api_key = k
                st.rerun()
            st.divider()
            if st.button("🧠 Indexar Workspace Completo"):
                if 'drive_root_id' not in st.session_state: st.error("Conecta Drive primero.")
                else:
                    with st.spinner("Indexando..."):
                        from utils.drive_manager import get_recursive_files, download_file_to_io
                        from utils.file_parser import extract_text_from_file
                        all_f = get_recursive_files(st.session_state.drive_root_id, api_key=st.session_state.drive_api_key)
                        ingest = []
                        for f in all_f:
                            io_f = download_file_to_io(f['id'], api_key=st.session_state.drive_api_key)
                            if io_f:
                                txt = extract_text_from_file(io_f, f['name'])
                                ingest.append((txt, f['name'], {"file_id": f['id'], "folder_id": f.get('parents', [''])[0]}))
                        st.session_state.chatbot.vector_ingest_multiple(ingest)
                        st.success("¡Workspace indexado!")

            if st.button("Conectar Drive Demo"):
                st.session_state.drive_root_id = "1sF8_SuiiFdiWq_9htA-cNZP1Gp0djc4N"
                st.session_state.drive_api_key = "DEMO_KEY"
                st.session_state.current_folder_id = st.session_state.drive_root_id
                st.session_state.folder_history = [(st.session_state.drive_root_id, "Raíz Pactora")]
                st.session_state.drive_root_name = "Raíz Pactora (Demo)"
                # Mock items for verification
                st.session_state.mock_items = [
                    {'id': 'doc1', 'name': 'Contrato_Suno_Solar_v1.docx', 'mimeType': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'},
                    {'id': 'doc2', 'name': 'EPC_Pactora_Final.docx', 'mimeType': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'},
                    {'id': 'fold1', 'name': 'Anexos_Legales', 'mimeType': 'application/vnd.google-apps.folder'}
                ]
                st.rerun()

    # Right Panel Rendering
    if col_side:
        render_side_chat_panel(col_side)

if __name__ == "__main__":
    main()
