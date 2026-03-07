import streamlit as st
import json
import datetime
from utils.shared import apply_styles, page_header, init_session_state, api_status_banner

apply_styles()
init_session_state()

page_header()
api_status_banner()
st.header("Metricas de Cumplimiento")

stats = st.session_state.chatbot.get_stats()
versiones = sum(len(v.get("history", [])) for v in st.session_state.doc_versions.values())

# ─── KPIs basicos ─────────────────────────────────────────────────────────────
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

if not stats["sources"]:
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
    st.stop()

import pandas as pd

# ─── Extraer insights de contratos ────────────────────────────────────────────
st.subheader("Analisis Inteligente del Portfolio")

col_btn, col_info = st.columns([2, 3])
with col_btn:
    if st.button("Extraer insights con JuanMitaBot", use_container_width=True, type="primary"):
        with st.spinner("JuanMitaBot extrayendo datos de todos los contratos..."):
            raw = st.session_state.chatbot.ask_question(
                "Para cada contrato indexado extrae en formato JSON (solo JSON, sin texto adicional, "
                "sin bloques de codigo markdown): una lista de objetos con los campos: "
                "nombre (string), tipo (PPA/EPC/OyM/Legal/Otro), "
                "valor_total (numero o null), moneda (string o null), "
                "fecha_inicio (YYYY-MM-DD o null), fecha_vencimiento (YYYY-MM-DD o null), "
                "partes (lista de strings), nivel_riesgo (ROJO/AMARILLO/VERDE)."
            )
        # Parsear JSON
        try:
            # Limpiar posibles bloques de codigo
            clean = raw.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            insights = json.loads(clean)
            st.session_state.contract_insights = insights
            st.success(f"Insights extraidos para {len(insights)} contrato(s).")
        except Exception:
            st.warning("No se pudo parsear la respuesta como JSON. Revisa la pestaña de texto.")
            st.session_state.contract_insights = None
            with st.expander("Respuesta raw de JuanMitaBot"):
                st.text(raw)

with col_info:
    if "contract_insights" not in st.session_state:
        st.info("Haz clic en 'Extraer insights' para obtener metricas avanzadas basadas en el contenido real de los contratos.")

# ─── Dashboard de insights ────────────────────────────────────────────────────
insights = st.session_state.get("contract_insights")

if insights and isinstance(insights, list) and len(insights) > 0:

    # ── KPIs avanzados
    today = datetime.date.today()
    total_valor = sum(c.get("valor_total") or 0 for c in insights if c.get("valor_total"))
    moneda_comun = next((c.get("moneda") for c in insights if c.get("moneda")), "USD")

    vencen_30 = 0
    vencen_60 = 0
    vencen_90 = 0
    vencidos = 0
    for c in insights:
        fv = c.get("fecha_vencimiento")
        if fv:
            try:
                d = datetime.date.fromisoformat(fv)
                diff = (d - today).days
                if diff < 0:
                    vencidos += 1
                elif diff <= 30:
                    vencen_30 += 1
                elif diff <= 60:
                    vencen_60 += 1
                elif diff <= 90:
                    vencen_90 += 1
            except Exception:
                pass

    adv1, adv2, adv3, adv4 = st.columns(4)
    adv1.markdown(
        f'<div class="metric-card"><div class="metric-val" style="font-size:22px;">'
        f'{"N/A" if total_valor == 0 else f"{total_valor:,.0f} {moneda_comun}"}</div>'
        '<div class="metric-lbl">Valor total estimado</div></div>', unsafe_allow_html=True
    )
    adv2.markdown(
        f'<div class="metric-card"><div class="metric-val" style="color:#e53935;">{vencidos}</div>'
        '<div class="metric-lbl">Contratos vencidos</div></div>', unsafe_allow_html=True
    )
    adv3.markdown(
        f'<div class="metric-card"><div class="metric-val" style="color:#f57c00;">{vencen_30}</div>'
        '<div class="metric-lbl">Vencen en 30 dias</div></div>', unsafe_allow_html=True
    )
    adv4.markdown(
        f'<div class="metric-card"><div class="metric-val" style="color:#388e3c;">{vencen_60 + vencen_90}</div>'
        '<div class="metric-lbl">Vencen 31-90 dias</div></div>', unsafe_allow_html=True
    )

    st.markdown("---")
    ch1, ch2 = st.columns(2)

    # ── Distribucion por tipo
    with ch1:
        st.subheader("Distribucion por tipo")
        tipos = [c.get("tipo", "Otro") for c in insights]
        tipo_counts = {}
        for t in tipos:
            tipo_counts[t] = tipo_counts.get(t, 0) + 1
        df_tipo = pd.DataFrame({"Tipo": list(tipo_counts.keys()), "Contratos": list(tipo_counts.values())})
        st.bar_chart(df_tipo.set_index("Tipo"))

    # ── Semaforo de riesgo
    with ch2:
        st.subheader("Nivel de riesgo")
        riesgo_counts = {"VERDE": 0, "AMARILLO": 0, "ROJO": 0}
        for c in insights:
            r = (c.get("nivel_riesgo") or "VERDE").upper()
            if r in riesgo_counts:
                riesgo_counts[r] += 1
        r1, r2, r3 = st.columns(3)
        r1.markdown(
            f'<div class="metric-card" style="border-left:4px solid #388e3c;">'
            f'<div class="metric-val" style="color:#388e3c;">{riesgo_counts["VERDE"]}</div>'
            '<div class="metric-lbl">VERDE</div></div>', unsafe_allow_html=True
        )
        r2.markdown(
            f'<div class="metric-card" style="border-left:4px solid #f57c00;">'
            f'<div class="metric-val" style="color:#f57c00;">{riesgo_counts["AMARILLO"]}</div>'
            '<div class="metric-lbl">AMARILLO</div></div>', unsafe_allow_html=True
        )
        r3.markdown(
            f'<div class="metric-card" style="border-left:4px solid #e53935;">'
            f'<div class="metric-val" style="color:#e53935;">{riesgo_counts["ROJO"]}</div>'
            '<div class="metric-lbl">ROJO</div></div>', unsafe_allow_html=True
        )

    # ── Timeline de vencimientos
    fechas_venc = []
    for c in insights:
        fv = c.get("fecha_vencimiento")
        if fv:
            try:
                d = datetime.date.fromisoformat(fv)
                fechas_venc.append({"Mes": d.strftime("%Y-%m"), "Contrato": c.get("nombre", "?")})
            except Exception:
                pass
    if fechas_venc:
        st.subheader("Timeline de vencimientos")
        df_venc = pd.DataFrame(fechas_venc)
        mes_counts = df_venc.groupby("Mes").size().reset_index(name="Cantidad")
        st.bar_chart(mes_counts.set_index("Mes"))

    st.markdown("---")

    # ── Tabla de contratos con semaforo
    st.subheader("Tabla de contratos")
    RISK_COLOR = {"ROJO": "#e53935", "AMARILLO": "#f57c00", "VERDE": "#388e3c"}
    for c in insights:
        riesgo = (c.get("nivel_riesgo") or "VERDE").upper()
        color = RISK_COLOR.get(riesgo, "#888")
        venc_str = c.get("fecha_vencimiento") or "N/A"
        valor_str = f"{c.get('valor_total'):,.0f} {c.get('moneda','')}" if c.get("valor_total") else "N/A"
        partes = ", ".join(c.get("partes") or []) or "N/A"

        # Alerta si vence pronto
        alerta = ""
        if c.get("fecha_vencimiento"):
            try:
                diff = (datetime.date.fromisoformat(c["fecha_vencimiento"]) - today).days
                if diff < 0:
                    alerta = " ⚠️ VENCIDO"
                elif diff <= 30:
                    alerta = f" ⚠️ Vence en {diff}d"
            except Exception:
                pass

        st.markdown(
            f'<div class="factora-card" style="border-left:4px solid {color};margin-bottom:10px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;">'
            f'<span style="font-weight:900;font-size:15px;">{c.get("nombre","?")}</span>'
            f'<span style="background:{color};color:white;border-radius:4px;padding:2px 10px;font-size:12px;font-weight:700;">'
            f'{riesgo}</span></div>'
            f'<div style="color:#666;font-size:13px;margin-top:6px;">'
            f'Tipo: <b>{c.get("tipo","N/A")}</b> &nbsp;|&nbsp; '
            f'Valor: <b>{valor_str}</b> &nbsp;|&nbsp; '
            f'Vencimiento: <b>{venc_str}{alerta}</b></div>'
            f'<div style="color:#888;font-size:12px;margin-top:4px;">Partes: {partes}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")

# ─── Analisis narrativo del portfolio ─────────────────────────────────────────
st.subheader("Analisis narrativo — JuanMitaBot")
if "portfolio_analysis" not in st.session_state:
    st.session_state.portfolio_analysis = None

if st.button("Generar analisis narrativo del portfolio", use_container_width=True):
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
