import streamlit as st
import io
import datetime
from utils.shared import apply_styles, page_header, init_session_state, api_status_banner

apply_styles()
init_session_state()

page_header()
api_status_banner()
st.header("Analisis de Riesgos y Contratos")

tab_upload, tab_editor, tab_versions, tab_compare = st.tabs(
    ["Cargar Contrato", "Editor de Borrador", "Historial de Versiones", "Comparar Contratos"]
)

# ─── Cargar contrato ──────────────────────────────────────────────────────────
with tab_upload:
    up = st.file_uploader("Sube un contrato (PDF o DOCX)", type=["pdf", "docx"])
    if up:
        from utils.file_parser import extract_text_from_file
        text = extract_text_from_file(io.BytesIO(up.read()), up.name)

        if text and not text.startswith("Error"):
            st.success(f"{up.name} cargado — {len(text):,} caracteres.")

            if up.name not in st.session_state.doc_versions:
                st.session_state.doc_versions[up.name] = {
                    "original": text, "draft": text, "history": []
                }
                with st.spinner("Indexando en JuanMitaBot..."):
                    ok, msg = st.session_state.chatbot.vector_ingest(
                        text, up.name, {"file_type": up.name.split(".")[-1]}
                    )
                st.info(msg)
            else:
                st.info("Documento ya indexado. Ve al Editor para editarlo.")

            with st.expander("Vista previa"):
                st.text(text[:2000] + ("..." if len(text) > 2000 else ""))

            if st.button("Analizar riesgos con JuanMitaBot"):
                with st.spinner("JuanMitaBot analizando..."):
                    analysis = st.session_state.chatbot.ask_question(
                        f"Analiza los riesgos, obligaciones principales, partes y fechas clave "
                        f"del contrato '{up.name}'. Usa el semaforo ROJO/AMARILLO/VERDE.",
                        filter_metadata={"source": up.name}
                    )
                st.markdown("### Analisis de Riesgos")
                st.markdown(analysis)
        else:
            st.error(f"No se pudo extraer texto: {text}")

# ─── Editor de borrador ───────────────────────────────────────────────────────
with tab_editor:
    if not st.session_state.doc_versions:
        st.info("Carga un contrato en 'Cargar Contrato' para empezar a editar.")
    else:
        doc_sel = st.selectbox(
            "Selecciona documento", list(st.session_state.doc_versions.keys())
        )
        ver = st.session_state.doc_versions[doc_sel]
        col_orig, col_draft = st.columns(2)

        with col_orig:
            st.markdown("#### Original (solo lectura)")
            st.text_area("orig", value=ver["original"][:3000], height=400,
                         disabled=True, label_visibility="collapsed")

        with col_draft:
            st.markdown("#### Borrador de trabajo")
            new_draft = st.text_area("draft", value=ver["draft"], height=400,
                                     key=f"draft_{doc_sel}", label_visibility="collapsed")

        col_save, col_reset, col_export = st.columns(3)
        with col_save:
            if st.button("Guardar version"):
                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                st.session_state.doc_versions[doc_sel]["history"].append(
                    {"timestamp": ts, "content": ver["draft"]}
                )
                st.session_state.doc_versions[doc_sel]["draft"] = new_draft
                st.success(f"Version guardada ({ts})")
                st.rerun()
        with col_reset:
            if st.button("Restaurar original"):
                st.session_state.doc_versions[doc_sel]["draft"] = ver["original"]
                st.rerun()
        with col_export:
            st.download_button(
                "Exportar borrador",
                data=new_draft.encode("utf-8"),
                file_name=f"BORRADOR_{doc_sel.replace('.docx','').replace('.pdf','')}.txt",
                mime="text/plain"
            )

        if st.button("JuanMitaBot: que cambie?"):
            orig_words = set(ver["original"].split())
            draft_words = set(new_draft.split())
            added = list(draft_words - orig_words)[:50]
            removed = list(orig_words - draft_words)[:50]
            diff_ctx = f"Palabras anadidas: {', '.join(added)}\nPalabras eliminadas: {', '.join(removed)}"
            with st.spinner("Analizando cambios..."):
                analysis = st.session_state.chatbot.ask_question(
                    f"Evalua las modificaciones al contrato '{doc_sel}' e indica si representan riesgos legales.\n{diff_ctx}"
                )
            st.markdown("#### Analisis de cambios")
            st.markdown(analysis)

# ─── Comparar contratos ───────────────────────────────────────────────────────
with tab_compare:
    stats_cmp = st.session_state.chatbot.get_stats()
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("#### Contratos de referencia (indexados)")
        if not stats_cmp["sources"]:
            st.info("No hay contratos indexados. Conecta Drive en Ajustes.")
        else:
            search_filter = st.text_input(
                "Filtrar contratos", placeholder="Buscar por nombre...", key="cmp_search"
            )
            filtered = [s for s in stats_cmp["sources"] if search_filter.lower() in s.lower()] \
                if search_filter else stats_cmp["sources"]
            selected_contracts = st.multiselect(
                "Selecciona contratos a comparar",
                options=filtered,
                default=[],
                key="cmp_selected"
            )

    with col_right:
        st.markdown("#### Contrato a comparar (sube un archivo)")
        up_cmp = st.file_uploader(
            "Sube el nuevo contrato (PDF o DOCX)",
            type=["pdf", "docx"],
            key="cmp_upload"
        )
        if up_cmp:
            st.caption(f"Archivo cargado: {up_cmp.name}")

    if st.button("Comparar con JuanMitaBot", type="primary", use_container_width=True,
                 key="btn_compare"):
        if not up_cmp:
            st.error("Sube un contrato para comparar.")
        elif not selected_contracts:
            st.error("Selecciona al menos un contrato de referencia.")
        else:
            from utils.file_parser import extract_text_from_file
            text_new = extract_text_from_file(io.BytesIO(up_cmp.read()), up_cmp.name)
            if not text_new or text_new.startswith("Error"):
                st.error(f"No se pudo extraer texto: {text_new}")
            else:
                # Indexar temporalmente si no esta
                if up_cmp.name not in st.session_state.chatbot._indexed_sources:
                    with st.spinner("Indexando contrato nuevo..."):
                        st.session_state.chatbot.vector_ingest(text_new, up_cmp.name, {})

                refs = ", ".join(selected_contracts)
                with st.spinner("JuanMitaBot comparando contratos..."):
                    analysis = st.session_state.chatbot.ask_question(
                        f"Compara el contrato '{up_cmp.name}' con los siguientes contratos de referencia: "
                        f"{refs}. "
                        f"Identifica diferencias y similitudes en: clausulas principales, montos o valores, "
                        f"plazos y fechas, obligaciones de cada parte, penalidades, y nivel de riesgo. "
                        f"Para cada diferencia relevante usa semaforo ROJO/AMARILLO/VERDE. "
                        f"Organiza la respuesta por seccion."
                    )
                st.markdown("### Resultado de la comparacion")
                st.markdown(analysis)

# ─── Historial de versiones ───────────────────────────────────────────────────
with tab_versions:
    has_versions = any(v["history"] for v in st.session_state.doc_versions.values())
    if not has_versions:
        st.info("No hay versiones guardadas aun.")
    else:
        for doc_name, ver in st.session_state.doc_versions.items():
            if ver["history"]:
                st.markdown(f"#### {doc_name}")
                for i, snap in enumerate(reversed(ver["history"])):
                    with st.expander(f"Version {len(ver['history'])-i} — {snap['timestamp']}"):
                        st.text(snap["content"][:1000] + ("..." if len(snap["content"]) > 1000 else ""))
                        if st.button(f"Restaurar esta version", key=f"restore_{doc_name}_{i}"):
                            st.session_state.doc_versions[doc_name]["draft"] = snap["content"]
                            st.rerun()
