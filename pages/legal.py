import json
import streamlit as st
import io
import datetime
import difflib
from utils.shared import apply_styles, page_header, init_session_state, api_status_banner, render_document_preview

# ─── Persistencia de versiones en Drive ───────────────────────────────────────
_VERSIONS_FILENAME = "_pactora_versions.json"


def _save_versions_to_drive() -> bool:
    """Guarda doc_versions (historial) como JSON en Drive root. Retorna True si OK."""
    drive_root_id = st.session_state.get("drive_root_id", "")
    if not drive_root_id:
        return False
    try:
        from utils.auth_helper import get_drive_service
        from googleapiclient.http import MediaIoBaseUpload
        service = get_drive_service()
        if not service:
            return False

        payload = {}
        for doc_name, ver in st.session_state.doc_versions.items():
            payload[doc_name] = {
                "original": ver.get("original", "")[:50000],   # cap para no superar límite Drive
                "draft": ver.get("draft", "")[:50000],
                "history": [
                    {"timestamp": h["timestamp"], "content": h["content"][:50000]}
                    for h in ver.get("history", [])
                ],
            }

        data_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        media = MediaIoBaseUpload(io.BytesIO(data_bytes), mimetype="application/json", resumable=False)

        # Buscar si ya existe el archivo en Drive root
        query = (
            f"name='{_VERSIONS_FILENAME}' and "
            f"'{drive_root_id}' in parents and trashed=false"
        )
        results = service.files().list(
            q=query, fields="files(id)",
            supportsAllDrives=True, includeItemsFromAllDrives=True
        ).execute()
        existing = results.get("files", [])

        if existing:
            service.files().update(
                fileId=existing[0]["id"],
                media_body=media
            ).execute()
        else:
            service.files().create(
                body={"name": _VERSIONS_FILENAME, "parents": [drive_root_id]},
                media_body=media,
                fields="id",
                supportsAllDrives=True
            ).execute()
        return True
    except Exception as e:
        import logging
        logging.getLogger("pactora").warning("[versions] No se pudo guardar en Drive: %s", e)
        return False


def _load_versions_from_drive() -> bool:
    """Carga doc_versions desde Drive root si existe el archivo. Retorna True si cargó algo."""
    drive_root_id = st.session_state.get("drive_root_id", "")
    if not drive_root_id:
        return False
    if st.session_state.get("_versions_loaded_from_drive"):
        return False  # ya se cargó en esta sesión
    try:
        from utils.auth_helper import get_drive_service
        service = get_drive_service()
        if not service:
            return False

        query = (
            f"name='{_VERSIONS_FILENAME}' and "
            f"'{drive_root_id}' in parents and trashed=false"
        )
        results = service.files().list(
            q=query, fields="files(id)",
            supportsAllDrives=True, includeItemsFromAllDrives=True
        ).execute()
        found = results.get("files", [])
        if not found:
            return False

        from utils.drive_manager import _do_download
        bio = _do_download(service, found[0]["id"])
        payload = json.loads(bio.read().decode("utf-8"))

        loaded = 0
        for doc_name, ver in payload.items():
            if doc_name not in st.session_state.doc_versions:
                st.session_state.doc_versions[doc_name] = ver
                loaded += 1
            else:
                # Fusionar historial — añadir versiones que no estén ya
                existing_ts = {h["timestamp"] for h in st.session_state.doc_versions[doc_name].get("history", [])}
                for h in ver.get("history", []):
                    if h["timestamp"] not in existing_ts:
                        st.session_state.doc_versions[doc_name]["history"].append(h)

        st.session_state["_versions_loaded_from_drive"] = True
        return loaded > 0
    except Exception as e:
        import logging
        logging.getLogger("pactora").warning("[versions] No se pudo cargar desde Drive: %s", e)
        return False

apply_styles()
init_session_state()
page_header()
api_status_banner()

from core.llm_service import LLM_AVAILABLE

st.markdown("## Análisis Legal de Contratos")
_legal_caption = (
    "Análisis legal potenciado con IA (Gemini 2.5 Flash) · JuanMitaBot activo"
    if LLM_AVAILABLE else
    "Análisis local por búsqueda semántica · Activa Gemini en Ajustes para IA completa"
)
st.caption(_legal_caption)


def _detect_contract_type(name: str, text: str = "") -> str:
    """Detecta el tipo de contrato desde el nombre o texto."""
    s = (name + " " + text[:500]).upper()
    for kw, tipo in [
        ("PPA", "PPA"), ("EPC", "EPC"), ("O&M", "O&M"), ("OAM", "O&M"),
        ("SHA", "SHA"), ("NDA", "NDA"), ("ARRIENDO", "Arriendo"),
        ("FIDUCIA", "Fiducia"), ("REPRESENTACION", "Representación de Frontera"),
        ("FRONTERA", "Representación de Frontera"),
    ]:
        if kw in s:
            return tipo
    return "General"


def _render_risk_result(risk: dict):
    """Renderiza el resultado de analyze_risk() con semáforo visual."""
    nivel = risk.get("Nivel", "VERDE").upper()
    color_map = {"ROJO": ("#e53935", "🔴"), "AMARILLO": ("#f57c00", "🟡"), "VERDE": ("#388e3c", "🟢")}
    color, emoji = color_map.get(nivel, ("#915BD8", "🔵"))
    score = risk.get("compliance_score", 0)

    st.markdown(
        f'<div style="background:white;border-left:5px solid {color};border-radius:0 10px 10px 0;'
        f'padding:14px 18px;margin-bottom:12px;box-shadow:0 2px 8px rgba(0,0,0,0.07);">'
        f'<div style="font-size:22px;font-weight:900;color:{color};">'
        f'{emoji} Nivel de riesgo: {nivel}</div>'
        f'<div style="color:#555;font-size:13px;margin-top:6px;">{risk.get("summary","")}</div>'
        f'</div>',
        unsafe_allow_html=True
    )
    st.progress(score / 100, text=f"Compliance score: {score}/100")

    alertas = risk.get("Alertas", [])
    if alertas:
        st.markdown("**⚠️ Alertas:**")
        for a in alertas:
            st.markdown(f"- {a}")

    risks = risk.get("risks", [])
    if risks:
        st.markdown("**Detalle por cláusula:**")
        for r in risks:
            lvl = r.get("level", "Verde").capitalize()
            c2, e2 = color_map.get(lvl.upper(), ("#915BD8", "🔵"))
            st.markdown(
                f'<div style="background:#fafafa;border-left:3px solid {c2};'
                f'padding:8px 12px;margin:4px 0;border-radius:0 6px 6px 0;font-size:13px;">'
                f'<b>{e2} {r.get("clause","")}</b> — {r.get("reason","")}<br>'
                f'<span style="color:#915BD8;">→ {r.get("action","")}</span></div>',
                unsafe_allow_html=True
            )

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab_biblioteca, tab_dashboard, tab_upload, tab_compare, tab_editor, tab_historial = st.tabs([
    "📚 Biblioteca",
    "📊 Dashboard",
    "📤 Cargar Contrato",
    "🔀 Comparar",
    "✏️ Editor",
    "🕓 Historial",
])

# ─── BIBLIOTECA ───────────────────────────────────────────────────────────────
def _get_chunks_for(src):
    try:
        all_docs = st.session_state.chatbot.vectorstore.get(include=["documents", "metadatas"])
        return [d for d, m in zip(all_docs.get("documents", []), all_docs.get("metadatas", []))
                if m and m.get("source") == src]
    except Exception:
        return []

with tab_biblioteca:
    stats = st.session_state.chatbot.get_stats()
    sources = stats.get("sources", [])

    selected_src = st.session_state.get("library_selected")

    # ── MODO SPLIT VIEW (documento seleccionado) ───────────────────────────────
    if selected_src and selected_src in sources:
        nav_cols = st.columns([1, 8, 1])
        if nav_cols[0].button("← Volver", key="bib_back"):
            del st.session_state["library_selected"]
            st.rerun()
        ext_sel = selected_src.lower().split(".")[-1] if "." in selected_src else ""
        icon_sel = "📄" if ext_sel == "pdf" else "📝"
        nav_cols[1].markdown(f"**{icon_sel} {selected_src}**")
        if nav_cols[2].button("Comparar →", key="bib_to_cmp"):
            st.session_state["cmp_preselect"] = selected_src
            st.toast(f"'{selected_src[:40]}' preseleccionado para comparar", icon="✅")

        col_doc, col_chat = st.columns([3, 2], gap="medium")

        # ── Panel izquierdo: documento ─────────────────────────────────────────
        with col_doc:
            st.markdown("##### Documento")
            render_document_preview(selected_src, height=660)

        # ── Panel derecho: chat contextualizado ────────────────────────────────
        with col_chat:
            st.markdown("##### 💬 JuanMitaBot — sobre este contrato")
            chat_sk = f"doc_chat_{selected_src}"
            if chat_sk not in st.session_state:
                st.session_state[chat_sk] = []
            doc_hist = st.session_state[chat_sk]

            # Historial
            chat_box = st.container(height=530)
            with chat_box:
                if not doc_hist:
                    st.markdown(
                        '<div style="color:#aaa;text-align:center;margin-top:120px;font-size:13px;">'
                        '🤖 Pregunta cualquier cosa<br>sobre este contrato específico</div>',
                        unsafe_allow_html=True
                    )
                for msg in doc_hist:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

            # Input como form para evitar conflicto con sidebar chat_input
            with st.form(key=f"doc_chat_form", clear_on_submit=True):
                doc_q = st.text_input(
                    "Pregunta", placeholder="¿Cuáles son las partes del contrato?",
                    label_visibility="collapsed"
                )
                sent = st.form_submit_button("Enviar →", width="stretch")

            if sent and doc_q:
                st.session_state[chat_sk].append({"role": "user", "content": doc_q})
                try:
                    with st.spinner("Analizando..."):
                        ans = st.session_state.chatbot.ask_question(
                            doc_q,
                            filter_metadata={"source": selected_src}
                        )
                except Exception as _ce:
                    ans = f"⚠️ Error: {_ce}"
                st.session_state[chat_sk].append({"role": "assistant", "content": ans})
                # Actualizar contexto del sidebar también
                st.session_state["sidebar_chat_filter"] = {"source": selected_src}
                st.session_state["sidebar_chat_title"] = selected_src
                st.rerun()

            if doc_hist:
                if st.button("🗑 Limpiar chat", key="clear_doc_chat"):
                    st.session_state[chat_sk] = []
                    st.rerun()

            # ── Análisis de riesgos con IA ────────────────────────────────────
            st.markdown("---")
            st.markdown("##### 🔍 Análisis de Riesgos")
            risk_key = f"risk_{selected_src}"
            cached_risk = st.session_state.get(risk_key)

            if cached_risk:
                _render_risk_result(cached_risk)
                if st.button("🔄 Re-analizar", key="reanalyze_risk", width="stretch"):
                    del st.session_state[risk_key]
                    st.rerun()
            else:
                btn_label = "🔍 Analizar riesgos con IA" if LLM_AVAILABLE else "📊 Analizar riesgos (local)"
                if st.button(btn_label, key="analyze_risk_btn", width="stretch", type="primary"):
                    chunks = _get_chunks_for(selected_src)
                    full_text = "\n".join(chunks)
                    if full_text:
                        with st.spinner("Analizando riesgos..."):
                            from core.llm_service import analyze_risk
                            contract_type = _detect_contract_type(selected_src, full_text)
                            risk_result = analyze_risk(full_text, contract_type)
                        st.session_state[risk_key] = risk_result
                        st.rerun()
                    else:
                        st.warning("Sin texto disponible para analizar.")

    # ── MODO LISTA ─────────────────────────────────────────────────────────────
    else:
        hrow = st.columns([9, 1])
        hrow[0].markdown("#### Contratos indexados")
        with hrow[1].popover("ℹ️"):
            st.markdown(
                "Haz clic en **Abrir** para ver el documento y chatear con JuanMitaBot "
                "sobre ese contrato específico. Los PDFs subidos en esta sesión se "
                "muestran como previsualización nativa; los demás muestran el texto extraído."
            )

        if not sources:
            st.info("No hay contratos indexados. Usa la pestaña **Cargar Contrato** o ve a **Ajustes**.")
        else:
            search = st.text_input(
                "buscar_bib", placeholder="🔍 Filtrar contratos...",
                label_visibility="collapsed", key="bib_search"
            )
            filtered_s = [s for s in sources if search.lower() in s.lower()] if search else sources
            st.caption(f"{len(filtered_s)} contrato(s)")

            for src in filtered_s:
                cols = st.columns([5, 1, 1])
                ext = src.lower().split(".")[-1] if "." in src else ""
                icon = "📄" if ext == "pdf" else "📝"
                has_pdf = src in st.session_state.get("_file_cache", {})
                label = f"**{icon} {src}**" + (" `PDF`" if has_pdf else "")
                cols[0].markdown(label)

                if cols[1].button("Abrir", key=f"bopen_{src}", width="stretch"):
                    st.session_state["library_selected"] = src
                    st.session_state["sidebar_chat_filter"] = {"source": src}
                    st.session_state["sidebar_chat_title"] = src
                    st.rerun()

                if cols[2].button("Comparar", key=f"bcmp_{src}", width="stretch"):
                    st.session_state["cmp_preselect"] = src
                    st.toast(f"'{src[:40]}' preseleccionado", icon="✅")

                st.divider()

# ─── DASHBOARD ────────────────────────────────────────────────────────────────
with tab_dashboard:
    import pandas as _pd_dash

    hrow = st.columns([9, 1])
    hrow[0].markdown("#### Dashboard de Contratos")
    with hrow[1].popover("ℹ️"):
        st.markdown(
            "Tabla filtrable con todos los contratos indexados. "
            "Filtra por tipo, formato o búsqueda de texto. "
            "Haz clic en **Abrir** para ir al detalle en Biblioteca."
        )

    _dash_stats = st.session_state.chatbot.get_stats()
    _dash_sources = _dash_stats.get("sources", [])

    if not _dash_sources:
        st.info("No hay contratos indexados. Usa **Cargar Contrato** o ve a **Ajustes**.")
    else:
        # Construir tabla de contratos
        _dash_rows = []
        _risk_cache = {}  # Reutilizar análisis de riesgo ya cacheados en session
        for src in _dash_sources:
            ext = src.lower().rsplit(".", 1)[-1] if "." in src else "?"
            tipo = _detect_contract_type(src)
            risk_key = f"risk_{src}"
            risk_data = st.session_state.get(risk_key)
            risk_nivel = risk_data.get("Nivel", "—").upper() if risk_data else "—"
            risk_score = risk_data.get("compliance_score", "—") if risk_data else "—"
            # Leer metadata del vectorstore (drive_id, indexed_at)
            indexed_at = "—"
            try:
                from utils.shared import _load_index_metadata
                _imeta = _load_index_metadata()
                if src in _imeta:
                    dt_str = _imeta[src].get("indexed_at", "")
                    if dt_str:
                        indexed_at = dt_str[:10]  # YYYY-MM-DD
            except Exception:
                pass
            _dash_rows.append({
                "Contrato": src,
                "Tipo": tipo,
                "Formato": ext.upper(),
                "Riesgo": risk_nivel,
                "Score": risk_score,
                "Indexado": indexed_at,
            })

        df_dash = _pd_dash.DataFrame(_dash_rows)

        # ── Filtros ─────────────────────────────────────────────────────────
        fcols = st.columns([3, 2, 2, 3])
        with fcols[0]:
            _search_d = st.text_input("Buscar", placeholder="🔍 Nombre del contrato...",
                                      label_visibility="collapsed", key="dash_search")
        with fcols[1]:
            _tipos_uniq = ["Todos"] + sorted(df_dash["Tipo"].unique().tolist())
            _tipo_filter = st.selectbox("Tipo", _tipos_uniq, key="dash_tipo")
        with fcols[2]:
            _fmts_uniq = ["Todos"] + sorted(df_dash["Formato"].unique().tolist())
            _fmt_filter = st.selectbox("Formato", _fmts_uniq, key="dash_fmt")
        with fcols[3]:
            _risk_opts = ["Todos", "ROJO", "AMARILLO", "VERDE", "—"]
            _risk_filter = st.selectbox("Riesgo", _risk_opts, key="dash_risk")

        # Aplicar filtros
        df_filt = df_dash.copy()
        if _search_d:
            df_filt = df_filt[df_filt["Contrato"].str.contains(_search_d, case=False, na=False)]
        if _tipo_filter != "Todos":
            df_filt = df_filt[df_filt["Tipo"] == _tipo_filter]
        if _fmt_filter != "Todos":
            df_filt = df_filt[df_filt["Formato"] == _fmt_filter]
        if _risk_filter != "Todos":
            df_filt = df_filt[df_filt["Riesgo"] == _risk_filter]

        st.caption(f"{len(df_filt)} contrato(s) — {len(_dash_sources)} total")

        # ── Tabla con botón Abrir ────────────────────────────────────────────
        RISK_EMOJI = {"ROJO": "🔴", "AMARILLO": "🟡", "VERDE": "🟢"}
        FMT_ICON = {"PDF": "📄", "DOCX": "📝", "XLSX": "📊", "PPTX": "📑",
                    "PNG": "🖼", "JPG": "🖼", "CSV": "📋", "TXT": "📃"}

        for _, row in df_filt.iterrows():
            dcols = st.columns([5, 1, 1, 1, 1, 1])
            fmt_icon = FMT_ICON.get(row["Formato"], "📁")
            risk_emoji = RISK_EMOJI.get(row["Riesgo"], "⚪")
            dcols[0].markdown(f"{fmt_icon} **{row['Contrato']}**")
            dcols[1].markdown(f'<div style="font-size:12px;color:#555;">{row["Tipo"]}</div>', unsafe_allow_html=True)
            dcols[2].markdown(f'<div style="font-size:12px;color:#555;">{row["Formato"]}</div>', unsafe_allow_html=True)
            dcols[3].markdown(f'<div style="text-align:center;">{risk_emoji}</div>', unsafe_allow_html=True)
            dcols[4].markdown(f'<div style="font-size:11px;color:#888;">{row["Indexado"]}</div>', unsafe_allow_html=True)
            if dcols[5].button("Abrir", key=f"dash_open_{row['Contrato']}", width="stretch"):
                st.session_state["library_selected"] = row["Contrato"]
                st.session_state["sidebar_chat_filter"] = {"source": row["Contrato"]}
                st.session_state["sidebar_chat_title"] = row["Contrato"]
                # Navegar a la pestaña Biblioteca seleccionando el documento
                st.toast(f"Abriendo '{row['Contrato'][:40]}' en Biblioteca", icon="📚")
                st.rerun()
            st.divider()

        # ── KPIs resumen ─────────────────────────────────────────────────────
        st.markdown("---")
        kpi_cols = st.columns(4)
        kpi_cols[0].metric("Total contratos", len(_dash_sources))
        tipos_count = df_dash["Tipo"].value_counts()
        kpi_cols[1].metric("Tipos distintos", len(tipos_count))
        formatos_count = df_dash["Formato"].value_counts()
        kpi_cols[2].metric("Formatos distintos", len(formatos_count))
        analizados = df_dash[df_dash["Riesgo"] != "—"].shape[0]
        kpi_cols[3].metric("Con análisis de riesgo", analizados)

        # Desglose por formato
        if len(formatos_count) > 1:
            with st.expander("Desglose por formato"):
                fmt_html = '<div style="display:flex;flex-wrap:wrap;gap:8px;">'
                for fmt, cnt in formatos_count.items():
                    icon = FMT_ICON.get(fmt, "📁")
                    fmt_html += (
                        f'<div style="background:#f5f0ff;border-radius:8px;padding:8px 14px;'
                        f'text-align:center;min-width:70px;">'
                        f'<div style="font-size:20px;">{icon}</div>'
                        f'<div style="font-weight:700;color:#915BD8;">{cnt}</div>'
                        f'<div style="font-size:11px;color:#555;">{fmt}</div></div>'
                    )
                fmt_html += "</div>"
                st.markdown(fmt_html, unsafe_allow_html=True)


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
        # Cachear PDF para previsualización
        if up.name.lower().endswith(".pdf") and len(raw) <= 10 * 1024 * 1024:
            if "_file_cache" not in st.session_state:
                st.session_state["_file_cache"] = {}
            st.session_state["_file_cache"][up.name] = raw
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

            with st.expander("Vista previa del documento", expanded=True):
                render_document_preview(up.name, height=500)

            st.markdown("---")
            st.markdown("##### 🔍 Análisis de Riesgos")
            _up_risk_key = f"risk_{up.name}"
            if st.session_state.get(_up_risk_key):
                _render_risk_result(st.session_state[_up_risk_key])
                if st.button("🔄 Re-analizar", key="up_reanalyze"):
                    del st.session_state[_up_risk_key]
                    st.rerun()
            else:
                _btn_lbl = "🔍 Analizar riesgos con IA" if LLM_AVAILABLE else "📊 Analizar riesgos (local)"
                if st.button(_btn_lbl, key="up_analyze_risk", width="stretch", type="primary"):
                    with st.spinner("Analizando riesgos..."):
                        from core.llm_service import analyze_risk
                        _ct = _detect_contract_type(up.name, text)
                        st.session_state[_up_risk_key] = analyze_risk(text, _ct)
                    st.rerun()
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
            + ("✨ Análisis comparativo con IA disponible." if LLM_AVAILABLE else "Activa Gemini para análisis IA de diferencias.")
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
                _safe = text_left[:2500].replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                st.markdown(
                    f'<div style="height:300px;overflow-y:auto;padding:14px 16px;'
                    f'background:#fff;border:1px solid #e0e0e0;border-radius:8px;'
                    f'font-size:12.5px;line-height:1.65;color:#333;white-space:pre-wrap;">'
                    f'{_safe}</div>',
                    unsafe_allow_html=True
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
                    _safe_r = text_right[:2500].replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                    st.markdown(
                        f'<div style="height:300px;overflow-y:auto;padding:14px 16px;'
                        f'background:#fff;border:1px solid #e0e0e0;border-radius:8px;'
                        f'font-size:12.5px;line-height:1.65;color:#333;white-space:pre-wrap;">'
                        f'{_safe_r}</div>',
                        unsafe_allow_html=True
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
                    _safe_ru = text_right[:2500].replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                    st.markdown(
                        f'<div style="height:300px;overflow-y:auto;padding:14px 16px;'
                        f'background:#fff;border:1px solid #e0e0e0;border-radius:8px;'
                        f'font-size:12.5px;line-height:1.65;color:#333;white-space:pre-wrap;">'
                        f'{_safe_ru}</div>',
                        unsafe_allow_html=True
                    )

    st.markdown("---")
    if st.button("🔀 Comparar textos", type="primary", width="stretch"):
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

            # ── Análisis IA de diferencias ─────────────────────────────────────
            st.markdown("---")
            _cmp_key = f"cmp_ia_{contract_left}_{contract_right}"
            if st.session_state.get(_cmp_key):
                st.markdown("#### 🤖 Análisis IA de diferencias")
                st.markdown(
                    f'<div style="background:white;border-left:4px solid #915BD8;border-radius:0 10px 10px 0;'
                    f'padding:14px 18px;box-shadow:0 2px 8px rgba(0,0,0,0.07);">'
                    f'{st.session_state[_cmp_key]}</div>',
                    unsafe_allow_html=True
                )
                if st.button("🔄 Re-analizar con IA", key="cmp_reanalyze"):
                    del st.session_state[_cmp_key]
                    st.rerun()
            elif LLM_AVAILABLE:
                if st.button("🤖 Analizar diferencias con IA", key="cmp_ia_btn", width="stretch", type="primary"):
                    with st.spinner("Analizando diferencias con IA..."):
                        from core.llm_service import generate_response
                        _cmp_prompt = (
                            f"Compara estos dos contratos y genera:\n"
                            f"1. Tabla de diferencias clave (cláusulas, montos, plazos)\n"
                            f"2. Cláusulas presentes en uno pero ausentes en el otro\n"
                            f"3. Cuál tiene mayor riesgo y por qué (semáforo 🔴🟡🟢)\n\n"
                            f"**Contrato base ({contract_left}):**\n{text_left[:4000]}\n\n"
                            f"**Contrato comparado ({contract_right}):**\n{text_right[:4000]}"
                        )
                        _cmp_ctx = f"[Fuente: {contract_left}]\n{text_left[:3000]}\n\n[Fuente: {contract_right}]\n{text_right[:3000]}"
                        _ia_result = generate_response(_cmp_prompt, _cmp_ctx)
                    if _ia_result:
                        st.session_state[_cmp_key] = _ia_result
                        st.rerun()
            else:
                st.caption("📊 Activa Gemini en Ajustes para obtener análisis IA de diferencias entre contratos.")

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

    # Importar borrador generado desde Plantillas (si se usó "Abrir en Editor")
    if st.session_state.get("draft_content") and st.session_state.get("draft_filename"):
        draft_fn = st.session_state.pop("draft_filename")
        draft_ct = st.session_state.pop("draft_content")
        if draft_fn not in st.session_state.doc_versions:
            st.session_state.doc_versions[draft_fn] = {
                "original": draft_ct, "draft": draft_ct, "history": []
            }
            st.toast(f"Borrador '{draft_fn}' cargado desde Plantillas.", icon="✅")

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
            if st.button("💾 Guardar versión", width="stretch", key="btn_save_ver"):
                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                ver["history"].append({"timestamp": ts, "content": ver["draft"]})
                ver["draft"] = new_draft
                saved_to_drive = _save_versions_to_drive()
                drive_note = " · guardado en Drive ☁️" if saved_to_drive else ""
                st.toast(f"Versión guardada — {ts}{drive_note}", icon="💾")
                st.rerun()
        with col_reset:
            if st.button("↩ Restaurar original", width="stretch", key="btn_reset_ver"):
                ver["draft"] = ver["original"]
                st.rerun()
        with col_export:
            st.download_button(
                "⬇ Exportar borrador",
                data=new_draft.encode("utf-8"),
                file_name=f"BORRADOR_{doc_sel.rsplit('.', 1)[0]}.txt",
                mime="text/plain",
                width="stretch",
                key="btn_export_draft"
            )

        # ─── Diff visual línea a línea ────────────────────────────────────────
        orig_lines = ver["original"].splitlines()
        draft_lines = new_draft.splitlines()
        diff_lines = list(difflib.unified_diff(
            orig_lines, draft_lines,
            fromfile="Original", tofile="Borrador",
            lineterm="", n=1
        ))

        if not diff_lines:
            st.caption("Sin cambios respecto al original.")
        else:
            # Estadísticas rápidas
            added_lines = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
            removed_lines = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))
            st.caption(
                f"Cambios: "
                f"**+{added_lines}** línea(s) añadida(s) · "
                f"**-{removed_lines}** línea(s) eliminada(s)"
            )
            with st.expander("Ver diff detallado (Original → Borrador)", expanded=False):
                html_rows = []
                for line in diff_lines:
                    esc = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    if line.startswith("+") and not line.startswith("+++"):
                        html_rows.append(
                            f'<div style="background:#e8f5e9;color:#1b5e20;'
                            f'font-family:monospace;font-size:12px;padding:1px 8px;'
                            f'white-space:pre-wrap;">{esc}</div>'
                        )
                    elif line.startswith("-") and not line.startswith("---"):
                        html_rows.append(
                            f'<div style="background:#ffebee;color:#b71c1c;'
                            f'font-family:monospace;font-size:12px;padding:1px 8px;'
                            f'white-space:pre-wrap;">{esc}</div>'
                        )
                    elif line.startswith("@@"):
                        html_rows.append(
                            f'<div style="background:#e3f2fd;color:#0d47a1;'
                            f'font-family:monospace;font-size:12px;padding:1px 8px;">{esc}</div>'
                        )
                    else:
                        html_rows.append(
                            f'<div style="font-family:monospace;font-size:12px;'
                            f'padding:1px 8px;color:#555;white-space:pre-wrap;">{esc}</div>'
                        )
                st.markdown(
                    '<div style="border:1px solid #e0e0e0;border-radius:8px;'
                    'overflow-y:auto;max-height:380px;">'
                    + "".join(html_rows) + "</div>",
                    unsafe_allow_html=True
                )
                # Exportar diff como parche unificado
                diff_text = "\n".join(diff_lines)
                st.download_button(
                    "⬇ Exportar diff (.patch)",
                    data=diff_text.encode("utf-8"),
                    file_name=f"diff_{doc_sel.rsplit('.', 1)[0]}_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.patch",
                    mime="text/plain",
                    key="btn_export_diff"
                )

# ─── HISTORIAL ────────────────────────────────────────────────────────────────
with tab_historial:
    hrow = st.columns([9, 1])
    hrow[0].markdown("#### Historial de versiones")
    with hrow[1].popover("ℹ️"):
        st.markdown(
            "Muestra todas las versiones guardadas de cada contrato editado. "
            "Puedes restaurar cualquier versión anterior o comparar dos versiones. "
            "Las versiones se sincronizan automáticamente en Google Drive si está conectado."
        )

    # Auto-cargar versiones desde Drive (solo una vez por sesión)
    if st.session_state.get("drive_root_id") and not st.session_state.get("_versions_loaded_from_drive"):
        with st.spinner("Sincronizando versiones desde Drive..."):
            loaded = _load_versions_from_drive()
        if loaded:
            st.toast("Versiones restauradas desde Drive ☁️", icon="📂")

    # Botón manual de sync
    sync_col, _ = st.columns([2, 8])
    with sync_col:
        if st.session_state.get("drive_root_id"):
            if st.button("☁️ Sincronizar con Drive", width="stretch", key="btn_sync_versions"):
                saved = _save_versions_to_drive()
                st.toast("Versiones guardadas en Drive ☁️" if saved else "No se pudo sincronizar con Drive", icon="☁️" if saved else "⚠️")

    has_versions = any(v.get("history") for v in st.session_state.doc_versions.values())
    if not has_versions:
        st.markdown(
            '<div style="text-align:center;padding:40px;color:#999;">'
            '<div style="font-size:40px;">🕓</div>'
            '<div style="font-size:15px;margin-top:8px;">No hay versiones guardadas.</div>'
            '<div style="font-size:13px;margin-top:4px;">Edita un contrato en el <b>Editor</b> '
            'y presiona "Guardar versión".</div>'
            '</div>',
            unsafe_allow_html=True
        )
    else:
        for doc_name, ver in st.session_state.doc_versions.items():
            history = ver.get("history", [])
            if not history:
                continue
            st.markdown(f"#### 📝 {doc_name}")
            st.caption(f"{len(history)} versión(es) guardada(s)")

            for i, snap in enumerate(reversed(history)):
                ver_num = len(history) - i
                with st.expander(f"Versión {ver_num} — {snap['timestamp']}"):
                    col_prev, col_diff = st.columns([3, 2])
                    with col_prev:
                        st.text_area(
                            f"snap_prev_{doc_name}_{i}",
                            value=snap["content"][:1200] + ("…" if len(snap["content"]) > 1200 else ""),
                            height=200, disabled=True, label_visibility="collapsed"
                        )
                    with col_diff:
                        # Diff vs versión anterior (o vs original si es v1)
                        if i < len(history) - 1:
                            prev_snap = history[len(history) - i - 2]
                            prev_label = f"v{ver_num - 1}"
                            prev_content = prev_snap["content"]
                        else:
                            prev_label = "original"
                            prev_content = ver.get("original", "")

                        diff_snap = list(difflib.unified_diff(
                            prev_content.splitlines(),
                            snap["content"].splitlines(),
                            fromfile=prev_label, tofile=f"v{ver_num}",
                            lineterm="", n=1
                        ))
                        if diff_snap:
                            added_s = sum(1 for l in diff_snap if l.startswith("+") and not l.startswith("+++"))
                            removed_s = sum(1 for l in diff_snap if l.startswith("-") and not l.startswith("---"))
                            st.markdown(
                                f'<div style="background:#f5f5f5;border-radius:8px;padding:8px;">'
                                f'<div style="font-size:12px;color:#666;margin-bottom:6px;">'
                                f'vs {prev_label}: '
                                f'<span style="color:#388e3c;">+{added_s}</span> / '
                                f'<span style="color:#e53935;">-{removed_s}</span> líneas</div>'
                                + "".join(
                                    f'<div style="font-family:monospace;font-size:11px;'
                                    f'padding:1px 4px;white-space:pre-wrap;'
                                    f'background:{"#e8f5e9" if l.startswith("+") and not l.startswith("+++") else "#ffebee" if l.startswith("-") and not l.startswith("---") else "transparent"};'
                                    f'color:{"#1b5e20" if l.startswith("+") and not l.startswith("+++") else "#b71c1c" if l.startswith("-") and not l.startswith("---") else "#555"};">'
                                    f'{l.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")}</div>'
                                    for l in diff_snap[:30]
                                )
                                + ("…" if len(diff_snap) > 30 else "")
                                + "</div>",
                                unsafe_allow_html=True
                            )
                        else:
                            st.caption(f"Sin cambios vs {prev_label}")

                    if st.button("↩ Restaurar esta versión", key=f"restore_{doc_name}_{i}"):
                        ver["draft"] = snap["content"]
                        st.toast("Versión restaurada. Ve al Editor para continuar.", icon="✅")
                        st.rerun()

            st.divider()
