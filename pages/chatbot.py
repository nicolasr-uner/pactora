import streamlit as st
from utils.shared import apply_styles, page_header, init_session_state, api_status_banner

apply_styles()
init_session_state()

page_header()
api_status_banner()
st.header("JuanMitaBot — Agente de Contratos")

stats = st.session_state.chatbot.get_stats()

if stats["total_docs"] > 0:
    sources_preview = ", ".join(stats["sources"][:3])
    extra = f" y {len(stats['sources'])-3} mas" if len(stats["sources"]) > 3 else ""
    st.success(
        f"JuanMitaBot tiene contexto de **{stats['total_docs']} contrato(s)**: "
        f"{sources_preview}{extra}"
    )
else:
    st.warning(
        "JuanMitaBot no tiene contratos indexados aun. "
        "Ve a **Ajustes** para conectar Google Drive — se indexaran automaticamente."
    )

col_chat, col_info = st.columns([3, 1])

with col_chat:
    if st.session_state.chat_history:
        if st.button("Limpiar conversacion"):
            st.session_state.chat_history = []
            st.rerun()

    chat_container = st.container(height=500)
    with chat_container:
        for m in st.session_state.chat_history:
            avatar = "🤖" if m["role"] == "assistant" else None
            with st.chat_message(m["role"], avatar=avatar):
                st.markdown(m["content"])

    prompt = st.chat_input("Pregunta sobre los contratos indexados...")
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("JuanMitaBot analizando contratos..."):
                    history_for_llm = st.session_state.chat_history[:-1]
                    res = st.session_state.chatbot.ask_question(
                        prompt, chat_history=history_for_llm
                    )
                st.markdown(res)
        st.session_state.chat_history.append({"role": "assistant", "content": res})

with col_info:
    st.markdown("### Contratos disponibles")
    if stats["sources"]:
        for s in stats["sources"]:
            st.markdown(f"- `{s}`")
    else:
        st.caption("Sin contratos indexados.")

    st.markdown("---")
    st.markdown("### Preguntas sugeridas")
    suggestions = [
        "Resume los contratos indexados",
        "Cuales son las partes de cada contrato?",
        "Hay riesgos regulatorios CREG?",
        "Cuales son las fechas de vencimiento?",
        "Identifica obligaciones de pago",
    ]
    for s in suggestions:
        if st.button(s, key=f"sug_{s[:20]}", use_container_width=True):
            st.session_state.chat_history.append({"role": "user", "content": s})
            st.rerun()
