import streamlit as st
from utils.shared import apply_styles, page_header, init_session_state

apply_styles()
init_session_state()

page_header()
st.header("Biblioteca de Plantillas")

plantillas = [
    {"nombre": "PPA_Standard_V2.docx",    "tipo": "PPA",  "version": "v2.1"},
    {"nombre": "EPC_Contrato_Base.docx",   "tipo": "EPC",  "version": "v1.3"},
    {"nombre": "O&M_Marco_General.docx",   "tipo": "O&M",  "version": "v1.0"},
    {"nombre": "Cesion_Derechos.docx",     "tipo": "Legal","version": "v1.2"},
    {"nombre": "NDA_Confidencialidad.docx","tipo": "Legal","version": "v2.0"},
]

st.markdown("---")
for p in plantillas:
    col_a, col_b, col_c, col_d = st.columns([5, 1, 1, 2])
    col_a.markdown(f"**{p['nombre']}**")
    col_b.markdown(
        f'<span class="version-badge">{p["tipo"]}</span>', unsafe_allow_html=True
    )
    col_c.markdown(
        f'<span class="version-badge">{p["version"]}</span>', unsafe_allow_html=True
    )
    col_d.button("Descargar", key=f"dl_{p['nombre']}")
    st.markdown("---")

st.info("Conecta Google Drive para acceder a las plantillas reales del repositorio corporativo.")
