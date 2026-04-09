"""
auth.py — Módulo de autenticación legacy (usado por biblioteca.py / chatbot.py).
La gestión principal de usuarios está en utils/auth_manager.py.
Escribe en: Drive (primero) → _pactora_users_local.json (fallback) → memoria de sesión.
"""
import json
import logging
import io
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

import streamlit as st
from utils.auth_helper import get_drive_service

log = logging.getLogger("pactora")

CONFIG_FILENAME     = "pactora_users.json"
_LOCAL_USERS_FILE   = "./_pactora_users_local.json"


# ─── Helpers locales ──────────────────────────────────────────────────────────

def _load_local() -> Optional[Dict[str, Any]]:
    try:
        if os.path.exists(_LOCAL_USERS_FILE):
            with open(_LOCAL_USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def _save_local(data: Dict[str, Any]) -> bool:
    try:
        with open(_LOCAL_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log.warning("[auth] No se pudo guardar localmente: %s", e)
        return False


# ─── Drive helpers ────────────────────────────────────────────────────────────

def _save_to_drive(service, root_id: str, data: Dict, file_id: Optional[str] = None):
    """Guarda el dict de usuarios en Drive (no-resumable para evitar error de cuota SA)."""
    from googleapiclient.http import MediaIoBaseUpload
    file_metadata = {"name": CONFIG_FILENAME, "mimeType": "application/json"}
    media = MediaIoBaseUpload(
        io.BytesIO(json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")),
        mimetype="application/json",
        resumable=False,  # resumable=True falla con SA sin cuota
    )
    if not file_id:
        file_metadata["parents"] = [root_id]
        service.files().create(
            body=file_metadata, media_body=media, fields="id",
            supportsAllDrives=True,
        ).execute()
    else:
        service.files().update(
            fileId=file_id, media_body=media,
            supportsAllDrives=True,
        ).execute()


@st.cache_data(ttl=300)
def load_users_config() -> Dict[str, Any]:
    """Carga pactora_users.json desde Drive → local → memoria vacía."""
    service = get_drive_service()
    if service:
        try:
            from googleapiclient.http import MediaIoBaseDownload
            root_id = st.secrets.get("DRIVE_ROOT_FOLDER_ID", "")
            query   = (f"'{root_id}' in parents and name='{CONFIG_FILENAME}' and trashed=false"
                       if root_id else f"name='{CONFIG_FILENAME}' and trashed=false")
            results = service.files().list(
                q=query, fields="files(id,name)",
                includeItemsFromAllDrives=True, supportsAllDrives=True,
            ).execute()
            files = results.get("files", [])

            if files:
                file_id = files[0]["id"]
                buf = io.BytesIO()
                dl  = MediaIoBaseDownload(
                    buf, service.files().get_media(fileId=file_id, supportsAllDrives=True)
                )
                done = False
                while not done:
                    _, done = dl.next_chunk()
                buf.seek(0)
                data = json.load(buf)
                _save_local(data)  # mantener copia local actualizada
                return data

            # No existe en Drive → inicializar con bootstrap
            default_config = _make_default_config()
            try:
                root_id = st.secrets.get("DRIVE_ROOT_FOLDER_ID", "")
                _save_to_drive(service, root_id, default_config, None)
            except Exception as e:
                log.error("[auth] Error al crear config inicial en Drive: %s", e)
            _save_local(default_config)
            return default_config

        except Exception as e:
            log.error("[auth] Error cargando usuarios desde Drive: %s", e)

    # Fallback: archivo local
    local = _load_local()
    if local:
        return local

    # Último recurso: config vacía en memoria
    return _make_default_config()


def _make_default_config() -> Dict[str, Any]:
    bootstrap_admin = ""
    try:
        bootstrap_admin = st.secrets.get("auth", {}).get("bootstrap_admin", "")
    except Exception:
        pass
    cfg: Dict[str, Any] = {"admins": [], "users": {}}
    if bootstrap_admin:
        cfg["admins"] = [bootstrap_admin]
        cfg["users"][bootstrap_admin] = {
            "name":                   "Administrador Bootstrap",
            "active":                 True,
            "role":                   "admin",
            "allowed_folders":        ["all"],
            "allowed_contract_types": ["all"],
            "added_at":               datetime.utcnow().isoformat() + "Z",
            "added_by":               "system",
        }
    return cfg


def save_users_config(config_data: Dict[str, Any]):
    """Guarda config en Drive (si disponible) + copia local + limpia caché."""
    _save_local(config_data)  # siempre guardar localmente primero
    service = get_drive_service()
    if service:
        try:
            root_id = st.secrets.get("DRIVE_ROOT_FOLDER_ID", "")
            query   = (f"'{root_id}' in parents and name='{CONFIG_FILENAME}' and trashed=false"
                       if root_id else f"name='{CONFIG_FILENAME}' and trashed=false")
            results = service.files().list(
                q=query, fields="files(id)",
                includeItemsFromAllDrives=True, supportsAllDrives=True,
            ).execute()
            files   = results.get("files", [])
            file_id = files[0]["id"] if files else None
            _save_to_drive(service, root_id, config_data, file_id)
        except Exception as e:
            log.error("[auth] Error guardando en Drive: %s", e)
    load_users_config.clear()


def get_current_user() -> Optional[Dict[str, Any]]:
    """Devuelve dict con permisos del usuario logueado o None."""
    try:
        st_user = getattr(st, "user", getattr(st, "experimental_user", None))
        if not st_user:
            return None
        if not getattr(st_user, "is_logged_in", False):
            email = getattr(st_user, "email", None)
            if not email:
                return None
        else:
            email = getattr(st_user, "email", None)
            if not email:
                return None

        config = load_users_config()
        if email in config.get("users", {}):
            u_data = dict(config["users"][email])
            u_data["email"] = email
            return u_data
    except Exception as e:
        log.error("[auth] Error get_current_user: %s", e)
    return None


def require_auth():
    """Bloquea la ejecución y muestra login o acceso denegado."""
    st_user = getattr(st, "user", getattr(st, "experimental_user", None))

    if not st_user or not getattr(st_user, "is_logged_in", False):
        st.markdown(
            """
            <div style="text-align:center;margin-top:100px;">
                <h1 style="font-size:48px;color:#FFF;">🏛️ Pactora CLM</h1>
                <p style="color:#c9b8e8;font-size:18px;margin-bottom:40px;">
                Sistema Inteligente de Contratos — Unergy</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.info("Debes iniciar sesión con tu cuenta de Google (Unergy) para continuar.", icon="🔒")
            if st.button("Continuar con Google", type="primary", width="stretch"):
                if hasattr(st, "login"):
                    st.login("google")
                else:
                    st.warning("st.login no está disponible en esta versión de Streamlit.")
        st.stop()

    email = getattr(st_user, "email", "")
    config = load_users_config()

    # Bootstrap del primer admin
    bootstrap_admin = ""
    try:
        bootstrap_admin = st.secrets.get("auth", {}).get("bootstrap_admin", "")
    except Exception:
        pass

    if bootstrap_admin and email == bootstrap_admin and email not in config.get("users", {}):
        log.info("[auth] Registrando admin bootstrap: %s", email)
        config.setdefault("admins", [])
        if email not in config["admins"]:
            config["admins"].append(email)
        config.setdefault("users", {})[email] = {
            "name":                   getattr(st_user, "name", "Admin Bootstrap"),
            "active":                 True,
            "role":                   "admin",
            "allowed_folders":        ["all"],
            "allowed_contract_types": ["all"],
            "added_at":               datetime.utcnow().isoformat() + "Z",
            "added_by":               "system",
        }
        save_users_config(config)

    user_data = config.get("users", {}).get(email, {})

    if not user_data or not user_data.get("active", False):
        st.markdown(
            f"""
            <div style="text-align:center;margin-top:100px;">
                <h1 style="font-size:48px;color:#e53935;">⛔ Acceso Denegado</h1>
                <p style="color:#ccc;font-size:18px;margin-bottom:40px;">
                Tu cuenta <b>{email}</b> no está autorizada o fue suspendida.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.info(f"Contacta al administrador ({bootstrap_admin or 'tu admin'}) para solicitar acceso.")
            if st.button("Cerrar Sesión", width="stretch"):
                if hasattr(st, "logout"):
                    st.logout()
        st.stop()


def is_admin() -> bool:
    u = get_current_user()
    return u is not None and u.get("role") == "admin"


def filter_sources_for_user(sources: List[str], user_data: Dict[str, Any]) -> List[str]:
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
    if not user_data:
        return []
    allowed_folders = user_data.get("allowed_folders", [])
    if "all" in allowed_folders:
        return folders
    return [f for f in folders if f.get("id") in allowed_folders]
