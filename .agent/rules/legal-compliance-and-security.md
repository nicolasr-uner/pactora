# Pactora — Legal Compliance & Security Rules

> **Contexto:** Pactora es una plataforma CLM para Unergy. Este documento define las reglas estrictas de cumplimiento legal y seguridad de datos.

---

## 1. Semáforo de Riesgo Legal (Risk Semaphore)

Todo documento analizado por Gemini debe ser clasificado bajo estos criterios:

- 🔴 **Rojo (Riesgo Crítico):** 
    - Incumplimiento de normativas CREG (Comisión de Regulación de Energía y Gas).
    - Falta de cláusulas de Fuerza Mayor en contratos EPC.
    - Penalidades que superen el 20% del valor del contrato.
- 🟡 **Amarillo (Revisión Detallada):**
    - Desviación > 10% respecto a la **Plantilla Maestra**.
    - Fórmulas de indexación (IPP/IPC) no estándar.
    - Vigencias menores a 5 años en contratos PPA.
- 🟢 **Verde (Conforme):**
    - Alineación total con las plantillas de Unergy.
    - Cláusulas estándar de arbitraje y jurisdicción.

---

## 2. Privacidad y Seguridad

- **Inviolabilidad de Datos:** Los documentos son propiedad privada de Unergy. Nunca deben ser usados para entrenar modelos externos fuera del contexto de esta sesión.
- **Manejo de API Keys:** Las claves de Gemini y Drive deben residir únicamente en `secrets.toml` o variables de entorno. NUNCA hacer commit a archivos que las contengan.
- **Human-in-the-loop:** Ningún cambio en el contrato se considera final hasta que haya sido validado en el `st.data_editor` por un miembro del equipo legal.
