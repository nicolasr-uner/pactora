import json
import logging
import io
from datetime import datetime
from typing import Dict, Any, List, Optional
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

import streamlit as st
from utils.auth_helper import get_drive_service

log = logging.getLogger("pactora")

CONFIG_FILENAME = "pactora_users.json"


@st.cache_data(ttl=300)
def load_users_config() -> Dict[str, Any]:
    """Descarga o inicializa pactora_users.json desde Drive (cacheado por 5 min)."""
    service = get_drive_service()
    if not service:
        log.warning("[auth] No hay servicio de Drive, usando config vacía.")
        return {"admins": [], "users": {}}

    try:
        root_id = st.secrets.get("DRIVE_ROOT_FOLDER_ID", "")
        # Buscar el archivo en la raíz
        query = f"'{root_id}' in parents and name='{CONFIG_FILENAME}' and trashed=false"
        results = service.files().list(
            q=query, spaces='drive', fields='files(id, name)'
        ).execute()
        files = results.get('files', [])
        
        if files:
            file_id = files[0]['id']
            request = service.files().get_media(fileId=file_id)
            file_io = io.BytesIO()
            downloader = MediaIoBaseDownload(file_io, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            file_io.seek(0)
            data = json.load(file_io)
            return data
        else:
            # Inicializar si no existe
            bootstrap_admin = ""
            try:
                bootstrap_admin = st.secrets["auth"]["bootstrap_admin"]
            except Exception:
                pass
            
            default_config = {
                "admins": [bootstrap_admin] if bootstrap_admin else [],
                "users": {}
            }
            if bootstrap_admin:
                default_config["users"][bootstrap_admin] = {
                    "name": "Administrador Bootstrap",
                    "active": True,
                    "role": "admin",
                    "allowed_folders": ["all"],
                    "allowed_contract_types": ["all"],
                    "added_at": datetime.utcnow().isoformat() + "Z",
                    "added_by": "system"
                }
            
            _save_to_drive(service, root_id, default_config, None)
            return default_config
            
    except Exception as e:
        log.error(f"[auth] Error cargando usuarios: {e}")
        return {"admins": [], "users": {}}


def _save_to_drive(service, root_id: str, data: Dict, file_id: Optional[str] = None):
    """Guarda el dict de usuarios en Drive como JSON."""
    file_metadata = {
        'name': CONFIG_FILENAME,
        'mimeType': 'application/json'
    }
    media = MediaIoBaseUpload(
        io.BytesIO(json.dumps(data, indent=2).encode('utf-8')),
        mimetype='application/json',
        resumable=True
    )
    if not file_id:
        file_metadata['parents'] = [root_id]
        service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
    else:
        service.files().update(
            fileId=file_id,
            media_body=media
        ).execute()


def save_users_config(config_data: Dict[str, Any]):
    """Guarda actualizando Drive y limpia caché."""
    service = get_drive_service()
    if not service:
        return
        
    try:
        root_id = st.secrets.get("DRIVE_ROOT_FOLDER_ID", "")
        query = f"'{root_id}' in parents and name='{CONFIG_FILENAME}' and trashed=false"
        results = service.files().list(
            q=query, spaces='drive', fields='files(id, name)'
        ).execute()
        files = results.get('files', [])
        
        file_id = files[0]['id'] if files else None
        _save_to_drive(service, root_id, config_data, file_id)
        
        # Limpiar caché
        load_users_config.clear()
    except Exception as e:
        log.error(f"[auth] Error guardando usuarios: {e}")


def get_current_user() -> Optional[Dict[str, Any]]:
    """Devuelve dict con permisos del usuario logueado o None."""
    if not getattr(st, "experimental_user", None) and not getattr(st, "user", None):
        # Fallback si st.user no existe en esta versión
        pass
    
    st_user = getattr(st, "user", getattr(st, "experimental_user", None))
    # Para Streamlit Community Cloud (OAuth):
    try:
        if not st_user or not getattr(st_user, "is_logged_in", False):
            # En local dev puede ser None o que no haya login
            # Simulamos login local si hay st.secrets["auth"]["bootstrap_admin"] solo si el core app.py lo permite
            pass
    except Exception:
        pass
        
    try:
        if st_user and hasattr(st_user, 'is_logged_in') and st_user.is_logged_in:
            email = getattr(st_user, "email", "desconocido@ejemplo.com")
            # En modo dev local, si el email es "test@example.com", se asume admin si coincide
        elif hasattr(st_user, "email"):
            # A veces st.user object en OSS no es muy completo localmente
            email = getattr(st_user, "email", None)
            if not email:
                return None
        else:
            # Modo manual/test (no production)
            return None
            
        config = load_users_config()
        if email in config.get("users", {}):
            u_data = config["users"][email]
            u_data["email"] = email
            return u_data
            
    except Exception as e:
        log.error(f"[auth] Error get_current_user: {e}")
        
    return None


def require_auth():
    """Bloquea la ejecución y muestra la pantalla de login o acceso denegado."""
    st_user = getattr(st, "user", getattr(st, "experimental_user", None))
    
    if not st_user or not getattr(st_user, 'is_logged_in', False):
        st.markdown(
            """
            <div style="text-align: center; margin-top: 100px;">
                <h1 style="font-size: 48px; color: #FFF;">🏛️ Pactora CLM</h1>
                <p style="color: #c9b8e8; font-size: 18px; margin-bottom: 40px;">Sistema Inteligente de Contratos — Unergy</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.info("Debes iniciar sesión con tu cuenta de Google (Unergy) para continuar.", icon="🔒")
            if st.button("Continuar con Google", use_container_width=True, type="primary"):
                if hasattr(st, "login"):
                    st.login("google")
                else:
                    st.warning("st.login no está disponible en esta versión de Streamlit.")
        st.stop()
        
    email = getattr(st_user, "email", "")
    config = load_users_config()
    
    # Bootstrap para el primer admin
    bootstrap_admin = st.secrets.get("auth", {}).get("bootstrap_admin", "")
    if email == bootstrap_admin and email not in config.get("users", {}):
        log.info(f"Registrando admin bootstrap autodetectado: {email}")
        config["users"][email] = {
            "name": getattr(st_user, "name", "Admin Bootstrap"),
            "active": True,
            "role": "admin",
            "allowed_folders": ["all"],
            "allowed_contract_types": ["all"],
            "added_at": datetime.utcnow().isoformat() + "Z",
            "added_by": "system"
        }
        if email not in config.get("admins", []):
            if "admins" not in config:
                config["admins"] = []
            config["admins"].append(email)
        save_users_config(config)
    
    user_data = config.get("users", {}).get(email, {})
    
    if not user_data or not user_data.get("active", False):
        st.markdown(
            """
            <div style="text-align: center; margin-top: 100px;">
                <h1 style="font-size: 48px; color: #e53935;">⛔ Acceso Denegado</h1>
                <p style="color: #ccc; font-size: 18px; margin-bottom: 40px;">Tu cuenta <b>{}</b> no está autorizada o fue suspendida.</p>
            </div>
            """.format(email), 
            unsafe_allow_html=True
        )
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.info(f"Por favor contacta a un administrador ({bootstrap_admin}) para solicitar acceso.")
            if st.button("Cerrar Sesión", use_container_width=True):
                if hasattr(st, "logout"):
                    st.logout()
        st.stop()
        

def is_admin() -> bool:
    """True si el usuario actual tiene rol de admin."""
    u = get_current_user()
    return u is not None and u.get("role") == "admin"


def filter_sources_for_user(sources: List[str], user_data: Dict[str, Any]) -> List[str]:
    """Filtra la lista de archivos indexados según los permisos de tipo de contrato."""
    if not user_data:
        return []
    
    allowed_types = user_data.get("allowed_contract_types", [])
    if "all" in allowed_types:
        return sources
        
    filtered = []
    for src in sources:
        ext = src.split(".")[-1].lower() if "." in src else ""
        if ext in allowed_types:
            filtered.append(src)
            
    return filtered


def filter_folders_for_user(folders: List[Dict], user_data: Dict[str, Any]) -> List[Dict]:
    """Filtra una lista de diccionarios de carpetas de Drive según permisos."""
    if not user_data:
        return []
        
    allowed_folders = user_data.get("allowed_folders", [])
    if "all" in allowed_folders:
        return folders
        
    filtered = []
    for folder in folders:
        fid = folder.get("id")
        if fid in allowed_folders:
            filtered.append(folder)
            
    return filtered
