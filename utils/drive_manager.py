from googleapiclient.errors import HttpError
from utils.auth_helper import get_drive_service

def list_documents(query="mimeType='application/pdf' or mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'", max_results=20):
    """
    Lista archivos de Google Drive aplicando regla de Inviolabilidad (ReadOnly).
    Por defecto filtra PDFs y documentos Word (.docx) que suelen ser contratos.
    """
    try:
        service = get_drive_service()
        # nextpagetoken nos servirá si después queremos iterar
        results = service.files().list(
            q=query,
            pageSize=max_results,
            fields="nextPageToken, files(id, name, mimeType, webViewLink, createdTime)",
            orderBy="createdTime desc"
        ).execute()
        items = results.get('files', [])
        return items
    except HttpError as error:
        print(f"Ocurrió un error en la API de Drive: {error}")
        return []

def create_project_folder(folder_name: str, parent_id: str = None):
    """
    Permite creación de carpetas para derivados/borradores nuevos (Escritura Restringida).
    """
    try:
        service = get_drive_service()
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]

        folder = service.files().create(body=file_metadata, fields='id, name, webViewLink').execute()
        return folder.get('id')
    except HttpError as error:
        print(f"Ocurrió un error al crear la carpeta '{folder_name}': {error}")
        return None

def download_file(file_id: str, dest_path: str):
    """
    Descarga archivo desde Drive para procesarlo localmente y alimentar el RAG / Gemini.
    """
    import io
    from googleapiclient.http import MediaIoBaseDownload
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
