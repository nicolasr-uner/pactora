# Guía de Configuración Local para Pactora (Nivel Dummies) 🚀

Para que **Pactora (Unergy DocBrain)** funcione en tu computador, necesita acceso a dos "cerebros":
1. **Google (Drive y Calendar)** para poder leer o guardar cosas.
2. **Gemini 1.5 Pro (IA)** para poder analizar y razonar sobre los contratos.

Sigue estos pasos uno a uno.

---

## PASO 1: Conseguir la Llave de la Inteligencia Artificial (Gemini)
Esta llave es como una contraseña larguísima que le dice a Google que Unergy tiene permiso de usar su IA más avanzada.

1. Entra a [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Inicia sesión con una cuenta de Google (preferiblemente de Unergy).
3. Haz clic en el botón azul grande que dice **"Create API Key"** (Crear clave de API).
4. Elige un proyecto (o crea uno nuevo si te lo pide) y copia el texto larguísimo que te genera (se ve algo así como `AIzaSyB...`).
5. **No pierdas esa clave.**
6. Ve a la carpeta de tu computadora donde está el proyecto Pactora (`C:\Users\PC\.gemini\antigravity\scratch\pactora`).
7. Crea un archivo nuevo y nómbralo exactamente `.env` (Punto e ene ve).
8. Ábrelo con el bloc de notas y pega tu clave así:
   ```text
   GEMINI_API_KEY=ACA_PEGAS_TU_CLAVE_LARGUISIMA
   ```
9. Guarda el archivo `.env` y ciérralo.

---

## PASO 2: Conseguir el Permiso de Google Workspace (El archivo credentials.json)
Esto es para que la aplicación pueda leer PDFs de Drive y crear eventos de Calendar sin que Google la bloquee.

1. Entra a la [Consola de Google Cloud](https://console.cloud.google.com/).
2. Inicia sesión y arriba a la izquierda (al lado del logo de Google Cloud), haz clic en **"Selecciona un proyecto"** y luego en **"Proyecto Nuevo"**. Llámalo "Pactora Unergy".
3. En el buscador superior de esa página escribe **"Google Drive API"** y haz clic en "Habilitar" (Enable). Haz lo mismo buscando **"Google Calendar API"** y habilítala también.
4. En el menú de la izquierda, ve a **"APIs y Servicios" > "Pantalla de consentimiento de OAuth"**.
   - Elige **"Externo"** (o Interno si tienes Workspace de empresa) y dale a Crear.
   - Llena los campos obligatorios (Nombre de la app: Pactora, y pon tu correo). Guarda y continúa hasta el final. No necesitas agregar "Scopes" aquí, sáltalo.
   - *Importante:* Si elegiste Externo, en la sección de "Usuarios de prueba", agrega los correos de tu equipo que van a participar en la Hackathon.
5. Ahora, en el menú de la izquierda ve a **"Credenciales"**.
   - Clic arriba en **"+ CREAR CREDENCIALES"**.
   - Elige **"ID de cliente de OAuth"**.
   - En Tipo de aplicación, elige **"App de escritorio"** (Desktop app).
   - Haz clic en Crear.
6. Te saldrá una ventana con tus credenciales. Haz clic en el botón de **"Descargar JSON"** (es un icono de una flecha hacia abajo).
7. Mueve ese archivo descargado a la carpeta raíz de Pactora (`C:\Users\PC\.gemini\antigravity\scratch\pactora`) y **renómbralo** para que se llame exactamente:
   `credentials.json`

---

## PASO 3: Encender el Motor (Ejecutar la App)

¡Ya tienes los cerebros conectados! Ahora vamos a prender la app.

1. Abre la **Terminal** en VS Code o PowerShell y asegúrate de estar dentro de la carpeta del proyecto.
2. Descarga los materiales de construcción (librerías) ejecutando:
   ```bash
   pip install -r requirements.txt
   ```
3. Enciende Pactora con este comando:
   ```bash
   streamlit run app.py
   ```
4. Se abrirá una pestaña en tu navegador (usualmente en `http://localhost:8501`).
5. Ve a la pestaña de **"Configuración"** en Pactora y haz clic en "Conectar con Google Workspace". Te saltará una ventana para iniciar sesión con tu cuenta de Google. ¡Acepta los permisos y listo!

¡Ya puedes empezar a subir contratos en la pestaña de Ingesta y hablar con el Chatbot!
