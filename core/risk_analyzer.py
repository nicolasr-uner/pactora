import os
import json
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def analyze_risk(content: str, contract_type: str) -> dict:
    """
    Evaluates contract clauses against energy regulations (CREG/BMA) and standard templates.
    Returns a Risk Traffic Light classification (Red, Yellow, Green) with justification.
    """
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY environment variable not set."}
        
    prompt = f"""
Eres un experto legal y técnico en energía solar, y Oficial de Cumplimiento (Compliance Officer) para Unergy/Suno/Solenium.
Analiza el siguiente texto de un contrato tipo {contract_type}.

Deberás evaluar el riesgo general del contrato bajo el siguiente esquema de Semáforo de Riesgo:
- ROJO (Riesgo Alto): Incumplimiento crítico de la normativa CREG o de la BMA (Bermuda Monetary Authority), o ausencia grave de cláusulas esenciales (ej. Fuerza Mayor, Terminación Anticipada sin justa causa, cesión no autorizada).
- AMARILLO (Riesgo Medio): Desviaciones mayores al 10% frente a la plantilla maestra (ej. penalidades excesivas, plazos comerciales desbalanceados, garantías atípicas).
- VERDE (Riesgo Bajo/Estándar): El contrato fluye acorde a los estándares del mercado y protege a Unergy/Suno.

Debes devolver el resultado estrictamente en formato JSON con la siguiente estructura:
{{
  "Nivel": "ROJO|AMARILLO|VERDE",
  "Justificacion": "Explicación detallada de por qué se asignó este nivel de riesgo.",
  "Alertas": [
    "Cláusula 4.2 excede la penalidad estándar por retraso en el COD.",
    "Falta cláusula de Fuerza Mayor."
  ]
}}

A continuación el contrato:
"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        full_prompt = prompt + "\n\n" + content
        
        response = model.generate_content(full_prompt)
        response_text = response.text.strip()
        
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        extracted_data = json.loads(response_text)
        return extracted_data
        
    except json.JSONDecodeError as e:
        print(f"Error parsing Gemini JSON response for risk: {e}")
        return {"error": "Failed to parse JSON from AI response."}
    except Exception as e:
        print(f"Error calling Gemini AI for risk: {e}")
        return {"error": str(e)}
