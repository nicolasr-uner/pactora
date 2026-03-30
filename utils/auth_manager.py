"""
auth_manager.py — Gestión de acceso y permisos de usuario en Pactora CLM.

Almacenamiento persistente: _pactora_auth_users.json en Google Drive (Shared Drive).
Todas las llamadas a Drive usan supportsAllDrives=True para compatibilidad con Shared Drives.
Fallback: st.secrets["auth_config"]["admin_emails"] si Drive no está disponible.
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

AUTH_USERS_FILENAME = "_pactora_auth_users.json"
_CACHE_TTL_SECONDS  = 120
_USERS_CACHE_KEY    = "_auth_users_cache"
_USERS_CACHE_TS_KEY = "_auth_users_cache_ts"

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
        "role":           role,
        "allowed_types":  ["*"],
        "allowed_tags":   ["*"],
        "added_at":       datetime.now(timezone.utc).isoformat(),
        "added_by":       added_by,
        "active":         True,
    }


# ─── Drive helpers ─────────────────────────────────────────────────────────────

def _get_drive_root_id() -> str:
    try:
        return st.secrets.get("DRIVE_ROOT_FOLDER_ID", "")
    except Exception:
        return ""


def _load_users_from_drive() -> dict | None:
    """Lee _pactora_auth_users.json desde Drive (Shared Drive compatible)."""
    try:
        from utils.auth_helper import get_drive_service_sa
        from googleapiclient.http import MediaIoBaseDownload

        service = get_drive_service_sa()
        if not service:
            return None

        root_id = _get_drive_root_id()
        query_parts = [f"name='{AUTH_USERS_FILENAME}'", "trashed=false"]
        if root_id:
            query_parts.append(f"'{root_id}' in parents")

        results = service.files().list(
            q=" and ".join(query_parts),
            fields="files(id,name)",
            pageSize=1,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
        ).execute()

        files = results.get("files", [])
        if not files:
            return None

        file_id = files[0]["id"]
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(
            buf,
            service.files().get_media(fileId=file_id, supportsAllDrives=True),
        )
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
            _log.warning("[auth_manager] Service Account no disponible")
            return False

        root_id = _get_drive_root_id()
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        media   = MediaIoBaseUpload(io.BytesIO(payload), mimetype="application/json", resumable=False)

        # Buscar si ya existe
        query_parts = [f"name='{AUTH_USERS_FILENAME}'", "trashed=false"]
        if root_id:
            query_parts.append(f"'{root_id}' in parents")

        results  = service.files().list(
            q=" and ".join(query_parts),
            fields="files(id)",
            pageSize=1,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
        ).execute()
        existing = results.get("files", [])

        if existing:
            service.files().update(
                fileId=existing[0]["id"],
                media_body=media,
                supportsAllDrives=True,
            ).execute()
        else:
            meta: dict[str, Any] = {"name": AUTH_USERS_FILENAME, "mimeType": "application/json"}
            if root_id:
                meta["parents"] = [root_id]
            service.files().create(
                body=meta,
                media_body=media,
                fields="id",
                supportsAllDrives=True,
            ).execute()

        _log.info("[auth_manager] Usuarios guardados en Drive (%d)", len(data.get("users", [])))
        return True
    except Exception as e:
        _log.error("[auth_manager] Error al guardar en Drive: %s", e)
        return False


# ─── Secrets fallback ─────────────────────────────────────────────────────────

def _admin_emails_from_secrets() -> list[str]:
    try:
        cfg = st.secrets.get("auth_config", {})
        return [e.lower().strip() for e in cfg.get("admin_emails", []) if e]
    except Exception:
        return []


def _initial_allowed_from_secrets() -> list[str]:
    try:
        cfg = st.secrets.get("auth_config", {})
        return [e.lower().strip() for e in cfg.get("initial_allowed_emails", []) if e]
    except Exception:
        return []


def _bootstrap_initial_data() -> dict:
    users = []
    for email in _admin_emails_from_secrets():
        users.append(_empty_user(email, role="admin", added_by="system"))
    for email in _initial_allowed_from_secrets():
        if email not in {u["email"] for u in users}:
            users.append(_empty_user(email, role="viewer", added_by="system"))
    return {"users": users, "updated_at": datetime.now(timezone.utc).isoformat()}


# ─── Cache ────────────────────────────────────────────────────────────────────

def _invalidate_cache() -> None:
    st.session_state.pop(_USERS_CACHE_KEY, None)
    st.session_state.pop(_USERS_CACHE_TS_KEY, None)


def get_all_users(force_reload: bool = False) -> list[dict]:
    if not force_reload:
        ts = st.session_state.get(_USERS_CACHE_TS_KEY, 0)
        if time.time() - ts < _CACHE_TTL_SECONDS:
            cached = st.session_state.get(_USERS_CACHE_KEY)
            if cached is not None:
                return cached

    drive_data = _load_users_from_drive()
    if drive_data is None:
        drive_data = _bootstrap_initial_data()
        _save_users_to_drive(drive_data)

    users: list[dict] = drive_data.get("users", [])

    # Garantizar acceso de admins definidos en secrets
    existing = {u["email"] for u in users}
    for email in _admin_emails_from_secrets():
        if email not in existing:
            users.append(_empty_user(email, role="admin", added_by="secrets_fallback"))
            existing.add(email)

    st.session_state[_USERS_CACHE_KEY]    = users
    st.session_state[_USERS_CACHE_TS_KEY] = time.time()
    return users


def _find_user(email: str) -> dict | None:
    email = email.lower().strip()
    return next(
        (u for u in get_all_users() if u["email"] == email and u.get("active", True)),
        None,
    )


# ─── API pública ──────────────────────────────────────────────────────────────

def is_authorized(email: str) -> bool:
    return bool(email) and _find_user(email) is not None


def is_admin(email: str) -> bool:
    u = _find_user(email)
    return u is not None and u.get("role") == "admin"


def get_user_permissions(email: str) -> dict:
    u = _find_user(email)
    if u is None:
        return {"email": email, "role": None, "allowed_types": [], "allowed_tags": []}
    return {
        "email":         u["email"],
        "role":          u.get("role", "viewer"),
        "allowed_types": u.get("allowed_types", ["*"]),
        "allowed_tags":  u.get("allowed_tags", ["*"]),
    }


def can_view_contract(user_email: str, contract_metadata: dict) -> bool:
    perms = get_user_permissions(user_email)
    if perms["role"] == "admin":
        return True
    allowed = perms.get("allowed_types", ["*"])
    if "*" in allowed:
        return True
    ct = contract_metadata.get("contract_type", "")
    if ct and ct in allowed:
        return True
    source = contract_metadata.get("source", "").lower()
    return any(a.lower() in source for a in allowed)


# ─── CRUD ─────────────────────────────────────────────────────────────────────

def add_user(
    email: str,
    role: str = "viewer",
    allowed_types: list | None = None,
    allowed_tags: list | None = None,
    added_by: str = "admin",
) -> tuple[bool, str]:
    email = email.lower().strip()
    if not email or "@" not in email:
        return False, "Correo inválido."

    users = get_all_users(force_reload=True)
    if any(u["email"] == email for u in users):
        return False, f"'{email}' ya existe en la lista."

    new_user = _empty_user(email, role=role, added_by=added_by)
    if allowed_types is not None:
        new_user["allowed_types"] = allowed_types
    if allowed_tags is not None:
        new_user["allowed_tags"] = allowed_tags

    users.append(new_user)
    if _save_users_to_drive({"users": users}):
        _invalidate_cache()
        return True, ""
    return False, "No se pudo guardar en Drive. Verifica la conexión."


def remove_user(email: str) -> tuple[bool, str]:
    email = email.lower().strip()
    users = get_all_users(force_reload=True)

    target = next((u for u in users if u["email"] == email), None)
    if target is None:
        return False, "Usuario no encontrado."

    admins_remaining = [
        u for u in users
        if u.get("role") == "admin" and u.get("active", True) and u["email"] != email
    ]
    if target.get("role") == "admin" and not admins_remaining:
        return False, "No puedes eliminar el único administrador."

    target["active"] = False
    if _save_users_to_drive({"users": users}):
        _invalidate_cache()
        return True, ""
    return False, "No se pudo guardar en Drive."


def update_user_permissions(
    email: str,
    role: str | None = None,
    allowed_types: list | None = None,
    allowed_tags: list | None = None,
) -> tuple[bool, str]:
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

    if _save_users_to_drive({"users": users}):
        _invalidate_cache()
        return True, ""
    return False, "No se pudo guardar en Drive."
