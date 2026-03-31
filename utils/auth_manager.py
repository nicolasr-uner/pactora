"""
auth_manager.py — Gestión de acceso y permisos de usuario en Pactora CLM.

Almacenamiento persistente: Google Sheets (AUTH_USERS_SHEET_ID en st.secrets).
El Service Account necesita acceso Editor al Sheet.
Fallback: st.secrets["auth_config"]["admin_emails"] si Sheets no está disponible.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

import streamlit as st

_log = logging.getLogger("pactora")

_SHEET_RANGE        = "Sheet1!A:H"
_HEADERS            = ["email", "role", "allowed_types", "allowed_tags", "features", "added_at", "added_by", "active"]
_CACHE_TTL_SECONDS  = 120
_USERS_CACHE_KEY    = "_auth_users_cache"
_USERS_CACHE_TS_KEY = "_auth_users_cache_ts"

# Funciones disponibles para control de acceso granular por usuario.
# Los admins siempre tienen todas las funciones independientemente de este dict.
FEATURES: dict[str, str] = {
    "juanmitabot": "💬 JuanMitaBot Chat",
    "resolver":    "🎯 Resolver con JuanMitaBot",
    "analisis":    "⚖️ Análisis Legal",
    "comparar":    "🔀 Comparar Contratos",
    "exportar":    "📤 Exportar Informes",
}

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
        "features":       ["*"],
        "added_at":       datetime.now(timezone.utc).isoformat(),
        "added_by":       added_by,
        "active":         True,
    }


# ─── Sheets helpers ────────────────────────────────────────────────────────────

def _get_sheet_id() -> str:
    try:
        return st.secrets.get("AUTH_USERS_SHEET_ID", "")
    except Exception:
        return ""


def _load_users_from_sheets() -> dict | None:
    """
    Lee filas desde el Google Sheet de usuarios.
    Fila 1 = headers: email|role|allowed_types|allowed_tags|added_at|added_by|active
    Retorna {"users": [...], "updated_at": "..."} o None si no está configurado.
    """
    try:
        from utils.auth_helper import get_sheets_service_sa

        sheet_id = _get_sheet_id()
        if not sheet_id:
            return None

        service = get_sheets_service_sa()
        if not service:
            return None

        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=sheet_id, range=_SHEET_RANGE)
            .execute()
        )
        rows = result.get("values", [])
        if not rows:
            # Sheet vacío — inicializar con headers
            _write_headers_if_empty(service, sheet_id)
            return {"users": [], "updated_at": datetime.now(timezone.utc).isoformat()}

        # Usar fila de headers para mapear columnas por nombre (robusto a cambios de esquema)
        header_row = rows[0]
        col = {h: i for i, h in enumerate(header_row)}

        def _cell(row: list, key: str, default: str = "") -> str:
            i = col.get(key, -1)
            if i < 0 or i >= len(row):
                return default
            return str(row[i]).strip()

        users: list[dict] = []
        for row in rows[1:]:
            if not row:
                continue

            try:
                allowed_types = json.loads(_cell(row, "allowed_types")) if _cell(row, "allowed_types") else ["*"]
            except (json.JSONDecodeError, ValueError):
                allowed_types = ["*"]
            try:
                allowed_tags = json.loads(_cell(row, "allowed_tags")) if _cell(row, "allowed_tags") else []
            except (json.JSONDecodeError, ValueError):
                allowed_tags = []
            try:
                features_raw = _cell(row, "features")
                features = json.loads(features_raw) if features_raw else ["*"]
            except (json.JSONDecodeError, ValueError):
                features = ["*"]

            email = _cell(row, "email").lower()
            if not email:
                continue
            users.append({
                "email":         email,
                "role":          _cell(row, "role") or "viewer",
                "allowed_types": allowed_types,
                "allowed_tags":  allowed_tags,
                "features":      features,
                "added_at":      _cell(row, "added_at"),
                "added_by":      _cell(row, "added_by"),
                "active":        _cell(row, "active", "True").lower() == "true",
            })

        _log.info("[auth_manager] %d usuarios cargados desde Sheets", len(users))
        return {"users": users, "updated_at": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        _log.warning("[auth_manager] No se pudo leer desde Sheets: %s", e)
        return None


def _write_headers_if_empty(service, sheet_id: str) -> None:
    try:
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range="Sheet1!A1",
            valueInputOption="RAW",
            body={"values": [_HEADERS]},
        ).execute()
    except Exception as e:
        _log.warning("[auth_manager] No se pudo escribir headers: %s", e)


def _save_users_to_sheets(data: dict) -> bool:
    """
    Sobreescribe el Sheet completo con los usuarios actuales.
    Fila 1 = headers, filas 2+ = datos.
    """
    try:
        from utils.auth_helper import get_sheets_service_sa

        sheet_id = _get_sheet_id()
        if not sheet_id:
            _log.warning("[auth_manager] AUTH_USERS_SHEET_ID no configurado")
            return False

        service = get_sheets_service_sa()
        if not service:
            _log.warning("[auth_manager] Sheets SA no disponible")
            return False

        rows = [_HEADERS]
        for u in data.get("users", []):
            rows.append([
                u.get("email", ""),
                u.get("role", "viewer"),
                json.dumps(u.get("allowed_types", ["*"]), ensure_ascii=False),
                json.dumps(u.get("allowed_tags", []), ensure_ascii=False),
                json.dumps(u.get("features", ["*"]), ensure_ascii=False),
                u.get("added_at", ""),
                u.get("added_by", ""),
                str(u.get("active", True)),
            ])

        sheets = service.spreadsheets().values()
        sheets.clear(spreadsheetId=sheet_id, range=_SHEET_RANGE).execute()
        sheets.update(
            spreadsheetId=sheet_id,
            range="Sheet1!A1",
            valueInputOption="RAW",
            body={"values": rows},
        ).execute()

        _log.info("[auth_manager] %d usuarios guardados en Sheets", len(rows) - 1)
        return True
    except Exception as e:
        _log.error("[auth_manager] Error al guardar en Sheets: %s", e)
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

    drive_data = _load_users_from_sheets()
    if drive_data is None:
        drive_data = _bootstrap_initial_data()
        _save_users_to_sheets(drive_data)

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


def has_feature(email: str, feature: str) -> bool:
    """
    Verifica si el usuario tiene acceso a una función específica.
    Los admins siempre tienen todas las funciones.
    Viewers con features=["*"] o features=[] tienen todas las funciones (retrocompatibilidad).
    """
    u = _find_user(email)
    if u is None:
        return False
    if u.get("role") == "admin":
        return True
    features = u.get("features", ["*"])
    # [] tratado como ["*"] para retrocompatibilidad con usuarios creados antes de esta feature
    if not features or "*" in features:
        return True
    return feature in features


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
    features: list | None = None,
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
    if features is not None:
        new_user["features"] = features

    users.append(new_user)
    if _save_users_to_sheets({"users": users}):
        _invalidate_cache()
        return True, ""
    return False, "No se pudo guardar en Sheets. Verifica que AUTH_USERS_SHEET_ID esté configurado y el SA tenga acceso Editor."


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
    if _save_users_to_sheets({"users": users}):
        _invalidate_cache()
        return True, ""
    return False, "No se pudo guardar en Sheets."


def update_user_permissions(
    email: str,
    role: str | None = None,
    allowed_types: list | None = None,
    allowed_tags: list | None = None,
    features: list | None = None,
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
    if features is not None:
        target["features"] = features

    if _save_users_to_sheets({"users": users}):
        _invalidate_cache()
        return True, ""
    return False, "No se pudo guardar en Sheets."
