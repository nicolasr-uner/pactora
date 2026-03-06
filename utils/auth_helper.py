import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scopes exigidos: Lectura estricta para documentos, permisos para crear carpetas, y control sobre eventos de calendario.
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/calendar.events'
]

def authenticate_google_apis():
    """
    Gestiona la autenticación leyendo credentials.json / token.json de forma segura,
    sin exposición al frontend ni posibilidad de commitearlo accidentalmente.
    """
    creds = None
    # El archivo token.json almacena los tokens de acceso del usuario de forma local
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    # Si no hay credenciales (válidas) disponibles, solicita inicio de sesión
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError(
                    "Falta credentials.json. Por reglas de Privacidad de Pactora, "
                    "debes descargar tus credenciales de Google Cloud, guardarlas "
                    "en la raíz del proyecto y NUNCA hacerles commit."
                )
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Guarda las credenciales autorizadas en token.json
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds

def get_drive_service():
    """Retorna el cliente para Google Drive API usando OAuth2.
    Retorna None si las credenciales no están disponibles (ej. en cloud deploy)."""
    try:
        creds = authenticate_google_apis()
        return build('drive', 'v3', credentials=creds)
    except (FileNotFoundError, Exception):
        return None

def get_drive_service_with_apikey(api_key: str):
    """Retorna el cliente para Google Drive API usando una API Key Pública."""
    return build('drive', 'v3', developerKey=api_key)

def get_calendar_service():
    """Retorna el cliente para Google Calendar API.
    Retorna None si las credenciales no están disponibles."""
    try:
        creds = authenticate_google_apis()
        return build('calendar', 'v3', credentials=creds)
    except (FileNotFoundError, Exception):
        return None
