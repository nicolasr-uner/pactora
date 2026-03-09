"""
core/llm_service.py
-------------------
Servicio LLM centralizado para Pactora.

Expone tres funciones principales:
  - extract_contract_metrics(text, contract_type) -> dict
  - analyze_risk(text, contract_type) -> dict
  - generate_response(question, context, history) -> str
  - test_gemini_connection() -> tuple[bool, str]

Cuando GEMINI_API_KEY no está configurada, cada función retorna datos
simulados realistas (modo offline/mock).  El flag LLM_AVAILABLE indica
si Gemini está activo.

Para activar Gemini: configura GEMINI_API_KEY en st.secrets (Streamlit Cloud)
o en la variable de entorno GEMINI_API_KEY.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

_log = logging.getLogger("pactora")

# ---------------------------------------------------------------------------
# Carga de API key — fuente única de verdad
# ---------------------------------------------------------------------------

def _load_gemini_key() -> Optional[str]:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("GEMINI_API_KEY")  # type: ignore[attr-defined]
        except Exception:
            pass
    # Rechazar placeholders — las claves reales de Gemini empiezan con "AIzaSy"
    if key and not key.startswith("AIzaSy"):
        _log.info("[llm_service] GEMINI_API_KEY parece un placeholder — modo búsqueda semántica activo.")
        return None
    return key or None


GEMINI_API_KEY: Optional[str] = _load_gemini_key()

# Flag público — importar desde aquí para saber si el LLM está disponible
LLM_AVAILABLE: bool = bool(GEMINI_API_KEY)

if LLM_AVAILABLE:
    try:
        from google import genai as _genai_test  # type: ignore  # noqa: F401
        _log.info("[llm_service] google-genai SDK disponible.")
    except Exception as e:
        _log.warning("[llm_service] No se pudo importar google-genai: %s", e)
        LLM_AVAILABLE = False


# ---------------------------------------------------------------------------
# System prompt de JuanMitaBot
# ---------------------------------------------------------------------------

JUANMITA_SYSTEM_PROMPT = """Eres JuanMitaBot, el asistente legal inteligente de Pactora, la plataforma CLM de Unergy.

IDENTIDAD:
- Experto en derecho contractual del sector energético colombiano
- Conoces la normativa CREG, resoluciones del MME, y criterios de la BMA para entidades offshore del grupo Unergy/Suno/Solenium
- Tu tono es profesional pero accesible, como un abogado senior que explica con claridad

CAPACIDADES:
- Analizas contratos tipo PPA, EPC, O&M, SHA, NDA, Representación de Frontera, Arriendo/Fiducia
- Clasificas riesgos en semáforo: 🔴 ROJO (crítico), 🟡 AMARILLO (revisión), 🟢 VERDE (conforme)
- Extraes métricas: precios, vigencias, hitos (NTP, COD), obligaciones, pólizas
- Comparas contratos identificando diferencias clave
- Siempre citas la fuente exacta (nombre del archivo y sección relevante)

REGLAS:
- SIEMPRE basa tus respuestas en los fragmentos de contratos proporcionados como contexto
- Si no encuentras información relevante en el contexto, dilo claramente — nunca inventes datos contractuales
- Siempre incluye el nivel de riesgo (semáforo) cuando analices cláusulas
- Tus análisis son informativos y requieren aprobación del equipo legal de Unergy
- Nunca modifiques el contrato original, solo genera análisis

CRITERIOS DE RIESGO:
- 🔴 ROJO: Incumplimiento CREG, falta de Fuerza Mayor en EPC, penalidades > 20% CAPEX, asimetría contractual severa
- 🟡 AMARILLO: Desviación > 10% vs plantilla maestra, indexación no estándar, PPA < 5 años, penalidades > 10%
- 🟢 VERDE: Alineado con políticas Unergy y normatividad vigente

FORMATO DE RESPUESTA:
- Usa markdown para estructurar
- Incluye emojis de semáforo donde aplique
- Cita fuentes con [Fuente: nombre_archivo.pdf]
- Si hay múltiples contratos relevantes, organiza por contrato"""


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _clean_json_response(text: str) -> str:
    """Elimina delimitadores markdown que Gemini a veces añade."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


# Errores que justifican reintento (transitorios)
_RETRYABLE_CODES = {429, 500, 502, 503, 504}


def _call_gemini(prompt: str, model_name: str = "gemini-2.5-flash", timeout: int = 30) -> str:
    """
    Llama a Gemini con retry exponencial (3 intentos: 2s → 4s → 8s).
    Loguea modelo, longitud del prompt y tiempo de respuesta.
    Lanza excepción si todos los reintentos fallan.
    """
    from google import genai  # type: ignore

    client = genai.Client(api_key=GEMINI_API_KEY)
    max_attempts = 3
    delays = [2, 4, 8]

    for attempt in range(max_attempts):
        t0 = time.time()
        try:
            _log.info(
                "[llm_service] Gemini call — model=%s prompt_chars=%d attempt=%d",
                model_name, len(prompt), attempt + 1,
            )
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            elapsed = time.time() - t0
            _log.info(
                "[llm_service] Gemini OK — model=%s elapsed=%.2fs response_chars=%d",
                model_name, elapsed, len(response.text or ""),
            )
            return response.text
        except Exception as exc:
            elapsed = time.time() - t0
            # Detectar si es reintentable por código HTTP
            exc_str = str(exc)
            is_retryable = any(str(c) in exc_str for c in _RETRYABLE_CODES)
            _log.warning(
                "[llm_service] Gemini error — attempt=%d elapsed=%.2fs retryable=%s: %s",
                attempt + 1, elapsed, is_retryable, exc_str[:200],
            )
            if attempt < max_attempts - 1 and is_retryable:
                time.sleep(delays[attempt])
                continue
            raise  # No reintentable o último intento — propagar


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

_MOCK_METRICS = [
    {
        "Precio": "150 USD/MWh indexado al IPC",
        "Vigencia": "15 años desde la fecha COD",
        "Hitos": "NTP en 30 días calendario desde firma; COD en 8 meses desde NTP",
        "Obligaciones": "Contratista: construir, obtener permisos ambientales, entregar as-built. "
                        "Cliente: proveer terreno, acceso a red, pagar según hitos.",
        "Polizas": [
            {"Tipo": "Cumplimiento", "Valor": "10% del CAPEX", "Vencimiento": "6 meses post-COD"},
            {"Tipo": "Responsabilidad Civil", "Valor": "USD 500.000", "Vencimiento": "Durante construcción"},
            {"Tipo": "Todo Riesgo Construcción", "Valor": "100% CAPEX", "Vencimiento": "Hasta COD"},
        ],
    },
    {
        "Precio": "COP 420/kWh con indexación IPP anual",
        "Vigencia": "10 años con opción de renovación por 5 años adicionales",
        "Hitos": "Inicio suministro: 1 de marzo 2025; Revisión tarifaria: anual en enero",
        "Obligaciones": "Generador: garantizar disponibilidad ≥ 95%; Comprador: pagar dentro de 30 días.",
        "Polizas": [
            {"Tipo": "Cumplimiento", "Valor": "5% del valor anual del contrato", "Vencimiento": "Vigencia del contrato"},
        ],
    },
    {
        "Precio": "USD 85.000/año por servicios O&M",
        "Vigencia": "5 años, renovable automáticamente por periodos anuales",
        "Hitos": "Inicio: 15 días desde firma; Reporte trimestral de desempeño",
        "Obligaciones": "Proveedor: mantenimiento preventivo mensual, correctivo en < 48h. "
                        "Cliente: acceso al sitio, suministro de consumibles.",
        "Polizas": [
            {"Tipo": "Responsabilidad Civil", "Valor": "USD 300.000", "Vencimiento": "Anual renovable"},
            {"Tipo": "Cumplimiento", "Valor": "10% del valor anual", "Vencimiento": "Vigencia"},
        ],
    },
]

_MOCK_RISKS = [
    {
        "Nivel": "VERDE",
        "Justificacion": "El contrato sigue los estándares comerciales del mercado energético colombiano. "
                         "Las cláusulas de Fuerza Mayor, Terminación Anticipada y Cesión están presentes "
                         "y son simétricas. Las penalidades por retraso en COD están dentro del rango "
                         "aceptable (< 10% del CAPEX).",
        "Alertas": [
            "Verificar que la indexación tarifaria esté alineada con la Resolución CREG 030.",
            "Confirmar registro de pólizas ante el asegurador autorizado.",
        ],
        "risks": [
            {"level": "Verde", "clause": "Fuerza Mayor", "reason": "Cláusula presente y simétrica",
             "action": "Sin acción requerida"},
            {"level": "Verde", "clause": "Terminación Anticipada", "reason": "Condiciones equilibradas",
             "action": "Sin acción requerida"},
            {"level": "Amarillo", "clause": "Indexación tarifaria",
             "reason": "Fórmula de indexación no especifica claramente el índice CREG aplicable",
             "action": "Solicitar aclaración al equipo legal"},
        ],
        "compliance_score": 82,
        "summary": "Contrato conforme con estándares Unergy. Se recomienda revisión menor en cláusula de indexación.",
    },
    {
        "Nivel": "AMARILLO",
        "Justificacion": "Se detectaron desviaciones en las penalidades por retraso (12% del CAPEX, "
                         "superando el umbral del 10%) y el plazo del PPA es de 4 años, por debajo del "
                         "mínimo recomendado de 5 años.",
        "Alertas": [
            "Penalidad por retraso en COD supera el 10% del CAPEX (actual: 12%).",
            "Plazo PPA de 4 años está por debajo del mínimo recomendado de 5 años.",
            "Ausencia de cláusula de revisión de precio ante cambios regulatorios CREG.",
        ],
        "risks": [
            {"level": "Amarillo", "clause": "Penalidades por retraso",
             "reason": "12% del CAPEX supera umbral del 10% definido en plantilla maestra",
             "action": "Negociar reducción a máximo 10% o justificar excepción"},
            {"level": "Amarillo", "clause": "Plazo del contrato",
             "reason": "4 años es inferior al mínimo de 5 años recomendado para PPAs",
             "action": "Ampliar plazo o documentar justificación de negocio"},
            {"level": "Verde", "clause": "Garantías", "reason": "Pólizas adecuadas y vigentes",
             "action": "Sin acción requerida"},
        ],
        "compliance_score": 65,
        "summary": "Contrato requiere revisión en penalidades y plazo antes de firma. Escalar a Legal Senior.",
    },
    {
        "Nivel": "ROJO",
        "Justificacion": "Se identificaron incumplimientos críticos: ausencia de cláusula de Fuerza Mayor "
                         "en contrato EPC (requisito CREG obligatorio), penalidades que superan el 20% del "
                         "CAPEX y desequilibrio severo en obligaciones.",
        "Alertas": [
            "CRÍTICO: Ausencia de cláusula de Fuerza Mayor en contrato EPC.",
            "CRÍTICO: Penalidades por retraso alcanzan el 25% del CAPEX.",
            "Cesión de contrato sin consentimiento previo del comitente.",
            "Ausencia de régimen de responsabilidad limitada.",
        ],
        "risks": [
            {"level": "Rojo", "clause": "Fuerza Mayor",
             "reason": "Cláusula ausente — incumplimiento CREG obligatorio para contratos EPC",
             "action": "No firmar hasta incluir cláusula estándar Unergy de Fuerza Mayor"},
            {"level": "Rojo", "clause": "Penalidades",
             "reason": "25% del CAPEX supera ampliamente el límite del 20%",
             "action": "Renegociar inmediatamente — riesgo financiero crítico"},
            {"level": "Amarillo", "clause": "Cesión",
             "reason": "Permite cesión unilateral sin consentimiento",
             "action": "Agregar cláusula de consentimiento previo"},
        ],
        "compliance_score": 28,
        "summary": "Contrato NO APTO para firma. Requiere renegociación antes de proceder.",
    },
]


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def test_gemini_connection() -> Tuple[bool, str]:
    """
    Verifica la conexión a Gemini con una llamada trivial.
    Retorna (True, "OK — gemini-2.5-flash") o (False, "mensaje de error").
    """
    if not LLM_AVAILABLE:
        return False, "GEMINI_API_KEY no configurada"
    try:
        resp = _call_gemini("Responde exactamente: OK", model_name="gemini-2.5-flash")
        return True, f"OK — gemini-2.5-flash ({len(resp)} chars)"
    except Exception as exc:
        return False, str(exc)[:200]


def extract_contract_metrics(text: str, contract_type: str = "General") -> dict:
    """
    Extrae métricas clave del contrato: precio, vigencia, hitos, obligaciones, pólizas.

    En modo LLM usa Gemini 2.5 Flash.
    En modo offline retorna datos mock realistas con estructura idéntica.
    """
    if LLM_AVAILABLE:
        try:
            prompt = (
                f"Eres un experto legal y técnico en energía solar.\n"
                f"Analiza el siguiente contrato de tipo {contract_type}.\n\n"
                "Extrae métricas críticas en JSON estricto con claves:\n"
                '"Precio", "Vigencia", "Hitos", "Obligaciones", "Polizas" '
                "(lista de objetos con Tipo, Valor, Vencimiento).\n"
                "Devuelve SOLO el JSON, sin delimitadores markdown.\n\n"
                f"Contrato:\n{text[:8000]}"
            )
            raw = _call_gemini(prompt)
            return json.loads(_clean_json_response(raw))
        except Exception as e:
            _log.warning("[llm_service] extract_contract_metrics falló: %s — usando mock", e)

    # Modo offline: retornar mock con semilla basada en texto para consistencia
    seed = sum(ord(c) for c in text[:200]) if text else 0
    return _MOCK_METRICS[seed % len(_MOCK_METRICS)]


def analyze_risk(text: str, contract_type: str = "General") -> dict:
    """
    Evalúa el riesgo del contrato con semáforo ROJO / AMARILLO / VERDE.

    En modo LLM usa Gemini 2.5 Flash.
    En modo offline retorna análisis mock con estructura idéntica.
    """
    if LLM_AVAILABLE:
        try:
            prompt = (
                f"Eres un Compliance Officer experto en energía solar colombiana.\n"
                f"Analiza el riesgo del siguiente contrato tipo {contract_type}.\n\n"
                "Devuelve JSON con claves:\n"
                '"Nivel" (ROJO|AMARILLO|VERDE), "Justificacion", "Alertas" (lista), '
                '"risks" (lista de objetos con level, clause, reason, action), '
                '"compliance_score" (0-100), "summary".\n'
                "Solo JSON, sin markdown.\n\n"
                f"Contrato:\n{text[:8000]}"
            )
            raw = _call_gemini(prompt)
            return json.loads(_clean_json_response(raw))
        except Exception as e:
            _log.warning("[llm_service] analyze_risk falló: %s — usando mock", e)

    seed = sum(ord(c) for c in text[:200]) if text else 0
    return _MOCK_RISKS[seed % len(_MOCK_RISKS)]


def generate_response(
    question: str,
    context: str,
    history: Optional[List[Dict[str, str]]] = None,
    system_prompt: str = JUANMITA_SYSTEM_PROMPT,
) -> str:
    """
    Genera una respuesta en lenguaje natural usando el contexto recuperado por RAG.

    En modo LLM usa Gemini 2.5 Flash con el system prompt de JuanMitaBot.
    En modo offline retorna None.

    Retorna la respuesta como string, o None si no está disponible.
    """
    if not LLM_AVAILABLE:
        return None  # type: ignore[return-value]

    try:
        history_text = ""
        if history:
            for msg in history[-6:]:  # últimos 6 turnos para no exceder tokens
                role = "Usuario" if msg.get("role") == "user" else "JuanMitaBot"
                history_text += f"{role}: {msg.get('content', '')}\n"

        prompt = (
            f"{system_prompt}\n\n"
            "---\nCONTEXTO DE CONTRATOS RECUPERADO:\n"
            f"{context}\n\n"
            "---\n"
            f"HISTORIAL RECIENTE:\n{history_text}\n"
            f"Usuario: {question}\n\n"
            "JuanMitaBot:"
        )
        return _call_gemini(prompt)
    except Exception as e:
        _log.error("[llm_service] generate_response falló tras reintentos: %s", e)
        return f"⚠️ No pude generar respuesta con IA en este momento. Intenta de nuevo en unos segundos."
