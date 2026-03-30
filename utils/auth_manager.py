"""
auth_manager.py — Gestión de acceso y permisos de usuario en Pactora CLM.

Almacenamiento: st.secrets["auth_config"] (Streamlit Cloud secrets editor).
No requiere Drive ni base de datos externa.

Formato de secrets.toml:
    [auth_config]
    admin_emails = ["tu@empresa.com"]

    [[auth_config.users]]
    email         = "colega@empresa.com"
    role          = "viewer"
    allowed_types = ["*"]

    [[auth_config.users]]
    email         = "otro@empresa.com"
    role          = "viewer"
    allowed_types = ["PPA", "EPC"]
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import streamlit as st

_log = logging.getLogger("pactora")

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

_CACHE_KEY    = "_auth_users_cache"
_CACHE_TS_KEY = "_auth_users_ts"
_CACHE_TTL    = 60   # segundos


# ─── Lectura desde secrets ────────────────────────────────────────────────────

def _read_from_secrets() -> list[dict]:
    """
    Lee la lista de usuarios desde st.secrets["auth_config"].
    Fusiona admin_emails + users array.
    """
    users: list[dict] = []
    seen: set[str] = set()

    try:
        cfg = st.secrets.get("auth_config", {})

        # 1. Admins siempre autorizados
        for email in cfg.get("admin_emails", []):
            e = email.lower().strip()
            if e and e not in seen:
                users.append({
                    "email":         e,
                    "role":          "admin",
                    "allowed_types": ["*"],
                    "allowed_tags":  ["*"],
                    "source":        "secrets:admin_emails",
                })
                seen.add(e)

        # 2. Usuarios adicionales (array of tables [[auth_config.users]])
        for u in cfg.get("users", []):
            e = str(u.get("email", "")).lower().strip()
            if e and e not in seen:
                allowed = list(u.get("allowed_types", ["*"]))
                users.append({
                    "email":         e,
                    "role":          str(u.get("role", "viewer")),
                    "allowed_types": allowed,
                    "allowed_tags":  list(u.get("allowed_tags", ["*"])),
                    "source":        "secrets:users",
                })
                seen.add(e)

    except Exception as exc:
        _log.warning("[auth_manager] Error leyendo secrets: %s", exc)

    return users


# ─── Cache en session_state ───────────────────────────────────────────────────

def _invalidate_cache() -> None:
    st.session_state.pop(_CACHE_KEY, None)
    st.session_state.pop(_CACHE_TS_KEY, None)


def get_all_users(force_reload: bool = False) -> list[dict]:
    """Retorna lista de usuarios autorizados (cacheada 60 s)."""
    import time
    if not force_reload:
        ts = st.session_state.get(_CACHE_TS_KEY, 0)
        if time.time() - ts < _CACHE_TTL:
            cached = st.session_state.get(_CACHE_KEY)
            if cached is not None:
                return cached

    users = _read_from_secrets()
    st.session_state[_CACHE_KEY]    = users
    st.session_state[_CACHE_TS_KEY] = time.time()
    return users


def _find_user(email: str) -> dict | None:
    email = email.lower().strip()
    return next((u for u in get_all_users() if u["email"] == email), None)


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
    """True si el usuario puede ver el contrato según sus permisos."""
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


# ─── Generador de TOML (para el panel de admin) ───────────────────────────────

def generate_toml_snippet(
    email: str,
    role: str = "viewer",
    allowed_types: list | None = None,
) -> str:
    """
    Genera el bloque TOML listo para pegar en Streamlit Cloud secrets.
    """
    if allowed_types is None or "*" in allowed_types:
        types_toml = '["*"]'
    else:
        types_toml = "[" + ", ".join(f'"{t}"' for t in allowed_types) + "]"

    if role == "admin":
        return (
            f'\n# Agrega este correo a admin_emails dentro de [auth_config]:\n'
            f'# admin_emails = [..., "{email}"]\n'
        )

    return (
        f'\n[[auth_config.users]]\n'
        f'email         = "{email}"\n'
        f'role          = "{role}"\n'
        f'allowed_types = {types_toml}\n'
    )
