import io
import logging

_log = logging.getLogger("pactora")


def extract_text_from_file(file_obj, filename: str, gemini_api_key: str = None) -> str:
    """
    Extrae texto de PDF, DOCX, XLSX, XLS, CSV o TXT usando librerías locales.
    Para PDFs escaneados intenta pymupdf como fallback con mejor extracción.
    """
    fname = filename.lower()

    if fname.endswith(".docx"):
        return _extract_docx(file_obj)
    elif fname.endswith(".pdf"):
        file_bytes = file_obj.read() if hasattr(file_obj, "read") else bytes(file_obj)
        return _extract_pdf_bytes(file_bytes)
    elif fname.endswith(".xlsx") or fname.endswith(".xls"):
        return _extract_excel(file_obj, fname)
    elif fname.endswith(".csv"):
        return _extract_csv(file_obj)
    elif fname.endswith(".txt") or fname.endswith(".md"):
        try:
            raw = file_obj.read() if hasattr(file_obj, "read") else bytes(file_obj)
            return raw.decode("utf-8", errors="replace")
        except Exception:
            return ""
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


def _extract_excel(file_obj, fname: str) -> str:
    """Extrae texto de XLSX (openpyxl) o XLS (xlrd)."""
    file_bytes = file_obj.read() if hasattr(file_obj, "read") else bytes(file_obj)

    # XLSX con openpyxl
    if fname.endswith(".xlsx"):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
            parts = []
            for sheet in wb.worksheets:
                parts.append(f"[Hoja: {sheet.title}]")
                for row in sheet.iter_rows(values_only=True):
                    row_text = " | ".join(str(c) for c in row if c is not None and str(c).strip())
                    if row_text:
                        parts.append(row_text)
            return "\n".join(parts)
        except Exception as e:
            return f"Error extrayendo XLSX: {e}"

    # XLS con xlrd
    try:
        import xlrd
        wb = xlrd.open_workbook(file_contents=file_bytes)
        parts = []
        for sheet in wb.sheets():
            parts.append(f"[Hoja: {sheet.name}]")
            for rx in range(sheet.nrows):
                row_text = " | ".join(str(v) for v in sheet.row_values(rx) if str(v).strip())
                if row_text:
                    parts.append(row_text)
        return "\n".join(parts)
    except Exception as e:
        return f"Error extrayendo XLS: {e}"


def _extract_csv(file_obj) -> str:
    try:
        import csv
        raw = file_obj.read() if hasattr(file_obj, "read") else bytes(file_obj)
        text = raw.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        return "\n".join(" | ".join(row) for row in reader if any(c.strip() for c in row))
    except Exception as e:
        return f"Error extrayendo CSV: {e}"


def _extract_pdf_bytes(file_bytes: bytes) -> str:
    """Intenta pypdf → PyPDF2 → pymupdf (mejor para PDFs complejos)."""
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

    # Intento 3: pymupdf (fitz) — mejor extracción en PDFs con layouts complejos
    try:
        import fitz  # pymupdf
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        parts = []
        for page in doc:
            text = page.get_text("text")
            if text and text.strip():
                parts.append(text)
        doc.close()
        if parts:
            return "\n".join(parts)
    except Exception:
        pass

    # Intento 4: Gemini Vision OCR — para PDFs escaneados sin texto seleccionable
    try:
        from core.llm_service import LLM_AVAILABLE, GEMINI_API_KEY
        if LLM_AVAILABLE:
            import fitz  # pymupdf
            from google import genai  # type: ignore
            import PIL.Image

            client = genai.Client(api_key=GEMINI_API_KEY)

            doc = fitz.open(stream=file_bytes, filetype="pdf")
            parts = []
            for page in doc:
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                img = PIL.Image.open(io.BytesIO(img_bytes))
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[
                        "Extrae todo el texto de esta página de documento. Devuelve solo el texto preservando estructura y párrafos.",
                        img,
                    ],
                )
                page_text = response.text if response.text else ""
                if page_text.strip():
                    parts.append(page_text)
            doc.close()

            if parts:
                result = "\n".join(parts)
                _log.info("[file_parser] OCR Gemini Vision exitoso — %d páginas, %d chars", len(parts), len(result))
                return result
    except Exception as e:
        _log.warning("[file_parser] OCR Gemini Vision falló: %s", e)
        return ""

    return ""
