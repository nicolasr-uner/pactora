import streamlit as st
from datetime import datetime
from utils.shared import apply_styles, page_header, init_session_state
from utils.auth import load_users_config, save_users_config, is_admin
from utils.drive_manager import get_folder_contents

# Verificación de seguridad adicional
if not is_admin():
    st.error("No tienes permisos para ver esta página.")
    st.stop()

apply_styles()
init_session_state()
page_header()

st.markdown("## 🔐 Panel de Administración")
st.markdown("Gestiona los usuarios que tienen acceso a Pactora CLM y sus permisos.")

config = load_users_config()
users = config.get("users", {})

col1, col2 = st.columns([8, 2])
with col1:
    st.subheader(f"Usuarios Registrados ({len(users)})")

# --- Añadir nuevo usuario ---
with st.expander("➕ Añadir Nuevo Usuario"):
    with st.form("new_user_form", clear_on_submit=True):
        n_email = st.text_input("Correo Electrónico (Google Workspace)")
        n_name = st.text_input("Nombre Completo")
        n_role = st.selectbox("Rol", ["viewer", "admin"])
        
        if st.form_submit_button("Registrar Usuario", type="primary"):
            n_email = n_email.strip().lower()
            if n_email and "@" in n_email:
                if n_email in users:
                    st.warning("Este usuario ya está registrado.")
                else:
                    users[n_email] = {
                        "name": n_name.strip() or "Usuario Invitado",
                        "active": True,
                        "role": n_role,
                        "allowed_folders": ["all"],
                        "allowed_contract_types": ["all"],
                        "added_at": datetime.utcnow().isoformat() + "Z",
                        "added_by": getattr(getattr(st, "user", None), "email", "system")
                    }
                    if n_role == "admin" and n_email not in config.get("admins", []):
                        if "admins" not in config:
                            config["admins"] = []
                        config["admins"].append(n_email)
                    save_users_config(config)
                    st.success(f"Usuario {n_email} registrado exitosamente.")
                    st.rerun()
            else:
                st.error("Ingresa un correo válido.")

st.divider()

# --- Tabla/Lista de Usuarios ---
# Listado de carpetas raíz (se usa en edición de permisos)
root_id = st.secrets.get("DRIVE_ROOT_FOLDER_ID", "")
available_folders = get_folder_contents(root_id) if root_id else []

for email, data in users.items():
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
        
        status_icon = "🟢" if data.get("active") else "🔴"
        role_label = "Administrador" if data.get("role") == "admin" else "Visor"
        c1.markdown(f"**{data.get('name', 'Sin Nombre')}**<br><span style='font-size:0.8em;color:gray'>{email}</span>", unsafe_allow_html=True)
        c2.markdown(f"{status_icon} **{role_label}**")
        
        access_lbl = "Acceso Completo" if "all" in data.get("allowed_folders", []) else f"{len(data.get('allowed_folders', []))} Carpeta(s)"
        c3.markdown(f"📂 {access_lbl}")
        
        with c4:
            if st.popover(f"⚙️ Editar"):
                st.write(f"### Permisos de {email}")
                
                new_active = st.toggle("Cuenta Activa", value=data.get("active", False), key=f"act_{email}")
                new_role = st.selectbox("Rol", ["viewer", "admin"], index=0 if data.get("role") != "admin" else 1, key=f"rol_{email}")
                
                st.subheader("Acceso a Carpetas (Raíz Pactora)")
                all_folders = st.checkbox("Acceso Total a TODAS las carpetas", value="all" in data.get("allowed_folders", ["all"]), key=f"allf_{email}")
                
                selected_folders = []
                if not all_folders:
                    curr_selected = data.get("allowed_folders", [])
                    st.write("Seleciona las carpetas permitidas:")
                    for f in available_folders:
                        # Si es carpeta, mostrar
                        if f.get("mimeType") == "application/vnd.google-apps.folder":
                            val = f["id"] in curr_selected
                            if st.checkbox(f"📁 {f['name']}", value=val, key=f"fchk_{email}_{f['id']}"):
                                selected_folders.append(f["id"])
                
                st.subheader("Tipos de Contrato Permitidos")
                all_types = st.checkbox("Todos los tipos", value="all" in data.get("allowed_contract_types", ["all"]), key=f"allt_{email}")
                
                selected_types = []
                if not all_types:
                    curr_types = data.get("allowed_contract_types", [])
                    t_options = {"pdf": "PDF", "docx": "Word", "xlsx": "Excel", "txt": "Texto"}
                    cols = st.columns(4)
                    i = 0
                    for ext, lbl in t_options.items():
                        val = ext in curr_types
                        if cols[i%4].checkbox(lbl, value=val, key=f"tchk_{email}_{ext}"):
                            selected_types.append(ext)
                        i += 1
                
                if st.button("Guardar Cambios", type="primary", key=f"save_{email}"):
                    data["active"] = new_active
                    data["role"] = new_role
                    
                    if all_folders:
                        data["allowed_folders"] = ["all"]
                    else:
                        data["allowed_folders"] = selected_folders
                        
                    if all_types:
                        data["allowed_contract_types"] = ["all"]
                    else:
                        data["allowed_contract_types"] = selected_types
                    
                    # Logica extra para cambiar admins list
                    if new_role == "admin" and email not in config.get("admins", []):
                        if "admins" not in config: config["admins"] = []
                        config["admins"].append(email)
                    elif new_role != "admin" and email in config.get("admins", []):
                        config["admins"].remove(email)
                        
                    users[email] = data
                    save_users_config(config)
                    st.success("Permisos guardados.")
                    st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
