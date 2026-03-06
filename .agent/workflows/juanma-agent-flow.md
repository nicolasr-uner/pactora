---
description: Flujo autónomo del agente JuanMa para análisis proactivo de contratos en Pactora
---

# Workflow: JuanMa — Análisis Autónomo de Contratos

Este workflow se activa cuando el usuario habilita el toggle "Activar Agente (JuanMa)" en la interfaz de Pactora.

---

## Fase 1: Inicialización y Verificación de Contexto

### Paso 1.1 — Verificar si hay un documento cargado
- Revisar `st.session_state['current_contract_text']`
- Si no hay documento: Mostrar mensaje *"JuanMa está en espera. Carga un contrato en la pestaña de Ingesta para que pueda actuar."*
- Si hay documento: Continuar al Paso 1.2

### Paso 1.2 — Verificar si hay vectorización disponible
- Revisar `st.session_state['chatbot_ready']`
- Si no hay vectorización: Intentar indexar automáticamente usando `chatbot.vector_ingest()`
- Si indexación falla: Mostrar alerta y proceder con análisis solo con texto plano.

---

## Fase 2: Escaneo Inicial Rápido

JuanMa realiza un primer análisis estructural usando el `gemini_engine`:

```python
# Llamada autónoma al motor: JuanMa actúa sin esperar pregunta del usuario
scan_prompt = """
Dame en 3 líneas:
1. Tipo de contrato (PPA, EPC, OyM, etc.)
2. Partes involucradas
3. Fecha de firma y vigencia (si están presentes)
"""
```

Resultado se muestra automáticamente en la sección de Chatbot RAG como mensaje del sistema (role: assistant).

---

## Fase 3: Checklist de Cláusulas Críticas

JuanMa verifica la presencia de estas cláusulas:

| Cláusula | Requerida en | Acción si falta |
|---|---|---|
| Fuerza Mayor | EPC, PPA | 🔴 Alerta Roja |
| Terminación Anticipada | Todos | 🟡 Alerta Amarilla |
| Cesión de Derechos | Todos | 🟡 Alerta Amarilla |
| Límite de Responsabilidad | EPC, PPA | 🔴 Alerta Roja |
| Mecanismo de Disputas | Todos | 🟡 Alerta Amarilla |
| Pólizas (Cumplimiento, R.C.) | EPC, OyM | 🔴 Alerta Roja |

---

## Fase 4: Emisión del Reporte Autónomo

JuanMa emite un mensaje proactivo en el chat de Pactora con este formato:

```
🤖 **JuanMa — Análisis Autónomo**

Tipo de Contrato detectado: [tipo]
Partes: [parte A] ↔ [parte B]

🟡 NIVEL DE RIESGO: AMARILLO

📋 HALLAZGOS:
- Falta cláusula de Fuerza Mayor para eventos sísmicos y de red eléctrica.
- La indexación de precio (IPP) no tiene cap máximo, riesgo en escenario inflacionario.

⚠️ ALERTAS CRÍTICAS:
- El plazo de COD (8 meses) está por debajo del estándar del mercado para un proyecto > 1MWp.

💡 RECOMENDACIÓN:
- Solicitar adición de Otrosí para limitar la indexación al 3% anual.
- Verificar con el equipo técnico si el plazo de 8 meses es viable antes de firmar.

---
*Este análisis es informativo. Requiere aprobación del equipo legal de Unergy.*
```

---

## Fase 5: Guardar Reporte en Session State

```python
st.session_state['juanma_report'] = {
    "nivel": "AMARILLO",
    "hallazgos": [...],
    "alertas": [...],
    "recomendaciones": [...]
}
```

El reporte de JuanMa se integra al Dashboard Comercial como una sección nueva y se incluye en la descarga del "Informe de Due Diligence".

---

## Reglas del Workflow

- ✅ JuanMa solo actúa cuando el toggle está activado.
- ✅ El análisis de JuanMa no reemplaza al Human-in-the-Loop; siempre requiere aprobación legal.
- ❌ JuanMa nunca modifica datos ya aprobados por el equipo.
- ❌ JuanMa no almacena información entre sesiones.
