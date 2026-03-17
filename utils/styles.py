"""
styles.py — Estilos CSS y dark mode para Pactora CLM.
Paleta Unergy: #915BD8 (púrpura), #2C2039 (oscuro), #FDFAF7 (fondo), #F6FF72 (amarillo).
"""
import streamlit as st

STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Lato:wght@400;700;900&display=swap');
.stApp { background-color: #FDFAF7; font-family: 'Lato', sans-serif; color: #212121; }
section[data-testid="stSidebar"] { background-color: #2C2039 !important; }
[data-testid="stSidebar"] * { color: #FDFAF7 !important; }
/* Chat input en sidebar — translúcido, integrado con sidebar */
[data-testid="stSidebar"] [data-testid="stChatInput"] textarea,
[data-testid="stSidebar"] [data-testid="stChatInput"] input {
    color: #E8E0F0 !important;
    background: transparent !important;
}
[data-testid="stSidebar"] [data-testid="stChatInput"] {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(145,91,216,0.35) !important;
    border-radius: 14px !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] [data-testid="stChatInput"] textarea::placeholder {
    color: #9d87c0 !important;
}
/* Botón enviar chat sidebar */
[data-testid="stSidebar"] button[data-testid="stChatInputSubmitButton"] {
    background-color: #915BD8 !important; border: none !important;
    border-radius: 10px !important;
}
[data-testid="stSidebar"] button[data-testid="stChatInputSubmitButton"] svg {
    fill: white !important;
}
/* Popover ℹ️ — botón trigger */
[data-testid="stPopover"] button {
    background-color: rgba(145,91,216,0.08) !important;
    border: 1px solid rgba(145,91,216,0.25) !important;
    color: #915BD8 !important;
}
.factora-card {
    background: rgba(255,255,255,0.9); border-radius: 16px; padding: 22px;
    box-shadow: 0 6px 24px rgba(145,91,216,0.07); border: 1px solid rgba(145,91,216,0.12);
    margin-bottom: 18px;
}
.card-title {
    font-size: 17px; font-weight: 900; color: #2C2039; margin-bottom: 14px;
    border-left: 4px solid #915BD8; padding-left: 10px;
}
.metric-card {
    background: white; border-radius: 12px; padding: 18px; text-align: center;
    box-shadow: 0 4px 16px rgba(145,91,216,0.08); border: 1px solid rgba(145,91,216,0.1);
}
.metric-val { font-size: 34px; font-weight: 900; color: #915BD8; }
.metric-lbl { font-size: 12px; color: #666; margin-top: 4px; }
.version-badge {
    background: #915BD8; color: white; border-radius: 4px;
    padding: 2px 8px; font-size: 11px; font-weight: 700;
}
div[data-testid="stButton"] > button {
    background-color: #915BD8 !important; color: white !important; border: none;
    border-radius: 8px; font-weight: 700; padding: 8px 20px; transition: background 0.2s;
}
div[data-testid="stButton"] > button:hover { background-color: #7a48c0 !important; }
/* Tabs — active tab Unergy purple */
button[data-testid="stTab"][aria-selected="true"] {
    border-bottom: 3px solid #915BD8 !important; color: #915BD8 !important; font-weight: 700;
}
/* Logo classes */
.pactora-title { color: #2C2039; }
.pactora-sub { color: #915BD8; }
/* Text inputs — elimina fondo amarillo de Streamlit, borde purple en focus */
.stTextInput input, .stTextArea textarea {
    background-color: #ffffff !important;
    color: #212121 !important;
    border-color: #d0c4e8 !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    background-color: #ffffff !important;
    border-color: #915BD8 !important;
    box-shadow: 0 0 0 2px rgba(145,91,216,0.15) !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder {
    color: #9d87c0 !important; opacity: 1 !important;
}
</style>
"""

DARK_STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Lato:wght@400;700;900&display=swap');
.stApp { background-color: #1A1225; font-family: 'Lato', sans-serif; color: #E8E0F0; }
section[data-testid="stSidebar"] { background-color: #120D1A !important; }
[data-testid="stSidebar"] * { color: #E8E0F0 !important; }
[data-testid="stSidebar"] [data-testid="stChatInput"] textarea,
[data-testid="stSidebar"] [data-testid="stChatInput"] input {
    color: #E8E0F0 !important;
    background: transparent !important;
}
[data-testid="stSidebar"] [data-testid="stChatInput"] {
    background: rgba(145,91,216,0.08) !important;
    border: 1px solid rgba(145,91,216,0.3) !important;
    border-radius: 14px !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] [data-testid="stChatInput"] textarea::placeholder {
    color: #9d87c0 !important;
}
/* Botón enviar chat sidebar */
[data-testid="stSidebar"] button[data-testid="stChatInputSubmitButton"] {
    background-color: #7a48c0 !important; border: none !important;
    border-radius: 10px !important;
}
[data-testid="stSidebar"] button[data-testid="stChatInputSubmitButton"] svg {
    fill: white !important;
}
/* Streamlit header/toolbar — fondo oscuro */
header[data-testid="stHeader"] {
    background: rgba(26,18,37,0.97) !important;
    border-bottom: 1px solid rgba(145,91,216,0.2) !important;
}
header[data-testid="stHeader"] * { color: #E8E0F0 !important; }
[data-testid="stToolbar"] { background: transparent !important; }
/* Popover */
[data-testid="stPopover"] button {
    background-color: rgba(145,91,216,0.15) !important;
    border: 1px solid rgba(145,91,216,0.35) !important;
    color: #C39DFF !important;
}
[data-testid="stPopoverBody"],
[data-testid="stPopover"] [data-testid="stMarkdownContainer"] {
    background-color: #2C2039 !important;
    color: #E8E0F0 !important;
}
.factora-card {
    background: #2C2039; border-radius: 16px; padding: 22px;
    box-shadow: 0 6px 24px rgba(145,91,216,0.18); border: 1px solid rgba(145,91,216,0.35);
    margin-bottom: 18px;
}
.card-title {
    font-size: 17px; font-weight: 900; color: #E8E0F0; margin-bottom: 14px;
    border-left: 4px solid #915BD8; padding-left: 10px;
}
.metric-card {
    background: #2C2039; border-radius: 12px; padding: 18px; text-align: center;
    box-shadow: 0 4px 16px rgba(145,91,216,0.18); border: 1px solid rgba(145,91,216,0.35);
}
.metric-val { font-size: 34px; font-weight: 900; color: #C39DFF; }
.metric-lbl { font-size: 12px; color: #9d87c0; margin-top: 4px; }
.version-badge {
    background: #915BD8; color: white; border-radius: 4px;
    padding: 2px 8px; font-size: 11px; font-weight: 700;
}
div[data-testid="stButton"] > button {
    background-color: #7a48c0 !important; color: white !important; border: none;
    border-radius: 8px; font-weight: 700; padding: 8px 20px; transition: background 0.2s;
}
div[data-testid="stButton"] > button:hover { background-color: #915BD8 !important; }
/* Input fields */
.stTextInput input, .stTextArea textarea, .stSelectbox select {
    background-color: #2C2039 !important; color: #E8E0F0 !important;
    border-color: rgba(145,91,216,0.4) !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder {
    color: #9d87c0 !important; opacity: 1 !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    background-color: #2C2039 !important;
    border-color: #915BD8 !important;
    box-shadow: 0 0 0 2px rgba(145,91,216,0.2) !important;
}
/* Tables and dataframes */
.stDataFrame { background: #2C2039 !important; }
/* Info/success/warning boxes */
.stAlert { background: #2C2039 !important; border-color: rgba(145,91,216,0.3) !important; }
/* Dividers */
hr { border-color: rgba(145,91,216,0.25) !important; }
/* Expanders */
.streamlit-expanderHeader,
[data-testid="stExpander"] summary {
    background: #2C2039 !important; color: #E8E0F0 !important;
}
[data-testid="stExpander"] { border-color: rgba(145,91,216,0.3) !important; }
/* Tabs */
button[data-testid="stTab"] { color: #9d87c0 !important; }
button[data-testid="stTab"][aria-selected="true"] {
    border-bottom: 3px solid #C39DFF !important; color: #C39DFF !important; font-weight: 700;
}
/* Caption and small text */
.stCaption, small { color: #9d87c0 !important; }
/* Main content blocks */
[data-testid="stMainBlockContainer"],
[data-testid="stVerticalBlock"],
[data-testid="column"] { background-color: transparent !important; }
/* Logo classes */
.pactora-title { color: #E8E0F0; }
.pactora-sub { color: #C39DFF; }
/* Heading overrides for dark mode */
h1, h2, h3, h4, h5, h6 { color: #E8E0F0 !important; }
p, li, label { color: #D0C8E0 !important; }
/* Override inline light backgrounds from pages */
.stApp [style*="background:#e8f5e9"],
.stApp [style*="background: #e8f5e9"],
.stApp [style*="background:#e3f2fd"],
.stApp [style*="background: #e3f2fd"],
.stApp [style*="background:#f3e5f5"],
.stApp [style*="background: #f3e5f5"],
.stApp [style*="background:#f9f5ff"],
.stApp [style*="background: #f9f5ff"],
.stApp [style*="background:white"],
.stApp [style*="background: white"],
.stApp [style*="background:#fff"],
.stApp [style*="background: #fff"],
.stApp [style*="background:rgba(255,255,255"],
.stApp [style*="background: rgba(255,255,255"] { background: #2C2039 !important; }
/* Override hardcoded dark text colors */
.stApp [style*="color:#2C2039"],
.stApp [style*="color: #2C2039"],
.stApp [style*="color:#1b5e20"],
.stApp [style*="color:#0d47a1"],
.stApp [style*="color:#4a148c"],
.stApp [style*="color:#212121"] { color: #E8E0F0 !important; }
.stApp [style*="color:#2e7d32"],
.stApp [style*="color:#666"],
.stApp [style*="color: #666"],
.stApp [style*="color:#888"],
.stApp [style*="color:#999"],
.stApp [style*="color:#aaa"] { color: #9d87c0 !important; }
</style>
"""


def apply_styles():
    """Aplica la hoja de estilos según el modo claro/oscuro activo."""
    dark = st.session_state.get("dark_mode", False)
    st.markdown(DARK_STYLES if dark else STYLES, unsafe_allow_html=True)


def dark_mode_toggle():
    """Botón de toggle dark/light mode en la sidebar."""
    with st.sidebar:
        dark = st.session_state.get("dark_mode", False)
        label = "☀️ Modo claro" if dark else "🌙 Modo oscuro"
        if st.button(label, key="toggle_dark_mode", width="stretch"):
            st.session_state["dark_mode"] = not dark
            st.rerun()
