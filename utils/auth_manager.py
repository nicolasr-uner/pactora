"""
auth_manager.py — Gestión de acceso y permisos de usuario en Pactora CLM.

Flujo de autenticación:
  1. Streamlit Native Auth (OAuth Google) valida la identidad del usuario.
  2. Este módulo verifica si el correo está en la whitelist.
  3. Si está autorizado, aplica sus permisos de contratos.

Almacenamiento persistente:
  - Fuente primaria: archivo JSON en Google Drive (_pactora_auth_users.json),
    leído/escrito con el Service Account existente.
  - Fallback: st.secrets["auth_config"]["admin_emails"] (siempre acceden).

Uso típico en app.py:
    from utils.auth_manager import is_authorized, is_admin, get_user_permissions
    if not st.user.is_logged_in:
        st.login("google"); st.stop()
    if not is_authorized(st.user.email):
        show_access_denied(); st.stop()
"""

from __future__ import annotations

import io
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

import streamlit as st

_log = logging.getLogger("pactora")

# ─── Constantes ───────────────────────────────────────────────────────────────

AUTH_USERS_FILENAME = "_pactora_auth_users.json"
_CACHE_TTL_SECONDS  = 120   # Recarga la lista de Drive cada 2 min
_USERS_CACHE_KEY    = "_auth_users_cache"
_USERS_CACHE_TS_KEY = "_auth_users_cache_ts"

# Tipos de contrato disponibles (opciones del desplegable en admin)
CONTRACT_TYPES = [
    "PPA",
    "EPC",
    "O&M",
    "Arrendamiento",
    "Compraventa",
    "Prestación de servicios",
    "Confidencialidad (NDA)",
    "Consorcio / Joint Venture",
    "Financiamiento",
    "Otro",
]

# ─── Estructura de usuario ─────────────────────────────────────────────────────

def _empty_user(email: str, role: str = "viewer", added_by: str = "system") -> dict:
    return {
        "email":          email.lower().strip(),
        "role":           role,                     # "admin" | "viewer"
        "allowed_types":  ["*"],                    # ["*"] = todos los tipos
        "allowed_tags":   ["*"],                    # ["*"] = todas las carpetas/tags
        "added_at":       datetime.now(timezone.utc).isoformat(),
        "added_by":       added_by,
        "active":         True,
    }


# ─── Carga / guardado Drive ────────────────────────────────────────────────────

def _get_drive_root_id() -> str:
    try:
        return st.secrets.get("DRIVE_ROOT_FOLDER_ID", "")
    except Exception:
        return ""


def _load_users_from_drive() -> dict | None:
    """Lee _pactora_auth_users.json desde Drive. Retorna None si no existe."""
    try:
        from utils.auth_helper import get_drive_service_sa
        from googleapiclient.http import MediaIoBaseDownload

        service = get_drive_service_sa()
        if not service:
            return None

        root_id = _get_drive_root_id()
        query_parts = [
            f"name='{AUTH_USERS_FILENAME}'",
            "trashed=false",
        ]
        if root_id:
            query_parts.append(f"'{root_id}' in parents")

        results = service.files().list(
            q=" and ".join(query_parts),
            fields="files(id,name)",
            pageSize=1,
        ).execute()

        files = results.get("files", [])
        if not files:
            return None

        file_id = files[0]["id"]
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, service.files().get_media(fileId=file_id))
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buf.seek(0)
        return json.loads(buf.read().decode("utf-8"))
    except Exception as e:
        _log.warning("[auth_manager] No se pudo leer desde Drive: %s", e)
        return None


def _save_users_to_drive(data: dict) -> bool:
    """Guarda (crea o actualiza) _pactora_auth_users.json en Drive."""
    try:
        from utils.auth_helper import get_drive_service_sa
        from googleapiclient.http import MediaIoBaseUpload

        service = get_drive_service_sa()
        if not service:
            _log.warning("[auth_manager] Service Account no disponible — no se pudo guardar")
            return False

        root_id = _get_drive_root_id()
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        media    = MediaIoBaseUpload(io.BytesIO(payload), mimetype="application/json", resumable=False)

        # Buscar si ya existe
        query_parts = [f"name='{AUTH_USERS_FILENAME}'", "trashed=false"]
        if root_id:
            query_parts.append(f"'{root_id}' in parents")

        results  = service.files().list(q=" and ".join(query_parts), fields="files(id)", pageSize=1).execute()
        existing = results.get("files", [])

        if existing:
            service.files().update(fileId=existing[0]["id"], media_body=media).execute()
        else:
            meta: dict[str, Any] = {"name": AUTH_USERS_FILENAME, "mimeType": "application/json"}
            if root_id:
                meta["parents"] = [root_id]
            service.files().create(body=meta, media_body=media, fields="id").execute()

        _log.info("[auth_manager] Usuarios guardados en Drive (%d usuarios)", len(data.get("users", [])))
        return True
    except Exception as e:
        _log.error("[auth_manager] Error al guardar en Drive: %s", e)
        return False


# ─── Bootstrap desde secrets ──────────────────────────────────────────────────

def _admin_emails_from_secrets() -> list[str]:
    """Retorna la lista de admin_emails definida en secrets (siempre válida)."""
    try:
        cfg = st.secrets.get("auth_config", {})
        emails = cfg.get("admin_emails", [])
        return [e.lower().strip() for e in emails if e]
    except Exception:
        return []


def _initial_allowed_from_secrets() -> list[str]:
    """Retorna correos iniciales permitidos (no admins) desde secrets."""
    try:
        cfg = st.secrets.get("auth_config", {})
        emails = cfg.get("initial_allowed_emails", [])
        return [e.lower().strip() for e in emails if e]
    except Exception:
        return []


def _bootstrap_initial_data() -> dict:
    """Crea estructura inicial si no hay JSON en Drive todavía."""
    users = []
    for email in _admin_emails_from_secrets():
        users.append(_empty_user(email, role="admin", added_by="system"))
    for email in _initial_allowed_from_secrets():
        if email not in {u["email"] for u in users}:
            users.append(_empty_user(email, role="viewer", added_by="system"))
    return {"users": users, "updated_at": datetime.now(timezone.utc).isoformat()}


# ─── Cache en memoria ─────────────────────────────────────────────────────────

def _get_cached_users() -> list[dict] | None:
    ts = st.session_state.get(_USERS_CACHE_TS_KEY, 0)
    if time.time() - ts < _CACHE_TTL_SECONDS:
        return st.session_state.get(_USERS_CACHE_KEY)
    return None


def _set_cached_users(users: list[dict]) -> None:
    st.session_state[_USERS_CACHE_KEY]    = users
    st.session_state[_USERS_CACHE_TS_KEY] = time.time()


def _invalidate_cache() -> None:
    st.session_state.pop(_USERS_CACHE_KEY, None)
    st.session_state.pop(_USERS_CACHE_TS_KEY, None)


# ─── API pública ──────────────────────────────────────────────────────────────

def get_all_users(force_reload: bool = False) -> list[dict]:
    """
    Retorna la lista completa de usuarios autorizados.
    Fusiona: Drive JSON + admins de secrets (para garantizar acceso de emergencia).
    """
    if not force_reload:
        cached = _get_cached_users()
        if cached is not None:
            return cached

    drive_data = _load_users_from_drive()
    if drive_data is None:
        drive_data = _bootstrap_initial_data()
        _save_users_to_drive(drive_data)   # Crea el archivo por primera vez

    users: list[dict] = drive_data.get("users", [])

    # Garantizar que los admin_emails de secrets siempre tengan acceso
    existing_emails = {u["email"] for u in users}
    for email in _admin_emails_from_secrets():
        if email not in existing_emails:
            users.append(_empty_user(email, role="admin", added_by="secrets_fallback"))
            existing_emails.add(email)

    _set_cached_users(users)
    return users


def _find_user(email: str) -> dict | None:
    email = email.lower().strip()
    for u in get_all_users():
        if u["email"] == email and u.get("active", True):
            return u
    return None


def is_authorized(email: str) -> bool:
    """True si el correo está en la whitelist y activo."""
    if not email:
        return False
    return _find_user(email) is not None


def is_admin(email: str) -> bool:
    """True si el usuario tiene rol 'admin'."""
    user = _find_user(email)
    return user is not None and user.get("role") == "admin"


def get_user_permissions(email: str) -> dict:
    """
    Retorna dict con permisos del usuario:
      {role, allowed_types, allowed_tags, email}
    Si no existe retorna permisos vacíos.
    """
    user = _find_user(email)
    if user is None:
        return {"email": email, "role": None, "allowed_types": [], "allowed_tags": []}
    return {
        "email":         user["email"],
        "role":          user.get("role", "viewer"),
        "allowed_types": user.get("allowed_types", ["*"]),
        "allowed_tags":  user.get("allowed_tags", ["*"]),
    }


def can_view_contract(user_email: str, contract_metadata: dict) -> bool:
    """
    True si el usuario puede ver el contrato según sus permisos.
    contract_metadata puede tener 'source' (nombre de archivo) o 'contract_type'.
    """
    perms = get_user_permissions(user_email)
    if perms["role"] == "admin":
        return True

    allowed_types = perms.get("allowed_types", ["*"])
    if "*" in allowed_types:
        return True

    # Intentar coincidir por tipo de contrato si está en metadata
    ct = contract_metadata.get("contract_type", "")
    if ct and ct in allowed_types:
        return True

    # Coincidir por nombre de archivo (fuente)
    source = contract_metadata.get("source", "").lower()
    for allowed in allowed_types:
        if allowed.lower() in source:
            return True

    return False


# ─── CRUD de usuarios ─────────────────────────────────────────────────────────

def add_user(
    email: str,
    role: str          = "viewer",
    allowed_types: list | None = None,
    allowed_tags:  list | None = None,
    added_by: str      = "admin",
) -> tuple[bool, str]:
    """
    Agrega un usuario a la whitelist.
    Retorna (True, "") en éxito o (False, motivo) en error.
    """
    email = email.lower().strip()
    if not email or "@" not in email:
        return False, "Correo inválido."

    users = get_all_users(force_reload=True)
    existing = {u["email"] for u in users}
    if email in existing:
        return False, f"'{email}' ya existe en la lista."

    new_user = _empty_user(email, role=role, added_by=added_by)
    if allowed_types is not None:
        new_user["allowed_types"] = allowed_types
    if allowed_tags is not None:
        new_user["allowed_tags"] = allowed_tags

    users.append(new_user)
    data  = {"users": users}
    saved = _save_users_to_drive(data)
    if saved:
        _invalidate_cache()
        return True, ""
    return False, "No se pudo guardar en Drive. Verifica la conexión."


def remove_user(email: str) -> tuple[bool, str]:
    """Desactiva (soft delete) a un usuario."""
    email = email.lower().strip()
    users = get_all_users(force_reload=True)

    # No permitir eliminar el último admin
    admins = [u for u in users if u.get("role") == "admin" and u.get("active", True) and u["email"] != email]
    target = next((u for u in users if u["email"] == email), None)
    if target is None:
        return False, "Usuario no encontrado."
    if target.get("role") == "admin" and not admins:
        return False, "No puedes eliminar el único administrador."

    target["active"] = False
    saved = _save_users_to_drive({"users": users})
    if saved:
        _invalidate_cache()
        return True, ""
    return False, "No se pudo guardar en Drive."


def update_user_permissions(
    email: str,
    role:          str | None  = None,
    allowed_types: list | None = None,
    allowed_tags:  list | None = None,
) -> tuple[bool, str]:
    """Actualiza los permisos de un usuario existente."""
    email = email.lower().strip()
    users = get_all_users(force_reload=True)
    target = next((u for u in users if u["email"] == email), None)
    if target is None:
        return False, "Usuario no encontrado."

    if role is not None:
        target["role"] = role
    if allowed_types is not None:
        target["allowed_types"] = allowed_types
    if allowed_tags is not None:
        target["allowed_tags"] = allowed_tags

    saved = _save_users_to_drive({"users": users})
    if saved:
        _invalidate_cache()
        return True, ""
    return False, "No se pudo guardar en Drive."
