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

import collections
import json
import logging
import os
import threading
import time
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

_log = logging.getLogger("pactora")

# ---------------------------------------------------------------------------
# Rate limiter interno — máximo 10 llamadas por minuto
# ---------------------------------------------------------------------------

_RATE_LIMIT_MAX = 10  # llamadas por minuto
_rate_lock = threading.Lock()
_rate_timestamps: collections.deque = collections.deque()  # timestamps de llamadas recientes

# Contador diario de llamadas (se resetea automáticamente al cambiar de día)
_call_count_today: int = 0
_call_count_date: str = ""  # fecha YYYY-MM-DD del contador actual


def _check_and_record_call() -> None:
    """
    Verifica el rate limit (10 llamadas/minuto) y registra la llamada actual.
    Lanza ValueError si el límite está excedido, indicando cuántos segundos esperar.
    """
    global _call_count_today, _call_count_date

    with _rate_lock:
        now = time.time()
        today_str = date.today().isoformat()

        # Reset contador diario si cambió el día
        if _call_count_date != today_str:
            _call_count_today = 0
            _call_count_date = today_str

        # Eliminar timestamps más viejos de 60 segundos
        cutoff = now - 60.0
        while _rate_timestamps and _rate_timestamps[0] < cutoff:
            _rate_timestamps.popleft()

        # Verificar límite por minuto
        if len(_rate_timestamps) >= _RATE_LIMIT_MAX:
            oldest = _rate_timestamps[0]
            wait_s = int(60.0 - (now - oldest)) + 1
            raise ValueError(
                f"rate_limit: Límite de {_RATE_LIMIT_MAX} llamadas/minuto alcanzado. "
                f"Espera ~{wait_s}s antes de la próxima consulta."
            )

        # Registrar llamada
        _rate_timestamps.append(now)
        _call_count_today += 1


def get_call_stats() -> Dict[str, Any]:
    """Retorna estadísticas de uso de la API Gemini para mostrar en Ajustes."""
    with _rate_lock:
        now = time.time()
        cutoff = now - 60.0
        calls_last_minute = sum(1 for t in _rate_timestamps if t >= cutoff)
        return {
            "calls_today": _call_count_today,
            "calls_last_minute": calls_last_minute,
            "rate_limit_per_minute": _RATE_LIMIT_MAX,
            "primary_model": _GEMINI_MODEL,
            "fallback_model": _GEMINI_FALLBACK_MODEL,
            "model_chain": _GEMINI_MODEL_CHAIN,
        }

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
        from google.genai import types as _types_test  # type: ignore  # noqa: F401
        _log.info("[llm_service] google-genai SDK disponible.")
    except Exception as e:
        _log.warning("[llm_service] No se pudo importar google-genai: %s", e)
        LLM_AVAILABLE = False

# Cadena de modelos Gemini — de más inteligente a más disponible.
# Se intenta en orden: cuando uno agota su quota diaria (429), se baja al siguiente.
# gemini-2.5-flash: más inteligente, ~20 req/día free tier
# gemini-2.0-flash: muy bueno, ~1,500 req/día free tier
# gemini-1.5-flash: quota muy generosa — último recurso antes de modo offline
_GEMINI_MODEL_CHAIN = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]
_GEMINI_MODEL = _GEMINI_MODEL_CHAIN[0]          # alias para compatibilidad y display
_GEMINI_FALLBACK_MODEL = _GEMINI_MODEL_CHAIN[-1]  # alias para display en Ajustes


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


def _call_gemini_single(
    prompt: "str | list",
    model_name: str,
    config: Any,
    client: Any,
) -> str:
    """Ejecuta una sola llamada a Gemini con retry exponencial (3 intentos)."""
    import re as _re

    prompt_len = len(prompt) if isinstance(prompt, str) else len(prompt)
    max_attempts = 3
    delays = [2, 4, 8]

    for attempt in range(max_attempts):
        t0 = time.time()
        try:
            _log.info(
                "[llm_service] Gemini call — model=%s prompt_len=%d attempt=%d",
                model_name, prompt_len, attempt + 1,
            )
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            elapsed = time.time() - t0
            _log.info(
                "[llm_service] Gemini OK — model=%s elapsed=%.2fs response_chars=%d",
                model_name, elapsed, len(response.text or ""),
            )
            return response.text
        except Exception as exc:
            elapsed = time.time() - t0
            exc_str = str(exc)

            # 403 REFERRER_BLOCKED: no reintentable, fallo inmediato
            if "403" in exc_str and "API_KEY_HTTP_REFERRER_BLOCKED" in exc_str:
                _log.error(
                    "[llm_service] API key bloqueada por restricción de HTTP referrer. "
                    "Ve a Google Cloud Console → APIs & Services → Credentials → tu API Key → "
                    "'Application restrictions' y selecciona 'None'."
                )
                raise

            # 429 RESOURCE_EXHAUSTED: parsear retryDelay para detectar quota diaria agotada
            if "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str:
                retry_delay_s = 0
                try:
                    m = _re.search(r'"retryDelay"\s*:\s*"(\d+)s"', exc_str)
                    if m:
                        retry_delay_s = int(m.group(1))
                except Exception:
                    pass
                if retry_delay_s > 15:
                    _log.warning(
                        "[llm_service] Quota diaria agotada en %s (retryDelay=%ds).",
                        model_name, retry_delay_s,
                    )
                    raise  # propagar para que _call_gemini intente fallback

            is_retryable = any(str(c) in exc_str for c in _RETRYABLE_CODES)
            _log.warning(
                "[llm_service] Gemini error — attempt=%d elapsed=%.2fs retryable=%s: %s",
                attempt + 1, elapsed, is_retryable, exc_str[:200],
            )
            if attempt < max_attempts - 1 and is_retryable:
                time.sleep(delays[attempt])
                continue
            raise


def _call_gemini(
    prompt: "str | list",
    model_name: str = _GEMINI_MODEL,
    system_instruction: Optional[str] = None,
    timeout: int = 30,
) -> str:
    """
    Llama a Gemini con rate limiter y fallback automático por cadena de modelos.

    Flujo:
      1. Verifica rate limit interno (10 llamadas/minuto).
      2. Recorre _GEMINI_MODEL_CHAIN desde model_name hacia abajo:
         gemini-2.5-flash → gemini-2.0-flash → gemini-1.5-flash
      3. Si el modelo activo devuelve 429 (quota agotada), baja al siguiente.
      4. Si todos fallan o el error no es de quota, propaga la excepción.

    Args:
        prompt: String simple o lista de types.Content (para multi-turn).
        model_name: Modelo desde el que iniciar la cadena (por defecto el primero).
        system_instruction: Instrucción de sistema separada (no embebida en prompt).
        timeout: Reservado para uso futuro.
    """
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore

    # 1. Rate limit check — lanza ValueError si se excede el límite/minuto
    _check_and_record_call()

    client = genai.Client(api_key=GEMINI_API_KEY)
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
    ) if system_instruction else None

    # 2. Recorrer la cadena de modelos de más a menos capaz.
    # Si model_name no está en la cadena, se agrega al inicio como modelo extra.
    chain = _GEMINI_MODEL_CHAIN[:]
    if model_name not in chain:
        chain.insert(0, model_name)
    else:
        # Empezar desde el modelo solicitado (no necesariamente el primero)
        start_idx = chain.index(model_name)
        chain = chain[start_idx:]

    last_exc: Exception = RuntimeError("Sin modelos disponibles")
    for current_model in chain:
        try:
            return _call_gemini_single(prompt, current_model, config, client)
        except Exception as exc:
            exc_str = str(exc)
            is_quota_exhausted = (
                ("429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str)
                and "API_KEY_HTTP_REFERRER_BLOCKED" not in exc_str
            )
            if is_quota_exhausted and current_model != chain[-1]:
                _log.warning(
                    "[llm_service] Quota agotada en %s — bajando al siguiente modelo.",
                    current_model,
                )
                last_exc = exc
                continue  # intentar con el siguiente en la cadena
            raise  # error no recuperable o último modelo — propagar
    raise last_exc


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
    Verifica la conexión recorriendo la cadena de modelos hasta que uno responda.
    Retorna (True, "OK — gemini-2.5-flash (activo)") o (False, "mensaje de error").
    """
    if not LLM_AVAILABLE:
        return False, "GEMINI_API_KEY no configurada"
    try:
        from google import genai  # type: ignore
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        return False, f"No se pudo inicializar el cliente Gemini: {e}"
    for model in _GEMINI_MODEL_CHAIN:
        try:
            resp = _call_gemini_single("Responde exactamente: OK", model, None, client)
            return True, f"OK — {model} (activo, {len(resp)} chars)"
        except Exception as exc:
            exc_str = str(exc)
            is_quota = "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str
            if is_quota and model != _GEMINI_MODEL_CHAIN[-1]:
                continue  # intentar siguiente modelo
            return False, f"{model}: {exc_str[:200]}"
    return False, "Todos los modelos agotaron su quota"


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
            # Incluir contexto normativo aplicable al tipo de contrato
            _normativa_ctx = ""
            try:
                from core.normativa_db import get_normativa_summary_for_prompt
                _normativa_ctx = "\n\n" + get_normativa_summary_for_prompt(contract_type)
            except Exception:
                pass

            prompt = (
                f"Eres un Compliance Officer experto en energía solar colombiana.\n"
                f"Analiza el riesgo del siguiente contrato tipo {contract_type}.\n\n"
                "Devuelve JSON con claves:\n"
                '"Nivel" (ROJO|AMARILLO|VERDE), "Justificacion", "Alertas" (lista), '
                '"risks" (lista de objetos con level, clause, reason, action), '
                '"compliance_score" (0-100), "summary".\n'
                "Solo JSON, sin markdown.\n\n"
                + (_normativa_ctx if _normativa_ctx else "")
                + f"\nContrato:\n{text[:8000]}"
            )
            raw = _call_gemini(prompt)
            return json.loads(_clean_json_response(raw))
        except Exception as e:
            _log.warning("[llm_service] analyze_risk falló: %s — usando mock", e)

    seed = sum(ord(c) for c in text[:200]) if text else 0
    return _MOCK_RISKS[seed % len(_MOCK_RISKS)]


def build_portfolio_context() -> str:
    """
    Genera un bloque de contexto dinámico con el registro estructurado del portafolio.
    Usa los metadatos almacenados en ChromaDB (contract_type por documento) para
    producir un inventario preciso que se inyecta en el system prompt de JuanMitaBot.
    """
    try:
        import streamlit as st
        cb = st.session_state.get("chatbot")
        if not cb:
            return ""

        # Usar registry enriquecido (incluye contract_type de metadata ChromaDB)
        registry: List[Dict[str, Any]] = []
        if hasattr(cb, "get_contract_registry"):
            registry = cb.get_contract_registry()

        # Fallback: construir registry básico desde stats si el método no está disponible
        # o si los contratos fueron indexados antes de esta versión (sin contract_type en meta)
        if not registry:
            stats = cb.get_stats()
            sources = stats.get("sources", [])
            if not sources:
                return "\nMEMORIA DE CONTRATOS: Sin contratos indexados actualmente."
            _TIPO_KWS = [
                ("PPA", "PPA"), ("EPC", "EPC"), ("O&M", "O&M"), ("OAM", "O&M"),
                ("SHA", "SHA"), ("NDA", "NDA"), ("ARRIENDO", "Arriendo"),
                ("FIDUCIA", "Fiducia"), ("FRONTERA", "Rep. Frontera"),
            ]
            def _guess_type(name: str) -> str:
                u = name.upper()
                for kw, tipo in _TIPO_KWS:
                    if kw in u:
                        return tipo
                return "General"
            registry = [{"source": s, "contract_type": _guess_type(s)} for s in sources]

        if not registry:
            return "\nMEMORIA DE CONTRATOS: Sin contratos indexados actualmente."

        total = len(registry)

        # Conteo por tipo
        type_counts: Dict[str, int] = {}
        for r in registry:
            t = r.get("contract_type", "General")
            type_counts[t] = type_counts.get(t, 0) + 1
        type_summary = ", ".join(
            f"{cnt} {tipo}" for tipo, cnt in sorted(type_counts.items())
        )

        # Registro compacto: tipo + nombre (máx 60 contratos para no saturar tokens)
        lines = []
        for r in registry[:60]:
            tipo = r.get("contract_type", "General")
            src = r.get("source", "")
            lines.append(f"  • [{tipo}] {src}")
        more = f"\n  … y {total - 60} contratos más" if total > 60 else ""
        registry_block = "\n".join(lines) + more

        return (
            f"\n\nMEMORIA DEL PORTAFOLIO ({total} contrato(s) indexados):\n"
            f"Distribución: {type_summary}\n\n"
            f"Registro completo de contratos disponibles:\n"
            f"{registry_block}\n\n"
            f"INSTRUCCIÓN DE MEMORIA: Cuando el usuario pregunte qué contratos existen, "
            f"cuántos hay, de qué tipo, o si un contrato específico está disponible — "
            f"responde directamente con esta memoria. Para el CONTENIDO (cláusulas, "
            f"fechas, partes, montos), usa siempre el CONTEXTO DE CONTRATOS RECUPERADO "
            f"que se adjunta en cada pregunta.\n"
        )
    except Exception:
        return ""


def generate_response(
    question: str,
    context: str,
    history: Optional[List[Dict[str, str]]] = None,
    system_prompt: str = JUANMITA_SYSTEM_PROMPT,
) -> str:
    """
    Genera una respuesta en lenguaje natural usando el contexto recuperado por RAG.

    Usa GenerateContentConfig(system_instruction=...) para separar el system prompt
    del contenido del usuario, y types.Content con roles nativos para el historial.

    En modo LLM usa Gemini 2.5 Flash. En modo offline retorna None.
    """
    if not LLM_AVAILABLE:
        return None  # type: ignore[return-value]

    try:
        from google.genai import types  # type: ignore

        # Enriquecer system prompt con estado actual del portafolio
        portfolio_block = build_portfolio_context()
        effective_system = system_prompt + portfolio_block if portfolio_block else system_prompt

        # Construir historial con roles nativos del SDK (no como texto plano)
        contents: List[Any] = []
        if history:
            for msg in history[-6:]:  # últimos 6 turnos para no exceder tokens
                sdk_role = "user" if msg.get("role") == "user" else "model"
                contents.append(
                    types.Content(
                        role=sdk_role,
                        parts=[types.Part(text=msg.get("content", ""))],
                    )
                )

        # Turno actual: contexto RAG + pregunta del usuario
        user_text = (
            "CONTEXTO DE CONTRATOS RECUPERADO:\n"
            f"{context}\n\n"
            f"Pregunta: {question}"
        )
        contents.append(
            types.Content(role="user", parts=[types.Part(text=user_text)])
        )

        # system_instruction va separado en GenerateContentConfig, no en el prompt
        return _call_gemini(
            prompt=contents,
            system_instruction=effective_system,
        )
    except Exception as e:
        _log.error("[llm_service] generate_response falló: %s — tipo: %s", e, type(e).__name__)
        return None  # ask_question hace fallback a búsqueda semántica


def generate_response_stream(
    question: str,
    context: str,
    history: Optional[List[Dict[str, str]]] = None,
    system_prompt: str = JUANMITA_SYSTEM_PROMPT,
):
    """
    Como generate_response pero retorna un generador que hace yield de chunks de texto.
    Usar con st.write_stream() en Streamlit para mostrar la respuesta progresivamente.

    Retorna None si LLM no está disponible o si falla antes de empezar a streamear.
    El generador interno propaga errores de quota bajando por _GEMINI_MODEL_CHAIN.
    """
    if not LLM_AVAILABLE:
        return None

    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore

        portfolio_block = build_portfolio_context()
        effective_system = system_prompt + portfolio_block if portfolio_block else system_prompt

        contents: List[Any] = []
        if history:
            for msg in history[-6:]:
                sdk_role = "user" if msg.get("role") == "user" else "model"
                contents.append(
                    types.Content(
                        role=sdk_role,
                        parts=[types.Part(text=msg.get("content", ""))],
                    )
                )

        user_text = (
            "CONTEXTO DE CONTRATOS RECUPERADO:\n"
            f"{context}\n\n"
            f"Pregunta: {question}"
        )
        contents.append(types.Content(role="user", parts=[types.Part(text=user_text)]))

        config = types.GenerateContentConfig(system_instruction=effective_system)
        client = genai.Client(api_key=GEMINI_API_KEY)

        def _stream_gen():
            _check_and_record_call()
            for model in _GEMINI_MODEL_CHAIN:
                try:
                    for chunk in client.models.generate_content_stream(
                        model=model,
                        contents=contents,
                        config=config,
                    ):
                        if chunk.text:
                            yield chunk.text
                    return  # stream completado exitosamente
                except Exception as exc:
                    exc_str = str(exc)
                    is_quota = (
                        ("429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str)
                        and "API_KEY_HTTP_REFERRER_BLOCKED" not in exc_str
                    )
                    if is_quota and model != _GEMINI_MODEL_CHAIN[-1]:
                        _log.warning(
                            "[llm_service] stream: quota agotada en %s — bajando modelo.", model
                        )
                        continue
                    raise

        return _stream_gen()

    except Exception as e:
        _log.error("[llm_service] generate_response_stream falló antes de iniciar: %s", e)
        return None
