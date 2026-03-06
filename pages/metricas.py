import streamlit as st
from utils.shared import apply_styles, page_header, init_session_state

apply_styles()
init_session_state()

page_header()
st.header("Metricas de Cumplimiento")

stats = st.session_state.chatbot.get_stats()
versiones = sum(len(v.get("history", [])) for v in st.session_state.doc_versions.values())

k1, k2, k3 = st.columns(3)
k1.markdown(
    f'<div class="metric-card"><div class="metric-val">{stats["total_docs"]}</div>'
    '<div class="metric-lbl">Contratos indexados</div></div>', unsafe_allow_html=True
)
k2.markdown(
    f'<div class="metric-card"><div class="metric-val">{stats["total_chunks"]}</div>'
    '<div class="metric-lbl">Fragmentos en RAG</div></div>', unsafe_allow_html=True
)
k3.markdown(
    f'<div class="metric-card"><div class="metric-val">{versiones}</div>'
    '<div class="metric-lbl">Versiones guardadas</div></div>', unsafe_allow_html=True
)

st.markdown("---")

if stats["sources"]:
    import pandas as pd

    # Grafico de fragmentos por documento
    try:
        all_meta = st.session_state.chatbot.vectorstore.get(include=["metadatas"])
        metas = all_meta.get("metadatas", [])
        counts = {src: sum(1 for m in metas if m and m.get("source") == src) for src in stats["sources"]}
        df = pd.DataFrame({"Documento": [s[:35] for s in counts], "Fragmentos": list(counts.values())})
        st.subheader("Fragmentos indexados por contrato")
        st.bar_chart(df.set_index("Documento"))
    except Exception:
        pass

    st.subheader("Documentos indexados")
    for i, src in enumerate(stats["sources"], 1):
        st.markdown(f"**{i}.** {src}")

    st.markdown("---")

    # JuanMitaBot genera analisis del portfolio
    st.subheader("Analisis de Portfolio — JuanMitaBot")
    if "portfolio_analysis" not in st.session_state:
        st.session_state.portfolio_analysis = None

    if st.button("Generar analisis de portfolio con JuanMitaBot", use_container_width=True):
        with st.spinner("JuanMitaBot analizando todos los contratos..."):
            analysis = st.session_state.chatbot.ask_question(
                "Genera un resumen ejecutivo del portfolio de contratos indexados. "
                "Para cada contrato identifica: partes involucradas, tipo de contrato, "
                "monto o capacidad si existe, fecha de inicio/vencimiento, y nivel de riesgo "
                "(semaforo ROJO/AMARILLO/VERDE). Al final, da una vista general del riesgo del portfolio."
            )
        st.session_state.portfolio_analysis = analysis

    if st.session_state.portfolio_analysis:
        st.markdown(st.session_state.portfolio_analysis)
else:
    if "drive_root_id" in st.session_state:
        st.warning("Drive conectado pero sin contratos indexados aun.")
        if st.button("Indexar contratos del Drive ahora", use_container_width=True):
            from utils.shared import run_drive_indexation
            with st.spinner("JuanMitaBot indexando contratos..."):
                ok, msg = run_drive_indexation(
                    st.session_state.drive_root_id,
                    st.session_state.get("drive_api_key", "")
                )
            if ok:
                st.success(msg)
            else:
                st.warning(msg)
            st.rerun()
    else:
        st.info(
            "No hay contratos indexados aun. Conecta Google Drive en **Ajustes** "
            "para que JuanMitaBot indexe automaticamente todos los contratos."
        )
