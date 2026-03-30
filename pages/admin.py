"""
admin.py — Panel de administración de Pactora CLM.
Solo accesible para usuarios con rol "admin".
"""

import streamlit as st
from utils.shared import apply_styles, page_header, init_session_state
from utils.auth_manager import (
    get_all_users,
    is_admin,
    CONTRACT_TYPES,
    generate_toml_snippet,
    _invalidate_cache,
)

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

if not is_admin(_user_email):
    st.error("⛔ Acceso denegado. Esta sección es exclusiva para administradores.")
    st.caption(f"Tu correo ({_user_email}) no tiene permisos de administrador.")
    st.stop()

# ─── Header ───────────────────────────────────────────────────────────────────

page_header("Administración de Acceso")
st.markdown("## Panel de Administración")
st.caption(
    "Los usuarios se gestionan desde **Streamlit Cloud → Settings → Secrets**. "
    "Usa esta página para ver quién tiene acceso y generar el TOML listo para pegar."
)

# ─── Tabs ─────────────────────────────────────────────────────────────────────

tab_users, tab_add = st.tabs(["👥 Usuarios autorizados", "➕ Agregar usuario"])

# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — Lista de usuarios actuales
# ════════════════════════════════════════════════════════════════════════════════

with tab_users:
    st.markdown("### Usuarios con acceso")

    col_reload, _ = st.columns([1, 5])
    with col_reload:
        if st.button("🔄 Recargar", key="reload_users"):
            _invalidate_cache()
            st.rerun()

    users = get_all_users(force_reload=False)

    if not users:
        st.warning(
            "No hay usuarios configurados. Agrega `admin_emails` en tus secrets de Streamlit Cloud."
        )
    else:
        import pandas as pd

        rows = []
        for u in users:
            allowed = u.get("allowed_types", ["*"])
            rows.append({
                "Correo": u["email"],
                "Rol":    "🔑 Admin" if u.get("role") == "admin" else "👁 Viewer",
                "Tipos de contrato": "✅ Todos" if "*" in allowed else ", ".join(allowed),
                "Fuente": u.get("source", "secrets"),
            })

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with st.expander("🗑 ¿Cómo eliminar un usuario?"):
        st.markdown("""
1. Ve a **Streamlit Cloud → tu app → Settings → Secrets**
2. Encuentra el bloque `[[auth_config.users]]` del correo que quieres eliminar
3. Borra ese bloque completo y guarda
4. La app se recarga automáticamente

Para remover un **admin**, quita su correo del array `admin_emails`.
        """)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — Generador de TOML para agregar usuario
# ════════════════════════════════════════════════════════════════════════════════

with tab_add:
    st.markdown("### Agregar usuario")
    st.info(
        "Completa el formulario → copia el TOML generado → pégalo en "
        "**Streamlit Cloud → Settings → Secrets** → guarda.",
        icon="📋",
    )

    with st.form("form_generate_toml"):
        new_email = st.text_input(
            "Correo electrónico de Google",
            placeholder="usuario@empresa.com",
        )
        new_role = st.radio(
            "Rol",
            options=["viewer", "admin"],
            format_func=lambda r: "👁 Viewer — solo lectura" if r == "viewer" else "🔑 Admin — acceso total",
            horizontal=True,
        )

        all_types = st.checkbox("✅ Acceso a todos los tipos de contrato", value=True)
        if not all_types:
            selected_types = st.multiselect("Tipos permitidos", options=CONTRACT_TYPES)
        else:
            selected_types = ["*"]

        generate_btn = st.form_submit_button("Generar TOML", type="primary")

    if generate_btn:
        if not new_email or "@" not in new_email:
            st.error("Ingresa un correo válido.")
        else:
            snippet = generate_toml_snippet(
                email=new_email.strip().lower(),
                role=new_role,
                allowed_types=selected_types,
            )
            st.success("✅ TOML generado. Cópialo y pégalo en tus Secrets:")
            st.code(snippet, language="toml")
            st.markdown(
                "**Pasos:** Copia el bloque → "
                "[Streamlit Cloud](https://share.streamlit.io) → tu app → **Settings → Secrets** → "
                "pega al final → **Save**"
            )


# ─── Formato de referencia ────────────────────────────────────────────────────

with st.expander("ℹ️ Formato completo de secrets.toml"):
    st.code("""
[auth_config]
admin_emails = ["tu@empresa.com", "otro-admin@empresa.com"]

[[auth_config.users]]
email         = "colega@empresa.com"
role          = "viewer"
allowed_types = ["*"]

[[auth_config.users]]
email         = "externo@gmail.com"
role          = "viewer"
allowed_types = ["PPA", "EPC"]
    """, language="toml")
