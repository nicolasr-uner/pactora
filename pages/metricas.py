import re
import streamlit as st
import datetime
import pandas as pd
from utils.shared import apply_styles, page_header, init_session_state, api_status_banner
from core.llm_service import LLM_AVAILABLE

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


def _extract_amounts(text: str) -> list[str]:
    """
    Extrae montos monetarios del texto usando regex.
    Detecta: USD X.XXX, COP X.XXX, $ X.XXX, X% del CAPEX, tarifa XX COP/kWh, etc.
    Retorna lista de strings únicos (máx. 8).
    """
    found = []
    patterns = [
        r'USD\s*[\d,\.]+(?:\s*(?:millones?|mil))?',
        r'COP\s*[\d,\.]+(?:\s*(?:millones?|mil))?',
        r'\$\s*[\d,\.]+(?:\s*(?:millones?|mil|USD|COP))?',
        r'[\d,\.]+\s*(?:COP|USD|EUR)(?:/kWh|/MWh|/MW)?',
        r'[\d,\.]+\s*(?:millones?|mil)\s*(?:de\s*)?(?:pesos?|dólares?|USD|COP)',
        r'\d+(?:[.,]\d+)?%?\s*del\s*(?:CAPEX|valor|contrato)',
        r'tarifa\s+(?:fija\s+)?de\s+[\w\s,\.]+(?:USD|COP|pesos)',
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            val = m.group(0).strip()
            if val not in found and len(val) < 60:
                found.append(val)
    return found[:8]


def _extract_parties(text: str) -> list[str]:
    """
    Extrae nombres de partes contractuales usando patrones heurísticos.
    Busca frases como 'Vendedor: X', 'entre X y Y', 'suscrito por X', etc.
    Retorna lista de strings únicos (máx. 6).
    """
    found = []
    # Patrón: Rol: Nombre en mayúsculas
    for m in re.finditer(
        r'(?:Vendedor|Comprador|Contratante|Contratista|Propietario|Operador|'
        r'Cedente|Cesionario|Parte\s+\w+)\s*:\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s\.,S\.A\.]+?)(?:\n|\.|-)',
        text
    ):
        val = m.group(1).strip().rstrip(".,")
        if val and len(val) > 3 and val not in found:
            found.append(val)
    # Patrón: entre [X] y [Y]
    for m in re.finditer(
        r'entre\s+([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s\.,S\.A\.]+?)\s+y\s+([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s\.,S\.A\.]+?)(?:\s*,|\s*\.)',
        text
    ):
        for g in (m.group(1), m.group(2)):
            val = g.strip().rstrip(".,")
            if val and len(val) > 3 and val not in found:
                found.append(val)
    # Patrón: suscrito por X
    for m in re.finditer(r'suscrito\s+por\s+([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s\.,S\.A\.]+?)(?:\n|,|\.)', text):
        val = m.group(1).strip().rstrip(".,")
        if val and len(val) > 3 and val not in found:
            found.append(val)
    return found[:6]


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
    amounts = _extract_amounts(text)
    parties = _extract_parties(text)
    contract_data.append({
        "nombre": src,
        "tipo": tipo,
        "ext": ext.upper(),
        "words": words,
        "pages": pages_est,
        "keywords": keyword_counts,
        "risk": risk,
        "risk_color": risk_color,
        "amounts": amounts,
        "parties": parties,
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
        + ('<br>✨ <b>Con Gemini activo:</b> extracción semántica de montos, fechas y partes.' if LLM_AVAILABLE else '<br>📊 Activa Gemini en Ajustes para análisis semántico avanzado.')
        + '</div></div>',
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
            + ("*✨ Usa **Analizar riesgos con IA** en Análisis Legal para análisis semántico por contrato.*" if LLM_AVAILABLE else "*Activa Gemini en Ajustes para análisis semántico profundo.*")
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

        _risk_note = ('✨ Usa Análisis Legal → Abrir → Analizar riesgos con IA.' if LLM_AVAILABLE else 'Activa Gemini para análisis semántico.')
        st.markdown(
            f'<div style="padding:8px;border-left:4px solid {color};background:white;'
            f'border-radius:0 6px 6px 0;margin-top:8px;">'
            f'<span style="font-weight:700;color:{color};">Nivel de riesgo: {c["risk"]}</span>'
            f'<div style="font-size:11px;color:#888;margin-top:2px;">'
            f'Calculado por frecuencia de keywords. {_risk_note}'
            f'</div></div>',
            unsafe_allow_html=True
        )

        # Montos extraídos
        if c.get("amounts"):
            st.markdown("**Montos detectados:**")
            st.markdown(
                " &nbsp;·&nbsp; ".join(
                    f'<code style="background:#e8f5e9;color:#1b5e20;padding:2px 6px;'
                    f'border-radius:4px;">{a}</code>'
                    for a in c["amounts"]
                ),
                unsafe_allow_html=True
            )

        # Partes contractuales
        if c.get("parties"):
            st.markdown("**Partes identificadas:**")
            st.markdown(
                " &nbsp;·&nbsp; ".join(
                    f'<span style="background:#e3f2fd;color:#0d47a1;padding:2px 8px;'
                    f'border-radius:4px;font-size:12px;">👤 {p}</span>'
                    for p in c["parties"]
                ),
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

st.markdown("---")

# ─── Resumen de montos y partes (extracción local) ────────────────────────────
ins_hrow = st.columns([9, 1])
ins_hrow[0].markdown("#### Insights del portfolio")
with ins_hrow[1].popover("ℹ️"):
    st.markdown(
        "Montos, partes contractuales y tipos detectados por análisis local (regex). "
        "Con Gemini activo, JuanMitaBot enriquecerá estos datos con extracción semántica profunda."
    )

llm_badge = "🟢 Gemini activo" if LLM_AVAILABLE else "📊 Análisis local"

col_ins1, col_ins2, col_ins3 = st.columns(3)

# Montos únicos en todo el portfolio
all_amounts = []
for c in contract_data:
    for a in c.get("amounts", []):
        if a not in all_amounts:
            all_amounts.append(a)

with col_ins1:
    st.markdown(
        f'<div style="background:#e8f5e9;border-radius:10px;padding:14px;">'
        f'<div style="font-weight:900;color:#1b5e20;margin-bottom:6px;">💰 Montos detectados</div>'
        + (
            "".join(
                f'<div style="font-size:12px;color:#2e7d32;margin:2px 0;">• {a}</div>'
                for a in all_amounts[:10]
            )
            if all_amounts else
            '<div style="font-size:12px;color:#888;">No se detectaron montos explícitos.</div>'
        )
        + f'<div style="font-size:10px;color:#aaa;margin-top:8px;">{llm_badge}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

# Partes únicas en todo el portfolio
all_parties = []
for c in contract_data:
    for p in c.get("parties", []):
        if p not in all_parties:
            all_parties.append(p)

with col_ins2:
    st.markdown(
        f'<div style="background:#e3f2fd;border-radius:10px;padding:14px;">'
        f'<div style="font-weight:900;color:#0d47a1;margin-bottom:6px;">👥 Partes identificadas</div>'
        + (
            "".join(
                f'<div style="font-size:12px;color:#1565c0;margin:2px 0;">• {p}</div>'
                for p in all_parties[:10]
            )
            if all_parties else
            '<div style="font-size:12px;color:#888;">No se identificaron partes explícitas.</div>'
        )
        + f'<div style="font-size:10px;color:#aaa;margin-top:8px;">{llm_badge}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

# Distribución de tipos
with col_ins3:
    tipo_summary = {}
    for c in contract_data:
        tipo_summary[c["tipo"]] = tipo_summary.get(c["tipo"], 0) + 1
    TIPO_COLORS_INS = {
        "PPA": "#4CAF50", "EPC": "#2196F3", "O&M": "#FF9800",
        "NDA": "#9C27B0", "Cesión": "#E91E63", "Otro": "#607D8B",
    }
    st.markdown(
        f'<div style="background:#f9f5ff;border-radius:10px;padding:14px;">'
        f'<div style="font-weight:900;color:#2C2039;margin-bottom:6px;">📊 Tipos de contrato</div>'
        + "".join(
            f'<div style="display:flex;justify-content:space-between;margin:3px 0;">'
            f'<span style="background:{TIPO_COLORS_INS.get(t,"#607D8B")};color:white;'
            f'border-radius:4px;padding:1px 7px;font-size:11px;">{t}</span>'
            f'<span style="font-weight:700;color:#2C2039;">{n}</span></div>'
            for t, n in sorted(tipo_summary.items(), key=lambda x: -x[1])
        )
        + f'<div style="font-size:10px;color:#aaa;margin-top:8px;">{llm_badge}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

# ─── Resumen ejecutivo con JuanMitaBot ────────────────────────────────────────
st.markdown("")
_portfolio_ia_key = "portfolio_ia_analysis"
btn_label = "✨ Enriquecer con JuanMitaBot" if LLM_AVAILABLE else "📊 Resumen del portfolio"

col_btn, col_clear = st.columns([4, 1])
with col_btn:
    run_analysis = st.button(btn_label, use_container_width=True, key="btn_insights_portfolio", type="primary")
with col_clear:
    if st.session_state.get(_portfolio_ia_key):
        if st.button("🗑 Limpiar", use_container_width=True, key="btn_clear_portfolio_ia"):
            del st.session_state[_portfolio_ia_key]
            st.rerun()

# Mostrar análisis cacheado si existe
if st.session_state.get(_portfolio_ia_key):
    st.markdown(
        f'<div style="background:white;border-left:5px solid #915BD8;border-radius:0 12px 12px 0;'
        f'padding:18px 22px;box-shadow:0 4px 16px rgba(145,91,216,0.1);margin-top:8px;">'
        f'<div style="font-weight:900;color:#2C2039;margin-bottom:10px;font-size:16px;">'
        f'🤖 Resumen ejecutivo del portfolio</div>'
        f'{st.session_state[_portfolio_ia_key]}</div>',
        unsafe_allow_html=True
    )
elif run_analysis:
    n_contracts = len(contract_data)
    n_rojos = risk_counts.get("ROJO", 0)
    n_amarillos = risk_counts.get("AMARILLO", 0)
    n_verdes = risk_counts.get("VERDE", 0)
    tipos_str = ", ".join(f"{t} ({n})" for t, n in sorted(tipo_summary.items(), key=lambda x: -x[1]))

    if LLM_AVAILABLE:
        # Construir contexto con primeros chunks de cada contrato
        ctx_parts = []
        for c in contract_data[:6]:  # máximo 6 contratos para no exceder tokens
            txt = _get_full_text(c["nombre"])
            if txt:
                ctx_parts.append(f"[Contrato: {c['nombre']} | Tipo: {c['tipo']} | Riesgo local: {c['risk']}]\n{txt[:1200]}")
        context = "\n\n---\n\n".join(ctx_parts) if ctx_parts else "No hay texto disponible."

        prompt = (
            f"Genera un resumen ejecutivo del portfolio de contratos de Unergy con estos {n_contracts} contratos:\n\n"
            f"Distribución: {tipos_str}\n"
            f"Riesgo: 🔴 {n_rojos} ROJO, 🟡 {n_amarillos} AMARILLO, 🟢 {n_verdes} VERDE\n"
            f"Total: {total_pages} páginas, {total_words:,} palabras\n\n"
            f"Incluye:\n"
            f"1. Estado general del portfolio (1 párrafo)\n"
            f"2. Contratos que requieren atención inmediata (si los hay)\n"
            f"3. Alertas de vencimiento o fechas críticas detectadas\n"
            f"4. Recomendaciones prioritarias para el equipo legal\n"
            f"Usa markdown y semáforos 🔴🟡🟢 donde aplique."
        )
        with st.spinner("JuanMitaBot analizando el portfolio..."):
            from core.llm_service import generate_response
            result = generate_response(prompt, context)
        if result:
            st.session_state[_portfolio_ia_key] = result
            st.rerun()
    else:
        # Modo local: resumen basado en datos ya calculados
        local_summary = (
            f"**📋 Resumen del portfolio ({n_contracts} contratos)**\n\n"
            f"Total: **{total_pages:,} páginas** · **{total_words:,} palabras**\n\n"
            f"**Distribución por tipo:** {tipos_str}\n\n"
            f"**Semáforo de riesgo:** "
            f"🔴 {n_rojos} ROJO · 🟡 {n_amarillos} AMARILLO · 🟢 {n_verdes} VERDE\n"
            + (f"\n**Montos detectados:** {', '.join(all_amounts[:5])}\n" if all_amounts else "")
            + (f"\n**Partes identificadas:** {', '.join(all_parties[:5])}\n" if all_parties else "")
            + "\n\n*Análisis calculado localmente · Activa Gemini para resumen ejecutivo con IA.*"
        )
        st.session_state[_portfolio_ia_key] = local_summary
        st.rerun()
