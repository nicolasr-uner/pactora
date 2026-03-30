import streamlit as st
from utils.shared import apply_styles, page_header, init_session_state, render_document_preview
from utils.auth import get_current_user, filter_sources_for_user

apply_styles()
init_session_state()
page_header()

st.markdown("## Biblioteca de Documentos")

user = get_current_user()
stats = st.session_state.chatbot.get_stats()
sources = stats.get("sources", [])
sources = filter_sources_for_user(sources, user)
selected_src = st.session_state.get("biblioteca_selected")

# ── MODO SPLIT VIEW (documento abierto) ───────────────────────────────────────
if selected_src and selected_src in sources:
    nav_cols = st.columns([1, 8, 1])
    if nav_cols[0].button("← Volver", key="bib_back"):
        del st.session_state["biblioteca_selected"]
        st.rerun()
    ext_sel = selected_src.lower().split(".")[-1] if "." in selected_src else ""
    icon_sel = "📄" if ext_sel == "pdf" else "📝"
    nav_cols[1].markdown(f"**{icon_sel} {selected_src}**")
    if nav_cols[2].button("⚖ Analizar", key="bib_to_legal"):
        st.session_state["library_selected"] = selected_src
        st.switch_page("pages/legal.py")

    col_doc, col_chat = st.columns([3, 2], gap="medium")

    with col_doc:
        st.markdown("##### Documento")
        render_document_preview(selected_src, height=660)

    with col_chat:
        st.markdown("##### 💬 JuanMitaBot — sobre este contrato")
        chat_sk = f"bib_chat_{selected_src}"
        if chat_sk not in st.session_state:
            st.session_state[chat_sk] = []
        doc_hist = st.session_state[chat_sk]

        chat_box = st.container(height=530)
        with chat_box:
            if not doc_hist:
                st.markdown(
                    '<div style="color:#aaa;text-align:center;margin-top:120px;font-size:13px;">'
                    '🤖 Pregunta cualquier cosa<br>sobre este documento</div>',
                    unsafe_allow_html=True
                )
            for msg in doc_hist:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        with st.form(key="bib_chat_form", clear_on_submit=True):
            doc_q = st.text_input(
                "Pregunta", placeholder="¿Qué dice sobre...?",
                label_visibility="collapsed"
            )
            sent = st.form_submit_button("Enviar →", width="stretch")

        if sent and doc_q:
            st.session_state[chat_sk].append({"role": "user", "content": doc_q})
            with st.spinner("Consultando..."):
                answer = st.session_state.chatbot.ask_question(
                    doc_q,
                    filter_metadata={"source": selected_src},
                    chat_history=doc_hist,
                )
            st.session_state[chat_sk].append({"role": "assistant", "content": answer})
            st.rerun()

# ── MODO LISTA ────────────────────────────────────────────────────────────────
else:
    if not sources:
        st.info("No hay documentos indexados. Ve a **Ajustes** para cargar archivos.")
    else:
        hrow = st.columns([6, 3])
        with hrow[0]:
            search = st.text_input(
                "buscar_bib", placeholder="🔍 Filtrar documentos...",
                label_visibility="collapsed", key="bib_search"
            )
        filtered = [s for s in sources if search.lower() in s.lower()] if search else sources
        st.caption(f"{len(filtered)} documento(s) indexado(s)")

        for src in filtered:
            ext = src.lower().split(".")[-1] if "." in src else ""
            icon = "📄" if ext == "pdf" else "📝"
            cols = st.columns([6, 1, 1])
            cols[0].markdown(f"**{icon} {src}**")

            if cols[1].button("Abrir", key=f"bopen_{src}", width="stretch"):
                st.session_state["biblioteca_selected"] = src
                st.rerun()

            if cols[2].button("⚖", key=f"blegal_{src}", width="stretch", help="Abrir en Análisis Legal"):
                st.session_state["library_selected"] = src
                st.switch_page("pages/legal.py")

            st.divider()
