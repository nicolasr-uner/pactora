import io
import os
import tempfile


def extract_text_from_file(file_obj, filename: str, gemini_api_key: str = None) -> str:
    """
    Extrae texto de PDF o DOCX.
    Para PDFs escaneados (sin texto embebido), usa Gemini Files API como fallback.
    """
    fname = filename.lower()

    if fname.endswith(".docx"):
        return _extract_docx(file_obj)
    elif fname.endswith(".pdf"):
        # Leer bytes una sola vez para poder reintentar
        if hasattr(file_obj, "read"):
            file_bytes = file_obj.read()
        else:
            file_bytes = bytes(file_obj)

        text = _extract_pdf_bytes(file_bytes)

        # Si no hay texto (PDF escaneado), intentar con Gemini
        if not text.strip() and gemini_api_key:
            text = _extract_with_gemini(file_bytes, filename, gemini_api_key)

        return text
    else:
        try:
            raw = file_obj.read() if hasattr(file_obj, "read") else bytes(file_obj)
            return raw.decode("utf-8", errors="replace")
        except Exception:
            return ""


def _extract_docx(file_obj) -> str:
    try:
        from docx import Document
        doc = Document(file_obj)
        parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text)
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
                if row_text:
                    parts.append(row_text)
        return "\n".join(parts)
    except Exception as e:
        return f"Error extrayendo DOCX: {e}"


def _extract_pdf_bytes(file_bytes: bytes) -> str:
    """Intenta pypdf primero, luego PyPDF2. Maneja paginas None."""
    # Intento 1: pypdf
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        parts = [t for page in reader.pages for t in [page.extract_text()] if t and t.strip()]
        if parts:
            return "\n".join(parts)
    except Exception:
        pass

    # Intento 2: PyPDF2
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        parts = [t for page in reader.pages for t in [page.extract_text()] if t and t.strip()]
        if parts:
            return "\n".join(parts)
    except Exception:
        pass

    return ""


def _extract_with_gemini(file_bytes: bytes, filename: str, api_key: str) -> str:
    """
    Lee el PDF directamente con Gemini Files API.
    Funciona con PDFs escaneados (imagenes) que PyPDF2 no puede leer.
    """
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)

        # Escribir a archivo temporal para subir a Gemini
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(file_bytes)
            tmp_path = f.name

        try:
            uploaded = genai.upload_file(
                tmp_path,
                mime_type="application/pdf",
                display_name=filename
            )
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content([
                uploaded,
                "Extrae todo el texto de este contrato. "
                "Incluye partes, clausulas, fechas, montos y obligaciones. "
                "Solo el texto del documento, sin reformatear ni resumir."
            ])
            # Eliminar el archivo de Gemini despues de usarlo
            try:
                genai.delete_file(uploaded.name)
            except Exception:
                pass
            return response.text or ""
        finally:
            os.unlink(tmp_path)

    except Exception as e:
        return ""
