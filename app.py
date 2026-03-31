import sys

# Fix: Python 3.14 PEP 649 breaks pydantic v1 metaclass annotation reading.
if sys.version_info >= (3, 14):
    import pydantic.v1.main as _pv1m
    if not getattr(_pv1m.ModelMetaclass.__new__, "_pep649_patched", False):
        _orig_metaclass_new = _pv1m.ModelMetaclass.__new__
        def _patched_metaclass_new(mcs, name, bases, namespace, **kwargs):
            if "__annotate_func__" in namespace and "__annotations__" not in namespace:
                try:
                    namespace["__annotations__"] = namespace["__annotate_func__"](1)
                except Exception:
                    pass
            return _orig_metaclass_new(mcs, name, bases, namespace, **kwargs)
        _patched_metaclass_new._pep649_patched = True
        _pv1m.ModelMetaclass.__new__ = _patched_metaclass_new

import streamlit as st

st.set_page_config(
    page_title="Pactora CLM — Unergy",
    page_icon="🏛",
    layout="wide"
)

# ─── Auth gate ────────────────────────────────────────────────────────────────
# Verificar autenticación ANTES de cualquier otra cosa.
# Si st.user no está disponible (auth no configurada), se muestra una advertencia
# pero se permite el acceso para no romper entornos de desarrollo local.

_auth_configured = False
try:
    _auth_configured = hasattr(st, "user") and hasattr(st.user, "is_logged_in")
except Exception:
    pass

if _auth_configured:
    if not st.user.is_logged_in:
        # ── Página de inicio de sesión ─────────────────────────────────────
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"] { display: none; }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="text-align:center;margin-top:80px;">'
            '<div style="font-family:Lato,sans-serif;font-weight:900;font-size:56px;">Pactora</div>'
            '<div style="font-weight:600;font-size:18px;color:#9d87c0;margin-bottom:8px;">by Unergy</div>'
            '<div style="color:#666;margin-bottom:40px;font-size:15px;">'
            'Gestión inteligente de contratos de energía renovable'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button(
                "🔐  Iniciar sesión con Google",
                type="primary",
                use_container_width=True,
            ):
                st.login("google")
        st.stop()

    # ── Verificar whitelist ────────────────────────────────────────────────
    try:
        from utils.auth_manager import is_authorized, is_admin, get_user_permissions

        _email = st.user.email or ""
        if not is_authorized(_email):
            st.markdown(
                """
                <style>
                [data-testid="stSidebar"] { display: none; }
                </style>
                """,
                unsafe_allow_html=True,
            )
            st.error("⛔ **Acceso denegado**", icon="🔒")
            st.markdown(
                f"Tu cuenta **{_email}** no está autorizada para acceder a Pactora CLM.  \n"
                "Contacta al administrador para solicitar acceso."
            )
            col_a, col_b, _ = st.columns([1, 1, 4])
            with col_a:
                st.button("Cerrar sesión", on_click=st.logout)
            st.stop()

        # Guardar contexto del usuario en session_state
        if "current_user_email" not in st.session_state:
            st.session_state.current_user_email = _email
            st.session_state.current_user_is_admin = is_admin(_email)
            st.session_state.current_user_permissions = get_user_permissions(_email)

    except Exception as _auth_err:
        # Si auth_manager falla (ej. Drive no disponible), loggear pero no bloquear
        import logging
        logging.getLogger("pactora").error("[app] auth_manager error: %s", _auth_err)

# ─── Inicialización y sidebar ─────────────────────────────────────────────────

from utils.shared import init_session_state, juanmitabot_sidebar, dark_mode_toggle

init_session_state()
dark_mode_toggle()
juanmitabot_sidebar()

# ─── Navegación ───────────────────────────────────────────────────────────────

_is_admin = st.session_state.get("current_user_is_admin", False)
_current_email = st.session_state.get("current_user_email", "")

# Feature-gated pages
try:
    from utils.auth_manager import has_feature as _has_feature
    _has_resolver = _has_feature(_current_email, "resolver") if _current_email else True
except Exception:
    _has_resolver = True  # si auth falla, mostrar la página (entorno dev)

_sistema_pages = [
    st.Page("pages/ajustes.py", title="Ajustes", icon="⚙"),
]
if _is_admin:
    _sistema_pages.append(
        st.Page("pages/admin.py", title="Administración", icon="🔑")
    )

_principal_pages = [
    st.Page("pages/inicio.py",   title="Inicio",      icon="🏠", default=True),
    st.Page("pages/chatbot.py",  title="JuanMitaBot", icon="🤖"),
]
if _has_resolver:
    _principal_pages.append(
        st.Page("pages/resolver.py", title="Resolver", icon="🎯")
    )

pg = st.navigation({
    "Principal": _principal_pages,
    "Contratos": [
        st.Page("pages/biblioteca.py",  title="Biblioteca",     icon="📚"),
        st.Page("pages/legal.py",       title="Analisis Legal", icon="⚖"),
        st.Page("pages/plantillas.py",  title="Plantillas",     icon="📄"),
    ],
    "Analisis": [
        st.Page("pages/metricas.py",    title="Metricas",         icon="📊"),
        st.Page("pages/calendario.py",  title="Calendario",       icon="📅"),
        st.Page("pages/normativo.py",   title="Gestor Normativo", icon="⚖"),
    ],
    "Sistema": _sistema_pages,
})
pg.run()
