import os
import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',  # Ingestion reads (Strict mode)
    'https://www.googleapis.com/auth/drive.file',      # Creation of folders/drafts
    'https://www.googleapis.com/auth/calendar.events'  # Calendar event creation
]

TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'credentials.json'

def authenticate_google_apis():
    """
    Authenticates the user with Google APIs using OAuth2.
    Returns the credentials object.
    """
    creds = None
    
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            st.error(f"Error reading token.json: {e}")
            
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                st.warning(f"Could not refresh token: {e}. Re-authenticating...")
                creds = None
                
        if not creds:
            if not os.path.exists(CREDENTIALS_FILE):
                st.error(f"Missing {CREDENTIALS_FILE}. Please ensure it is present for authentication.")
                return None
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                st.error(f"Error during authentication flow: {e}")
                return None
                
        # Save the credentials for the next run
        try:
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        except Exception as e:
            st.error(f"Could not save {TOKEN_FILE}: {e}")

    return creds

def get_drive_service():
    from googleapiclient.discovery import build
    creds = authenticate_google_apis()
    if creds:
        return build('drive', 'v3', credentials=creds)
    return None

def get_calendar_service():
    from googleapiclient.discovery import build
    creds = authenticate_google_apis()
    if creds:
        return build('calendar', 'v3', credentials=creds)
    return None
