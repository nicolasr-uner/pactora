import io


def extract_text_from_file(file_obj, filename: str, gemini_api_key: str = None) -> str:
    """
    Extrae texto de PDF o DOCX usando librerias locales.
    gemini_api_key reservado para uso futuro (OCR de PDFs escaneados).
    """
    fname = filename.lower()

    if fname.endswith(".docx"):
        return _extract_docx(file_obj)
    elif fname.endswith(".pdf"):
        if hasattr(file_obj, "read"):
            file_bytes = file_obj.read()
        else:
            file_bytes = bytes(file_obj)
        return _extract_pdf_bytes(file_bytes)
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
    """Intenta pypdf primero, luego PyPDF2."""
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
