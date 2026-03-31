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
    FEATURES,
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
st.caption("Gestiona quién puede acceder a Pactora CLM, qué contratos ve cada usuario y a qué funciones tiene acceso.")

tab_users, tab_add, tab_perms, tab_features = st.tabs([
    "👥 Usuarios autorizados",
    "➕ Agregar usuario",
    "🔧 Editar permisos",
    "🎛️ Permisos de funciones",
])


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
            features = u.get("features", ["*"])
            rows.append({
                "Correo":            u["email"],
                "Rol":               "🔑 Admin" if u.get("role") == "admin" else "👁 Viewer",
                "Tipos de contrato": "✅ Todos" if "*" in allowed else ", ".join(allowed),
                "Funciones":         "✅ Todas" if (u.get("role") == "admin" or not features or "*" in features)
                                     else str(len(features)),
                "Agregado por":      u.get("added_by", "—"),
                "Fecha":             u.get("added_at", "—")[:10],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

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
            options=["viewer", "admin"],
            format_func=lambda r: "👁 Viewer — solo lectura" if r == "viewer" else "🔑 Admin — acceso total + administración",
            horizontal=True,
        )

        st.markdown("**Tipos de contrato permitidos**")
        all_types = st.checkbox("✅ Todos los tipos", value=True, key="add_all_types")
        if not all_types:
            selected_types = st.multiselect("Tipos específicos", options=CONTRACT_TYPES)
        else:
            selected_types = ["*"]

        st.markdown("**Funciones permitidas**")
        all_features = st.checkbox("✅ Todas las funciones", value=True, key="add_all_features")
        if not all_features:
            selected_features = st.multiselect(
                "Funciones específicas",
                options=list(FEATURES.keys()),
                format_func=lambda k: FEATURES[k],
            )
        else:
            selected_features = ["*"]

        submitted = st.form_submit_button("Agregar usuario", type="primary")

    if submitted:
        if not new_email or "@" not in new_email:
            st.error("Ingresa un correo válido.")
        else:
            ok, msg = add_user(
                email=new_email,
                role=new_role,
                allowed_types=selected_types if selected_types else ["*"],
                features=selected_features if selected_features else ["*"],
                added_by=_user_email,
            )
            if ok:
                tipos_str = "todos los tipos" if "*" in selected_types else ", ".join(selected_types)
                funcs_str = "todas las funciones" if "*" in selected_features else ", ".join(
                    FEATURES.get(f, f) for f in selected_features
                )
                st.success(
                    f"✅ '{new_email}' agregado como **{new_role}**.\n"
                    f"Contratos: {tipos_str} | Funciones: {funcs_str}."
                )
                st.rerun()
            else:
                st.error(f"No se pudo agregar: {msg}")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — Editar permisos (tipos de contrato + rol)
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
            with st.form("form_edit_perms"):
                edit_role = st.radio(
                    "Rol",
                    options=["viewer", "admin"],
                    index=0 if target.get("role") == "viewer" else 1,
                    format_func=lambda r: "👁 Viewer" if r == "viewer" else "🔑 Admin",
                    horizontal=True,
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
                    st.success(f"✅ Permisos de '{email_to_edit}' actualizados.")
                    st.rerun()
                else:
                    st.error(f"Error: {msg}")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — Permisos de funciones (matriz de checkboxes)
# ════════════════════════════════════════════════════════════════════════════════

with tab_features:
    st.markdown("### Permisos de funciones por usuario")
    st.caption(
        "Controla a qué funciones tiene acceso cada viewer. "
        "Los admins siempre tienen acceso a todo, independientemente de esta tabla."
    )

    import pandas as pd

    all_users_feat = get_all_users(force_reload=False)
    # Solo viewers activos — los admins no necesitan gestión
    viewers = [u for u in all_users_feat if u.get("active", True) and u.get("role") != "admin"]

    if not viewers:
        st.info("No hay viewers para gestionar. Agrega usuarios con rol Viewer primero.")
    else:
        # Construir dataframe con una fila por viewer y una columna bool por feature
        feat_ids   = list(FEATURES.keys())
        feat_names = [FEATURES[f] for f in feat_ids]

        rows = []
        for u in viewers:
            user_features = u.get("features", ["*"])
            has_all = not user_features or "*" in user_features
            row = {"Usuario": u["email"]}
            for fid, fname in zip(feat_ids, feat_names):
                row[fname] = has_all or fid in user_features
            rows.append(row)

        df = pd.DataFrame(rows)

        col_cfg = {"Usuario": st.column_config.TextColumn("Usuario", disabled=True, width="medium")}
        for fname in feat_names:
            col_cfg[fname] = st.column_config.CheckboxColumn(fname, default=True, width="small")

        st.markdown("Marca ✅ para dar acceso, desmarca para revocar:")
        edited = st.data_editor(
            df,
            column_config=col_cfg,
            use_container_width=True,
            hide_index=True,
            key="features_matrix_editor",
        )

        col_save, col_info = st.columns([2, 5])
        with col_save:
            save_features = st.button("💾 Guardar permisos de funciones", type="primary")
        with col_info:
            st.caption("Los cambios se aplican al siguiente inicio de sesión del usuario.")

        if save_features:
            errors = []
            saved = 0
            for _, row in edited.iterrows():
                email = row["Usuario"]
                new_features = [fid for fid, fname in zip(feat_ids, feat_names) if row[fname]]
                ok, msg = update_user_permissions(email=email, features=new_features if new_features else [])
                if ok:
                    saved += 1
                else:
                    errors.append(f"{email}: {msg}")
            if saved:
                _invalidate_cache()
                st.success(f"✅ Permisos actualizados para {saved} usuario(s).")
                st.rerun()
            if errors:
                for e in errors:
                    st.error(e)


# ─── Info ─────────────────────────────────────────────────────────────────────

with st.expander("ℹ️ ¿Cómo funcionan los permisos?"):
    st.markdown("""
**Roles:**
- **Admin** — acceso completo + este panel de administración + todas las funciones.
- **Viewer** — ve solo los contratos asignados y las funciones que le habilites.

**Tipos de contrato:**
- `✅ Todos` — puede ver cualquier contrato.
- Tipos específicos (ej. `PPA`, `EPC`) — solo ve contratos cuyo nombre o tipo coincida.

**Funciones disponibles:**
- 💬 **JuanMitaBot Chat** — acceso al chatbot de IA
- 🎯 **Resolver con JuanMitaBot** — flujo guiado de análisis contractual profundo
- ⚖️ **Análisis Legal** — análisis de riesgo y métricas de contratos individuales
- 🔀 **Comparar Contratos** — comparación lado a lado de múltiples contratos
- 📤 **Exportar Informes** — generación y descarga de informes PDF

**Almacenamiento:** Los datos se guardan en Google Sheets (`AUTH_USERS_SHEET_ID`).
Los admins definidos en `secrets.toml → auth_config.admin_emails` siempre tienen acceso como respaldo.
    """)
