import streamlit as st
import datetime
import pandas as pd
from utils.shared import apply_styles, page_header, init_session_state, api_status_banner

apply_styles()
init_session_state()
page_header()
api_status_banner()

st.markdown("## Métricas del Portfolio de Contratos")
st.caption("Análisis cuantitativo y cualitativo de los contratos cargados en el sistema.")

# ─── Helpers ──────────────────────────────────────────────────────────────────
RISK_KEYWORDS = {
    "Penalidades": ["penalid", "multa", "sanción", "sancion", "incumplimiento"],
    "Terminación anticipada": ["terminación", "terminacion", "rescisión", "rescision", "resolución", "resolucion"],
    "Fuerza mayor": ["fuerza mayor", "caso fortuito", "evento extraordinario"],
    "Obligaciones de pago": ["pago", "factura", "precio", "valor contrato", "monto"],
    "Renovación": ["renovación", "renovacion", "prórroga", "prorroga", "extensión", "extension"],
    "Confidencialidad": ["confidencial", "secreto", "reservado"],
    "Responsabilidad": ["responsabilidad", "indemnización", "indemnizacion", "daños y perjuicios"],
    "Garantías": ["garantía", "garantia", "fianza", "caución", "caucion", "seguro"],
}

TIPO_MAP = {
    "ppa": "PPA", "power purchase": "PPA",
    "epc": "EPC", "ingeniería, procura": "EPC",
    "o&m": "O&M", "operación y mantenimiento": "O&M", "operacion y mantenimiento": "O&M",
    "nda": "NDA", "confidencialidad": "NDA",
    "cesion": "Cesión", "cesión": "Cesión",
}


def _get_full_text(src):
    try:
        all_docs = st.session_state.chatbot.vectorstore.get(include=["documents", "metadatas"])
        return " ".join(
            d for d, m in zip(all_docs.get("documents", []), all_docs.get("metadatas", []))
            if m and m.get("source") == src
        )
    except Exception:
        return ""


def _guess_tipo(name, text):
    combined = (name + " " + text[:500]).lower()
    for key, val in TIPO_MAP.items():
        if key in combined:
            return val
    return "Otro"


def _risk_level(keyword_counts):
    total = sum(keyword_counts.values())
    high_risk = keyword_counts.get("Penalidades", 0) + keyword_counts.get("Terminación anticipada", 0)
    if high_risk == 0 and total < 3:
        return "VERDE", "#388e3c"
    if high_risk >= 3 or total >= 10:
        return "ROJO", "#e53935"
    return "AMARILLO", "#f57c00"


# ─── Obtener datos de contratos ────────────────────────────────────────────────
stats = st.session_state.chatbot.get_stats()
sources = stats.get("sources", [])

# ─── KPIs principales ─────────────────────────────────────────────────────────
hrow = st.columns([9, 1])
hrow[0].markdown('<div class="card-title">Resumen del Portfolio</div>', unsafe_allow_html=True)
with hrow[1].popover("ℹ️"):
    st.markdown(
        "Métricas globales calculadas sobre los contratos cargados: "
        "cantidad total, palabras extraídas, páginas estimadas y distribución por tipo. "
        "Los datos se calculan localmente sin necesidad de IA."
    )

# Calcular métricas
contract_data = []
for src in sources:
    text = _get_full_text(src)
    words = len(text.split()) if text else 0
    pages_est = max(1, words // 350)
    tipo = _guess_tipo(src, text)
    ext = src.lower().split(".")[-1] if "." in src else "?"

    keyword_counts = {}
    text_lower = text.lower()
    for cat, kws in RISK_KEYWORDS.items():
        keyword_counts[cat] = sum(text_lower.count(kw) for kw in kws)

    risk, risk_color = _risk_level(keyword_counts)
    contract_data.append({
        "nombre": src,
        "tipo": tipo,
        "ext": ext.upper(),
        "words": words,
        "pages": pages_est,
        "keywords": keyword_counts,
        "risk": risk,
        "risk_color": risk_color,
    })

total_words = sum(c["words"] for c in contract_data)
total_pages = sum(c["pages"] for c in contract_data)
risk_counts = {"ROJO": 0, "AMARILLO": 0, "VERDE": 0}
for c in contract_data:
    risk_counts[c["risk"]] += 1

k1, k2, k3, k4 = st.columns(4)
k1.markdown(
    f'<div class="metric-card"><div class="metric-val">{len(sources) if sources else "0"}</div>'
    '<div class="metric-lbl">Contratos cargados</div></div>', unsafe_allow_html=True
)
k2.markdown(
    f'<div class="metric-card"><div class="metric-val">{total_pages:,}</div>'
    '<div class="metric-lbl">Páginas estimadas</div></div>', unsafe_allow_html=True
)
k3.markdown(
    f'<div class="metric-card"><div class="metric-val">{total_words:,}</div>'
    '<div class="metric-lbl">Palabras totales</div></div>', unsafe_allow_html=True
)
k4.markdown(
    f'<div class="metric-card"><div class="metric-val">'
    f'<span style="color:#e53935;">{risk_counts["ROJO"]}</span> / '
    f'<span style="color:#f57c00;">{risk_counts["AMARILLO"]}</span> / '
    f'<span style="color:#388e3c;">{risk_counts["VERDE"]}</span>'
    f'</div><div class="metric-lbl">Riesgo R / A / V</div></div>',
    unsafe_allow_html=True
)

if not sources:
    st.info("No hay contratos cargados. Ve a **Ajustes** para subir documentos PDF o DOCX.")
    st.markdown(
        '<div style="padding:16px;background:#f9f5ff;border-radius:12px;border:1px solid #e0d4f7;margin-top:16px;">'
        '<div style="font-weight:900;color:#2C2039;margin-bottom:8px;">¿Qué métricas verás aquí?</div>'
        '<div style="font-size:13px;color:#666;">'
        '<b>Para abogados:</b><br>'
        '• Detección de cláusulas de riesgo (penalidades, terminación, fuerza mayor)<br>'
        '• Semáforo de riesgo por contrato (ROJO / AMARILLO / VERDE)<br>'
        '• Distribución por tipo de contrato (PPA, EPC, O&M, Legal)<br>'
        '• Análisis de longitud y densidad contractual<br>'
        '• Frecuencia de cláusulas clave<br>'
        '<br>🔮 <b>Próximamente con IA:</b> extracción de montos, fechas y partes contractuales.'
        '</div></div>',
        unsafe_allow_html=True
    )
    st.stop()

st.markdown("---")

# ─── Gráficas ─────────────────────────────────────────────────────────────────
col_ch1, col_ch2 = st.columns(2)

with col_ch1:
    ch_hrow = st.columns([9, 1])
    ch_hrow[0].markdown("#### Distribución por tipo")
    with ch_hrow[1].popover("ℹ️"):
        st.markdown("Clasifica los contratos por tipo (PPA, EPC, O&M, etc.) basándose en el nombre del archivo y palabras clave del texto.")

    tipo_counts = {}
    for c in contract_data:
        tipo_counts[c["tipo"]] = tipo_counts.get(c["tipo"], 0) + 1
    df_tipo = pd.DataFrame({"Tipo": list(tipo_counts.keys()), "Contratos": list(tipo_counts.values())})
    st.bar_chart(df_tipo.set_index("Tipo"), color="#915BD8")

with col_ch2:
    ch_hrow2 = st.columns([9, 1])
    ch_hrow2[0].markdown("#### Semáforo de riesgo")
    with ch_hrow2[1].popover("ℹ️"):
        st.markdown(
            "Clasifica cada contrato según la presencia de cláusulas de riesgo detectadas localmente:\n\n"
            "🔴 **ROJO**: Alta presencia de penalidades o cláusulas de terminación\n\n"
            "🟡 **AMARILLO**: Riesgo moderado\n\n"
            "🟢 **VERDE**: Bajo riesgo detectado\n\n"
            "*🔮 Próximamente: análisis semántico con IA para mayor precisión.*"
        )

    r1, r2, r3 = st.columns(3)
    r1.markdown(
        f'<div class="metric-card" style="border-left:4px solid #388e3c;">'
        f'<div class="metric-val" style="color:#388e3c;">{risk_counts["VERDE"]}</div>'
        '<div class="metric-lbl">VERDE</div></div>', unsafe_allow_html=True
    )
    r2.markdown(
        f'<div class="metric-card" style="border-left:4px solid #f57c00;">'
        f'<div class="metric-val" style="color:#f57c00;">{risk_counts["AMARILLO"]}</div>'
        '<div class="metric-lbl">AMARILLO</div></div>', unsafe_allow_html=True
    )
    r3.markdown(
        f'<div class="metric-card" style="border-left:4px solid #e53935;">'
        f'<div class="metric-val" style="color:#e53935;">{risk_counts["ROJO"]}</div>'
        '<div class="metric-lbl">ROJO</div></div>', unsafe_allow_html=True
    )

    if len(contract_data) > 1:
        df_size = pd.DataFrame({
            "Contrato": [c["nombre"][:25] for c in contract_data],
            "Páginas": [c["pages"] for c in contract_data]
        })
        st.bar_chart(df_size.set_index("Contrato"))

st.markdown("---")

# ─── Tabla detallada por contrato ────────────────────────────────────────────
tbl_hrow = st.columns([9, 1])
tbl_hrow[0].markdown("#### Análisis por contrato")
with tbl_hrow[1].popover("ℹ️"):
    st.markdown(
        "Detalle de cada contrato: tipo inferido, tamaño estimado, nivel de riesgo y "
        "presencia de cláusulas clave detectadas mediante análisis de keywords. "
        "Expande cada contrato para ver el detalle de cláusulas."
    )

for c in contract_data:
    color = c["risk_color"]
    with st.expander(
        f"{c['nombre']} — {c['tipo']} — {c['pages']}p — "
        f"{'🔴' if c['risk']=='ROJO' else '🟡' if c['risk']=='AMARILLO' else '🟢'} {c['risk']}",
        expanded=False
    ):
        info_cols = st.columns(4)
        info_cols[0].markdown(f"**Tipo:** {c['tipo']}")
        info_cols[1].markdown(f"**Formato:** {c['ext']}")
        info_cols[2].markdown(f"**Páginas est.:** {c['pages']}")
        info_cols[3].markdown(f"**Palabras:** {c['words']:,}")

        st.markdown("**Cláusulas detectadas:**")
        kw_found = {k: v for k, v in c["keywords"].items() if v > 0}
        if kw_found:
            kw_cols = st.columns(min(4, len(kw_found)))
            for col, (cat, count) in zip(kw_cols, kw_found.items()):
                col.markdown(
                    f'<div style="text-align:center;padding:8px;background:white;'
                    f'border-radius:8px;border:1px solid #eee;">'
                    f'<div style="font-size:18px;font-weight:900;color:#915BD8;">{count}</div>'
                    f'<div style="font-size:11px;color:#666;">{cat}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        else:
            st.caption("No se detectaron cláusulas clave. El texto puede ser escaso.")

        st.markdown(
            f'<div style="padding:8px;border-left:4px solid {color};background:white;'
            f'border-radius:0 6px 6px 0;margin-top:8px;">'
            f'<span style="font-weight:700;color:{color};">Nivel de riesgo: {c["risk"]}</span>'
            f'<div style="font-size:11px;color:#888;margin-top:2px;">'
            f'Calculado localmente por frecuencia de keywords. '
            f'🔮 Próximamente: análisis semántico con IA.'
            f'</div></div>',
            unsafe_allow_html=True
        )

st.markdown("---")

# ─── Frecuencia global de cláusulas ──────────────────────────────────────────
freq_hrow = st.columns([9, 1])
freq_hrow[0].markdown("#### Frecuencia de cláusulas en todo el portfolio")
with freq_hrow[1].popover("ℹ️"):
    st.markdown(
        "Muestra cuántos contratos contienen cada tipo de cláusula. "
        "Útil para identificar qué cláusulas son más comunes en el portfolio "
        "y cuáles pueden estar faltando."
    )

clause_presence = {}
for cat in RISK_KEYWORDS:
    clause_presence[cat] = sum(1 for c in contract_data if c["keywords"].get(cat, 0) > 0)

df_freq = pd.DataFrame({
    "Cláusula": list(clause_presence.keys()),
    "Contratos con esta cláusula": list(clause_presence.values())
})
st.bar_chart(df_freq.set_index("Cláusula"), color="#915BD8")
