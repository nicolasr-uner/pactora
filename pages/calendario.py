import streamlit as st
from utils.shared import apply_styles, page_header, init_session_state

apply_styles()
init_session_state()

page_header()
st.header("Calendario Operativo")

view = st.radio("Vista", ["Mensual", "Semanal", "Diario"], horizontal=True)

stats = st.session_state.chatbot.get_stats()
if stats["total_docs"] > 0:
    if st.button("JuanMitaBot: fechas clave de contratos"):
        with st.spinner("Extrayendo fechas..."):
            ans = st.session_state.chatbot.ask_question(
                "Lista todas las fechas clave de los contratos indexados: "
                "fechas de inicio, vencimiento, opciones de renovacion, plazos de pago y cualquier hito importante. "
                "Organiza por contrato."
            )
        st.markdown(ans)

st.info(f"Vista {view} — Conecta Google Calendar en Ajustes para ver eventos reales.")
