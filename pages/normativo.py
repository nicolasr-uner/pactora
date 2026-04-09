import streamlit as st
from utils.shared import apply_styles, page_header, init_session_state, api_status_banner
import pandas as _pd
from core.llm_service import LLM_AVAILABLE, generate_response

# Importación defensiva — fallback si normativa_db.py es una versión anterior (sin multi-país)
try:
    from core.normativa_db import (
        NORMATIVA, NOVEDADES, NORMATIVA_POR_PAIS, NOVEDADES_POR_PAIS,
        get_normativa_for_contract_type, get_normativa_summary_for_prompt, search_normativa,
    )
except ImportError:
    # Versión antigua: solo Colombia. Los demás países se inicializan vacíos.
    from core.normativa_db import (  # type: ignore[no-redef]
        NORMATIVA, NOVEDADES,
        get_normativa_for_contract_type, get_normativa_summary_for_prompt, search_normativa,
    )
    NORMATIVA_POR_PAIS: dict = {"🇨🇴 Colombia": NORMATIVA}
    NOVEDADES_POR_PAIS: dict = {"🇨🇴 Colombia": NOVEDADES}

apply_styles()
init_session_state()
page_header()
api_status_banner()

st.markdown("## Gestor Normativo FNCER")
st.caption("Normativa energética aplicable a proyectos renovables — Colombia, Ecuador, México y Brasil")

# ─── Constantes visuales ──────────────────────────────────────────────────────
TIPO_COLOR = {
    "Ley": "#1565C0", "Lei": "#1565C0",
    "Decreto": "#6A1B9A",
    "Resolución CREG": "#00796B", "Resolución ARCERNNR": "#00796B",
    "Resolución CRE": "#00796B", "Resolução ANEEL": "#00796B",
    "Resolución UPME": "#E65100",
    "Resolución MME": "#37474F",
    "Resolución CENACE": "#37474F",
    "Plan Nacional": "#5D4037", "Tarifa": "#4527A0",
    "Reglamento": "#37474F", "Regras CCEE": "#2E7D32",
}
IMPACTO_BADGE = {
    "alto":  ("#e53935", "🔴 Alto"),
    "medio": ("#f57c00", "🟡 Medio"),
    "bajo":  ("#388e3c", "🟢 Bajo"),
}
PAISES = ["🇨🇴 Colombia", "🇪🇨 Ecuador", "🇲🇽 México", "🇧🇷 Brasil"]

tab_catalogo, tab_cruce, tab_novedades, tab_compliance = st.tabs([
    "📚 Catálogo Normativo",
    "🔗 Cruce con Contratos",
    "📡 Monitor de Novedades",
    "✅ Compliance Dashboard",
])

# ─── TAB 1: Catálogo multi-país ───────────────────────────────────────────────
with tab_catalogo:
    # Selector de país
    pais_cat = st.selectbox(
        "País", PAISES, index=0,
        key="norm_pais_cat",
        help="Selecciona el país cuya normativa energética deseas consultar",
    )
    normativa_activa = NORMATIVA_POR_PAIS.get(pais_cat, NORMATIVA)

    c_search, c_tipo, c_contrato = st.columns([3, 2, 2])
    with c_search:
        q = st.text_input("Buscar", placeholder="🔍 Nombre, tema o entidad...",
                          label_visibility="collapsed", key="norm_search")
    with c_tipo:
        tipos_disponibles = ["Todos"] + sorted(set(n["tipo"] for n in normativa_activa))
        filtro_tipo = st.selectbox("Tipo", tipos_disponibles,
                                   label_visibility="collapsed", key="norm_tipo")
    with c_contrato:
        tipos_contrato = ["Todos los contratos"] + sorted(
            set(a for n in normativa_activa for a in n.get("aplica_a", [])))
        filtro_contrato = st.selectbox("Aplica a", tipos_contrato,
                                       label_visibility="collapsed", key="norm_contrato")

    # Filtrar
    def _search_pais(q_: str, db: list) -> list:
        ql = q_.lower()
        return [
            n for n in db
            if ql in n["nombre"].lower() or ql in n["resumen"].lower()
            or any(ql in t.lower() for t in n.get("tags", []))
            or ql in n.get("titulo", "").lower()
        ]

    filtered = _search_pais(q, normativa_activa) if q else list(normativa_activa)
    if filtro_tipo != "Todos":
        filtered = [n for n in filtered if n["tipo"] == filtro_tipo]
    if filtro_contrato != "Todos los contratos":
        filtered = [n for n in filtered if filtro_contrato in n.get("aplica_a", [])]

    st.caption(f"{len(filtered)} norma(s) — Base {pais_cat}: {len(normativa_activa)}")

    # Agrupar y renderizar
    groups: dict = {}
    for n in filtered:
        groups.setdefault(n["tipo"], []).append(n)

    for tipo, normas in groups.items():
        color = TIPO_COLOR.get(tipo, "#915BD8")
        st.markdown(
            f'<div style="background:{color}18;border-left:4px solid {color};'
            f'padding:4px 12px;border-radius:0 6px 6px 0;margin:14px 0 6px 0;'
            f'font-weight:700;color:{color};">{tipo} ({len(normas)})</div>',
            unsafe_allow_html=True)
        for n in normas:
            with st.expander(f"**{n['nombre']}** — {n['titulo'][:65]}"):
                ec1, ec2 = st.columns([3, 1])
                with ec1:
                    st.markdown(
                        f"**Entidad:** {n['entidad']} | **Fecha:** {n['fecha']} | **Estado:** {n['estado']}")
                    st.markdown(n["resumen"])
                    tags_html = " ".join(
                        f'<span style="background:#f3e5f5;color:#6A1B9A;border-radius:4px;'
                        f'padding:1px 7px;font-size:11px;">{t}</span>'
                        for t in n.get("tags", []))
                    st.markdown(tags_html, unsafe_allow_html=True)
                with ec2:
                    st.markdown("**Aplica a:**")
                    for a in n.get("aplica_a", []):
                        st.markdown(f"• {a}")
                    if n.get("url"):
                        st.link_button("Ver fuente oficial", n["url"])
                arts = n.get("articulos_clave", [])
                if arts:
                    st.markdown("**Artículos / Cláusulas clave:**")
                    arts_html = " ".join(
                        f'<span style="background:{color}18;border-radius:4px;'
                        f'padding:2px 8px;font-size:12px;margin:2px;display:inline-block;">'
                        f'<b>{art["articulo"]}</b> — {art["tema"]}</span>'
                        for art in arts)
                    st.markdown(arts_html, unsafe_allow_html=True)

# ─── TAB 2: Cruce Normativo ───────────────────────────────────────────────────
with tab_cruce:
    st.markdown("#### Cruce automático contrato vs. normativa")
    stats   = st.session_state.chatbot.get_stats()
    sources = stats.get("sources", [])

    if not sources:
        st.info("Sin contratos indexados. Ve a **Ajustes** para cargar documentos.")
    else:
        selected = st.selectbox("Seleccionar contrato", sources, key="norm_cruce_src")

        def _get_text(src):
            try:
                r = st.session_state.chatbot.vectorstore.get(include=["documents", "metadatas"])
                return " ".join(
                    d for d, m in zip(r.get("documents", []), r.get("metadatas", []))
                    if m and m.get("source") == src)
            except Exception:
                return ""

        def _detect_type(src, text=""):
            combined = (src + " " + text[:500]).lower()
            if "ppa" in combined or "compraventa" in combined or "energía" in combined:
                return "PPA"
            if "epc" in combined or "construcción" in combined or "instalación" in combined:
                return "EPC"
            if "o&m" in combined or "mantenimiento" in combined or "operación" in combined:
                return "O&M"
            if "comunidad" in combined:
                return "Comunidades Energéticas"
            return "PPA"

        if st.button("🔗 Cruzar con normativa", type="primary",
                     key="btn_cruce", width="stretch"):
            with st.spinner("Analizando contrato..."):
                text = _get_text(selected)
                ct   = _detect_type(selected, text)
                normas_aplicables = get_normativa_for_contract_type(ct) or NORMATIVA[:6]
                rows = []
                for n in normas_aplicables:
                    patterns  = [n["numero"], n["nombre"][:20], n["entidad"]]
                    mencionada = any(p.lower() in text.lower() for p in patterns if p)
                    rows.append({
                        "Norma": n["nombre"], "Tipo": n["tipo"],
                        "Mencionada": "Sí" if mencionada else "No",
                        "Estado": "✅" if mencionada else "⚠️",
                        "Resumen": n["resumen"][:80],
                    })
                st.session_state["_cruce_result"] = {
                    "contrato": selected, "tipo": ct, "rows": rows,
                    "text": text, "normas": normas_aplicables,
                }

        cruce = st.session_state.get("_cruce_result")
        if cruce and cruce["contrato"] == selected:
            st.markdown(f"**Contrato:** {cruce['contrato']} | **Tipo:** {cruce['tipo']}")
            st.dataframe(
                _pd.DataFrame(cruce["rows"])[["Norma", "Tipo", "Mencionada", "Estado", "Resumen"]],
                hide_index=True, width="stretch",
            )
            _men = sum(1 for r in cruce["rows"] if r["Mencionada"] == "Sí")
            score = int(_men / len(cruce["rows"]) * 100) if cruce["rows"] else 0
            st.metric("Score de referencias normativas", f"{score}%",
                      help="% de normas aplicables mencionadas en el contrato")

            if LLM_AVAILABLE:
                _ia_key = f"_cruce_ia_{selected}"
                if st.session_state.get(_ia_key):
                    st.markdown("**Análisis IA:**")
                    st.markdown(st.session_state[_ia_key])
                else:
                    if st.button("✨ Analizar con IA", key="btn_cruce_ia"):
                        _prompt = (
                            f"Analiza si el contrato cumple con la normativa colombiana FNCER.\n\n"
                            f"{get_normativa_summary_for_prompt(cruce['tipo'])}\n\n"
                            f"Para cada norma indica: ✅ cumple / ⚠️ riesgo / ❌ incumple / N/A.\n"
                            f"Responde en markdown con tabla y observaciones.\n\n"
                            f"CONTRATO ({selected}):\n{cruce['text'][:4000]}"
                        )
                        with st.spinner("Analizando con Gemini..."):
                            _ia = generate_response(_prompt, context="")
                        if _ia:
                            st.session_state[_ia_key] = _ia
                            st.rerun()

            try:
                from utils.report_generator import generate_comparison_report_pdf
                _rows_text = "\n".join(
                    f"{r['Estado']} {r['Norma']}: {r['Resumen']}" for r in cruce["rows"])
                _pdf = generate_comparison_report_pdf(
                    selected, f"Normativa {cruce['tipo']}", score, _rows_text,
                    st.session_state.get(f"_cruce_ia_{selected}", ""))
                st.download_button("📥 Exportar PDF", data=_pdf,
                                   file_name=f"cruce_{selected[:20]}.pdf",
                                   mime="application/pdf", key="dl_cruce_pdf")
            except Exception:
                pass

# ─── TAB 3: Monitor de Novedades MSN-style ────────────────────────────────────
with tab_novedades:
    st.markdown("#### 📡 Monitor de Novedades Regulatorias")
    st.caption("Novedades del sector energético renovable — Colombia, Ecuador, México y Brasil")

    # Selector de país como tabs internos
    pais_nov = st.radio(
        "País", PAISES, horizontal=True, key="norm_pais_nov", label_visibility="collapsed",
    )
    novedades_activas = NOVEDADES_POR_PAIS.get(pais_nov, NOVEDADES)

    # CSS para las news cards
    st.markdown("""
    <style>
    .news-card {
        background: var(--background-color, #fff);
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 16px 18px;
        margin-bottom: 12px;
        transition: box-shadow .15s;
    }
    .news-card:hover { box-shadow: 0 3px 14px rgba(0,0,0,.12); }
    .news-source {
        font-size: 11px; font-weight: 700; text-transform: uppercase;
        color: #888; letter-spacing: .05em; margin-bottom: 4px;
    }
    .news-title { font-size: 15px; font-weight: 700; margin: 4px 0 6px 0; line-height: 1.3; }
    .news-date  { font-size: 11px; color: #aaa; margin-bottom: 8px; }
    .news-body  { font-size: 13px; color: #555; margin-bottom: 10px; line-height: 1.5; }
    .news-impact-tag {
        display: inline-block; border-radius: 20px;
        padding: 2px 10px; font-size: 11px; font-weight: 700;
        margin-bottom: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Botón IA (arriba de las cards)
    ia_col, _ = st.columns([2, 3])
    with ia_col:
        _nov_key = f"_novedades_ia_{pais_nov}"
        _buscar_ia = st.button(
            "🔍 Buscar noticias recientes con IA",
            type="primary", key=f"btn_nov_{pais_nov}",
            disabled=not LLM_AVAILABLE, width="stretch",
        )
    if not LLM_AVAILABLE:
        st.caption("Activa Gemini en Ajustes para buscar novedades con IA.")

    if st.session_state.get(_nov_key):
        st.markdown("---")
        st.markdown("**🤖 Novedades encontradas por IA:**")
        st.markdown(st.session_state[_nov_key])
        if st.button("🗑 Limpiar resultado IA", key=f"btn_nov_clear_{pais_nov}"):
            del st.session_state[_nov_key]
            st.rerun()
        st.markdown("---")

    if _buscar_ia and LLM_AVAILABLE:
        pais_nombre = pais_nov.split(" ", 1)[-1]  # e.g. "Colombia"
        _p = (
            f"Busca y resume las últimas noticias y resoluciones regulatorias del sector "
            f"energético renovable en {pais_nombre} de 2025 y 2026. "
            f"Incluye: entidad emisora, fecha, título, resumen breve e impacto estimado "
            f"para empresas de energía solar y generación distribuida. "
            f"Formato markdown — secciones por entidad reguladora."
        )
        with st.spinner(f"Consultando noticias de {pais_nombre} con Gemini..."):
            _r = generate_response(_p, context="")
        if _r:
            st.session_state[_nov_key] = _r
            st.rerun()

    # Grid de cards (2 columnas)
    card_cols = st.columns(2)
    for i, nov in enumerate(novedades_activas):
        imp_color, imp_label = IMPACTO_BADGE.get(nov.get("impacto", "bajo"), ("#607D8B", "⚫ N/A"))
        with card_cols[i % 2]:
            flag = pais_nov.split()[0]  # emoji del país seleccionado
            st.markdown(
                f'<div class="news-card">'
                f'<div class="news-source">{flag} {nov["entidad"]}</div>'
                f'<div class="news-title">{nov["titulo"]}</div>'
                f'<div class="news-date">📅 {nov["fecha"]}</div>'
                f'<span class="news-impact-tag" style="background:{imp_color}22;color:{imp_color};">'
                f'{imp_label}</span>'
                f'<div class="news-body">{nov["resumen"]}</div>'
                f'<div class="news-body" style="background:#fff8e1;border-left:3px solid {imp_color};'
                f'padding:4px 8px;border-radius:0 4px 4px 0;font-size:12px;">'
                f'<b>Impacto Unergy:</b> {nov.get("impacto_unergy", "")}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if nov.get("url"):
                st.link_button("🔗 Ver fuente oficial", nov["url"])

# ─── TAB 4: Compliance Dashboard ─────────────────────────────────────────────
with tab_compliance:
    st.markdown("#### Dashboard de Cumplimiento Normativo del Portfolio")
    _stats   = st.session_state.chatbot.get_stats()
    _sources = _stats.get("sources", [])

    if not _sources:
        st.info("Sin contratos indexados.")
    else:
        _comp_key = "_compliance_data"
        if st.button("📊 Calcular compliance del portfolio", type="primary",
                     key="btn_compliance", width="stretch"):
            _comp_data = []
            prog = st.progress(0)
            for i, src in enumerate(_sources):
                try:
                    r = st.session_state.chatbot.vectorstore.get(
                        include=["documents", "metadatas"])
                    txt = " ".join(
                        d for d, m in zip(r.get("documents", []), r.get("metadatas", []))
                        if m and m.get("source") == src)
                    ct = ("PPA" if "ppa" in src.lower() else
                          "EPC" if "epc" in src.lower() else
                          "O&M" if "o&m" in src.lower() or "mantenimiento" in src.lower() else
                          "PPA")
                    normas   = get_normativa_for_contract_type(ct) or NORMATIVA[:4]
                    menciones = sum(
                        1 for n in normas
                        if any(p.lower() in txt.lower()
                               for p in [n["numero"], n["entidad"]] if p))
                    score = int(menciones / len(normas) * 100) if normas else 0
                    _comp_data.append({"contrato": src, "tipo": ct, "normas": len(normas),
                                       "menciones": menciones, "score": score})
                except Exception:
                    _comp_data.append({"contrato": src, "tipo": "—",
                                       "normas": 0, "menciones": 0, "score": 0})
                prog.progress((i + 1) / len(_sources))
            prog.empty()
            st.session_state[_comp_key] = _comp_data

        comp_data = st.session_state.get(_comp_key, [])
        if comp_data:
            _df = _pd.DataFrame(comp_data)
            _df["Score"]  = _df["score"].apply(lambda x: f"{x}%")
            _df["Estado"] = _df["score"].apply(
                lambda x: "✅ Bueno" if x >= 60 else "⚠️ Revisar" if x >= 30 else "❌ Bajo")
            st.dataframe(_df[["contrato", "tipo", "menciones", "normas", "Score", "Estado"]],
                         hide_index=True, width="stretch")

            _avg = int(sum(d["score"] for d in comp_data) / len(comp_data)) if comp_data else 0
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Score global", f"{_avg}%")
            mc2.metric("Contratos revisados", len(comp_data))
            mc3.metric("Score bajo (<30%)", sum(1 for d in comp_data if d["score"] < 30))

            # Brechas normativas
            all_texts = []
            for src in _sources[:5]:
                try:
                    r2 = st.session_state.chatbot.vectorstore.get(
                        include=["documents", "metadatas"])
                    all_texts.append(" ".join(
                        d for d, m in zip(r2.get("documents", []), r2.get("metadatas", []))
                        if m and m.get("source") == src))
                except Exception:
                    pass
            combined   = " ".join(all_texts).lower()
            _sin_citar = [n for n in NORMATIVA
                          if not any(p.lower() in combined
                                     for p in [n["numero"], n["entidad"]] if p)]
            if _sin_citar:
                st.markdown(
                    f"**{len(_sin_citar)} norma(s) no citadas en ningún contrato (posibles brechas):**")
                brechas_html = " ".join(
                    f'<span style="background:#fff3e0;border:1px solid #ffb74d;border-radius:4px;'
                    f'padding:2px 8px;font-size:12px;margin:2px;display:inline-block;">'
                    f'{n["nombre"]}</span>'
                    for n in _sin_citar)
                st.markdown(brechas_html, unsafe_allow_html=True)
