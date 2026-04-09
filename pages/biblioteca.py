import streamlit as st
from utils.shared import apply_styles, page_header, init_session_state, render_document_preview
from utils.auth import get_current_user, filter_sources_for_user
from utils.indexing import _load_index_metadata

apply_styles()
init_session_state()
page_header()

# ── Helpers de clasificación ───────────────────────────────────────────────────
_INVERSIONISTAS = [
    ("SUNO", "Suno Energy"), ("SOLENIUM", "Solenium"), ("UNERGY", "Unergy"),
    ("ENEL", "Enel"), ("CELSIA", "Celsia"), ("ISAGEN", "Isagen"),
    ("EPM", "EPM"), ("ALPINA", "Alpina"), ("BANCOLOMBIA", "Bancolombia"),
    ("DAVIVIENDA", "Davivienda"), ("SURA", "Sura"), ("NUTRESA", "Nutresa"),
]
_TIPOS_CONTRACTUALES = {"PPA", "EPC", "O&M", "SHA", "NDA", "Rep. Frontera", "Arriendo", "Fiducia"}
_TIPOS_CORPORATIVOS  = {"Acta", "Poder"}

_FMT_ICON = {"pdf": "📄", "docx": "📝", "xlsx": "📊", "pptx": "📑", "csv": "📋", "txt": "🗒️"}

def _get_inversionista(name: str) -> str:
    u = name.upper()
    for kw, label in _INVERSIONISTAS:
        if kw in u:
            return label
    return "Otro"

def _get_categoria(contract_type: str) -> str:
    if contract_type in _TIPOS_CORPORATIVOS:
        return "Corporativo"
    if contract_type in _TIPOS_CONTRACTUALES:
        return "Contractual"
    return "General"

def _fmt_size(n) -> str:
    try:
        n = int(n)
        return f"{n/1024:.0f} KB" if n < 1_048_576 else f"{n/1_048_576:.1f} MB"
    except Exception:
        return ""

# ── Cargar datos enriquecidos ──────────────────────────────────────────────────
user    = get_current_user()
stats   = st.session_state.chatbot.get_stats()
sources = filter_sources_for_user(stats.get("sources", []), user)
meta_json = _load_index_metadata()   # {filename: {ext, indexed_at, size, contract_type}}

# Obtener contract_type desde ChromaDB registry (más preciso que el JSON)
registry_map: dict = {}
if hasattr(st.session_state.chatbot, "get_contract_registry"):
    for r in st.session_state.chatbot.get_contract_registry():
        registry_map[r["source"]] = r

# Construir lista unificada de documentos
docs_data = []
for src in sources:
    jm   = meta_json.get(src, {})
    rm   = registry_map.get(src, {})
    ext  = jm.get("ext", src.rsplit(".", 1)[-1].lower() if "." in src else "")
    ct   = rm.get("contract_type") or jm.get("contract_type", "General")
    docs_data.append({
        "source":       src,
        "ext":          ext,
        "icon":         _FMT_ICON.get(ext, "📁"),
        "contract_type": ct,
        "categoria":    _get_categoria(ct),
        "inversionista": _get_inversionista(src),
        "indexed_at":   jm.get("indexed_at", ""),
        "size":         jm.get("size", 0),
    })

selected_src = st.session_state.get("biblioteca_selected")

# ══════════════════════════════════════════════════════════════════════════════
# MODO VISOR — documento abierto
# ══════════════════════════════════════════════════════════════════════════════
if selected_src and selected_src in sources:
    nav = st.columns([1, 8, 1, 1])
    if nav[0].button("← Atrás", key="bib_back"):
        del st.session_state["biblioteca_selected"]
        st.rerun()
    doc_meta = next((d for d in docs_data if d["source"] == selected_src), {})
    nav[1].markdown(
        f"**{doc_meta.get('icon','📄')} {selected_src}** &nbsp;"
        f"<span style='background:#e8eaf6;border-radius:4px;padding:2px 8px;"
        f"font-size:12px;'>{doc_meta.get('contract_type','')}</span>",
        unsafe_allow_html=True,
    )
    if nav[2].button("⚖ Analizar", key="bib_to_legal"):
        st.session_state["library_selected"] = selected_src
        st.switch_page("pages/legal.py")
    if nav[3].button("💬 Chat", key="bib_toggle_chat"):
        st.session_state["bib_show_chat"] = not st.session_state.get("bib_show_chat", True)

    show_chat = st.session_state.get("bib_show_chat", True)
    if show_chat:
        col_doc, col_chat = st.columns([3, 2], gap="medium")
    else:
        col_doc = st.container()
        col_chat = None

    with col_doc:
        render_document_preview(selected_src, height=680)

    if show_chat and col_chat:
        with col_chat:
            st.markdown("##### 💬 JuanMitaBot — sobre este documento")
            chat_sk = f"bib_chat_{selected_src}"
            if chat_sk not in st.session_state:
                st.session_state[chat_sk] = []
            doc_hist = st.session_state[chat_sk]

            with st.container(height=540):
                if not doc_hist:
                    st.markdown(
                        '<div style="color:#aaa;text-align:center;margin-top:130px;font-size:13px;">'
                        '🤖 Pregunta cualquier cosa<br>sobre este documento</div>',
                        unsafe_allow_html=True,
                    )
                for msg in doc_hist:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

            with st.form("bib_chat_form", clear_on_submit=True):
                doc_q = st.text_input("Pregunta", placeholder="¿Qué dice sobre...?",
                                      label_visibility="collapsed")
                if st.form_submit_button("Enviar →", width="stretch") and doc_q:
                    st.session_state[chat_sk].append({"role": "user", "content": doc_q})
                    with st.spinner("Consultando..."):
                        answer = st.session_state.chatbot.ask_question(
                            doc_q,
                            filter_metadata={"source": selected_src},
                            chat_history=doc_hist,
                        )
                    st.session_state[chat_sk].append({"role": "assistant", "content": answer})
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# MODO EXPLORADOR
# ══════════════════════════════════════════════════════════════════════════════
else:
    st.markdown("## 📁 Biblioteca de Documentos")

    if not docs_data:
        st.info("No hay documentos indexados. Ve a **Ajustes** para cargar archivos.")
        st.stop()

    # ── Barra de filtros ──────────────────────────────────────────────────────
    all_tipos  = ["Todos"] + sorted(set(d["contract_type"] for d in docs_data))
    all_fmts   = ["Todos"] + sorted(set(d["ext"].upper() for d in docs_data if d["ext"]))
    all_cats   = ["Todas"] + sorted(set(d["categoria"] for d in docs_data))
    all_inv    = ["Todos"] + sorted(set(d["inversionista"] for d in docs_data))

    f1, f2, f3, f4, f5, fv = st.columns([3, 2, 2, 2, 2, 1])
    with f1:
        search = st.text_input("Buscar", placeholder="🔍 Nombre del documento...",
                               label_visibility="collapsed", key="bib_q")
    with f2:
        ftipo = st.selectbox("Tipo", all_tipos, label_visibility="collapsed", key="bib_ftipo")
    with f3:
        ffmt  = st.selectbox("Formato", all_fmts, label_visibility="collapsed", key="bib_ffmt")
    with f4:
        fcat  = st.selectbox("Categoría", all_cats, label_visibility="collapsed", key="bib_fcat")
    with f5:
        finv  = st.selectbox("Entidad", all_inv, label_visibility="collapsed", key="bib_finv")
    with fv:
        view_mode = st.selectbox("Vista", ["▦ Grid", "☰ Lista"],
                                 label_visibility="collapsed", key="bib_view")

    # Aplicar filtros
    filtered = docs_data
    if search:
        filtered = [d for d in filtered if search.lower() in d["source"].lower()]
    if ftipo != "Todos":
        filtered = [d for d in filtered if d["contract_type"] == ftipo]
    if ffmt != "Todos":
        filtered = [d for d in filtered if d["ext"].upper() == ffmt]
    if fcat != "Todas":
        filtered = [d for d in filtered if d["categoria"] == fcat]
    if finv != "Todos":
        filtered = [d for d in filtered if d["inversionista"] == finv]

    # Ordenar
    sort_col, sort_dir = st.columns([2, 1])
    with sort_col:
        sort_by = st.selectbox("Ordenar por", ["Nombre", "Fecha", "Tipo", "Formato"],
                               label_visibility="collapsed", key="bib_sort")
    with sort_dir:
        sort_asc = st.selectbox("↕", ["↑ Asc", "↓ Desc"],
                                label_visibility="collapsed", key="bib_sortdir")

    rev = sort_asc == "↓ Desc"
    if sort_by == "Nombre":
        filtered = sorted(filtered, key=lambda d: d["source"].lower(), reverse=rev)
    elif sort_by == "Fecha":
        filtered = sorted(filtered, key=lambda d: d["indexed_at"], reverse=rev)
    elif sort_by == "Tipo":
        filtered = sorted(filtered, key=lambda d: d["contract_type"], reverse=rev)
    elif sort_by == "Formato":
        filtered = sorted(filtered, key=lambda d: d["ext"], reverse=rev)

    st.caption(f"{len(filtered)} de {len(docs_data)} documento(s)")

    # ── CSS para cards ────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .bib-card {
        background: var(--background-color, #fff);
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 4px;
        transition: box-shadow .15s;
    }
    .bib-card:hover { box-shadow: 0 2px 10px rgba(145,91,216,.18); }
    .bib-badge {
        display: inline-block;
        border-radius: 4px;
        padding: 1px 8px;
        font-size: 11px;
        font-weight: 600;
        margin-right: 4px;
    }
    .bib-name {
        font-size: 13px;
        font-weight: 600;
        word-break: break-word;
        margin: 6px 0 4px 0;
    }
    .bib-meta { font-size: 11px; color: #888; margin-top: 2px; }
    </style>
    """, unsafe_allow_html=True)

    _TIPO_BG = {
        "PPA": "#e3f2fd", "EPC": "#e8f5e9", "O&M": "#fff3e0",
        "SHA": "#fce4ec", "NDA": "#f3e5f5", "Acta": "#e0f7fa",
        "Poder": "#fafafa", "Arriendo": "#fffde7", "Fiducia": "#f9fbe7",
        "Rep. Frontera": "#efebe9", "General": "#f5f5f5",
    }
    _TIPO_TXT = {
        "PPA": "#1565C0", "EPC": "#2E7D32", "O&M": "#E65100",
        "SHA": "#880E4F", "NDA": "#6A1B9A", "Acta": "#00695C",
        "Poder": "#424242", "Arriendo": "#F57F17", "Fiducia": "#558B2F",
        "Rep. Frontera": "#4E342E", "General": "#616161",
    }

    def _badge(ct):
        bg  = _TIPO_BG.get(ct, "#f5f5f5")
        txt = _TIPO_TXT.get(ct, "#616161")
        return (f'<span class="bib-badge" style="background:{bg};color:{txt};">{ct}</span>')

    # ── VISTA GRID ────────────────────────────────────────────────────────────
    if view_mode == "▦ Grid":
        cols_per_row = 3
        for row_start in range(0, len(filtered), cols_per_row):
            row_docs = filtered[row_start: row_start + cols_per_row]
            grid_cols = st.columns(cols_per_row)
            for col, doc in zip(grid_cols, row_docs):
                with col:
                    date_str = doc["indexed_at"][:10] if doc["indexed_at"] else "—"
                    size_str = _fmt_size(doc["size"]) if doc["size"] else ""
                    st.markdown(
                        f'<div class="bib-card">'
                        f'<div style="font-size:26px;text-align:center;">{doc["icon"]}</div>'
                        f'{_badge(doc["contract_type"])}'
                        f'<span class="bib-badge" style="background:#f5f5f5;color:#555;">'
                        f'{doc["ext"].upper()}</span>'
                        f'<div class="bib-name">{doc["source"]}</div>'
                        f'<div class="bib-meta">📅 {date_str} &nbsp;·&nbsp; {size_str}</div>'
                        f'<div class="bib-meta">🏢 {doc["inversionista"]} &nbsp;·&nbsp; '
                        f'{doc["categoria"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    bc1, bc2 = st.columns(2)
                    if bc1.button("Abrir", key=f"g_open_{doc['source']}", width="stretch"):
                        st.session_state["biblioteca_selected"] = doc["source"]
                        st.session_state["bib_show_chat"] = True
                        st.rerun()
                    if bc2.button("⚖ Legal", key=f"g_legal_{doc['source']}", width="stretch"):
                        st.session_state["library_selected"] = doc["source"]
                        st.switch_page("pages/legal.py")

    # ── VISTA LISTA ───────────────────────────────────────────────────────────
    else:
        for doc in filtered:
            date_str = doc["indexed_at"][:10] if doc["indexed_at"] else "—"
            size_str = _fmt_size(doc["size"]) if doc["size"] else ""
            lc = st.columns([0.4, 4.5, 1.5, 1.5, 1, 1, 1])
            lc[0].markdown(f"<div style='font-size:22px;padding-top:4px'>{doc['icon']}</div>",
                           unsafe_allow_html=True)
            lc[1].markdown(
                f"**{doc['source']}**\n\n"
                f"<span style='font-size:11px;color:#888;'>{date_str} · {size_str} · "
                f"{doc['inversionista']}</span>",
                unsafe_allow_html=True,
            )
            lc[2].markdown(_badge(doc["contract_type"]), unsafe_allow_html=True)
            lc[3].markdown(
                f'<span class="bib-badge" style="background:#f5f5f5;color:#555;">'
                f'{doc["ext"].upper()} · {doc["categoria"]}</span>',
                unsafe_allow_html=True,
            )
            if lc[4].button("Abrir", key=f"l_open_{doc['source']}", width="stretch"):
                st.session_state["biblioteca_selected"] = doc["source"]
                st.session_state["bib_show_chat"] = True
                st.rerun()
            if lc[5].button("⚖", key=f"l_legal_{doc['source']}", width="stretch",
                            help="Análisis Legal"):
                st.session_state["library_selected"] = doc["source"]
                st.switch_page("pages/legal.py")
            st.divider()
