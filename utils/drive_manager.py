import io
import os
from googleapiclient.http import MediaIoBaseDownload
from typing import Optional, Dict, Any
from utils.auth_helper import get_drive_service

def fetch_document(file_id: str) -> Optional[bytes]:
    """
    Downloads a document from Google Drive in a read-only manner.
    Used for ingesting contracts.
    """
    service = get_drive_service()
    if not service:
        return None
        
    try:
        request = service.files().get_media(fileId=file_id)
        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            
        return file_stream.getvalue()
    except Exception as e:
        print(f"Error fetching document {file_id}: {e}")
        return None

def create_project_folder(project_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
    """
    Creates a new folder for the specific project in Google Drive.
    Returns the ID of the newly created folder.
    """
    service = get_drive_service()
    if not service:
        return None
        
    folder_metadata: Dict[str, Any] = {
        'name': project_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    
    if parent_folder_id:
        folder_metadata['parents'] = [parent_folder_id]
        
    try:
        folder = service.files().create(body=folder_metadata, fields='id').execute()
        return folder.get('id')
    except Exception as e:
        print(f"Error creating folder {project_name}: {e}")
        return None
