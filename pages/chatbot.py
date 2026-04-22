import streamlit as st
from utils.shared import apply_styles, page_header, init_session_state, api_status_banner
from core.llm_service import LLM_AVAILABLE

apply_styles()
init_session_state()
page_header()
api_status_banner()

# ─── Estado inicial ────────────────────────────────────────────────────────────
if "jmc_pending_query" not in st.session_state:
    st.session_state.jmc_pending_query = None

chatbot = st.session_state.chatbot
stats = chatbot.get_stats()

from utils.auth import get_current_user, filter_sources_for_user
user = get_current_user()
filtered_sources = filter_sources_for_user(stats.get("sources", []), user)
stats["sources"] = filtered_sources
stats["total_docs"] = len(filtered_sources)

user_filter = None
if user and "all" not in user.get("allowed_contract_types", ["all"]):
    user_filter = {"source": {"$in": filtered_sources}}

# ─── Sin contratos indexados ───────────────────────────────────────────────────
if stats["total_docs"] == 0:
    st.markdown(
        '<div style="text-align:center;margin:8px 0 20px 0;">'
        '<div style="font-size:32px;font-weight:900;" class="pactora-title">💬 JuanMitaBot</div>'
        '<div style="font-size:15px;margin-top:4px;" class="pactora-sub">Asistente legal de Unergy</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Distinguir: ¿indexación en curso (metadata > 0) o genuinamente sin contratos?
    try:
        from utils.indexing import _load_index_metadata
        _meta = _load_index_metadata()
        _n_meta = len(_meta)
    except Exception:
        _meta, _n_meta = {}, 0

    if _n_meta > 0:
        # ChromaDB vacío pero metadata dice que hay docs → background thread aún indexando
        st.info(
            f"⏳ **Cargando {_n_meta} contrato(s) desde Drive** en segundo plano… "
            f"Actualizando automáticamente cada 5 s.",
            icon="🔄",
        )
        _r_col, _ = st.columns([1, 3])
        with _r_col:
            if st.button("🔄 Actualizar ahora", type="primary", key="btn_refresh_chatbot"):
                st.rerun()
        # Auto-polling: volver a comprobar cada 5 segundos sin intervención del usuario
        import time as _time
        _time.sleep(5)
        st.rerun()
    else:
        # Sin contratos reales
        st.warning("Sin contratos indexados. Ve a **Ajustes** para cargar documentos.", icon="📄")

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    for col, icon, title, desc in [
        (col1, "🔍", "Búsqueda semántica", "Encuentra cláusulas en lenguaje natural"),
        (col2, "📋", "Consulta de obligaciones", "Identifica fechas, montos y partes"),
        (col3, "⚖️", "Revisión de riesgos", "Detecta cláusulas problemáticas"),
    ]:
        with col:
            st.markdown(
                f'<div class="factora-card" style="text-align:center;">'
                f'<div style="font-size:28px;">{icon}</div>'
                f'<div style="font-weight:700;margin:8px 0 4px;">{title}</div>'
                f'<div style="font-size:13px;color:#666;">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    st.stop()

# ─── Header ────────────────────────────────────────────────────────────────────
modo_label = "🤖 JuanMitaBot — Modo IA" if LLM_AVAILABLE else "🤖 JuanMitaBot — Búsqueda semántica"
modo_desc = (
    "Conversación natural sobre tus contratos, potenciada por Gemini"
    if LLM_AVAILABLE else
    "Busca fragmentos relevantes en el contenido de tus contratos indexados"
)
h_col, btn_col = st.columns([8, 2])
with h_col:
    st.markdown(
        f'<div style="margin:4px 0 12px 0;">'
        f'<span style="font-size:24px;font-weight:900;" class="pactora-title">{modo_label}</span><br>'
        f'<span style="font-size:13px;" class="pactora-sub">{modo_desc}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
with btn_col:
    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
    if st.button("🗑 Nueva conversación", key="new_conv", help="Limpia el historial de esta sesión"):
        st.session_state.chat_history = []
        st.session_state.sidebar_chat_filter = None
        st.session_state.sidebar_chat_title = ""
        st.rerun()

# ─── Sugerencias rápidas ───────────────────────────────────────────────────────
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
    if col.button(s, key=f"sug_{s[:14]}", help=f'Preguntar: "{s}"'):
        st.session_state.jmc_pending_query = s
        st.rerun()

st.markdown("---")

# ─── Layout: chat + panel lateral ─────────────────────────────────────────────
col_chat, col_panel = st.columns([7, 3])

with col_panel:
    with st.expander(f"📄 Contratos disponibles ({stats['total_docs']})", expanded=False):
        for src in stats["sources"]:
            ext = src.lower().rsplit(".", 1)[-1] if "." in src else ""
            icon = {"pdf": "📕", "docx": "📝", "pptx": "📊", "xlsx": "📊"}.get(ext, "📄")
            st.markdown(f"{icon} {src}", unsafe_allow_html=False)

    with st.expander("💡 Cómo preguntar", expanded=False):
        st.markdown(
            "Escribe preguntas en lenguaje natural:\n\n"
            "- *¿Cuáles son las partes del contrato?*\n"
            "- *¿Qué dice sobre penalidades?*\n"
            "- *¿Cuándo vence el plazo?*\n"
            "- *Muéstrame las cláusulas de fuerza mayor*\n\n"
            + ("✨ **Gemini activo** — historial de conversación incluido"
               if LLM_AVAILABLE else
               "⚫ Modo semántico — activa Gemini en Ajustes para IA")
        )

    if LLM_AVAILABLE:
        try:
            from core.llm_service import get_call_stats
            _s = get_call_stats()
            st.caption(
                f"📊 Llamadas hoy: **{_s['calls_today']}** | "
                f"Último min: {_s['calls_last_minute']}/{_s['rate_limit_per_minute']}"
            )
        except Exception:
            pass

# ─── Chat principal ─────────────────────────────────────────────────────────
with col_chat:
    chat_history = st.session_state.chat_history

    # Mostrar historial
    if not chat_history:
        st.markdown(
            '<div style="text-align:center;padding:40px 0;color:#9d87c0;">'
            '<div style="font-size:48px;margin-bottom:12px;">💬</div>'
            '<div style="font-size:16px;font-weight:600;">¡Hola! Soy JuanMitaBot</div>'
            '<div style="font-size:13px;margin-top:6px;">Pregúntame sobre tus contratos indexados.<br>'
            'Recuerdo el contexto de toda la conversación.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        for i, msg in enumerate(chat_history):
            with st.chat_message(msg["role"]):
                content = msg["content"]
                # Respuestas largas: mostrar fragmento + expandir
                if msg["role"] == "assistant" and len(content) > 1200:
                    st.markdown(content[:900] + "\n\n*…[respuesta larga, ver completa abajo]*")
                    with st.expander("📖 Ver respuesta completa"):
                        st.markdown(content)
                else:
                    st.markdown(content)

    # ─── Input ────────────────────────────────────────────────────────────────
    user_input = st.chat_input(
        "Escribe tu pregunta..." if not chat_history else "Continúa la conversación...",
        key="chat_main_input",
    )

    # Consumir sugerencia pendiente
    if st.session_state.jmc_pending_query:
        user_input = st.session_state.jmc_pending_query
        st.session_state.jmc_pending_query = None

    if user_input:
        # Últimos 6 mensajes como contexto (antes de agregar el actual)
        history_for_llm = st.session_state.chat_history[-6:]

        # Mostrar mensaje del usuario inline (ya que aún no está en el historial)
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        # Calcular filtro combinado
        sidebar_filter = st.session_state.get("sidebar_chat_filter")
        final_filter = None
        if sidebar_filter and user_filter:
            final_filter = {"$and": [sidebar_filter, user_filter]}
        elif sidebar_filter:
            final_filter = sidebar_filter
        elif user_filter:
            final_filter = user_filter

        # Streaming de la respuesta del asistente
        try:
            stream_gen, sources = chatbot.ask_question_stream(
                user_input,
                filter_metadata=final_filter,
                chat_history=history_for_llm,
            )
            with st.chat_message("assistant"):
                full_response = st.write_stream(stream_gen)
                if sources:
                    footer = f"\n\n---\n*Fuentes consultadas: {', '.join(sources)}*"
                    st.markdown(footer.strip())
                    full_response = (full_response or "") + footer
        except Exception as exc:
            full_response = f"⚠️ Error interno: {exc}"
            with st.chat_message("assistant"):
                st.markdown(full_response)

        st.session_state.chat_history.append({"role": "assistant", "content": full_response or ""})
