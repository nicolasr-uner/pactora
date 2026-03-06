---
description: Flujo de Ingesta y Procesamiento de Contratos
---
# Flujo de Ingesta y Procesamiento de Contratos
1. Autenticación: Validar Google APIs (Drive/Calendar) vía `utils/auth_helper.py`.
2. Carga: Usuario sube .docx o selecciona de Drive.
3. Extracción IA: Gemini 1.5 Pro extrae (Precio, Vigencia, Hitos, Obligaciones, Pólizas).
4. Human-in-the-Loop: Mostrar datos en `st.data_editor`. El analista corrige/valida.
5. Vectorización: Guardar chunks en ChromaDB para el Chatbot RAG.
6. Automatización: Si hay pólizas/hitos, mostrar botón "Sincronizar con Calendar" para agendar a 30 días.
