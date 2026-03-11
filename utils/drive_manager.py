import io
import logging
import os
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from typing import Optional, Dict, Any, List

from utils.auth_helper import get_drive_service, get_drive_service_with_apikey

_log = logging.getLogger("pactora")

# ---------------------------------------------------------------------------
# Tipos de archivo soportados para indexación
# ---------------------------------------------------------------------------

SUPPORTED_MIMES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.ms-powerpoint',
    'text/csv',
    'text/plain',
    'image/png',
    'image/jpeg',
    'image/tiff',
}

# Google Docs nativos → MIME destino para export
GOOGLE_NATIVE_EXPORT = {
    'application/vnd.google-apps.document': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.google-apps.spreadsheet': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}

# MIME → extensión legible (para renombrar nativos exportados y para file_counts)
_MIME_TO_EXT: Dict[str, str] = {
    'application/pdf': 'pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
    'application/msword': 'doc',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
    'application/vnd.ms-excel': 'xls',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
    'application/vnd.ms-powerpoint': 'ppt',
    'text/csv': 'csv',
    'text/plain': 'txt',
    'image/png': 'png',
    'image/jpeg': 'jpg',
    'image/tiff': 'tiff',
    'application/vnd.google-apps.document': 'docx',
    'application/vnd.google-apps.spreadsheet': 'xlsx',
}


def get_ext_for_mime(mime: str) -> str:
    """Retorna extensión legible para un MIME type."""
    return _MIME_TO_EXT.get(mime, 'bin')

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
        service = get_drive_service() or (get_drive_service_with_apikey(api_key) if api_key else None)
        if not service:
            return {"id": folder_id, "name": "Carpeta Desconocida"}
        return service.files().get(fileId=folder_id, fields="id, name", supportsAllDrives=True).execute()
    except HttpError as error:
        _log.warning("[drive] get_folder_metadata error para %s: %s", folder_id, error)
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
        service = get_drive_service() or (get_drive_service_with_apikey(api_key) if api_key else None)
        if not service:
            return []
        return _list(service)
    except HttpError as error:
        # Si SA falló con 403/401, intentar con API key como último recurso
        if api_key and error.resp.status in (401, 403):
            try:
                return _list(get_drive_service_with_apikey(api_key))
            except Exception:
                pass
        _log.warning("[drive] get_folder_contents error para %s: %s", folder_id, error)
        return []


def _do_download(service, file_id: str) -> io.BytesIO:
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    file_io = io.BytesIO()
    downloader = MediaIoBaseDownload(file_io, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    size = file_io.tell()
    if size == 0:
        _log.error("[drive] _do_download: respuesta vacia (0 bytes) para file_id=%s", file_id)
    file_io.seek(0)
    return file_io


def _do_export(service, file_id: str, export_mime: str) -> io.BytesIO:
    """Exporta un Google Doc/Sheet nativo al formato indicado (DOCX/XLSX)."""
    request = service.files().export_media(fileId=file_id, mimeType=export_mime)
    file_io = io.BytesIO()
    downloader = MediaIoBaseDownload(file_io, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    size = file_io.tell()
    if size == 0:
        _log.error("[drive] _do_export: respuesta vacia (0 bytes) para file_id=%s", file_id)
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
        _log.error("[drive] requests HTTP %s para %s", resp.status_code, file_id)
        if resp.status_code in (401, 403):
            _log.error("[drive] ACCESO DENEGADO para %s — archivo privado, SA no configurada", file_id)
    except Exception as e:
        _log.error("[drive] requests fallo para %s: %s", file_id, e)
    return None


def download_file_to_io(file_id: str, api_key: str = None, mime_type: str = None) -> Optional[io.BytesIO]:
    """
    Descarga un archivo de Drive a BytesIO.
    Si mime_type es un Google Doc/Sheet nativo, usa export_media en lugar de get_media.
    Orden de intentos:
      1. Service Account (st.secrets[GOOGLE_SERVICE_ACCOUNT]) — descarga privada
      2. OAuth2 local (token.json) — desarrollo local
      3. requests con API Key — funciona si el archivo es publico/compartido publicamente
    """
    # Archivos Google nativos: usar export (no tienen binario descargable directo)
    if mime_type and mime_type in GOOGLE_NATIVE_EXPORT:
        export_mime = GOOGLE_NATIVE_EXPORT[mime_type]
        try:
            service = get_drive_service()
            if service:
                result = _do_export(service, file_id, export_mime)
                _log.info("[drive] Export nativo OK: %s → %s", mime_type, get_ext_for_mime(export_mime))
                return result
        except HttpError as e:
            _log.error("[drive] Export fallo para %s: HTTP %s — %s", file_id, e.resp.status, e)
        except Exception as e:
            _log.error("[drive] Export error inesperado para %s: %s", file_id, e)
        return None

    # 1. Service Account o OAuth (autenticacion completa — funciona con archivos privados)
    try:
        service = get_drive_service()
        if service:
            return _do_download(service, file_id)
    except HttpError as e:
        _log.error("[drive] Auth completa fallo para %s: HTTP %s — %s", file_id, e.resp.status, e)
    except Exception as e:
        _log.error("[drive] Error inesperado (auth completa) para %s: %s", file_id, e)

    # 2. requests con API Key (funciona solo para archivos compartidos publicamente)
    if api_key:
        result = _download_with_requests(file_id, api_key)
        if result:
            return result

    return None


def get_recursive_files(folder_id: str, api_key: str = None) -> List[Dict]:
    """
    Busca recursivamente todos los documentos indexables dentro de una carpeta.
    Soporta: PDF, DOCX, DOC, XLSX, XLS, PPTX, PPT, CSV, TXT, PNG, JPG, TIFF
    y Google Docs/Sheets nativos (exportados como DOCX/XLSX).
    """
    all_files = []

    def _list_folder(fid):
        def _execute(service):
            query = f"'{fid}' in parents and trashed=false"
            return service.files().list(
                q=query,
                pageSize=1000,
                fields="files(id, name, mimeType, size)",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True
            ).execute().get('files', [])

        try:
            service = get_drive_service() or (get_drive_service_with_apikey(api_key) if api_key else None)
            if not service:
                return []
            return _execute(service)
        except HttpError as error:
            # SA falló — intentar API key como último recurso
            if api_key and error.resp.status in (401, 403):
                try:
                    return _execute(get_drive_service_with_apikey(api_key))
                except Exception:
                    pass
            _log.error("[drive] Error en búsqueda recursiva para %s: %s", fid, error)
            return []

    for item in _list_folder(folder_id):
        mime = item.get('mimeType', '')
        if mime == 'application/vnd.google-apps.folder':
            all_files.extend(get_recursive_files(item['id'], api_key))
        elif mime in SUPPORTED_MIMES:
            all_files.append(item)
        elif mime in GOOGLE_NATIVE_EXPORT:
            # Renombrar con extensión correcta para que file_parser detecte el tipo
            ext = get_ext_for_mime(mime)
            item = dict(item)
            if not any(item['name'].lower().endswith(f'.{e}') for e in ('docx', 'xlsx', 'doc', 'xls')):
                item['name'] = f"{item['name']}.{ext}"
            all_files.append(item)

    return all_files

