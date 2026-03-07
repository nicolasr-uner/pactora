import io

def extract_text_from_file(file_obj, filename: str) -> str:
    """
    Extrae texto de PDF o DOCX. Intenta multiples librerias en orden.
    Retorna string con el texto, o string vacio si no hay texto extraible.
    """
    fname = filename.lower()

    if fname.endswith(".docx"):
        return _extract_docx(file_obj)
    elif fname.endswith(".pdf"):
        return _extract_pdf(file_obj)
    else:
        try:
            raw = file_obj.read()
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
        # Incluir tablas
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    parts.append(row_text)
        return "\n".join(parts)
    except Exception as e:
        return f"Error extrayendo DOCX: {e}"


def _extract_pdf(file_obj) -> str:
    """Intenta pypdf primero, luego PyPDF2, acepta texto parcial."""
    # Asegurar que estamos al inicio
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)

    text = ""

    # Intento 1: pypdf (mas moderno, mejor manejo de PDFs complejos)
    try:
        import pypdf
        reader = pypdf.PdfReader(file_obj)
        parts = []
        for page in reader.pages:
            try:
                t = page.extract_text()
                if t:
                    parts.append(t)
            except Exception:
                pass
        text = "\n".join(parts)
        if text.strip():
            return text
    except ImportError:
        pass
    except Exception:
        pass

    # Intento 2: PyPDF2 como fallback
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(file_obj)
        parts = []
        for page in reader.pages:
            try:
                t = page.extract_text()
                if t:
                    parts.append(t)
            except Exception:
                pass
        text = "\n".join(parts)
        if text.strip():
            return text
    except Exception:
        pass

    # Si llegamos aqui, el PDF es probablemente escaneado (solo imagen)
    # Retornamos string vacio (no "Error") para que se cuente como procesado
    return ""
