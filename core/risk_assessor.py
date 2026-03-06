import json
import os
import google.generativeai as genai

def _load_gemini_key():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("GEMINI_API_KEY")
        except Exception:
            pass
    return key

GEMINI_API_KEY = _load_gemini_key()
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def analyze_legal_risk(contract_text: str, contract_type: str) -> dict:
    """
    Analyzes contract text for risks and CREG compliance.
    Returns a list of risk objects with level (Red/Yellow/Green), clause, and reason.
    """
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY not configured."}
    
    prompt = f"""
Eres un 'Legal Engineer' Senior experto en el sector energético de Colombia (CREG, Resolución 030/015) y en contratos de Unergy.
Tu objetivo es realizar un análisis de riesgo técnico-legal de un contrato de tipo: {contract_type}.

Debes clasificar los riesgos en el siguiente formato JSON:
{{
  "risks": [
    {{
      "level": "Rojo" | "Amarillo" | "Verde",
      "clause": "Título o contexto de la cláusula",
      "reason": "Explicación breve del riesgo o cumplimiento",
      "action": "Acción recomendada"
    }}
  ],
  "compliance_score": 0-100,
  "summary": "Resumen ejecutivo del estado de riesgo"
}}

Criterios de Clasificación (Semáforo de Pactora):
- Rojo (Riesgo Crítico): Incumplimiento CREG, falta de Fuerza Mayor en EPC, penalidades > 20% CAPEX, riesgos de asimetría contractual severa.
- Amarillo (Revisión): Desviación de la 'Plantilla Maestra' de Unergy, fórmulas de indexación no estándar (fuera de IPP/IPC), plazos de PPA < 5 años.
- Verde (Estándar): Alineado con políticas de Unergy y normatividad vigente.

Texto del Contrato:
{contract_text}
"""
    
    try:
        model = genai.GenerativeModel('models/gemini-1.5-pro')
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Cleanup JSON formatting
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        risk_data = json.loads(response_text)
        return risk_data
        
    except Exception as e:
        print(f"Error in risk assessment: {e}")
        return {"error": str(e), "risks": [], "compliance_score": 0}
