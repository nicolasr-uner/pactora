import streamlit as st
import io
import datetime
import difflib
from utils.shared import apply_styles, page_header, init_session_state, api_status_banner

apply_styles()
init_session_state()
page_header()
api_status_banner()

st.markdown("## Análisis Legal de Contratos")
st.caption("Carga, previsualiza, edita y compara contratos. El análisis con IA estará disponible próximamente.")

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab_biblioteca, tab_upload, tab_compare, tab_editor, tab_historial = st.tabs([
    "📚 Biblioteca",
    "📤 Cargar Contrato",
    "🔀 Comparar",
    "✏️ Editor",
    "🕓 Historial",
])

# ─── BIBLIOTECA ───────────────────────────────────────────────────────────────
with tab_biblioteca:
    hrow = st.columns([9, 1])
    hrow[0].markdown("#### Contratos indexados")
    with hrow[1].popover("ℹ️"):
        st.markdown(
            "Lista todos los contratos cargados en el sistema. "
            "**Previsualizar** muestra el texto extraído del documento. "
            "**Análisis básico** detecta cláusulas clave de forma local. "
            "**Comparar** preselecciona el contrato para la pestaña Comparar."
        )

    stats = st.session_state.chatbot.get_stats()
    sources = stats.get("sources", [])

    if not sources:
        st.info("No hay contratos indexados. Usa la pestaña **Cargar Contrato** para agregar documentos.")
    else:
        search = st.text_input(
            "buscar_bib", placeholder="🔍 Filtrar contratos...",
            label_visibility="collapsed", key="bib_search"
        )
        filtered = [s for s in sources if search.lower() in s.lower()] if search else sources
        st.caption(f"{len(filtered)} contrato(s)")

        for src in filtered:
            with st.container():
                cols = st.columns([5, 1, 1, 1])
                ext = src.lower().split(".")[-1] if "." in src else ""
                icon = "📄" if ext == "pdf" else "📝"
                cols[0].markdown(f"**{icon} {src}**")

                prev_key = f"bib_prev_{src}"
                anal_key = f"bib_anal_{src}"

                if cols[1].button("Ver", key=f"bprev_{src}", use_container_width=True, help="Previsualizar texto"):
                    st.session_state[prev_key] = not st.session_state.get(prev_key, False)
                    st.rerun()

                if cols[2].button("Analizar", key=f"banal_{src}", use_container_width=True, help="Análisis básico local"):
                    st.session_state[anal_key] = not st.session_state.get(anal_key, False)
                    st.rerun()

                if cols[3].button("Comparar", key=f"bcmp_{src}", use_container_width=True, help="Preseleccionar para comparar"):
                    st.session_state["cmp_preselect"] = src
                    st.toast(f"'{src[:40]}' preseleccionado para comparar", icon="✅")

                # Previsualización
                if st.session_state.get(prev_key, False):
                    with st.expander(f"📄 Contenido: {src}", expanded=True):
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
                                texto = "\n\n---\n\n".join(chunks[:5])
                                st.text_area(
                                    "prev_text", value=texto[:4000],
                                    height=300, disabled=True,
                                    label_visibility="collapsed",
                                    key=f"ta_bib_{src}"
                                )
                                st.caption(f"{len(chunks)} fragmentos indexados")
                                st.download_button(
                                    "⬇ Exportar texto",
                                    data=texto.encode("utf-8"),
                                    file_name=f"{src}_texto.txt",
                                    mime="text/plain",
                                    key=f"dl_bib_{src}"
                                )
                            else:
                                st.caption("Sin texto previsualizable.")
                        except Exception as e:
                            st.caption(f"Error: {e}")

                # Análisis básico local (keywords)
                if st.session_state.get(anal_key, False):
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
                        full_text = " ".join(chunks).lower()

                        CLAUSULAS = {
                            "Penalidades": ["penalid", "multa", "sanción", "incumplimiento"],
                            "Terminación": ["terminación", "rescisión", "resolución", "cancelación"],
                            "Fuerza mayor": ["fuerza mayor", "caso fortuito", "evento extraordinario"],
                            "Pagos": ["pago", "factura", "precio", "valor", "monto"],
                            "Renovación": ["renovación", "prórroga", "extensión", "vencimiento"],
                            "Confidencialidad": ["confidencial", "secreto", "reservado", "sigilo"],
                            "Responsabilidad": ["responsabilidad", "indemnización", "daños y perjuicios"],
                        }

                        with st.expander(f"📋 Análisis: {src}", expanded=True):
                            st.markdown("**Cláusulas detectadas (análisis local):**")
                            found_any = False
                            for clausula, keywords in CLAUSULAS.items():
                                hits = sum(full_text.count(kw) for kw in keywords)
                                if hits > 0:
                                    found_any = True
                                    color = "#388e3c" if hits >= 3 else "#f57c00"
                                    st.markdown(
                                        f'<div style="display:flex;justify-content:space-between;'
                                        f'padding:6px 10px;border-left:3px solid {color};'
                                        f'margin-bottom:4px;background:white;border-radius:0 6px 6px 0;">'
                                        f'<span style="font-weight:600;">{clausula}</span>'
                                        f'<span style="color:{color};font-weight:700;">{hits} mención(es)</span>'
                                        f'</div>',
                                        unsafe_allow_html=True
                                    )
                            if not found_any:
                                st.caption("No se detectaron cláusulas clave. Verifica que el texto haya sido extraído correctamente.")

                            st.markdown(
                                '<div style="padding:8px;background:#f0f0f0;border-radius:8px;'
                                'font-size:12px;color:#666;margin-top:10px;">'
                                '🔮 <b>Próximamente:</b> análisis completo con IA (semáforo ROJO/AMARILLO/VERDE, '
                                'identificación de partes, fechas clave y riesgos contractuales).</div>',
                                unsafe_allow_html=True
                            )
                    except Exception as e:
                        st.caption(f"Error en análisis: {e}")

                st.divider()

# ─── CARGAR CONTRATO ──────────────────────────────────────────────────────────
with tab_upload:
    hrow = st.columns([9, 1])
    hrow[0].markdown("#### Cargar nuevo contrato")
    with hrow[1].popover("ℹ️"):
        st.markdown(
            "Sube un contrato en formato PDF o DOCX. "
            "El sistema extraerá el texto automáticamente y lo indexará para búsqueda. "
            "El documento también quedará disponible en el Editor para edición."
        )

    up = st.file_uploader("Sube un contrato (PDF o DOCX)", type=["pdf", "docx"])
    if up:
        from utils.file_parser import extract_text_from_file
        raw = up.read()
        text = extract_text_from_file(io.BytesIO(raw), up.name)

        if text and not text.startswith("Error"):
            st.success(f"✅ **{up.name}** cargado — {len(text):,} caracteres extraídos.")

            if up.name not in st.session_state.doc_versions:
                st.session_state.doc_versions[up.name] = {
                    "original": text, "draft": text, "history": []
                }
                with st.spinner("Indexando en JuanMitaChat..."):
                    ok, msg = st.session_state.chatbot.vector_ingest(
                        text, up.name, {"file_type": up.name.split(".")[-1]}
                    )
                if ok:
                    st.info(f"Indexado: {msg}")
                else:
                    st.warning(f"No se pudo indexar: {msg}")
            else:
                st.info("Documento ya indexado. Ve al **Editor** para modificarlo.")

            with st.expander("Vista previa del texto extraído"):
                st.text_area(
                    "up_prev", value=text[:3000] + ("…" if len(text) > 3000 else ""),
                    height=250, disabled=True, label_visibility="collapsed"
                )

            st.markdown(
                '<div style="padding:10px;background:#f9f5ff;border-radius:8px;'
                'border:1px solid #e0d4f7;font-size:13px;color:#555;">'
                '🔮 <b>Próximamente:</b> análisis automático de riesgos con IA — '
                'identificará partes, fechas clave, cláusulas problemáticas y nivel de riesgo.'
                '</div>',
                unsafe_allow_html=True
            )
        else:
            st.error(
                "No se pudo extraer texto del archivo. "
                "Verifica que el PDF no sea escaneado (imagen). "
                f"Error: {text}"
            )

# ─── COMPARAR CONTRATOS ───────────────────────────────────────────────────────
with tab_compare:
    hrow = st.columns([9, 1])
    hrow[0].markdown("#### Comparar contratos")
    with hrow[1].popover("ℹ️"):
        st.markdown(
            "Compara el texto de dos contratos lado a lado. "
            "Las diferencias se resaltan automáticamente. "
            "Puedes elegir contratos ya indexados o subir uno nuevo. "
            "🔮 *Próximamente: análisis comparativo con IA.*"
        )

    stats_cmp = st.session_state.chatbot.get_stats()
    all_sources = stats_cmp.get("sources", [])

    col_left, col_right = st.columns(2)

    def _get_chunks(src):
        try:
            all_docs = st.session_state.chatbot.vectorstore.get(
                include=["documents", "metadatas"]
            )
            return " ".join(
                d for d, m in zip(
                    all_docs.get("documents", []),
                    all_docs.get("metadatas", [])
                )
                if m and m.get("source") == src
            )
        except Exception:
            return ""

    with col_left:
        st.markdown("**Contrato base**")
        if not all_sources:
            st.info("No hay contratos indexados.")
            contract_left = None
            text_left = ""
        else:
            presel = st.session_state.get("cmp_preselect")
            def_idx = all_sources.index(presel) if presel and presel in all_sources else 0
            contract_left = st.selectbox("Contrato base", all_sources, index=def_idx, key="cmp_left")
            text_left = _get_chunks(contract_left) if contract_left else ""
            if text_left:
                st.text_area(
                    "text_left", value=text_left[:2500], height=300,
                    disabled=True, label_visibility="collapsed", key="ta_cmp_left"
                )

    with col_right:
        st.markdown("**Contrato a comparar**")
        modo = st.radio(
            "Origen", ["Desde indexados", "Subir archivo"],
            horizontal=True, key="cmp_modo"
        )
        contract_right = None
        text_right = ""

        if modo == "Desde indexados":
            if not all_sources:
                st.info("No hay contratos indexados.")
            else:
                contract_right = st.selectbox(
                    "Contrato a comparar", all_sources, key="cmp_right",
                    index=min(1, len(all_sources) - 1)
                )
                text_right = _get_chunks(contract_right) if contract_right else ""
                if text_right:
                    st.text_area(
                        "text_right", value=text_right[:2500], height=300,
                        disabled=True, label_visibility="collapsed", key="ta_cmp_right"
                    )
        else:
            up_cmp = st.file_uploader(
                "Sube contrato", type=["pdf", "docx"], key="cmp_upload"
            )
            if up_cmp:
                from utils.file_parser import extract_text_from_file
                text_right = extract_text_from_file(io.BytesIO(up_cmp.read()), up_cmp.name)
                contract_right = up_cmp.name
                if text_right:
                    st.text_area(
                        "text_right_up", value=text_right[:2500], height=300,
                        disabled=True, label_visibility="collapsed", key="ta_cmp_right2"
                    )

    st.markdown("---")
    if st.button("🔀 Comparar textos", type="primary", use_container_width=True):
        if not text_left or not text_right:
            st.error("Selecciona o carga ambos contratos para comparar.")
        elif contract_left == contract_right:
            st.warning("Selecciona dos contratos diferentes.")
        else:
            # Diff local con difflib
            words_a = text_left[:5000].split()
            words_b = text_right[:5000].split()
            matcher = difflib.SequenceMatcher(None, words_a, words_b)
            ratio = matcher.ratio()

            st.markdown(f"### Resultado de la comparación")
            st.markdown(f"**Base:** {contract_left}  |  **Comparado:** {contract_right}")

            similarity_pct = int(ratio * 100)
            color = "#388e3c" if similarity_pct > 70 else "#f57c00" if similarity_pct > 40 else "#e53935"
            st.markdown(
                f'<div style="padding:12px;border-left:4px solid {color};background:white;'
                f'border-radius:0 8px 8px 0;margin-bottom:16px;">'
                f'<div style="font-size:22px;font-weight:900;color:{color};">{similarity_pct}%</div>'
                f'<div style="color:#666;font-size:13px;">Similitud entre documentos</div>'
                f'</div>',
                unsafe_allow_html=True
            )

            # Mostrar diff visual
            diff_lines = list(difflib.unified_diff(
                text_left[:4000].splitlines(),
                text_right[:4000].splitlines(),
                fromfile=contract_left,
                tofile=contract_right,
                lineterm="",
                n=2
            ))
            if diff_lines:
                diff_text = "\n".join(diff_lines[:80])
                st.text_area(
                    "diff_result", value=diff_text, height=350,
                    disabled=True, label_visibility="collapsed"
                )
                st.download_button(
                    "⬇ Exportar comparación",
                    data=diff_text.encode("utf-8"),
                    file_name=f"comparacion_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain"
                )
            else:
                st.success("Los documentos son idénticos en el fragmento analizado.")

            st.markdown(
                '<div style="padding:10px;background:#f9f5ff;border-radius:8px;'
                'border:1px solid #e0d4f7;font-size:13px;color:#555;margin-top:12px;">'
                '🔮 <b>Próximamente:</b> comparación semántica con IA — identificará diferencias '
                'en cláusulas, montos, plazos y nivel de riesgo con semáforo ROJO/AMARILLO/VERDE.'
                '</div>',
                unsafe_allow_html=True
            )

# ─── EDITOR ───────────────────────────────────────────────────────────────────
with tab_editor:
    hrow = st.columns([9, 1])
    hrow[0].markdown("#### Editor de borradores")
    with hrow[1].popover("ℹ️"):
        st.markdown(
            "Edita el texto de los contratos cargados. "
            "El **original** se muestra a la izquierda (solo lectura). "
            "El **borrador** es editable y puedes guardar versiones. "
            "Usa **Restaurar original** para deshacer todos los cambios."
        )

    if not st.session_state.doc_versions:
        st.info("Carga un contrato en **Cargar Contrato** para comenzar a editar.")
    else:
        doc_sel = st.selectbox(
            "Documento a editar",
            list(st.session_state.doc_versions.keys()),
            key="editor_sel"
        )
        ver = st.session_state.doc_versions[doc_sel]
        col_orig, col_draft = st.columns(2)

        with col_orig:
            st.markdown("**📄 Original (solo lectura)**")
            st.text_area(
                "orig_ta", value=ver["original"][:4000], height=420,
                disabled=True, label_visibility="collapsed", key="ta_orig"
            )

        with col_draft:
            st.markdown("**✏️ Borrador de trabajo**")
            new_draft = st.text_area(
                "draft_ta", value=ver["draft"], height=420,
                label_visibility="collapsed", key=f"draft_{doc_sel}"
            )

        col_save, col_reset, col_export = st.columns(3)
        with col_save:
            if st.button("💾 Guardar versión", use_container_width=True):
                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                ver["history"].append({"timestamp": ts, "content": ver["draft"]})
                ver["draft"] = new_draft
                st.success(f"Versión guardada — {ts}")
                st.rerun()
        with col_reset:
            if st.button("↩ Restaurar original", use_container_width=True):
                ver["draft"] = ver["original"]
                st.rerun()
        with col_export:
            st.download_button(
                "⬇ Exportar borrador",
                data=new_draft.encode("utf-8"),
                file_name=f"BORRADOR_{doc_sel.rsplit('.', 1)[0]}.txt",
                mime="text/plain",
                use_container_width=True
            )

        # Contador de cambios
        orig_words = set(ver["original"].split())
        draft_words = set(new_draft.split())
        added = len(draft_words - orig_words)
        removed = len(orig_words - draft_words)
        if added or removed:
            st.caption(f"Cambios: **+{added}** palabras añadidas, **-{removed}** eliminadas respecto al original")
        else:
            st.caption("Sin cambios respecto al original")

# ─── HISTORIAL ────────────────────────────────────────────────────────────────
with tab_historial:
    hrow = st.columns([9, 1])
    hrow[0].markdown("#### Historial de versiones")
    with hrow[1].popover("ℹ️"):
        st.markdown(
            "Muestra todas las versiones guardadas de cada contrato editado. "
            "Puedes restaurar cualquier versión anterior haciendo clic en **Restaurar**."
        )

    has_versions = any(v.get("history") for v in st.session_state.doc_versions.values())
    if not has_versions:
        st.info("No hay versiones guardadas. Edita un contrato y guarda una versión para verla aquí.")
    else:
        for doc_name, ver in st.session_state.doc_versions.items():
            if ver.get("history"):
                st.markdown(f"#### 📝 {doc_name}")
                for i, snap in enumerate(reversed(ver["history"])):
                    with st.expander(
                        f"Versión {len(ver['history']) - i} — {snap['timestamp']}"
                    ):
                        st.text(snap["content"][:800] + ("…" if len(snap["content"]) > 800 else ""))
                        if st.button(
                            "↩ Restaurar esta versión",
                            key=f"restore_{doc_name}_{i}"
                        ):
                            ver["draft"] = snap["content"]
                            st.success("Versión restaurada. Ve al Editor para continuar.")
                            st.rerun()
