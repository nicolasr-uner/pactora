import os
import json
import google.generativeai as genai

# Setup Gemini API key (Should be configured in environment or secrets)
# For Streamlit, st.secrets can be used, but for now we expect it in the environment
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
# We will init the model when needed

def get_extraction_prompt(contract_type: str) -> str:
    """
    Returns the specific prompt based on the energy contract type.
    """
    base_prompt = f"""
Eres un experto legal y técnico en energía solar (Cerebro Sectorial Energético).
Analiza el siguiente contrato de tipo {contract_type}.

Debes extraer métricas críticas y estructurarlas en formato JSON estricto con las siguientes claves:
1. "Precio": Valor, tarifa o fórmula de indexación (ej. IPP/IPC).
2. "Vigencia": Plazo del contrato, fecha de inicio y fin si están presentes.
3. "Hitos": Fechas u obligaciones temporales clave como NTP (Notice to Proceed) o COD (Commercial Operation Date).
4. "Obligaciones": Obligaciones críticas del contratista y del cliente.
5. "Polizas": Lista de garantías o pólizas exigidas, incluyendo:
    - "Tipo": Tipo de póliza (Cumplimiento, Responsabilidad Civil, etc.)
    - "Valor": Valor asegurado.
    - "Vencimiento": Fecha límite o de vencimiento si se menciona.

El formato de salida debe ser un JSON válido, sin delimitadores extras de markdown (no uses ```json), solo el diccionario JSON crudo para que pueda ser parseado directamente.
Ejemplo de estructura esperada:
{{
  "Precio": "150 USD/MWh indexado al IPC",
  "Vigencia": "15 años",
  "Hitos": "NTP en 30 días, COD en 8 meses",
  "Obligaciones": "El contratista debe construir, el cliente debe proveer el terreno.",
  "Polizas": [
    {{"Tipo": "Cumplimiento", "Valor": "10% del CAPEX", "Vencimiento": "2025-12-31"}}
  ]
}}

A continuación, el texto del contrato:
"""
    return base_prompt

def process_contract(content: str, contract_type: str) -> dict:
    """
    Extracts Pricing, Validity, Obligations, and Policies using Gemini 1.5 Pro.
    Expects 'content' to be the extracted text from the document.
    """
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY environment variable not set."}
        
    try:
        model = genai.GenerativeModel('models/gemini-1.5-pro')
        
        prompt = get_extraction_prompt(contract_type)
        full_prompt = prompt + "\n\n" + content
        
        response = model.generate_content(full_prompt)
        response_text = response.text.strip()
        
        # Clean markdown formatting if accidentally included by Gemini
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        extracted_data = json.loads(response_text)
        return extracted_data
        
    except json.JSONDecodeError as e:
        print(f"Error parsing Gemini JSON response: {e}")
        print(f"Raw response: {response.text}")
        return {"error": "Failed to parse JSON from AI response."}
    except Exception as e:
        print(f"Error calling Gemini AI: {e}")
        return {"error": str(e)}

def extract_text_from_docx(file_bytes: bytes) -> str:
    """
    Helper to extract text from a DOCX file byte stream.
    """
    import io
    import docx
    
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        print(f"Error reading docx: {e}")
        return ""
