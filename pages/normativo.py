import re
import streamlit as st
from utils.shared import apply_styles, page_header, init_session_state, api_status_banner
from core.normativa_db import NORMATIVA, NOVEDADES, get_normativa_for_contract_type, search_normativa
from core.llm_service import LLM_AVAILABLE

apply_styles()
init_session_state()
page_header()
api_status_banner()

st.markdown("## Gestor Normativo FNCER")
st.caption("Normativa colombiana aplicable a proyectos de energía solar y generación distribuida — Unergy")

# ─── Constantes visuales ──────────────────────────────────────────────────────
TIPO_COLOR = {
    "Ley": "#1565C0",
    "Decreto": "#6A1B9A",
    "Resolución CREG": "#00796B",
    "Resolución UPME": "#E65100",
    "Resolución MME": "#37474F",
}
IMPACTO_BADGE = {
    "alto":  ("#e53935", "🔴 Alto"),
    "medio": ("#f57c00", "🟡 Medio"),
    "bajo":  ("#388e3c", "🟢 Bajo"),
}

tab_catalogo, tab_cruce, tab_novedades, tab_compliance = st.tabs([
    "📚 Catálogo Normativo",
    "🔗 Cruce con Contratos",
    "📡 Monitor de Novedades",
    "✅ Compliance Dashboard",
])

# ─── TAB 1: Catálogo ──────────────────────────────────────────────────────────
with tab_catalogo:
    c_search, c_tipo, c_contrato = st.columns([3, 2, 2])
    with c_search:
        q = st.text_input("buscar_norm", placeholder="🔍 Buscar por nombre, tema o entidad...",
                          label_visibility="collapsed", key="norm_search")
    with c_tipo:
        tipos_disponibles = ["Todos"] + sorted(set(n["tipo"] for n in NORMATIVA))
        filtro_tipo = st.selectbox("Tipo", tipos_disponibles, label_visibility="collapsed", key="norm_tipo")
    with c_contrato:
        tipos_contrato = ["Todos los contratos"] + sorted(
            set(a for n in NORMATIVA for a in n.get("aplica_a", [])))
        filtro_contrato = st.selectbox("Aplica a", tipos_contrato,
                                       label_visibility="collapsed", key="norm_contrato")

    # Filtrar
    filtered = search_normativa(q) if q else list(NORMATIVA)
    if filtro_tipo != "Todos":
        filtered = [n for n in filtered if n["tipo"] == filtro_tipo]
    if filtro_contrato != "Todos los contratos":
        filtered = [n for n in filtered if filtro_contrato in n.get("aplica_a", [])]

    st.caption(f"{len(filtered)} norma(s) — Total base: {len(NORMATIVA)}")

    # Agrupar por tipo
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
            with st.expander(f"**{n['nombre']}** — {n['titulo'][:60]}"):
                ec1, ec2 = st.columns([3, 1])
                with ec1:
                    st.markdown(f"**Entidad:** {n['entidad']} | **Fecha:** {n['fecha']} | **Estado:** {n['estado']}")
                    st.markdown(n["resumen"])
                    # Tags
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
                    st.markdown("**Artículos clave:**")
                    for art in arts:
                        st.markdown(
                            f'<span style="background:{color}18;border-radius:4px;'
                            f'padding:2px 8px;font-size:12px;margin-right:4px;">'
                            f'<b>{art["articulo"]}</b> — {art["tema"]}</span>',
                            unsafe_allow_html=True)

# ─── TAB 2: Cruce Normativo ───────────────────────────────────────────────────
with tab_cruce:
    st.markdown("#### Cruce automático contrato vs. normativa")
    stats = st.session_state.chatbot.get_stats()
    sources = stats.get("sources", [])

    if not sources:
        st.info("Sin contratos indexados. Ve a **Ajustes** para cargar documentos.")
    else:
        selected = st.selectbox("Seleccionar contrato", sources, key="norm_cruce_src")

        def _get_text(src):
            try:
                r = st.session_state.chatbot.vectorstore.get(include=["documents","metadatas"])
                return " ".join(d for d,m in zip(r.get("documents",[]),r.get("metadatas",[]))
                                if m and m.get("source")==src)
            except Exception:
                return ""

        def _detect_type(src, text=""):
            src_low = src.lower() + " " + text[:500].lower()
            if "ppa" in src_low or "compraventa" in src_low or "energía" in src_low:
                return "PPA"
            if "epc" in src_low or "construcción" in src_low or "instalación" in src_low:
                return "EPC"
            if "o&m" in src_low or "mantenimiento" in src_low or "operación" in src_low:
                return "O&M"
            if "comunidad" in src_low:
                return "Comunidades Energéticas"
            return "PPA"

        if st.button("🔗 Cruzar con normativa", type="primary", width="stretch", key="btn_cruce"):
            with st.spinner("Analizando contrato..."):
                text = _get_text(selected)
                ct = _detect_type(selected, text)
                normas_aplicables = get_normativa_for_contract_type(ct)
                if not normas_aplicables:
                    normas_aplicables = NORMATIVA[:6]

                # Detección por regex: menciones explícitas en el texto
                rows = []
                for n in normas_aplicables:
                    # Buscar menciones del número de norma en el texto
                    patterns = [n["numero"], n["nombre"][:20], n["entidad"]]
                    mencionada = any(p.lower() in text.lower() for p in patterns if p)
                    estado_cumplimiento = "✅" if mencionada else "⚠️"
                    rows.append({
                        "Norma": n["nombre"],
                        "Tipo": n["tipo"],
                        "Mencionada": "Sí" if mencionada else "No",
                        "Estado": estado_cumplimiento,
                        "Resumen": n["resumen"][:80],
                    })

                st.session_state["_cruce_result"] = {
                    "contrato": selected, "tipo": ct, "rows": rows, "text": text,
                    "normas": normas_aplicables,
                }

        cruce = st.session_state.get("_cruce_result")
        if cruce and cruce["contrato"] == selected:
            st.markdown(f"**Contrato:** {cruce['contrato']} | **Tipo detectado:** {cruce['tipo']}")
            import pandas as _pd
            df = _pd.DataFrame(cruce["rows"])[["Norma","Tipo","Mencionada","Estado","Resumen"]]
            st.dataframe(df, use_container_width=True, hide_index=True)

            _mencionadas = sum(1 for r in cruce["rows"] if r["Mencionada"]=="Sí")
            _total = len(cruce["rows"])
            score = int(_mencionadas / _total * 100) if _total else 0
            st.metric("Score de referencias normativas", f"{score}%",
                      help="% de normas aplicables mencionadas explícitamente en el contrato")

            # Análisis IA
            if LLM_AVAILABLE:
                _ia_key = f"_cruce_ia_{selected}"
                if st.session_state.get(_ia_key):
                    st.markdown("**Análisis IA:**")
                    st.markdown(st.session_state[_ia_key])
                else:
                    if st.button("✨ Analizar con IA", key="btn_cruce_ia"):
                        from core.llm_service import generate_response
                        from core.normativa_db import get_normativa_summary_for_prompt
                        _prompt = (
                            f"Analiza si el siguiente contrato cumple con la normativa colombiana FNCER.\n\n"
                            f"{get_normativa_summary_for_prompt(cruce['tipo'])}\n\n"
                            f"Para cada norma indica: ✅ cumple / ⚠️ riesgo / ❌ incumple / N/A no aplica.\n"
                            f"Responde en markdown con tabla y observaciones.\n\n"
                            f"CONTRATO ({selected}):\n{cruce['text'][:4000]}"
                        )
                        with st.spinner("Analizando con Gemini..."):
                            _ia = generate_response(_prompt, context="")
                        if _ia:
                            st.session_state[_ia_key] = _ia
                            st.rerun()

            # Exportar PDF
            try:
                from utils.report_generator import generate_comparison_report_pdf
                import datetime as _dt
                _rows_text = "\n".join(
                    f"{r['Estado']} {r['Norma']}: {r['Resumen']}" for r in cruce["rows"])
                _pdf = generate_comparison_report_pdf(
                    selected, f"Normativa {cruce['tipo']}", score,
                    _rows_text, st.session_state.get(f"_cruce_ia_{selected}", ""))
                st.download_button("📥 Exportar cruce normativo PDF", data=_pdf,
                                   file_name=f"cruce_{selected[:20]}.pdf",
                                   mime="application/pdf", key="dl_cruce_pdf")
            except Exception:
                pass

# ─── TAB 3: Monitor de Novedades ─────────────────────────────────────────────
with tab_novedades:
    st.markdown("#### Novedades regulatorias recientes — sector energético colombiano")
    st.caption("Fuente estática actualizada a 2025. Usa 'Buscar con IA' para novedades más recientes.")

    for nov in NOVEDADES:
        imp_color, imp_label = IMPACTO_BADGE.get(nov["impacto"], ("#607D8B", "⚫ N/A"))
        with st.expander(f"**{nov['titulo']}** — {nov['fecha']}"):
            nc1, nc2 = st.columns([3, 1])
            with nc1:
                st.markdown(f"**Entidad:** {nov['entidad']} | **Fecha:** {nov['fecha']}")
                st.markdown(nov["resumen"])
                st.markdown(
                    f'<div style="background:#fff8e1;border-left:3px solid {imp_color};'
                    f'padding:6px 10px;border-radius:0 6px 6px 0;margin-top:6px;">'
                    f'<b>Impacto para Unergy:</b> {nov["impacto_unergy"]}</div>',
                    unsafe_allow_html=True)
            with nc2:
                st.markdown(
                    f'<div style="text-align:center;padding:10px;">'
                    f'<div style="font-size:28px;">{"🔴" if nov["impacto"]=="alto" else "🟡" if nov["impacto"]=="medio" else "🟢"}</div>'
                    f'<div style="font-size:11px;font-weight:700;color:{imp_color};">'
                    f'Impacto {nov["impacto"].upper()}</div></div>',
                    unsafe_allow_html=True)
            if nov.get("url"):
                st.link_button("Ver fuente", nov["url"])

    st.markdown("---")
    if LLM_AVAILABLE:
        _nov_key = "_novedades_ia"
        if st.session_state.get(_nov_key):
            st.markdown("**Novedades encontradas por IA:**")
            st.markdown(st.session_state[_nov_key])
            if st.button("🔄 Buscar de nuevo", key="btn_nov_refresh"):
                del st.session_state[_nov_key]
                st.rerun()
        else:
            if st.button("🔍 Buscar novedades con IA", type="primary", key="btn_nov_ia"):
                from core.llm_service import generate_response
                _p = ("Busca y resume las últimas noticias y resoluciones regulatorias "
                      "del sector energético colombiano (FNCER, generación distribuida, "
                      "comunidades energéticas) de 2025 y 2026. "
                      "Incluye: entidad emisora, fecha, título, resumen, impacto estimado para "
                      "empresas de energía solar. Formato markdown con secciones por entidad (CREG, MME, UPME).")
                with st.spinner("Consultando a Gemini..."):
                    _r = generate_response(_p, context="")
                if _r:
                    st.session_state[_nov_key] = _r
                    st.rerun()
    else:
        st.caption("Activa Gemini en Ajustes para buscar novedades regulatorias con IA.")

# ─── TAB 4: Compliance Dashboard ─────────────────────────────────────────────
with tab_compliance:
    st.markdown("#### Dashboard de Cumplimiento Normativo del Portfolio")
    _stats = st.session_state.chatbot.get_stats()
    _sources = _stats.get("sources", [])

    if not _sources:
        st.info("Sin contratos indexados.")
    else:
        # Detectar tipo y calcular score por contrato
        _comp_key = "_compliance_data"
        if st.button("📊 Calcular compliance del portfolio", type="primary", key="btn_compliance"):
            _comp_data = []
            prog = st.progress(0)
            for i, src in enumerate(_sources):
                try:
                    r = st.session_state.chatbot.vectorstore.get(include=["documents","metadatas"])
                    txt = " ".join(d for d,m in zip(r.get("documents",[]),r.get("metadatas",[]))
                                   if m and m.get("source")==src)
                    ct = ("PPA" if "ppa" in src.lower() else
                          "EPC" if "epc" in src.lower() else
                          "O&M" if "o&m" in src.lower() or "mantenimiento" in src.lower() else
                          "PPA")
                    normas = get_normativa_for_contract_type(ct) or NORMATIVA[:4]
                    menciones = sum(
                        1 for n in normas
                        if any(p.lower() in txt.lower() for p in [n["numero"], n["entidad"]] if p)
                    )
                    score = int(menciones / len(normas) * 100) if normas else 0
                    _comp_data.append({"contrato": src, "tipo": ct, "normas": len(normas),
                                       "menciones": menciones, "score": score})
                except Exception:
                    _comp_data.append({"contrato": src, "tipo": "—", "normas": 0, "menciones": 0, "score": 0})
                prog.progress((i+1)/len(_sources))
            prog.empty()
            st.session_state[_comp_key] = _comp_data

        comp_data = st.session_state.get(_comp_key, [])
        if comp_data:
            import pandas as _pd2
            _df_comp = _pd2.DataFrame(comp_data)
            _df_comp["Score"] = _df_comp["score"].apply(lambda x: f"{x}%")
            _df_comp["Estado"] = _df_comp["score"].apply(
                lambda x: "✅ Bueno" if x>=60 else "⚠️ Revisar" if x>=30 else "❌ Bajo")
            st.dataframe(_df_comp[["contrato","tipo","menciones","normas","Score","Estado"]],
                         use_container_width=True, hide_index=True)

            _avg = int(sum(d["score"] for d in comp_data)/len(comp_data)) if comp_data else 0
            mc1,mc2,mc3 = st.columns(3)
            mc1.metric("Score global portfolio", f"{_avg}%")
            mc2.metric("Contratos revisados", len(comp_data))
            mc3.metric("Con score bajo (<30%)",
                       sum(1 for d in comp_data if d["score"]<30))

            # Normas no mencionadas en ningún contrato
            all_texts = []
            for src in _sources[:5]:
                try:
                    r2 = st.session_state.chatbot.vectorstore.get(include=["documents","metadatas"])
                    all_texts.append(" ".join(d for d,m in zip(r2.get("documents",[]),r2.get("metadatas",[]))
                                              if m and m.get("source")==src))
                except Exception:
                    pass
            combined = " ".join(all_texts).lower()
            _sin_mencionar = [n for n in NORMATIVA
                              if not any(p.lower() in combined
                                         for p in [n["numero"], n["entidad"]] if p)]
            if _sin_mencionar:
                st.markdown(f"**{len(_sin_mencionar)} norma(s) no mencionadas en ningún contrato (posibles brechas):**")
                for n in _sin_mencionar:
                    st.markdown(
                        f'<span style="background:#fff3e0;border:1px solid #ffb74d;border-radius:4px;'
                        f'padding:2px 8px;font-size:12px;margin:2px;display:inline-block;">'
                        f'{n["nombre"]}</span>',
                        unsafe_allow_html=True)
