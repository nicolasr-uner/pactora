"""
resolver.py — Resuelve con JuanMitaBot.
Flujo guiado de análisis contractual profundo.
Solo accesible para usuarios con la función "resolver" habilitada.
"""

import streamlit as st
from utils.shared import apply_styles, page_header, init_session_state

apply_styles()
init_session_state()

# ─── Verificación de acceso ───────────────────────────────────────────────────

try:
    _logged_in  = st.user.is_logged_in
    _user_email = st.user.email if _logged_in else ""
except Exception:
    _logged_in, _user_email = False, ""

if not _logged_in:
    st.error("Debes iniciar sesión para acceder a esta página.")
    st.stop()

try:
    from utils.auth_manager import has_feature, is_authorized
    if not is_authorized(_user_email):
        st.error("⛔ Acceso denegado. Tu cuenta no está autorizada.")
        st.stop()
    if not has_feature(_user_email, "resolver"):
        st.warning(
            "🔒 No tienes acceso a **Resolver con JuanMitaBot**.\n\n"
            "Contacta al administrador para que habilite esta función en tu cuenta."
        )
        st.stop()
except Exception:
    pass  # Si auth_manager falla, permitir acceso (entorno de desarrollo)

# ─── Header ───────────────────────────────────────────────────────────────────

page_header("Resolver con JuanMitaBot")

st.markdown(
    '<div style="margin:4px 0 16px 0;">'
    '<span style="font-size:28px;font-weight:900;" class="pactora-title">🎯 Resolver con JuanMitaBot</span><br>'
    '<span style="font-size:14px;" class="pactora-sub">'
    'Análisis contractual profundo y estructurado — JuanMitaBot te guía paso a paso'
    '</span>'
    '</div>',
    unsafe_allow_html=True,
)

# ─── Inicialización de estado ─────────────────────────────────────────────────

if "resolver_history" not in st.session_state:
    st.session_state.resolver_history = []
if "resolver_stage" not in st.session_state:
    # "idle" | "clarifying" | "analyzing" | "done"
    st.session_state.resolver_stage = "idle"
if "resolver_pending" not in st.session_state:
    st.session_state.resolver_pending = None

# ─── Verificar que haya contratos indexados ───────────────────────────────────

chatbot = st.session_state.get("chatbot")
if chatbot is None:
    st.warning("El sistema de contratos no está disponible. Recarga la página.")
    st.stop()

stats = chatbot.get_stats()

from utils.auth import get_current_user, filter_sources_for_user
user = get_current_user()
filtered_sources = filter_sources_for_user(stats.get("sources", []), user)

if not filtered_sources:
    st.warning(
        "Sin contratos indexados. Ve a **Ajustes** para cargar documentos primero.",
        icon="📄",
    )
    st.stop()

# ─── Layout ───────────────────────────────────────────────────────────────────

col_main, col_side = st.columns([7, 3])

# ── Panel lateral ─────────────────────────────────────────────────────────────

with col_side:
    st.markdown("### ¿Cómo funciona?")
    st.markdown(
        """
**1️⃣ Describe tu consulta**
Dile a JuanMitaBot qué necesitas analizar: un contrato específico, una cláusula, un riesgo, etc.

**2️⃣ JuanMitaBot aclara (≤ 2 preguntas)**
Si necesita más contexto, te hará máximo 2 preguntas para enfocar el análisis.

**3️⃣ Análisis automático**
Usa herramientas internas para buscar cláusulas, perfiles y vencimientos.

**4️⃣ Informe ejecutivo**
Recibes un informe estructurado con hallazgos, nivel de riesgo y próximos pasos.
        """
    )

    st.markdown("---")
    st.caption(f"📄 {len(filtered_sources)} contrato(s) disponibles")

    with st.expander("Ver contratos", expanded=False):
        for src in filtered_sources[:20]:
            ext = src.lower().rsplit(".", 1)[-1] if "." in src else ""
            icon = {"pdf": "📕", "docx": "📝", "pptx": "📊"}.get(ext, "📄")
            st.markdown(f"{icon} {src}")
        if len(filtered_sources) > 20:
            st.caption(f"…y {len(filtered_sources) - 20} más")

    st.markdown("---")
    if st.button("🗑 Nueva consulta", key="resolver_reset", use_container_width=True):
        st.session_state.resolver_history = []
        st.session_state.resolver_stage = "idle"
        st.session_state.resolver_pending = None
        st.rerun()

# ── Panel principal ────────────────────────────────────────────────────────────

with col_main:

    # ── Pantalla inicial (sin historial) ──────────────────────────────────────
    if not st.session_state.resolver_history:
        st.markdown(
            '<div style="text-align:center;padding:48px 0 32px 0;color:#9d87c0;">'
            '<div style="font-size:52px;margin-bottom:16px;">🎯</div>'
            '<div style="font-size:20px;font-weight:700;">¿Qué necesitas resolver hoy?</div>'
            '<div style="font-size:14px;margin-top:8px;color:#aaa;">'
            'Describe tu consulta contractual y JuanMitaBot te entregará un informe ejecutivo completo.'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        # Sugerencias rápidas
        st.markdown("##### Consultas frecuentes")
        suggestions = [
            ("⚠️ Riesgos críticos", "Analiza los riesgos críticos de nuestros contratos PPA activos"),
            ("📅 Vencimientos", "¿Qué contratos vencen en los próximos 90 días y qué acciones se requieren?"),
            ("💰 Penalidades", "Identifica todas las cláusulas de penalización en contratos EPC"),
            ("🔀 Comparativa", "Compara las condiciones de terminación anticipada entre nuestros contratos"),
            ("📋 Obligaciones", "Resume las obligaciones operativas del portafolio O&M"),
            ("🔒 Fuerza mayor", "Analiza las cláusulas de fuerza mayor — ¿son simétricas?"),
        ]

        cols = st.columns(2)
        for i, (label, query) in enumerate(suggestions):
            if cols[i % 2].button(label, key=f"res_sug_{i}", use_container_width=True, help=query):
                st.session_state.resolver_pending = query
                st.rerun()

    # ── Historial de conversación ─────────────────────────────────────────────
    else:
        for msg in st.session_state.resolver_history:
            with st.chat_message(msg["role"]):
                content = msg["content"]
                if msg["role"] == "assistant" and len(content) > 1500:
                    st.markdown(content[:1000] + "\n\n*…[ver informe completo abajo]*")
                    with st.expander("📋 Ver informe completo"):
                        st.markdown(content)
                else:
                    st.markdown(content)

    # ── Input ─────────────────────────────────────────────────────────────────
    placeholder = (
        "Describe tu consulta contractual…"
        if not st.session_state.resolver_history
        else "Responde o agrega más contexto…"
    )
    user_input = st.chat_input(placeholder, key="resolver_input")

    # Consumir sugerencia pendiente
    if st.session_state.resolver_pending:
        user_input = st.session_state.resolver_pending
        st.session_state.resolver_pending = None

    # ── Procesar input ────────────────────────────────────────────────────────
    if user_input:
        st.session_state.resolver_history.append({"role": "user", "content": user_input})

        # Filtro de contratos permitidos para este usuario
        user_filter = None
        if user and "all" not in user.get("allowed_contract_types", ["all"]):
            user_filter = {"source": {"$in": filtered_sources}}

        # Historial para el LLM (sin el mensaje que acabamos de agregar)
        history_for_llm = st.session_state.resolver_history[-7:-1]

        try:
            from core.llm_service import LLM_AVAILABLE, run_agent_turn, RESOLVER_SYSTEM_PROMPT

            with st.spinner("🎯 Analizando…"):
                if LLM_AVAILABLE:
                    answer = run_agent_turn(
                        question=user_input,
                        history=history_for_llm,
                        system_prompt=RESOLVER_SYSTEM_PROMPT,
                        filter_metadata=user_filter,
                    )
                    if not answer:
                        # Fallback: usar chatbot directamente
                        answer = chatbot.ask_question(
                            user_input,
                            filter_metadata=user_filter,
                            chat_history=history_for_llm,
                        )
                else:
                    answer = chatbot.ask_question(
                        user_input,
                        filter_metadata=user_filter,
                        chat_history=history_for_llm,
                    )
        except ValueError as ve:
            answer = f"⏳ {ve}"
        except Exception as exc:
            answer = f"⚠️ Error interno: {exc}"

        st.session_state.resolver_history.append({"role": "assistant", "content": answer})
        st.rerun()
