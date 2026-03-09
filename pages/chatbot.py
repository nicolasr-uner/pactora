import streamlit as st
from utils.shared import apply_styles, page_header, init_session_state

apply_styles()
init_session_state()
page_header()

# ─── Header estilo buscador ────────────────────────────────────────────────────
st.markdown(
    '<div style="text-align:center;margin:8px 0 20px 0;">'
    '<div style="font-size:32px;font-weight:900;color:#2C2039;">🤖 JuanMitaChat</div>'
    '<div style="color:#915BD8;font-size:15px;margin-top:4px;">'
    'Busca en el contenido de tus contratos indexados</div>'
    '</div>',
    unsafe_allow_html=True
)

stats = st.session_state.chatbot.get_stats()

if stats["total_docs"] == 0:
    st.warning("Sin contratos indexados. Ve a **Ajustes** para cargar documentos.", icon="📄")

    st.markdown("---")
    st.markdown("#### ¿Qué podrás hacer una vez cargues contratos?")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            '<div class="factora-card" style="text-align:center;">'
            '<div style="font-size:28px;">🔍</div>'
            '<div style="font-weight:700;margin:8px 0 4px;">Búsqueda semántica</div>'
            '<div style="font-size:13px;color:#666;">Encuentra cláusulas y términos en lenguaje natural</div>'
            '</div>',
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            '<div class="factora-card" style="text-align:center;">'
            '<div style="font-size:28px;">📋</div>'
            '<div style="font-weight:700;margin:8px 0 4px;">Consulta de obligaciones</div>'
            '<div style="font-size:13px;color:#666;">Identifica fechas, montos y partes de cada contrato</div>'
            '</div>',
            unsafe_allow_html=True
        )
    with col3:
        st.markdown(
            '<div class="factora-card" style="text-align:center;">'
            '<div style="font-size:28px;">⚖️</div>'
            '<div style="font-weight:700;margin:8px 0 4px;">Revisión de riesgos</div>'
            '<div style="font-size:13px;color:#666;">Detecta cláusulas problemáticas en los documentos</div>'
            '</div>',
            unsafe_allow_html=True
        )
    st.stop()

# ─── Barra de búsqueda central ────────────────────────────────────────────────
col_q, col_btn, col_info = st.columns([7, 1, 1])
with col_q:
    query = st.text_input(
        "buscar_juanmita",
        placeholder="¿Cuáles son las cláusulas de terminación? ¿Cuándo vence el contrato?",
        label_visibility="collapsed",
        key="jmc_query"
    )
with col_btn:
    buscar = st.button("Buscar", type="primary", use_container_width=True)
with col_info:
    with st.popover("ℹ️"):
        st.markdown(
            "**JuanMitaChat** busca en el texto de los contratos indexados y devuelve "
            "los fragmentos más relevantes para tu consulta.\n\n"
            "Escribe preguntas en lenguaje natural, términos legales o palabras clave. "
            "No necesita ortografía perfecta.\n\n"
            "*Próximamente: respuestas generadas por IA con Gemini.*"
        )

# ─── Sugerencias ──────────────────────────────────────────────────────────────
SUGERENCIAS = [
    "Fechas de vencimiento",
    "Cláusulas de penalización",
    "Partes del contrato",
    "Obligaciones de pago",
    "Fuerza mayor",
    "Renovación automática",
]

sug_cols = st.columns(len(SUGERENCIAS))
for col, s in zip(sug_cols, SUGERENCIAS):
    if col.button(s, key=f"sug_{s[:12]}", use_container_width=True):
        st.session_state.jmc_query = s
        st.rerun()

st.markdown("---")

# ─── Resultados ───────────────────────────────────────────────────────────────
active_query = query or (st.session_state.get("jmc_query", "") if buscar else "")

if active_query:
    with st.spinner("Buscando en contratos..."):
        result = st.session_state.chatbot.ask_question(active_query)

    st.markdown(
        f'<div style="color:#666;font-size:13px;margin-bottom:12px;">'
        f'Resultados para: <b>{active_query}</b> — '
        f'{stats["total_docs"]} contrato(s) consultado(s)</div>',
        unsafe_allow_html=True
    )
    st.markdown(result)

    # Guardar historial simple en session_state
    if "jmc_history" not in st.session_state:
        st.session_state.jmc_history = []
    if active_query not in st.session_state.jmc_history:
        st.session_state.jmc_history.insert(0, active_query)
        st.session_state.jmc_history = st.session_state.jmc_history[:10]

else:
    # Panel informativo cuando no hay búsqueda activa
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("### Contratos disponibles")
        for s in stats["sources"]:
            ext = s.lower().split(".")[-1] if "." in s else ""
            icon = "📄" if ext == "pdf" else "📝"
            st.markdown(f"{icon} &nbsp; {s}")

    with col_right:
        st.markdown("### ¿Cómo buscar?")
        st.markdown("""
Escribe tu consulta en lenguaje natural:

- *¿Cuáles son las partes del contrato?*
- *¿Qué dice sobre penalidades por incumplimiento?*
- *¿Cuándo vence el plazo de ejecución?*
- *Muéstrame las cláusulas de fuerza mayor*

Los resultados muestran los fragmentos más relevantes de los contratos indexados.

---
*🔮 Próximamente: respuestas generadas por IA*
        """)

        # Historial de búsquedas
        if st.session_state.get("jmc_history"):
            st.markdown("**Búsquedas recientes:**")
            for h in st.session_state.jmc_history[:5]:
                if st.button(f"↩ {h}", key=f"hist_{h[:20]}", use_container_width=True):
                    st.session_state.jmc_query = h
                    st.rerun()
