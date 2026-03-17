"""
preview.py — Renderizado de previsualizaciones de documentos para Pactora CLM.
"""
import io as _io
import logging

import streamlit as st

log = logging.getLogger("pactora")


def render_document_preview(source_name: str, height: int = 660):
    """
    Renderiza previsualización enriquecida para un documento indexado.
    Orden de intentos:
      1. PDF bytes en _file_cache (subidos en sesión actual) → base64 iframe
      2. drive_id en metadata de ChromaDB:
         - PDF → embed Google Drive viewer (/preview) sin descarga
         - Otros → descarga + render (imagen, Excel, CSV)
      3. Texto de chunks del vectorstore → div scrollable
    """
    fname_lower = source_name.lower()

    # 1. PDF en caché de sesión (subido manualmente en esta sesión)
    cached_pdf = st.session_state.get("_file_cache", {}).get(source_name)
    if cached_pdf and fname_lower.endswith(".pdf"):
        import base64 as _b64
        b64_pdf = _b64.b64encode(cached_pdf).decode()
        st.markdown(
            f'<iframe src="data:application/pdf;base64,{b64_pdf}" '
            f'width="100%" height="{height}" '
            f'style="border:1px solid #e0d4f7;border-radius:8px;"></iframe>',
            unsafe_allow_html=True,
        )
        st.download_button(
            "⬇ Descargar PDF", data=cached_pdf,
            file_name=source_name, mime="application/pdf",
            key=f"dl_pdf_prev_{source_name}",
        )
        return

    # 2. Buscar drive_id en metadata de ChromaDB
    drive_id = None
    try:
        cb = st.session_state.get("chatbot")
        if cb and cb.vectorstore:
            result = cb.vectorstore.get(include=["metadatas"])
            for m in result.get("metadatas", []):
                if m and m.get("source") == source_name and m.get("drive_id"):
                    drive_id = m["drive_id"]
                    break
    except Exception:
        pass

    if drive_id:
        if fname_lower.endswith(".pdf"):
            # 2a. PDF desde Drive — embed directo vía Google Viewer
            import streamlit.components.v1 as _components
            embed_url = f"https://drive.google.com/file/d/{drive_id}/preview"
            _components.iframe(embed_url, height=height, scrolling=True)
            dl_cache_key = f"_drive_dl_{drive_id}"
            dl_bytes = st.session_state.get(dl_cache_key)
            if dl_bytes:
                st.download_button(
                    "⬇ Descargar PDF", data=dl_bytes,
                    file_name=source_name, mime="application/pdf",
                    key=f"dl_pdf_drv_{drive_id}",
                )
            else:
                if st.button("⬇ Descargar PDF", key=f"dl_drv_btn_{drive_id}"):
                    with st.spinner("Descargando desde Drive..."):
                        try:
                            from utils.drive_manager import download_file_to_io
                            fio = download_file_to_io(drive_id)
                            if fio:
                                st.session_state[dl_cache_key] = fio.read()
                                st.rerun()
                        except Exception as _e:
                            st.error(f"Error al descargar: {_e}")
            return

        # 2b. Archivo no-PDF desde Drive — descargar y renderizar
        cache_key = f"_drive_preview_{drive_id}"
        file_bytes = st.session_state.get(cache_key)
        if file_bytes is None:
            with st.spinner(f"Cargando {source_name} desde Drive..."):
                try:
                    from utils.drive_manager import download_file_to_io
                    fio = download_file_to_io(drive_id)
                    if fio:
                        file_bytes = fio.read()
                        st.session_state[cache_key] = file_bytes
                except Exception as _e:
                    log.warning("[preview] Error descargando %s: %s", source_name, _e)

        if file_bytes:
            if any(fname_lower.endswith(e) for e in (".png", ".jpg", ".jpeg")):
                st.image(file_bytes, caption=source_name)
                return
            elif fname_lower.endswith(".tiff") or fname_lower.endswith(".tif"):
                try:
                    from PIL import Image
                    img = Image.open(_io.BytesIO(file_bytes))
                    st.image(img, caption=source_name)
                except Exception:
                    st.info("Formato TIFF — descarga el archivo para verlo.")
                st.download_button(
                    "⬇ Descargar imagen", data=file_bytes,
                    file_name=source_name, key=f"dl_img_drv_{drive_id}",
                )
                return
            elif fname_lower.endswith(".xlsx"):
                try:
                    import pandas as _pd
                    df = _pd.read_excel(_io.BytesIO(file_bytes), nrows=200)
                    st.dataframe(df, width="stretch", height=height)
                    st.download_button(
                        "⬇ Descargar Excel", data=file_bytes,
                        file_name=source_name, key=f"dl_xlsx_drv_{drive_id}",
                    )
                    return
                except Exception as _e:
                    st.warning(f"No se pudo mostrar como tabla: {_e}")
            elif fname_lower.endswith(".csv"):
                try:
                    import pandas as _pd
                    import io as _io2
                    df = _pd.read_csv(
                        _io2.StringIO(file_bytes.decode("utf-8", errors="replace")),
                        nrows=200,
                    )
                    st.dataframe(df, width="stretch", height=height)
                    return
                except Exception as _e:
                    st.warning(f"No se pudo mostrar como tabla: {_e}")

    # 3. Fallback: texto de chunks — div scrollable
    try:
        cb = st.session_state.get("chatbot")
        if cb and cb.vectorstore:
            result = cb.vectorstore.get(include=["documents", "metadatas"])
            chunks = [
                d for d, m in zip(result.get("documents", []), result.get("metadatas", []))
                if m and m.get("source") == source_name
            ]
            if chunks:
                full_text = "\n\n─────────────────────\n\n".join(chunks)
                safe_text = (
                    full_text[:30000]
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                st.markdown(
                    f'<div style="height:{height}px;overflow-y:auto;padding:20px 24px;'
                    f'background:#ffffff;border:1px solid #e0e0e0;border-radius:8px;'
                    f'font-family:\'Georgia\',serif;font-size:13.5px;line-height:1.75;'
                    f'color:#212121;white-space:pre-wrap;">{safe_text}</div>',
                    unsafe_allow_html=True,
                )
                st.download_button(
                    "⬇ Exportar texto", data=full_text.encode("utf-8"),
                    file_name=f"{source_name}_texto.txt", mime="text/plain",
                    key=f"dl_txt_prev_{source_name}",
                )
                return
    except Exception:
        pass

    st.info("Sin previsualización disponible para este documento.")
