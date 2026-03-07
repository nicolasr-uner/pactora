import io
import os
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from typing import Optional, Dict, Any, List

from utils.auth_helper import get_drive_service, get_drive_service_with_apikey

def search_documents(query: str = "", max_results: int = 20) -> List[Dict]:
    """
    Searches Google Drive for .docx files matching the query.
    Returns a list of dicts with 'id', 'name', and 'modifiedTime'.
    Always filters to .docx (Word) files only.
    """
    service = get_drive_service()
    if not service:
        return []

    try:
        # Build query: .docx or .pdf, optionally filter by name
        mime_docx = "mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'"
        mime_pdf = "mimeType='application/pdf'"
        
        mime_filter = f"({mime_docx} or {mime_pdf})"
        
        if query.strip():
            full_query = f"{mime_filter} and name contains '{query.strip()}' and trashed=false"
        else:
            full_query = f"{mime_filter} and trashed=false"


        results = service.files().list(
            q=full_query,
            pageSize=max_results,
            orderBy="modifiedTime desc",
            fields="files(id, name, modifiedTime, size)"
        ).execute()

        return results.get('files', [])

    except Exception as e:
        print(f"Error searching Drive documents: {e}")
        return []


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


def get_file_metadata(file_id: str) -> Optional[Dict]:
    """Fetches basic metadata (name, size) for a given file ID."""
    service = get_drive_service()
    if not service:
        return None
    try:
        return service.files().get(fileId=file_id, fields="id, name, modifiedTime, size").execute()
    except Exception as e:
        print(f"Error fetching metadata for {file_id}: {e}")
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


# --- Folder explorer helpers ---

def get_folder_metadata(folder_id: str, api_key: str = None):
    """Obtiene el nombre y detalles de una carpeta específica."""
    try:
        service = get_drive_service_with_apikey(api_key) if api_key else get_drive_service()
        return service.files().get(fileId=folder_id, fields="id, name", supportsAllDrives=True).execute()
    except HttpError as error:
        print(f"Error obteniendo metadata de {folder_id}: {error}")
        return {"id": folder_id, "name": "Carpeta Desconocida"}


def get_folder_contents(folder_id: str, api_key: str = None):
    """Lista el contenido de UN nivel de carpeta (explorador de archivos)."""
    def _list(service):
        query = f"'{folder_id}' in parents and trashed=false"
        results = service.files().list(
            q=query,
            pageSize=1000,
            fields="nextPageToken, files(id, name, mimeType, webViewLink, createdTime)",
            orderBy="folder, name",
            includeItemsFromAllDrives=True,
            supportsAllDrives=True
        ).execute()
        return results.get('files', [])

    try:
        service = get_drive_service_with_apikey(api_key) if api_key else get_drive_service()
        return _list(service)
    except HttpError as error:
        if api_key and error.resp.status in (401, 403):
            try:
                return _list(get_drive_service())
            except Exception:
                pass
        print(f"Error listando contenidos de {folder_id}: {error}")
        return []


def _do_download(service, file_id: str) -> io.BytesIO:
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    file_io = io.BytesIO()
    downloader = MediaIoBaseDownload(file_io, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    file_io.seek(0)
    return file_io


def _download_with_requests(file_id: str, api_key: str) -> Optional[io.BytesIO]:
    """Descarga directa via requests con API key. Funciona para archivos publicos/compartidos."""
    try:
        import requests as _req
        url = (
            f"https://www.googleapis.com/drive/v3/files/{file_id}"
            f"?alt=media&supportsAllDrives=true&key={api_key}"
        )
        resp = _req.get(url, timeout=60)
        if resp.status_code == 200:
            return io.BytesIO(resp.content)
        print(f"[drive] requests HTTP {resp.status_code} para {file_id}")
        if resp.status_code in (401, 403):
            print(f"[drive] ACCESO DENEGADO — el archivo es privado. "
                  f"Configura una Cuenta de Servicio en Ajustes para descargar archivos privados.")
    except Exception as e:
        print(f"[drive] requests fallo para {file_id}: {e}")
    return None


def download_file_to_io(file_id: str, api_key: str = None) -> Optional[io.BytesIO]:
    """
    Descarga un archivo de Drive a BytesIO.
    Orden de intentos:
      1. Service Account (st.secrets[GOOGLE_SERVICE_ACCOUNT]) — descarga privada
      2. OAuth2 local (token.json) — desarrollo local
      3. requests con API Key — funciona si el archivo es publico/compartido publicamente
    """
    # 1. Service Account o OAuth (autenticacion completa — funciona con archivos privados)
    try:
        service = get_drive_service()
        if service:
            return _do_download(service, file_id)
    except HttpError as e:
        print(f"[drive] Auth completa fallo para {file_id}: HTTP {e.resp.status} — {e}")
    except Exception as e:
        print(f"[drive] Error inesperado (auth completa) para {file_id}: {e}")

    # 2. requests con API Key (funciona solo para archivos compartidos publicamente)
    if api_key:
        result = _download_with_requests(file_id, api_key)
        if result:
            return result

    return None


def get_recursive_files(folder_id: str, api_key: str = None) -> List[Dict]:
    """Busca recursivamente todos los PDF/DOCX dentro de una carpeta."""
    all_files = []

    def _list_folder(fid):
        try:
            service = get_drive_service_with_apikey(api_key) if api_key else get_drive_service()
            query = f"'{fid}' in parents and trashed=false"
            results = service.files().list(
                q=query,
                pageSize=1000,
                fields="files(id, name, mimeType)",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True
            ).execute()
            return results.get('files', [])
        except HttpError as error:
            if api_key and error.resp.status in (401, 403):
                try:
                    service = get_drive_service()
                    query = f"'{fid}' in parents and trashed=false"
                    results = service.files().list(
                        q=query, pageSize=1000,
                        fields="files(id, name, mimeType)",
                        includeItemsFromAllDrives=True,
                        supportsAllDrives=True
                    ).execute()
                    return results.get('files', [])
                except Exception:
                    pass
            print(f"Error en búsqueda recursiva para {fid}: {error}")
            return []

    for item in _list_folder(folder_id):
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            all_files.extend(get_recursive_files(item['id'], api_key))
        elif 'pdf' in item['mimeType'] or 'word' in item['mimeType']:
            all_files.append(item)

    return all_files

