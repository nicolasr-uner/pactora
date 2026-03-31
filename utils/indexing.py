"""
indexing.py — Indexación de documentos Drive, backup/restore ChromaDB, metadata local.
"""
from __future__ import annotations

import datetime
import json
import logging
import os
import threading

import streamlit as st

log = logging.getLogger("pactora")

# ─── Constantes ────────────────────────────────────────────────────────────────
CHROMADB_BACKUP_FILENAME = "_pactora_chromadb_backup.zip"
CHROMADB_DIR = "./chroma_db"
INDEX_METADATA_FILE = "./_pactora_index_metadata.json"

# ─── Estado del proceso de indexación (compartido entre threads) ───────────────
_startup_index_triggered = False
_startup_index_lock = threading.Lock()
_startup_index_progress: dict = {
    "status": "idle",   # idle | running | complete | error
    "total": 0,
    "downloaded": 0,
    "indexed": 0,
    "last_file": "",
    "error": "",
    "file_counts": {},
    "ocr_quota_failed": 0,
    "ocr_quota_error": False,
}


# ─── Metadata helpers ──────────────────────────────────────────────────────────

def _load_index_metadata() -> dict:
    """Carga el archivo de metadata de indexación local."""
    try:
        if os.path.exists(INDEX_METADATA_FILE):
            with open(INDEX_METADATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        log.warning("[meta] Error cargando metadata: %s", e)
    return {}


def _save_index_metadata(meta: dict) -> None:
    """Guarda el archivo de metadata de indexación local."""
    try:
        with open(INDEX_METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning("[meta] Error guardando metadata: %s", e)


# ─── ChromaDB backup / restore ─────────────────────────────────────────────────

def _restore_chromadb_from_drive(drive_root_id: str) -> bool:
    """Descarga y extrae el backup ZIP de ChromaDB desde Drive. Retorna True si restauró."""
    import zipfile
    try:
        from utils.auth_helper import get_drive_service
        service = get_drive_service()
        if not service:
            log.info("[restore] Sin servicio Drive — omitiendo restore.")
            return False

        query = (
            f"name='{CHROMADB_BACKUP_FILENAME}' and "
            f"'{drive_root_id}' in parents and trashed=false"
        )
        result = service.files().list(
            q=query, fields="files(id, modifiedTime)",
            supportsAllDrives=True, includeItemsFromAllDrives=True,
        ).execute()
        found = result.get("files", [])
        if not found:
            log.info("[restore] No hay backup de ChromaDB en Drive.")
            return False

        file_id = found[0]["id"]
        log.info("[restore] Descargando backup ChromaDB (id: %s)...", file_id[:20])

        from utils.drive_manager import _do_download
        zip_io = _do_download(service, file_id)

        try:
            with zipfile.ZipFile(zip_io, "r") as zf:
                bad = zf.testzip()
                if bad:
                    log.error("[restore] ZIP corrupto — primer archivo dañado: %s", bad)
                    return False
                zip_io.seek(0)
                zf.extractall(".")
        except zipfile.BadZipFile as bz:
            log.error("[restore] ZIP no válido: %s", bz)
            return False

        log.info("[restore] ChromaDB restaurado desde Drive.")
        return True
    except Exception as e:
        log.error("[restore] Error al restaurar ChromaDB: %s", e)
        return False


def _backup_chromadb_to_drive(drive_root_id: str) -> bool:
    """Comprime ./chroma_db/ y sube el ZIP a Drive. Retorna True si tuvo éxito."""
    import io
    import zipfile
    try:
        if not os.path.exists(CHROMADB_DIR):
            log.warning("[backup] chroma_db no existe — nada que hacer backup.")
            return False

        from utils.auth_helper import get_drive_service
        from googleapiclient.http import MediaIoBaseUpload

        service = get_drive_service()
        if not service:
            log.warning("[backup] Sin servicio Drive — backup omitido.")
            return False

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, files in os.walk(CHROMADB_DIR):
                for fname in files:
                    filepath = os.path.join(root, fname)
                    arcname = os.path.relpath(filepath, ".")
                    zf.write(filepath, arcname)
        zip_size = zip_buffer.tell()
        zip_buffer.seek(0)
        log.info("[backup] ZIP creado: %.1f MB", zip_size / 1024 / 1024)

        media = MediaIoBaseUpload(zip_buffer, mimetype="application/zip", resumable=True)
        query = (
            f"name='{CHROMADB_BACKUP_FILENAME}' and "
            f"'{drive_root_id}' in parents and trashed=false"
        )
        existing = service.files().list(
            q=query, fields="files(id)",
            supportsAllDrives=True, includeItemsFromAllDrives=True,
        ).execute().get("files", [])

        if existing:
            service.files().update(
                fileId=existing[0]["id"], media_body=media,
                supportsAllDrives=True,
            ).execute()
            log.info("[backup] Backup actualizado en Drive.")
        else:
            service.files().create(
                body={"name": CHROMADB_BACKUP_FILENAME, "parents": [drive_root_id]},
                media_body=media, fields="id",
                supportsAllDrives=True,
            ).execute()
            log.info("[backup] Backup creado en Drive.")

        return True
    except Exception as e:
        err_str = str(e)
        if "storageQuotaExceeded" in err_str or "Service Accounts do not have storage quota" in err_str:
            log.warning(
                "[backup] Backup omitido — Service Accounts no tienen cuota de almacenamiento personal. "
                "Usa una Shared Drive o configura OAuth delegation."
            )
        else:
            log.error("[backup] Error al hacer backup ChromaDB: %s", e)
        return False


# ─── Background indexation ────────────────────────────────────────────────────

def _extract_and_save_profiles(docs: list, index_meta: dict) -> None:
    """
    Extrae un perfil estructurado (via LLM) para cada contrato recién indexado
    y lo persiste en el Contract Profiles Sheet.

    Solo actúa si LLM_AVAILABLE es True y CONTRACT_PROFILES_SHEET_ID está configurado.
    Guarda 'profile_extracted: True' en index_meta para evitar re-extracción.
    Los errores individuales se registran como warning sin abortar el proceso.
    """
    try:
        from core.llm_service import (
            LLM_AVAILABLE,
            detect_contract_type,
            extract_contract_profile,
            write_contract_profile,
        )
        if not LLM_AVAILABLE:
            return

        for text, filename, meta in docs:
            if index_meta.get(filename, {}).get("profile_extracted"):
                continue
            try:
                contract_type = detect_contract_type(filename, text)
                drive_id = meta.get("drive_id", "") if isinstance(meta, dict) else ""
                profile = extract_contract_profile(text, filename, contract_type, drive_id)
                write_contract_profile(profile)
                if filename in index_meta:
                    index_meta[filename]["profile_extracted"] = True
                log.info("[profile] Perfil extraído: %s (%s)", filename, contract_type)
            except Exception as e:
                log.warning("[profile] Error extrayendo perfil de '%s': %s", filename, e)
    except Exception as e:
        log.warning("[profile] _extract_and_save_profiles falló: %s", e)


def _get_chatbot_cached():
    """Obtiene la instancia compartida del chatbot desde st.cache_resource."""
    # Import inline para evitar circular imports con shared.py
    from utils.shared import _get_chatbot
    return _get_chatbot()


def _bg_startup_index(api_key, drive_root_id, drive_api_key):
    """Background thread: indexa todos los contratos de Drive en el startup del servidor."""
    chatbot = _get_chatbot_cached()
    prog = _startup_index_progress
    try:
        import concurrent.futures
        try:
            from utils.drive_manager import get_recursive_files, download_file_to_io
            from utils.file_parser import extract_text_from_file
        except (ImportError, KeyError) as _ie:
            log.error("Modulos no disponibles (hot-reload race): %s — abortando", _ie)
            prog["status"] = "error"
            prog["error"] = f"Import error: {_ie}"
            return

        index_meta = _load_index_metadata()

        restored = _restore_chromadb_from_drive(drive_root_id)
        if restored:
            chatbot._initialize_vectorstore()
            try:
                stats = chatbot.get_stats()
                chatbot._indexed_sources = stats.get("sources", [])
                log.info("[restore] Vectorstore recargado: %d docs, %d fuentes",
                         stats["total_docs"], len(chatbot._indexed_sources))
            except Exception as re:
                log.warning("[restore] No se pudieron cargar sources: %s", re)
        else:
            # Verificar si ChromaDB realmente tiene documentos
            try:
                chroma_count = chatbot.get_stats().get("total_docs", 0)
            except Exception:
                chroma_count = 0

            if chroma_count > 0 and index_meta:
                # ChromaDB tiene datos propios — el JSON es confiable como guía diferencial
                for fname in index_meta:
                    if fname not in chatbot._indexed_sources:
                        chatbot._indexed_sources.append(fname)
                log.info("[restore] _indexed_sources desde metadata JSON: %d entradas",
                         len(chatbot._indexed_sources))
            else:
                # ChromaDB vacío — el JSON está desincronizado, re-indexar todo desde Drive
                log.info("[restore] ChromaDB vacío sin backup — ignorando metadata local, se re-indexará todo.")
                index_meta = {}

        log.info("Iniciando indexacion de Drive (carpeta: %s)", drive_root_id)
        all_files = get_recursive_files(drive_root_id, api_key=drive_api_key)
        log.info("Archivos encontrados en Drive: %d", len(all_files))

        files_to_index = [
            f for f in all_files
            if f["name"] not in chatbot._indexed_sources
            and f["name"] not in index_meta
        ]
        already = len(all_files) - len(files_to_index)
        if already:
            log.info("Ya indexados previamente: %d archivo(s)", already)

        if not files_to_index:
            log.info("Nada nuevo que indexar.")
            prog["status"] = "complete"
            return

        log.info("Archivos nuevos a indexar: %d", len(files_to_index))
        prog["status"] = "running"
        prog["total"] = len(files_to_index)
        prog["downloaded"] = 0
        prog["indexed"] = 0
        prog["file_counts"] = {}

        BATCH = 20
        BACKUP_EVERY = 50
        total_indexed = 0

        def _ext_from_name(name: str) -> str:
            parts = name.rsplit(".", 1)
            return parts[-1].lower() if len(parts) > 1 else "otro"

        for batch_start in range(0, len(files_to_index), BATCH):
            batch = files_to_index[batch_start: batch_start + BATCH]
            log.info(
                "Lote %d/%d — archivos %d a %d",
                batch_start // BATCH + 1, -(-len(files_to_index) // BATCH),
                batch_start + 1, min(batch_start + BATCH, len(files_to_index)),
            )

            docs = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
                future_to_file = {
                    ex.submit(download_file_to_io, f["id"], drive_api_key, f.get("mimeType")): f
                    for f in batch
                }
                for future in concurrent.futures.as_completed(future_to_file, timeout=120):
                    f = future_to_file[future]
                    try:
                        fio = future.result()
                        prog["last_file"] = f["name"]
                        if fio:
                            txt = extract_text_from_file(fio, f["name"])
                            if txt == "QUOTA_EXHAUSTED":
                                prog["downloaded"] += 1
                                prog["ocr_quota_failed"] = prog.get("ocr_quota_failed", 0) + 1
                                prog["ocr_quota_error"] = True
                                log.warning("OCR cuota agotada: %s — omitido", f["name"])
                            elif txt and not txt.startswith("Error"):
                                docs.append((txt, f["name"], {"drive_id": f["id"]}))
                                prog["downloaded"] += 1
                                ext = _ext_from_name(f["name"])
                                prog["file_counts"][ext] = prog["file_counts"].get(ext, 0) + 1
                                index_meta[f["name"]] = {
                                    "drive_id": f["id"],
                                    "indexed_at": datetime.datetime.utcnow().isoformat(),
                                    "size": f.get("size", 0),
                                    "ext": ext,
                                }
                                log.info("OK (%d/%d): %s — %d chars",
                                         prog["downloaded"], prog["total"], f["name"], len(txt))
                            elif txt and txt.startswith("Error"):
                                prog["downloaded"] += 1
                                prog["error"] = f"{f['name']}: {txt[:100]}"
                                log.warning("Error extraccion %s: %s", f["name"], txt[:100])
                            else:
                                prog["downloaded"] += 1
                                log.warning("Sin texto: %s", f["name"])
                        else:
                            prog["downloaded"] += 1
                            log.warning("Descarga vacia: %s", f["name"])
                    except concurrent.futures.TimeoutError:
                        prog["downloaded"] += 1
                        log.warning("TIMEOUT: %s — omitido", f["name"])
                    except Exception as e:
                        prog["downloaded"] += 1
                        log.warning("ERROR %s: %s", f["name"], e)

            if docs:
                log.info("Indexando lote: %d documentos a ChromaDB...", len(docs))
                ok, ingest_msg = chatbot.vector_ingest_multiple(docs)
                if ok:
                    total_indexed += len(docs)
                    prog["indexed"] = total_indexed
                    log.info("Lote indexado. Acumulado: %d contrato(s).", total_indexed)
                    _extract_and_save_profiles(docs, index_meta)
                    _save_index_metadata(index_meta)
                    if total_indexed % BACKUP_EVERY == 0:
                        log.info("[backup] Backup parcial en checkpoint: %d docs", total_indexed)
                        _backup_chromadb_to_drive(drive_root_id)
                else:
                    log.error("Error al indexar lote: %s", ingest_msg)

        log.info("Descarga completada. Total con texto valido: %d/%d", total_indexed, len(files_to_index))

        try:
            real_count = chatbot.get_stats()["total_docs"]
            prog["indexed"] = real_count
            log.info("Verificacion ChromaDB: %d documentos.", real_count)
        except Exception as e:
            log.warning("No se pudo verificar ChromaDB: %s", e)

        if prog["indexed"] > 0:
            log.info("[backup] Guardando ChromaDB en Drive...")
            _backup_chromadb_to_drive(drive_root_id)

        prog["status"] = "complete"
        log.info("Indexacion finalizada. Total en ChromaDB: %d", prog["indexed"])
    except Exception as e:
        prog["status"] = "error"
        prog["error"] = str(e)[:120]
        log.error("Error fatal en indexacion: %s", e, exc_info=True)


def _trigger_startup_index(chatbot, drive_root_id: str, drive_api_key: str) -> None:
    """Lanza una sola indexación en background por proceso del servidor."""
    global _startup_index_triggered
    with _startup_index_lock:
        if _startup_index_triggered:
            return
        _startup_index_triggered = True
    api_key = chatbot.api_key if chatbot else None
    t = threading.Thread(
        target=_bg_startup_index,
        args=(api_key, drive_root_id, drive_api_key),
        daemon=True,
    )
    t.start()


def force_reindex(chatbot=None) -> None:
    """Resetea el flag y limpia _indexed_sources para re-indexar todos los archivos."""
    global _startup_index_triggered
    with _startup_index_lock:
        _startup_index_triggered = False
    _startup_index_progress.update({
        "status": "idle", "total": 0, "downloaded": 0,
        "indexed": 0, "last_file": "", "error": "",
    })
    if chatbot is not None:
        chatbot._indexed_sources = []


def run_drive_indexation(drive_root_id: str, drive_api_key: str):
    """Indexa todos los documentos del Drive con timeout por archivo. Retorna (ok, msg)."""
    import concurrent.futures
    from utils.drive_manager import get_recursive_files, download_file_to_io
    from utils.file_parser import extract_text_from_file

    def _download(fid, mime=None):
        return download_file_to_io(fid, api_key=drive_api_key, mime_type=mime)

    try:
        all_files = get_recursive_files(drive_root_id, api_key=drive_api_key)
        if not all_files:
            return False, "No se encontraron archivos PDF/DOCX en la carpeta."

        files_to_index = [
            f for f in all_files
            if f["name"] not in st.session_state.chatbot._indexed_sources
        ]
        docs = []
        skipped = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            future_to_file = {
                ex.submit(_download, f["id"], f.get("mimeType")): f
                for f in files_to_index
            }
            for future, f in future_to_file.items():
                try:
                    fio = future.result(timeout=30)
                    if fio:
                        txt = extract_text_from_file(fio, f["name"])
                        if txt and not txt.startswith("Error"):
                            docs.append((txt, f["name"], {}))
                        else:
                            skipped.append(f["name"])
                    else:
                        skipped.append(f["name"])
                except concurrent.futures.TimeoutError:
                    skipped.append(f["name"] + " (timeout)")
                except Exception:
                    skipped.append(f["name"])

        if not docs:
            msg = "No se pudo descargar ningun archivo nuevo."
            if skipped:
                msg += f" Omitidos: {', '.join(skipped[:5])}"
            return False, msg

        ok, ingest_msg = st.session_state.chatbot.vector_ingest_multiple(docs)
        msg = f"{len(docs)} contrato(s) indexados en JuanMitaBot."
        if skipped:
            msg += f" Omitidos ({len(skipped)}): {', '.join(skipped[:3])}"
        return ok, msg

    except Exception as e:
        return False, f"Error durante indexacion: {e}"
