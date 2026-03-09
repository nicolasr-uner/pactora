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
from utils.shared import init_session_state, juanmitabot_sidebar

st.set_page_config(
    page_title="Pactora CLM — Unergy",
    page_icon="🏛",
    layout="wide"
)

# Inicializar estado global (chatbot, session_state defaults) una sola vez por carga
init_session_state()

# Sidebar persistente con JuanMitaBot en todas las páginas
juanmitabot_sidebar()

pg = st.navigation({
    "Principal": [
        st.Page("pages/inicio.py",      title="Inicio",         icon="🏠", default=True),
        st.Page("pages/chatbot.py",     title="JuanMitaBot",    icon="🤖"),
    ],
    "Contratos": [
        st.Page("pages/legal.py",       title="Analisis Legal", icon="⚖"),
        st.Page("pages/plantillas.py",  title="Plantillas",     icon="📄"),
    ],
    "Analisis": [
        st.Page("pages/metricas.py",    title="Metricas",       icon="📊"),
        st.Page("pages/calendario.py",  title="Calendario",     icon="📅"),
    ],
    "Sistema": [
        st.Page("pages/ajustes.py",     title="Ajustes",        icon="⚙"),
    ],
})
pg.run()
