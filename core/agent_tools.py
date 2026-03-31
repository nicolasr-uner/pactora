"""
core/agent_tools.py — Herramientas del agente JuanMitaBot.

Cada herramienta implementa una capacidad concreta que Gemini puede invocar
durante una conversación. Las funciones son stateless; acceden al estado de
Streamlit y a los datos de Google Sheets en tiempo de ejecución.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

_log = logging.getLogger("pactora")


# ---------------------------------------------------------------------------
# Implementaciones de herramientas
# ---------------------------------------------------------------------------

def buscar_contratos(query: str, contract_type: str = "", max_results: int = 8) -> str:
    """Búsqueda semántica en el texto de los contratos indexados en ChromaDB."""
    try:
        import streamlit as st
        chatbot = st.session_state.get("chatbot")
        if not chatbot or chatbot.vectorstore is None:
            return "No hay contratos indexados en el sistema."

        filter_meta = {"contract_type": contract_type} if contract_type else None
        context, sources = chatbot._retrieve_context(query, filter_metadata=filter_meta)

        if not context:
            return f"No se encontraron fragmentos relevantes para: '{query}'"

        header = f"**Resultados de búsqueda para '{query}':**\n\n"
        return header + context[:4000]
    except Exception as e:
        _log.warning("[agent_tools] buscar_contratos: %s", e)
        return f"Error en búsqueda: {e}"


def obtener_perfil(filename: str) -> str:
    """Retorna el perfil estructurado de un contrato: partes, vigencia, valor, riesgo."""
    try:
        from core.llm_service import read_contract_profiles
        profiles = read_contract_profiles()

        if not profiles:
            return (
                "No hay perfiles de contratos disponibles. "
                "Configura CONTRACT_PROFILES_SHEET_ID en Streamlit Secrets."
            )

        fname_lower = filename.lower()
        # Exact partial match first
        match = next((p for p in profiles if fname_lower in p.get("filename", "").lower()), None)
        # Fuzzy: any significant word
        if not match:
            words = [w for w in fname_lower.split() if len(w) > 3]
            match = next(
                (p for p in profiles if any(w in p.get("filename", "").lower() for w in words)),
                None,
            )

        if not match:
            available = ", ".join(p.get("filename", "") for p in profiles[:8])
            return f"No se encontró perfil para '{filename}'.\nContratos disponibles: {available}"

        _RISK_EMOJI = {"ROJO": "🔴", "AMARILLO": "🟡", "VERDE": "🟢"}
        risk = match.get("risk_level", "").upper()
        return (
            f"**Perfil: {match.get('filename', '')}**\n"
            f"- Tipo: {match.get('contract_type', 'N/A')}\n"
            f"- Partes: {match.get('parties', 'N/A')}\n"
            f"- Vigencia: {match.get('start_date', '?')} → {match.get('end_date', '?')}\n"
            f"- Valor: {match.get('value_clp', 'N/A')}\n"
            f"- Riesgo: {_RISK_EMOJI.get(risk, '⚪')} {risk} "
            f"(score: {match.get('compliance_score', '?')}/100)\n"
            f"- Obligaciones: {match.get('obligations_summary', 'N/A')}\n"
            f"- Resumen riesgo: {match.get('risk_summary', 'N/A')}"
        )
    except Exception as e:
        _log.warning("[agent_tools] obtener_perfil: %s", e)
        return f"Error al obtener perfil: {e}"


def listar_contratos(contract_type: str = "", risk_level: str = "") -> str:
    """Lista contratos con sus métricas principales. Filtra por tipo y/o nivel de riesgo."""
    try:
        from core.llm_service import read_contract_profiles
        profiles = read_contract_profiles()

        if not profiles:
            import streamlit as st
            chatbot = st.session_state.get("chatbot")
            if chatbot:
                stats = chatbot.get_stats()
                sources = stats.get("sources", [])
                if sources:
                    return f"Contratos indexados ({len(sources)}):\n" + "\n".join(f"- {s}" for s in sources)
            return "No hay contratos indexados."

        filtered = profiles
        if contract_type:
            ct = contract_type.upper()
            filtered = [p for p in filtered if ct in p.get("contract_type", "").upper()]
        if risk_level:
            rl = risk_level.upper()
            filtered = [p for p in filtered if rl == p.get("risk_level", "").upper()]

        if not filtered:
            return f"No hay contratos con tipo='{contract_type}' y riesgo='{risk_level}'."

        _RISK_EMOJI = {"ROJO": "🔴", "AMARILLO": "🟡", "VERDE": "🟢"}
        lines = [f"**Contratos ({len(filtered)}):**"]
        for p in filtered:
            risk = p.get("risk_level", "").upper()
            emoji = _RISK_EMOJI.get(risk, "⚪")
            vence = p.get("end_date", "") or "sin fecha"
            lines.append(
                f"- {p.get('filename', 'N/A')} | {p.get('contract_type', 'N/A')} | "
                f"{emoji} {risk} | Vence: {vence}"
            )
        return "\n".join(lines)
    except Exception as e:
        _log.warning("[agent_tools] listar_contratos: %s", e)
        return f"Error al listar contratos: {e}"


def comparar_contratos(filenames: list) -> str:
    """Compara dos o más contratos mostrando sus métricas lado a lado en tabla markdown."""
    try:
        from core.llm_service import read_contract_profiles
        profiles = read_contract_profiles()

        if not profiles:
            return "No hay perfiles disponibles para comparar."

        found = []
        for fname in filenames:
            fname_lower = fname.lower()
            match = next(
                (p for p in profiles if fname_lower in p.get("filename", "").lower()),
                None,
            )
            found.append(match if match else {"filename": fname, "_not_found": True})

        if not any(p for p in found if not p.get("_not_found")):
            return "No se encontró ninguno de los contratos especificados."

        fields = [
            ("Tipo", "contract_type"),
            ("Partes", "parties"),
            ("Inicio", "start_date"),
            ("Vencimiento", "end_date"),
            ("Valor", "value_clp"),
            ("Riesgo", "risk_level"),
            ("Score", "compliance_score"),
            ("Obligaciones", "obligations_summary"),
        ]

        col_headers = [p.get("filename", "N/A")[:35] for p in found]
        lines = [
            "**Comparación de contratos:**\n",
            "| Campo | " + " | ".join(col_headers) + " |",
            "|-------|" + "".join(["--------|"] * len(found)),
        ]
        for label, key in fields:
            vals = []
            for p in found:
                if p.get("_not_found"):
                    vals.append("❌ no encontrado")
                else:
                    v = str(p.get(key, "") or "N/A")
                    vals.append(v[:70])
            lines.append(f"| **{label}** | " + " | ".join(vals) + " |")
        return "\n".join(lines)
    except Exception as e:
        _log.warning("[agent_tools] comparar_contratos: %s", e)
        return f"Error al comparar: {e}"


def contratos_por_vencer(dias: int = 90) -> str:
    """Contratos que vencen en los próximos N días (default 90) o que ya vencieron."""
    try:
        from core.llm_service import read_contract_profiles
        profiles = read_contract_profiles()

        if not profiles:
            return "No hay perfiles de contratos disponibles."

        today = datetime.now().date()
        cutoff = today + timedelta(days=dias)
        _RISK_EMOJI = {"ROJO": "🔴", "AMARILLO": "🟡", "VERDE": "🟢"}

        expired, upcoming, no_date = [], [], []

        for p in profiles:
            end_str = (p.get("end_date", "") or "").strip()[:10]
            if not end_str:
                no_date.append(p.get("filename", ""))
                continue
            try:
                end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
                risk = p.get("risk_level", "").upper()
                emoji = _RISK_EMOJI.get(risk, "⚪")
                entry = (end_date, p.get("filename", ""), emoji, risk)
                if end_date < today:
                    expired.append(entry)
                elif end_date <= cutoff:
                    upcoming.append(entry)
            except ValueError:
                no_date.append(p.get("filename", ""))

        if not expired and not upcoming:
            return f"✅ No hay contratos que venzan en los próximos {dias} días."

        lines = []
        if expired:
            lines.append(f"**⚠️ Contratos VENCIDOS ({len(expired)}):**")
            for end_date, fname, emoji, risk in sorted(expired):
                days_ago = (today - end_date).days
                lines.append(f"- {emoji} {fname} | Venció: {end_date} (hace {days_ago} días)")

        if upcoming:
            lines.append(f"\n**📅 Por vencer en {dias} días ({len(upcoming)}):**")
            for end_date, fname, emoji, risk in sorted(upcoming):
                days_left = (end_date - today).days
                lines.append(f"- {emoji} {fname} | Vence: {end_date} | {days_left} días restantes")

        if no_date:
            lines.append(f"\n*{len(no_date)} contratos sin fecha de vencimiento registrada.*")

        return "\n".join(lines)
    except Exception as e:
        _log.warning("[agent_tools] contratos_por_vencer: %s", e)
        return f"Error: {e}"


def resumen_portafolio() -> str:
    """Estadísticas globales: total, distribución por tipo/riesgo, score promedio, alertas ROJO."""
    try:
        from core.llm_service import read_contract_profiles
        profiles = read_contract_profiles()

        if not profiles:
            import streamlit as st
            chatbot = st.session_state.get("chatbot")
            if chatbot:
                stats = chatbot.get_stats()
                return (
                    f"Total contratos indexados: {stats.get('total_docs', 0)}\n"
                    f"Chunks vectoriales: {stats.get('total_chunks', 0)}\n"
                    f"(Perfiles no disponibles — configura CONTRACT_PROFILES_SHEET_ID)"
                )
            return "No hay contratos indexados."

        risk_counts: dict[str, int] = {"ROJO": 0, "AMARILLO": 0, "VERDE": 0}
        type_counts: dict[str, int] = {}
        scores: list[int] = []

        for p in profiles:
            risk = p.get("risk_level", "VERDE").upper()
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
            ctype = p.get("contract_type", "General")
            type_counts[ctype] = type_counts.get(ctype, 0) + 1
            try:
                scores.append(int(p.get("compliance_score", 0)))
            except (ValueError, TypeError):
                pass

        avg_score = round(sum(scores) / len(scores), 1) if scores else 0

        lines = [
            f"**Resumen del portafolio Pactora ({len(profiles)} contratos):**",
            f"- Compliance score promedio: {avg_score}/100",
            "",
            "**Distribución por tipo:**",
        ]
        for t, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  - {t}: {cnt}")

        lines += [
            "",
            "**Distribución por riesgo:**",
            f"  - 🔴 ROJO (crítico): {risk_counts['ROJO']}",
            f"  - 🟡 AMARILLO (revisión): {risk_counts['AMARILLO']}",
            f"  - 🟢 VERDE (conforme): {risk_counts['VERDE']}",
        ]

        rojos = [p.get("filename", "") for p in profiles if p.get("risk_level", "").upper() == "ROJO"]
        if rojos:
            lines.append("\n⚠️ **Contratos ROJOS que requieren atención inmediata:**")
            for r in rojos:
                lines.append(f"  - {r}")

        return "\n".join(lines)
    except Exception as e:
        _log.warning("[agent_tools] resumen_portafolio: %s", e)
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Declaraciones de herramientas para Gemini (se construyen lazy)
# ---------------------------------------------------------------------------

_TOOL_DECLARATIONS = None


def get_tool_declarations() -> Any:
    """Construye y cachea el types.Tool con todas las FunctionDeclarations."""
    global _TOOL_DECLARATIONS
    if _TOOL_DECLARATIONS is not None:
        return _TOOL_DECLARATIONS

    from google.genai import types  # type: ignore

    _TOOL_DECLARATIONS = types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="buscar_contratos",
                description=(
                    "Búsqueda semántica en el texto de los contratos indexados. "
                    "Úsala para encontrar cláusulas específicas, condiciones particulares "
                    "o información detallada que puede estar en el cuerpo del contrato."
                ),
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "query": {
                            "type": "STRING",
                            "description": "La pregunta o término a buscar en los contratos.",
                        },
                        "contract_type": {
                            "type": "STRING",
                            "description": "Filtro opcional de tipo: PPA, EPC, O&M, SHA, NDA, etc.",
                        },
                        "max_results": {
                            "type": "INTEGER",
                            "description": "Número máximo de fragmentos a retornar (default 8).",
                        },
                    },
                    "required": ["query"],
                },
            ),
            types.FunctionDeclaration(
                name="obtener_perfil",
                description=(
                    "Obtiene el perfil estructurado de un contrato: partes, vigencia, valor, "
                    "obligaciones y análisis de riesgo. Úsala cuando el usuario pregunta "
                    "sobre un contrato específico por nombre."
                ),
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "filename": {
                            "type": "STRING",
                            "description": "Nombre del archivo del contrato (puede ser parcial).",
                        },
                    },
                    "required": ["filename"],
                },
            ),
            types.FunctionDeclaration(
                name="listar_contratos",
                description=(
                    "Lista todos los contratos disponibles con sus métricas. "
                    "Permite filtrar por tipo o nivel de riesgo. "
                    "Úsala para preguntas de inventario o búsqueda por categoría."
                ),
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "contract_type": {
                            "type": "STRING",
                            "description": "Tipo a filtrar: PPA, EPC, O&M, SHA, NDA, etc. Vacío = todos.",
                        },
                        "risk_level": {
                            "type": "STRING",
                            "description": "Riesgo a filtrar: ROJO, AMARILLO, VERDE. Vacío = todos.",
                        },
                    },
                    "required": [],
                },
            ),
            types.FunctionDeclaration(
                name="comparar_contratos",
                description=(
                    "Compara dos o más contratos lado a lado en una tabla. "
                    "Úsala cuando el usuario quiere ver diferencias entre contratos específicos."
                ),
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "filenames": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"},
                            "description": "Lista de nombres de archivo de los contratos a comparar.",
                        },
                    },
                    "required": ["filenames"],
                },
            ),
            types.FunctionDeclaration(
                name="contratos_por_vencer",
                description=(
                    "Identifica contratos que vencen próximamente o que ya están vencidos. "
                    "Úsala para alertas de renovación y gestión proactiva del portafolio."
                ),
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "dias": {
                            "type": "INTEGER",
                            "description": "Horizonte en días para buscar vencimientos (default 90).",
                        },
                    },
                    "required": [],
                },
            ),
            types.FunctionDeclaration(
                name="resumen_portafolio",
                description=(
                    "Genera estadísticas globales del portafolio: distribución por tipo, "
                    "niveles de riesgo, compliance score promedio y alertas críticas. "
                    "Úsala para preguntas sobre el estado general del portafolio."
                ),
                parameters={
                    "type": "OBJECT",
                    "properties": {},
                    "required": [],
                },
            ),
        ]
    )
    return _TOOL_DECLARATIONS


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_TOOL_MAP = {
    "buscar_contratos":     buscar_contratos,
    "obtener_perfil":       obtener_perfil,
    "listar_contratos":     listar_contratos,
    "comparar_contratos":   comparar_contratos,
    "contratos_por_vencer": contratos_por_vencer,
    "resumen_portafolio":   resumen_portafolio,
}


def execute_tool(name: str, args: dict) -> str:
    """Ejecuta una herramienta por nombre y retorna su resultado como string."""
    fn = _TOOL_MAP.get(name)
    if fn is None:
        return f"Herramienta desconocida: '{name}'"
    try:
        return fn(**args)
    except Exception as e:
        _log.error("[agent_tools] execute_tool '%s' error: %s", name, e)
        return f"Error ejecutando {name}: {e}"
