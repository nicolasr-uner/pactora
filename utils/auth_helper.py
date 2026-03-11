import logging
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

_log = logging.getLogger("pactora")

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/calendar.events'
]


def get_drive_service_sa():
    """
    Retorna Drive service usando Service Account desde st.secrets.
    Esta es la unica forma de descargar archivos privados de Drive en produccion.
    Retorna None si no hay SA configurada.
    """
    try:
        import streamlit as st
        from google.oauth2 import service_account

        sa = st.secrets.get("GOOGLE_SERVICE_ACCOUNT", {})
        if not sa:
            _log.warning("[auth] GOOGLE_SERVICE_ACCOUNT no encontrado en st.secrets — SA no disponible")
            return None

        sa_dict = dict(sa)
        # Normalizar private_key: en TOML los \n pueden ser literales o reales
        if "private_key" in sa_dict:
            pk = str(sa_dict["private_key"])
            pk = pk.replace("\\n", "\n").replace("\r", "")
            sa_dict["private_key"] = pk
            _log.info(
                "[auth] PEM: len=%d, newlines=%d, has_begin=%s, has_end=%s",
                len(pk), pk.count("\n"),
                "BEGIN" in pk, "END" in pk,
            )
        creds = service_account.Credentials.from_service_account_info(
            sa_dict,
            scopes=[
                'https://www.googleapis.com/auth/drive.readonly',
                'https://www.googleapis.com/auth/drive.file',
            ]
        )
        return build('drive', 'v3', credentials=creds, cache_discovery=False)
    except Exception as e:
        _log.error("[auth] get_drive_service_sa fallo: %s", e)
        return None


def authenticate_google_apis():
    """
    Autenticacion OAuth2 local (solo funciona con credentials.json en disco).
    En produccion (Streamlit Cloud) usa get_drive_service_sa() en su lugar.
    """
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                return None
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds


def get_drive_service():
    """
    Retorna Drive service: primero intenta Service Account (produccion),
    luego OAuth2 local (desarrollo). Retorna None si ninguno esta disponible.
    """
    # 1. Service Account (Streamlit Cloud / produccion)
    sa_service = get_drive_service_sa()
    if sa_service:
        return sa_service
    # 2. OAuth2 local (desarrollo con credentials.json)
    try:
        creds = authenticate_google_apis()
        if creds:
            return build('drive', 'v3', credentials=creds, cache_discovery=False)
    except Exception:
        pass
    return None


def get_drive_service_with_apikey(api_key: str):
    """
    Drive service con API Key publica.
    SOLO sirve para LISTAR archivos publicos, NO para descargar archivos privados.
    Para descargas privadas usa get_drive_service() (Service Account).
    """
    return build('drive', 'v3', developerKey=api_key, cache_discovery=False)


def get_calendar_service():
    """Retorna Calendar service. Retorna None si no hay credenciales."""
    try:
        creds = authenticate_google_apis()
        if creds:
            return build('calendar', 'v3', credentials=creds, cache_discovery=False)
    except Exception:
        pass
    return None
