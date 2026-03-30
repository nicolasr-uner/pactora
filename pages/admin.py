"""
admin.py — Panel de administración de Pactora CLM.

Solo accesible para usuarios con rol "admin".
Permite gestionar la whitelist de usuarios y sus permisos de contratos.
"""

import streamlit as st
from utils.shared import apply_styles, page_header, init_session_state
from utils.auth_manager import (
    get_all_users,
    add_user,
    remove_user,
    update_user_permissions,
    CONTRACT_TYPES,
    is_admin,
)

apply_styles()
init_session_state()

# ─── Verificación de acceso ───────────────────────────────────────────────────

try:
    _logged_in = st.user.is_logged_in
    _user_email = st.user.email if _logged_in else ""
except Exception:
    _logged_in = False
    _user_email = ""

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
    "Gestiona quién puede acceder a Pactora CLM y qué contratos puede ver cada usuario. "
    "Los cambios se guardan automáticamente en Google Drive."
)

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _role_badge(role: str) -> str:
    if role == "admin":
        return "🔑 Admin"
    return "👁 Viewer"


def _types_display(allowed: list) -> str:
    if not allowed or "*" in allowed:
        return "✅ Todos"
    return ", ".join(allowed)


# ─── Tab layout ───────────────────────────────────────────────────────────────

tab_users, tab_add, tab_perms = st.tabs([
    "👥 Usuarios autorizados",
    "➕ Agregar usuario",
    "🔧 Editar permisos",
])


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — Lista de usuarios
# ════════════════════════════════════════════════════════════════════════════════

with tab_users:
    st.markdown("### Usuarios con acceso")

    col_reload, _ = st.columns([1, 5])
    with col_reload:
        if st.button("🔄 Recargar", key="reload_users"):
            from utils.auth_manager import _invalidate_cache
            _invalidate_cache()
            st.rerun()

    users = get_all_users(force_reload=False)
    active_users = [u for u in users if u.get("active", True)]

    if not active_users:
        st.info("No hay usuarios autorizados aún. Usa la pestaña **Agregar usuario** para comenzar.")
    else:
        # Tabla de usuarios
        import pandas as pd

        rows = []
        for u in active_users:
            rows.append({
                "Correo":             u["email"],
                "Rol":                _role_badge(u.get("role", "viewer")),
                "Tipos de contrato":  _types_display(u.get("allowed_types", ["*"])),
                "Agregado por":       u.get("added_by", "—"),
                "Fecha":              u.get("added_at", "—")[:10],
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### Eliminar usuario")
        st.caption("El usuario perderá acceso inmediatamente (no se puede deshacer desde aquí).")

        emails_removable = [
            u["email"] for u in active_users
            if u["email"] != _user_email   # no te puedes eliminar a ti mismo
        ]
        if not emails_removable:
            st.info("No hay otros usuarios para eliminar.")
        else:
            email_to_remove = st.selectbox(
                "Seleccionar usuario a eliminar",
                options=emails_removable,
                key="remove_select",
            )
            if st.button("🗑 Eliminar acceso", type="primary", key="btn_remove"):
                ok, msg = remove_user(email_to_remove)
                if ok:
                    st.success(f"Usuario '{email_to_remove}' eliminado correctamente.")
                    st.rerun()
                else:
                    st.error(f"Error: {msg}")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — Agregar usuario
# ════════════════════════════════════════════════════════════════════════════════

with tab_add:
    st.markdown("### Agregar usuario")
    st.caption(
        "El usuario debe autenticarse con Google (OAuth). "
        "Su correo exacto debe aparecer aquí para que el sistema le permita entrar."
    )

    with st.form("form_add_user", clear_on_submit=True):
        new_email = st.text_input(
            "Correo electrónico de Google",
            placeholder="usuario@ejemplo.com",
        )
        new_role = st.radio(
            "Rol",
            options=["viewer", "admin"],
            format_func=lambda r: "👁 Viewer — solo lectura" if r == "viewer" else "🔑 Admin — acceso total + administración",
            horizontal=True,
        )

        st.markdown("**Tipos de contrato permitidos**")
        all_types_toggle = st.checkbox("✅ Todos los tipos", value=True, key="add_all_types")
        if not all_types_toggle:
            selected_types = st.multiselect(
                "Seleccionar tipos específicos",
                options=CONTRACT_TYPES,
                key="add_types_select",
            )
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
                st.success(f"✅ '{new_email}' agregado como **{new_role}** con tipos: {_types_display(selected_types)}.")
                st.rerun()
            else:
                st.error(f"No se pudo agregar: {msg}")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — Editar permisos
# ════════════════════════════════════════════════════════════════════════════════

with tab_perms:
    st.markdown("### Editar permisos de usuario")
    st.caption("Cambia el rol o los tipos de contratos que puede ver un usuario existente.")

    users_for_edit = get_all_users(force_reload=False)
    active_for_edit = [u for u in users_for_edit if u.get("active", True)]

    if not active_for_edit:
        st.info("No hay usuarios para editar.")
    else:
        email_to_edit = st.selectbox(
            "Seleccionar usuario",
            options=[u["email"] for u in active_for_edit],
            key="edit_select",
        )
        target = next((u for u in active_for_edit if u["email"] == email_to_edit), None)

        if target:
            st.markdown(f"**Usuario:** `{target['email']}`")

            with st.form("form_edit_perms"):
                edit_role = st.radio(
                    "Rol",
                    options=["viewer", "admin"],
                    index=0 if target.get("role") == "viewer" else 1,
                    format_func=lambda r: "👁 Viewer" if r == "viewer" else "🔑 Admin",
                    horizontal=True,
                    key="edit_role_radio",
                )

                st.markdown("**Tipos de contrato permitidos**")
                current_types = target.get("allowed_types", ["*"])
                all_types_toggle_edit = st.checkbox(
                    "✅ Todos los tipos",
                    value="*" in current_types,
                    key="edit_all_types",
                )
                if not all_types_toggle_edit:
                    preselected = [t for t in current_types if t != "*"]
                    edit_types = st.multiselect(
                        "Seleccionar tipos específicos",
                        options=CONTRACT_TYPES,
                        default=[t for t in preselected if t in CONTRACT_TYPES],
                        key="edit_types_select",
                    )
                else:
                    edit_types = ["*"]

                save_btn = st.form_submit_button("Guardar cambios", type="primary")

            if save_btn:
                final_types = edit_types if edit_types else ["*"]
                ok, msg = update_user_permissions(
                    email=email_to_edit,
                    role=edit_role,
                    allowed_types=final_types,
                )
                if ok:
                    st.success(f"✅ Permisos de '{email_to_edit}' actualizados.")
                    st.rerun()
                else:
                    st.error(f"Error: {msg}")


# ─── Información de ayuda ─────────────────────────────────────────────────────

with st.expander("ℹ️ ¿Cómo funcionan los permisos?"):
    st.markdown("""
**Roles:**
- **Admin** — acceso completo a toda la app + este panel de administración.
- **Viewer** — acceso de solo lectura a contratos según los tipos asignados.

**Tipos de contrato:**
- Si el usuario tiene `✅ Todos`, puede ver cualquier contrato.
- Si tiene tipos específicos (ej. `PPA`, `EPC`), solo verá contratos cuyo nombre
  o tipo coincida con esa lista.
- La coincidencia busca el tipo dentro del nombre del archivo y en el campo
  `contract_type` si está disponible en los metadatos.

**Almacenamiento:**
- Esta lista se guarda en `_pactora_auth_users.json` en tu carpeta raíz de Google Drive.
- Puedes editarla directamente en Drive si necesitas un cambio de emergencia.
- También puedes definir admins de respaldo en `secrets.toml` → `auth_config.admin_emails`.
    """)
