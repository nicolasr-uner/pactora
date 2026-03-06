from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from utils.auth_helper import get_drive_service, get_drive_service_with_apikey
import io

def get_folder_metadata(folder_id: str, api_key: str = None):
    """Obtiene el nombre y detalles de una carpeta específica."""
    try:
        if api_key:
            service = get_drive_service_with_apikey(api_key)
        else:
            service = get_drive_service()
            
        file = service.files().get(fileId=folder_id, fields="id, name", supportsAllDrives=True).execute()
        return file
    except HttpError as error:
        print(f"Error obteniendo metadata de {folder_id}: {error}")
        return {"id": folder_id, "name": "Carpeta Desconocida"}

def get_folder_contents(folder_id: str, api_key: str = None):
    """
    Lista el contenido (carpetas y archivos soportados) DE UN SOLO NIVEL (sin recursión)
    para emular un Explorador de Archivos real paso a paso.
    """
    try:
        if api_key:
            service = get_drive_service_with_apikey(api_key)
        else:
            service = get_drive_service()
            
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
    except HttpError as error:
        print(f"Ocurrió un error en la API de Drive al listar contenidos: {error}")
        return []

def create_folder(folder_name: str, parent_id: str):
    """Crea una subcarpeta nueva."""
    try:
        service = get_drive_service()
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        folder = service.files().create(body=file_metadata, fields='id, name, webViewLink').execute()
        return folder
    except HttpError as error:
        print(f"Ocurrió un error al crear la carpeta '{folder_name}': {error}")
        return None

def rename_item(item_id: str, new_name: str):
    """Renombra un archivo o carpeta."""
    try:
        service = get_drive_service()
        file_metadata = {'name': new_name}
        updated_file = service.files().update(
            fileId=item_id,
            body=file_metadata,
            fields='id, name',
            supportsAllDrives=True
        ).execute()
        return updated_file
    except HttpError as error:
        print(f"Ocurrió un error al renombrar: {error}")
        return None

def delete_item(item_id: str):
    """Mueve un archivo o carpeta a la papelera (Soft Delete)."""
    try:
        service = get_drive_service()
        file_metadata = {'trashed': True}
        updated_file = service.files().update(
            fileId=item_id,
            body=file_metadata,
            fields='id, trashed',
            supportsAllDrives=True
        ).execute()
        return updated_file
    except HttpError as error:
        print(f"Ocurrió un error al eliminar: {error}")
        return None

def upload_file(file_bytes, filename: str, parent_id: str, mime_type: str = 'application/octet-stream'):
    """Sube un archivo a una carpeta específica."""
    try:
        service = get_drive_service()
        file_metadata = {
            'name': filename,
            'parents': [parent_id]
        }
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink, mimeType, createdTime',
            supportsAllDrives=True
        ).execute()
        return uploaded_file
    except HttpError as error:
        print(f"Ocurrió un error al subir el archivo: {error}")
        return None

def download_file(file_id: str, dest_path: str):
    """Descarga archivo desde Drive al disco local."""
    try:
        service = get_drive_service()
        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO(dest_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return True
    except HttpError as error:
        print(f"Error descargando el archivo {file_id}: {error}")
        return False

def download_file_to_io(file_id: str):
    """Descarga un archivo de Drive y lo devuelve como un objeto BytesIO en memoria."""
    try:
        service = get_drive_service()
        request = service.files().get_media(fileId=file_id)
        file_io = io.BytesIO()
        downloader = MediaIoBaseDownload(file_io, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        file_io.seek(0)
        return file_io
    except HttpError as error:
        print(f"Error descargando el archivo {file_id} a memoria: {error}")
        return None

def get_recursive_files(folder_id: str, api_key: str = None):
    """
    Busca recursivamente todos los archivos (PDF/Word) dentro de una carpeta y sus subcarpetas.
    """
    all_files = []
    try:
        if api_key:
            service = get_drive_service_with_apikey(api_key)
        else:
            service = get_drive_service()

        # Listar archivos y carpetas en el nivel actual
        query = f"'{folder_id}' in parents and trashed=false"
        results = service.files().list(
            q=query,
            pageSize=1000,
            fields="files(id, name, mimeType)",
            includeItemsFromAllDrives=True,
            supportsAllDrives=True
        ).execute()

        items = results.get('files', [])
        for item in items:
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                # Llamada recursiva
                all_files.extend(get_recursive_files(item['id'], api_key))
            else:
                # Filtrar solo PDF y DOCX
                if 'pdf' in item['mimeType'] or 'word' in item['mimeType']:
                    all_files.append(item)
        
        return all_files
    except HttpError as error:
        print(f"Error en búsqueda recursiva para {folder_id}: {error}")
        return []
