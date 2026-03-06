# Guía para subir Pactora a GitHub

Para subir el proyecto "Pactora" a GitHub de forma segura, sigue estos pasos:

## 1. Crear el repositorio en GitHub
1. Entra a [GitHub](https://github.com/) e inicia sesión.
2. Haz clic en el botón verde **"New"** (o "Nuevo repositorio").
3. Escribe el nombre del repositorio (ej. `pactora-clm-unergy`).
4. Selecciona si será **Public** (Público) o **Private** (Privado) - Recomendamos **Private** para proyectos internos de empresa.
5. **NO** marques las opciones de agregar README, .gitignore o licencia (ya los tenemos o los crearemos localmente).
6. Haz clic en **"Create repository"**.

## 2. Vincular el repositorio local con GitHub
Abre tu terminal (Símbolo del sistema, PowerShell o la terminal integrada de VS Code), asegúrate de estar en la carpeta del proyecto (`C:\Users\PC\.gemini\antigravity\scratch\pactora`) y ejecuta los siguientes comandos:

*Nota: Yo ya he ejecutado `git init` y el paso para añadir los archivos localmente, así que ya tienes el `.gitignore` creado para proteger tus contraseñas.*

Copia y pega este bloque de comandos (cambiando la URL por la de tu repositorio):

```bash
# 1. Haz tu primer "commit" (guardar los cambios localmente)
git commit -m "First commit - Pactora Initial Setup"

# 2. Renombra la rama principal a "main" (estándar actual)
git branch -M main

# 3. Vincula tu carpeta con el repositorio de GitHub (REEMPLAZA LA URL)
git remote add origin https://github.com/TU-USUARIO/NOMBRE-DEL-REPO.git

# 4. Sube los archivos a GitHub
git push -u origin main
```

## ⚠️ Aspecto de Seguridad Crítico
Asegúrate de **nunca** borrar o modificar el archivo `.gitignore` que he creado. Ese archivo evita que subas por accidente tus claves de la API de Google (`credentials.json`, `token.json`). Si esos archivos llegan a GitHub, cualquier persona podría acceder a la cuenta de Google Drive y Calendar vinculada.
