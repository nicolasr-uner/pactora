import streamlit as st
import io
import datetime
from utils.shared import apply_styles, page_header, init_session_state, api_status_banner

apply_styles()
init_session_state()

page_header()
api_status_banner()
st.header("Analisis de Riesgos y Contratos")

tab_biblioteca, tab_upload, tab_compare, tab_editor, tab_versions = st.tabs(
    ["Biblioteca", "Cargar Contrato", "Comparar Contratos", "Editor de Borrador", "Historial de Versiones"]
)

# ─── Biblioteca de contratos indexados ────────────────────────────────────────
with tab_biblioteca:
    stats = st.session_state.chatbot.get_stats()
    sources = stats.get("sources", [])

    if not sources:
        st.info("No hay contratos indexados todavia. Conecta Drive en Ajustes o sube un contrato en 'Cargar Contrato'.")
    else:
        col_search, col_count = st.columns([3, 1])
        with col_search:
            search = st.text_input(
                "buscar", placeholder="Filtrar contratos...", label_visibility="collapsed", key="bib_search"
            )
        with col_count:
            st.caption(f"{len(sources)} contrato(s) indexado(s)")

        filtered = [s for s in sources if search.lower() in s.lower()] if search else sources

        for src in filtered:
            with st.container():
                col_name, col_prev, col_anal, col_cmp = st.columns([5, 1, 1, 1])
                col_name.markdown(f"**{src}**")

                # Toggle preview
                prev_key = f"bib_prev_{src}"
                if col_prev.button("Previsualizar", key=f"btn_prev_{src}", use_container_width=True):
                    st.session_state[prev_key] = not st.session_state.get(prev_key, False)

                # Analizar con JuanMitaBot
                if col_anal.button("Analizar", key=f"btn_anal_{src}", use_container_width=True):
                    st.session_state["bib_analysis_target"] = src
                    st.session_state["bib_analysis_result"] = None

                # Preseleccionar para comparar
                if col_cmp.button("Comparar", key=f"btn_cmp_{src}", use_container_width=True):
                    st.session_state["cmp_preselect_left"] = src
                    st.toast(f"'{src[:40]}' seleccionado — ve a Comparar Contratos", icon="✅")

                # Preview inline desde ChromaDB
                if st.session_state.get(prev_key, False):
                    with st.expander(f"Contenido: {src}", expanded=True):
                        try:
                            all_docs = st.session_state.chatbot.vectorstore.get(
                                include=["documents", "metadatas"]
                            )
                            chunks = [
                                d for d, m in zip(
                                    all_docs.get("documents", []),
                                    all_docs.get("metadatas", [])
                                )
                                if m and m.get("source") == src
                            ]
                            if chunks:
                                preview = "\n\n---\n\n".join(chunks[:4])
                                st.text_area(
                                    "preview",
                                    value=preview[:4000] + ("..." if len(preview) > 4000 else ""),
                                    height=320,
                                    disabled=True,
                                    label_visibility="collapsed",
                                    key=f"ta_prev_{src}"
                                )
                                st.caption(f"{len(chunks)} fragmentos indexados — mostrando primeros 4")
                            else:
                                st.caption("No se encontro contenido para este contrato.")
                        except Exception as e:
                            st.caption(f"Error al cargar preview: {e}")

                # Analisis inline
                if st.session_state.get("bib_analysis_target") == src:
                    if st.session_state.get("bib_analysis_result") is None:
                        with st.spinner(f"JuanMitaBot analizando {src}..."):
                            result = st.session_state.chatbot.ask_question(
                                f"Analiza el contrato '{src}': partes involucradas, objeto del contrato, "
                                f"fechas clave, obligaciones principales, clausulas de riesgo y nivel ROJO/AMARILLO/VERDE.",
                                filter_metadata={"source": src}
                            )
                        st.session_state["bib_analysis_result"] = result
                    with st.expander(f"Analisis: {src}", expanded=True):
                        st.markdown(st.session_state.get("bib_analysis_result", ""))

                st.divider()

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

# ─── Comparar contratos ───────────────────────────────────────────────────────
with tab_compare:
    stats_cmp = st.session_state.chatbot.get_stats()
    all_sources = stats_cmp.get("sources", [])

    st.markdown("Selecciona los contratos a comparar. Puedes elegir contratos ya indexados o subir uno nuevo.")

    col_left, col_right = st.columns(2)

    # ── Lado izquierdo: contrato base ────────────────────────────────────────
    with col_left:
        st.markdown("#### Contrato base")
        if not all_sources:
            st.info("No hay contratos indexados. Conecta Drive en Ajustes.")
            contract_left = None
        else:
            search_left = st.text_input("Filtrar", placeholder="Buscar...", key="cmp_search_left")
            opts_left = [s for s in all_sources if search_left.lower() in s.lower()] if search_left else all_sources

            preselect = st.session_state.get("cmp_preselect_left")
            default_idx = opts_left.index(preselect) if preselect and preselect in opts_left else 0

            contract_left = st.selectbox(
                "Selecciona contrato base", opts_left, index=default_idx, key="cmp_sel_left"
            )

            # Preview del contrato base
            if contract_left and st.checkbox("Ver preview del contrato base", key="chk_prev_left"):
                try:
                    all_docs = st.session_state.chatbot.vectorstore.get(include=["documents", "metadatas"])
                    chunks = [
                        d for d, m in zip(all_docs.get("documents", []), all_docs.get("metadatas", []))
                        if m and m.get("source") == contract_left
                    ]
                    preview = "\n\n---\n\n".join(chunks[:3]) if chunks else "(sin contenido)"
                    st.text_area("prev_left", value=preview[:2500], height=200,
                                 disabled=True, label_visibility="collapsed")
                except Exception:
                    st.caption("No se pudo cargar el preview.")

    # ── Lado derecho: contrato a comparar ─────────────────────────────────────
    with col_right:
        st.markdown("#### Contrato a comparar")
        modo = st.radio("Origen del contrato", ["Desde indexados", "Subir archivo"], horizontal=True, key="cmp_modo")

        contract_right_name = None
        contract_right_text = None

        if modo == "Desde indexados":
            if not all_sources:
                st.info("No hay contratos indexados.")
            else:
                search_right = st.text_input("Filtrar", placeholder="Buscar...", key="cmp_search_right")
                opts_right = [s for s in all_sources if search_right.lower() in s.lower()] if search_right else all_sources
                contract_right_name = st.selectbox(
                    "Selecciona contrato a comparar", opts_right, key="cmp_sel_right"
                )

                if contract_right_name and st.checkbox("Ver preview del contrato a comparar", key="chk_prev_right"):
                    try:
                        all_docs = st.session_state.chatbot.vectorstore.get(include=["documents", "metadatas"])
                        chunks = [
                            d for d, m in zip(all_docs.get("documents", []), all_docs.get("metadatas", []))
                            if m and m.get("source") == contract_right_name
                        ]
                        preview = "\n\n---\n\n".join(chunks[:3]) if chunks else "(sin contenido)"
                        st.text_area("prev_right", value=preview[:2500], height=200,
                                     disabled=True, label_visibility="collapsed")
                    except Exception:
                        st.caption("No se pudo cargar el preview.")
        else:
            up_cmp = st.file_uploader("Sube el contrato (PDF o DOCX)", type=["pdf", "docx"], key="cmp_upload")
            if up_cmp:
                from utils.file_parser import extract_text_from_file
                contract_right_text = extract_text_from_file(io.BytesIO(up_cmp.read()), up_cmp.name)
                contract_right_name = up_cmp.name
                if contract_right_text and not contract_right_text.startswith("Error"):
                    st.caption(f"Cargado: {up_cmp.name} — {len(contract_right_text):,} chars")
                    with st.expander("Preview del archivo subido"):
                        st.text(contract_right_text[:1500])
                    if up_cmp.name not in st.session_state.chatbot._indexed_sources:
                        with st.spinner("Indexando..."):
                            st.session_state.chatbot.vector_ingest(contract_right_text, up_cmp.name, {})
                else:
                    st.error("No se pudo extraer texto del archivo.")
                    contract_right_name = None

    # ── Botón de comparacion ──────────────────────────────────────────────────
    st.markdown("---")
    aspectos = st.multiselect(
        "Aspectos a comparar",
        ["Partes y objeto", "Montos y valores", "Plazos y fechas", "Obligaciones",
         "Penalidades", "Clausulas de terminacion", "Nivel de riesgo (ROJO/AMARILLO/VERDE)"],
        default=["Partes y objeto", "Montos y valores", "Plazos y fechas", "Nivel de riesgo (ROJO/AMARILLO/VERDE)"],
        key="cmp_aspectos"
    )

    if st.button("Comparar con JuanMitaBot", type="primary", use_container_width=True, key="btn_compare"):
        if not contract_left:
            st.error("Selecciona un contrato base.")
        elif not contract_right_name:
            st.error("Selecciona o sube el contrato a comparar.")
        elif contract_left == contract_right_name:
            st.warning("Los dos contratos son el mismo.")
        else:
            aspectos_str = ", ".join(aspectos) if aspectos else "todos los aspectos"
            with st.spinner("JuanMitaBot comparando contratos..."):
                analysis = st.session_state.chatbot.ask_question(
                    f"Compara en detalle los contratos '{contract_left}' y '{contract_right_name}'. "
                    f"Enfocate en: {aspectos_str}. "
                    f"Para cada diferencia relevante usa semaforo ROJO/AMARILLO/VERDE. "
                    f"Presenta la comparacion en formato de tabla o secciones claras. "
                    f"Al final, da un resumen de cual contrato representa mayor riesgo y por que."
                )
            st.markdown("### Resultado de la comparacion")
            st.markdown(f"**Base:** {contract_left}  |  **Comparado:** {contract_right_name}")
            st.markdown(analysis)
            st.download_button(
                "Exportar comparacion (.txt)",
                data=f"COMPARACION\nBase: {contract_left}\nComparado: {contract_right_name}\n\n{analysis}".encode("utf-8"),
                file_name=f"comparacion_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain"
            )

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
