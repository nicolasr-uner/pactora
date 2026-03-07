import streamlit as st
from utils.shared import apply_styles, page_header, init_session_state, run_drive_indexation, api_status_banner

apply_styles()
init_session_state()

page_header()
api_status_banner()
st.header("Configuracion")
st.markdown("---")

col_gemini, col_drive = st.columns(2)

# ─── Gemini API ───────────────────────────────────────────────────────────────
with col_gemini:
    st.markdown("""
    <div style="background:white;border-radius:16px;padding:24px;
         box-shadow:0 4px 20px rgba(145,91,216,0.08);
         border:1px solid rgba(145,91,216,0.15);">
        <h3 style="color:#2C2039;margin-top:0;border-left:4px solid #915BD8;padding-left:10px;">
            Gemini API
        </h3>
    </div>""", unsafe_allow_html=True)

    if st.session_state.gemini_api_key:
        st.caption("✓ Configurada")
    k = st.text_input(
        "API Key",
        value="",
        type="password",
        label_visibility="collapsed",
        placeholder="Ingresa nueva Gemini API Key..."
    )
    if st.button("Guardar Key"):
        if k:
            from core.rag_chatbot import RAGChatbot
            st.session_state.gemini_api_key = k
            st.session_state.chatbot = RAGChatbot(api_key=k)
            st.success("API Key guardada y JuanMitaBot reiniciado.")
            st.rerun()
        else:
            st.warning("Ingresa una API Key para guardar.")

# ─── Google Drive ─────────────────────────────────────────────────────────────
with col_drive:
    st.markdown("""
    <div style="background:white;border-radius:16px;padding:24px;
         box-shadow:0 4px 20px rgba(145,91,216,0.08);
         border:1px solid rgba(145,91,216,0.15);">
        <h3 style="color:#2C2039;margin-top:0;border-left:4px solid #915BD8;padding-left:10px;">
            Conexion Drive
        </h3>
    </div>""", unsafe_allow_html=True)

    folder_id_input = st.text_input(
        "ID carpeta raiz",
        value=st.session_state.get("drive_root_id", ""),
        label_visibility="collapsed",
        placeholder="ID de carpeta raiz de Drive..."
    )
    if st.session_state.get("drive_api_key", "") and st.session_state.get("drive_api_key") != "DEMO_KEY":
        st.caption("✓ API Key configurada")
    drive_key_input = st.text_input(
        "Drive API Key",
        value="",
        type="password",
        label_visibility="collapsed",
        placeholder="API Key de Google Drive..."
    )

    if st.button("Conectar Drive e Indexar contratos", type="primary"):
        if not folder_id_input:
            st.error("Ingresa el ID de carpeta.")
        elif not st.session_state.gemini_api_key:
            st.error("Configura primero la API Key de Gemini.")
        else:
            st.session_state.drive_root_id = folder_id_input
            st.session_state.drive_api_key = drive_key_input or "DEMO_KEY"
            st.session_state.current_folder_id = folder_id_input
            st.session_state.folder_history = [(folder_id_input, "Raiz Pactora")]
            st.session_state.drive_indexed = False

            if st.session_state.drive_api_key != "DEMO_KEY":
                # Auto-indexar inmediatamente
                progress_placeholder = st.empty()
                progress_placeholder.info("JuanMitaBot esta indexando todos los contratos del Drive...")
                ok, msg = run_drive_indexation(folder_id_input, st.session_state.drive_api_key)
                st.session_state.drive_indexed = True
                if ok:
                    progress_placeholder.success(f"Drive conectado. {msg}")
                else:
                    progress_placeholder.warning(f"Drive conectado, pero hubo problemas en la indexacion: {msg}")
            else:
                st.session_state.mock_items = [
                    {"id": "doc1", "name": "Contrato_Demo_Solar.pdf",
                     "mimeType": "application/pdf"},
                    {"id": "doc2", "name": "EPC_Demo_Final.docx",
                     "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
                    {"id": "fold1", "name": "Anexos_Demo",
                     "mimeType": "application/vnd.google-apps.folder"},
                ]
                st.success("Drive conectado en modo demo.")
            st.rerun()

    if "drive_root_id" in st.session_state:
        st.caption(f"Conectado: {st.session_state.drive_root_id[:25]}...")

st.markdown("---")

# ─── Re-indexar manualmente ───────────────────────────────────────────────────
if "drive_root_id" in st.session_state and st.session_state.get("drive_api_key", "") != "DEMO_KEY":
    with st.expander("Re-indexar contratos del Drive"):
        st.caption("Fuerza una nueva indexacion de todos los archivos PDF/DOCX.")
        if st.button("Re-indexar ahora"):
            with st.spinner("JuanMitaBot indexando contratos..."):
                ok, msg = run_drive_indexation(
                    st.session_state.drive_root_id,
                    st.session_state.drive_api_key
                )
            if ok:
                st.success(msg)
            else:
                st.warning(msg)
            st.rerun()

# ─── Cerrar sesion ────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
if st.button("Cerrar sesion Pactora"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
