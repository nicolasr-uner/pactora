"""
admin.py — Panel de administración de Pactora CLM.
Solo accesible para usuarios con rol "admin".
"""

import streamlit as st
from utils.shared import apply_styles, page_header, init_session_state
from utils.auth_manager import (
    get_all_users,
    add_user,
    remove_user,
    update_user_permissions,
    is_admin,
    CONTRACT_TYPES,
    ROLES,
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
st.caption("Gestiona quién puede acceder a Pactora CLM y qué contratos puede ver cada usuario.")

tab_users, tab_add, tab_perms = st.tabs([
    "👥 Usuarios autorizados",
    "➕ Agregar usuario",
    "🔧 Editar permisos",
])

# ─── Helpers visuales ────────────────────────────────────────────────────────

_ROLE_LABELS = {
    "admin":    "🔑 Admin",
    "legal":    "⚖ Legal",
    "analista": "📊 Analista",
    "viewer":   "👁 Viewer",
}

def _role_label(r: str) -> str:
    return _ROLE_LABELS.get(r, f"• {r}")

_ROLE_OPTIONS = list(ROLES.keys())

def _role_fmt(r: str) -> str:
    return ROLES.get(r, r)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — Lista de usuarios
# ════════════════════════════════════════════════════════════════════════════════

with tab_users:
    st.markdown("### Usuarios con acceso")

    col_reload, _ = st.columns([1, 5])
    with col_reload:
        if st.button("🔄 Recargar", key="reload_users"):
            _invalidate_cache()
            st.rerun()

    users = get_all_users(force_reload=False)
    active_users = [u for u in users if u.get("active", True)]

    if not active_users:
        st.info("No hay usuarios autorizados. Usa **Agregar usuario** para comenzar.")
    else:
        import pandas as pd

        rows = []
        for u in active_users:
            allowed = u.get("allowed_types", ["*"])
            rows.append({
                "Correo":            u["email"],
                "Rol":               _role_label(u.get("role", "viewer")),
                "Tipos de contrato": "✅ Todos" if "*" in allowed else ", ".join(allowed),
                "Agregado por":      u.get("added_by", "—"),
                "Fecha":             u.get("added_at", "—")[:10],
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

        st.markdown("---")
        st.markdown("#### Eliminar usuario")

        removable = [u["email"] for u in active_users if u["email"] != _user_email]
        if not removable:
            st.info("No hay otros usuarios para eliminar.")
        else:
            email_to_remove = st.selectbox("Seleccionar usuario", removable, key="remove_select")
            if st.button("🗑 Eliminar acceso", type="primary", key="btn_remove"):
                ok, msg = remove_user(email_to_remove)
                if ok:
                    st.success(f"Usuario '{email_to_remove}' eliminado.")
                    st.rerun()
                else:
                    st.error(f"Error: {msg}")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — Agregar usuario
# ════════════════════════════════════════════════════════════════════════════════

with tab_add:
    st.markdown("### Agregar usuario")
    st.caption("El usuario debe iniciar sesión con la cuenta de Google exacta que registres aquí.")

    with st.form("form_add_user", clear_on_submit=True):
        new_email = st.text_input("Correo electrónico de Google", placeholder="usuario@ejemplo.com")
        new_role  = st.radio(
            "Rol",
            options=_ROLE_OPTIONS,
            format_func=_role_fmt,
            index=_ROLE_OPTIONS.index("viewer"),
            horizontal=False,
        )

        st.markdown("**Tipos de contrato permitidos**")
        all_types = st.checkbox("✅ Todos los tipos", value=True, key="add_all_types")
        if not all_types:
            selected_types = st.multiselect("Tipos específicos", options=CONTRACT_TYPES)
        else:
            selected_types = ["*"]

        submitted = st.form_submit_button("Agregar usuario", type="primary")

    if submitted:
        if not new_email or "@" not in new_email:
            st.error("Ingresa un correo válido.")
        else:
            ok, msg = add_user(
                email=new_email,
                role=new_role,
                allowed_types=selected_types if selected_types else ["*"],
                added_by=_user_email,
            )
            if ok:
                tipos_str = "todos los tipos" if "*" in selected_types else ", ".join(selected_types)
                st.success(
                    f"✅ **'{new_email}'** agregado como **{_role_label(new_role)}** "
                    f"con acceso a: {tipos_str}."
                )
                st.rerun()
            else:
                st.error(f"No se pudo agregar: {msg}")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — Editar permisos
# ════════════════════════════════════════════════════════════════════════════════

with tab_perms:
    st.markdown("### Editar permisos de usuario")

    all_active = get_all_users(force_reload=False)
    active_for_edit = [u for u in all_active if u.get("active", True)]

    if not active_for_edit:
        st.info("No hay usuarios para editar.")
    else:
        email_to_edit = st.selectbox(
            "Seleccionar usuario",
            [u["email"] for u in active_for_edit],
            key="edit_select",
        )
        target = next((u for u in active_for_edit if u["email"] == email_to_edit), None)

        if target:
            current_role = target.get("role", "viewer")
            if current_role not in _ROLE_OPTIONS:
                current_role = "viewer"

            with st.form("form_edit_perms"):
                edit_role = st.radio(
                    "Rol",
                    options=_ROLE_OPTIONS,
                    index=_ROLE_OPTIONS.index(current_role),
                    format_func=_role_fmt,
                    horizontal=False,
                    key="edit_role_radio",
                )

                current_types = target.get("allowed_types", ["*"])
                all_types_edit = st.checkbox(
                    "✅ Todos los tipos",
                    value="*" in current_types,
                    key="edit_all_types",
                )
                if not all_types_edit:
                    preselected = [t for t in current_types if t != "*" and t in CONTRACT_TYPES]
                    edit_types = st.multiselect(
                        "Tipos específicos",
                        options=CONTRACT_TYPES,
                        default=preselected,
                        key="edit_types_select",
                    )
                else:
                    edit_types = ["*"]

                save_btn = st.form_submit_button("Guardar cambios", type="primary")

            if save_btn:
                ok, msg = update_user_permissions(
                    email=email_to_edit,
                    role=edit_role,
                    allowed_types=edit_types if edit_types else ["*"],
                )
                if ok:
                    st.success(f"✅ Permisos de '{email_to_edit}' actualizados a **{_role_label(edit_role)}**.")
                    st.rerun()
                else:
                    st.error(f"Error: {msg}")


# ─── Info ─────────────────────────────────────────────────────────────────────

with st.expander("ℹ️ ¿Cómo funcionan los roles y permisos?"):
    st.markdown("""
**Roles disponibles:**

| Rol | Icono | Acceso |
|-----|-------|--------|
| **Admin** | 🔑 | Acceso completo + panel de administración + ajustes |
| **Legal Senior** | ⚖ | Inicio, JuanMitaBot, Biblioteca, Análisis Legal, Plantillas, Normativo |
| **Analista** | 📊 | Inicio, JuanMitaBot, Biblioteca, Métricas, Calendario, Normativo |
| **Viewer** | 👁 | Solo JuanMitaBot y Biblioteca (lectura) |

**Tipos de contrato:**
- `✅ Todos` — puede ver cualquier contrato.
- Tipos específicos (ej. `PPA`, `EPC`) — solo ve contratos cuyo nombre o tipo coincida.

**Almacenamiento:** Los datos se guardan en `_pactora_auth_users.json` en tu carpeta raíz de Google Drive.
Si Drive no está disponible, se guarda localmente como respaldo temporal.
Los admins definidos en `secrets.toml → auth_config.admin_emails` siempre tienen acceso como respaldo.
    """)
