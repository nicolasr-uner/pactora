# utils/file_parser.py
from docx import Document
import PyPDF2
import io

def extract_text_from_file(file_obj, filename):
    """
    Extrae texto de un archivo tipo .docx o .pdf.
    """
    text = ""
    try:
        if filename.endswith('.docx'):
            doc = Document(file_obj)
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif filename.endswith('.pdf'):
            reader = PyPDF2.PdfReader(file_obj)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        else:
            text = file_obj.read().decode('utf-8')
    except Exception as e:
        return f"Error al extraer texto: {e}"
    
    return text
