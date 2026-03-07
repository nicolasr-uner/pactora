import streamlit as st
from utils.shared import (
    apply_styles, page_header, init_session_state,
    api_status_banner, force_reindex, _trigger_startup_index,
)

apply_styles()
init_session_state()

page_header()
api_status_banner()
st.header("Configuracion")
st.markdown("---")

col_gemini, col_drive = st.columns(2)

# ─── Gemini API ───────────────────────────────────────────────────────────────
with col_gemini:
    st.markdown("""
    <div style="background:white;border-radius:16px;padding:24px;
         box-shadow:0 4px 20px rgba(145,91,216,0.08);
         border:1px solid rgba(145,91,216,0.15);">
        <h3 style="color:#2C2039;margin-top:0;border-left:4px solid #915BD8;padding-left:10px;">
            Gemini API
        </h3>
    </div>""", unsafe_allow_html=True)

    if st.session_state.gemini_api_key:
        st.caption("Configurada")
    k = st.text_input(
        "API Key",
        value="",
        type="password",
        label_visibility="collapsed",
        placeholder="Ingresa nueva Gemini API Key..."
    )
    if st.button("Guardar Key"):
        if k:
            from utils.shared import _get_chatbot
            _get_chatbot.clear()
            st.session_state.gemini_api_key = k
            st.success("API Key guardada y JuanMitaBot reiniciado.")
            st.rerun()
        else:
            st.warning("Ingresa una API Key para guardar.")

# ─── Google Drive ─────────────────────────────────────────────────────────────
with col_drive:
    st.markdown("""
    <div style="background:white;border-radius:16px;padding:24px;
         box-shadow:0 4px 20px rgba(145,91,216,0.08);
         border:1px solid rgba(145,91,216,0.15);">
        <h3 style="color:#2C2039;margin-top:0;border-left:4px solid #915BD8;padding-left:10px;">
            Conexion Drive
        </h3>
    </div>""", unsafe_allow_html=True)

    folder_id_input = st.text_input(
        "ID carpeta raiz",
        value=st.session_state.get("drive_root_id", ""),
        label_visibility="collapsed",
        placeholder="ID de carpeta raiz de Drive..."
    )
    if st.session_state.get("drive_api_key", "") and st.session_state.get("drive_api_key") != "DEMO_KEY":
        st.caption("API Key configurada")
    drive_key_input = st.text_input(
        "Drive API Key",
        value="",
        type="password",
        label_visibility="collapsed",
        placeholder="API Key de Google Drive..."
    )

    if st.button("Guardar configuracion Drive", type="primary"):
        if not folder_id_input:
            st.error("Ingresa el ID de carpeta.")
        else:
            st.session_state.drive_root_id = folder_id_input
            if drive_key_input:
                st.session_state.drive_api_key = drive_key_input
            st.session_state.current_folder_id = folder_id_input
            st.session_state.folder_history = [(folder_id_input, "Raiz Pactora")]
            st.success("Configuracion guardada. Usa 'Re-indexar' para iniciar la descarga.")
            st.rerun()

    if "drive_root_id" in st.session_state:
        st.caption(f"Conectado: {st.session_state.drive_root_id[:30]}")

st.markdown("---")

# ─── Diagnostico y re-indexacion ─────────────────────────────────────────────
if "drive_root_id" in st.session_state and st.session_state.get("drive_api_key", "") not in ("", "DEMO_KEY"):

    col_test, col_reindex = st.columns(2)

    with col_test:
        st.markdown("#### Test de descarga")
        st.caption("Verifica si la autenticacion puede descargar archivos del Drive.")
        if st.button("Probar descarga", use_container_width=True):
            with st.spinner("Buscando archivos..."):
                try:
                    from utils.drive_manager import get_recursive_files, download_file_to_io
                    files = get_recursive_files(
                        st.session_state.drive_root_id,
                        api_key=st.session_state.drive_api_key
                    )
                    if not files:
                        st.warning("No se encontraron archivos PDF/DOCX. Verifica el ID de carpeta.")
                    else:
                        st.info(f"Encontrados {len(files)} archivos. Probando descarga del primero...")
                        test_file = files[0]
                        fio = download_file_to_io(
                            test_file["id"],
                            api_key=st.session_state.drive_api_key
                        )
                        if fio:
                            data = fio.read()
                            st.success(
                                f"Descarga exitosa: **{test_file['name']}** "
                                f"({len(data):,} bytes). La indexacion funcionara correctamente."
                            )
                        else:
                            st.error(
                                f"No se pudo descargar **{test_file['name']}**. "
                                "Los archivos son privados — necesitas configurar una Cuenta de Servicio (ver abajo)."
                            )
                except Exception as e:
                    st.error(f"Error en test: {e}")

    with col_reindex:
        st.markdown("#### Re-indexar contratos")
        st.caption("Reinicia la indexacion en background (util tras cambiar credenciales).")
        if st.button("Re-indexar en background", use_container_width=True, type="primary"):
            force_reindex()
            _trigger_startup_index(
                st.session_state.chatbot,
                st.session_state.drive_root_id,
                st.session_state.drive_api_key,
            )
            st.success("Indexacion reiniciada en background. El contador aparecera en el banner superior.")
            st.rerun()

    st.markdown("---")

# ─── Guia de Cuenta de Servicio ───────────────────────────────────────────────
with st.expander("Como configurar Cuenta de Servicio (para archivos privados de Drive)"):
    st.markdown("""
**Los archivos privados de Drive requieren autenticacion completa. La API Key solo sirve para listar, no para descargar.**

### Pasos para configurar la Cuenta de Servicio:

**1. Crear la Cuenta de Servicio en Google Cloud Console**
- Ve a [console.cloud.google.com](https://console.cloud.google.com) → IAM y administracion → Cuentas de servicio
- Click "Crear cuenta de servicio" → ponle nombre: `pactora-drive`
- Rol: Visor (o sin rol, ya que el acceso es via Drive)
- Click "Listo"

**2. Descargar la clave JSON**
- En la lista de cuentas de servicio, click en `pactora-drive`
- Pestana "Claves" → "Agregar clave" → "Crear nueva clave" → JSON
- Se descarga un archivo `pactora-drive-xxxx.json`

**3. Compartir la carpeta de Drive con la Cuenta de Servicio**
- Abre el archivo JSON descargado y copia el campo `client_email` (algo como `pactora-drive@tu-proyecto.iam.gserviceaccount.com`)
- Ve a Google Drive → click derecho en la carpeta raiz de contratos → "Compartir"
- Pega el `client_email` y dale acceso de "Visualizador"

**4. Agregar el JSON a Streamlit Cloud Secrets**

Ve a tu app en Streamlit Cloud → Settings → Secrets, y agrega esto al final:

```toml
[GOOGLE_SERVICE_ACCOUNT]
type = "service_account"
project_id = "tu-proyecto-id"
private_key_id = "..."
private_key = "-----BEGIN RSA PRIVATE KEY-----\\n...\\n-----END RSA PRIVATE KEY-----\\n"
client_email = "pactora-drive@tu-proyecto.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/pactora-drive%40tu-proyecto.iam.gserviceaccount.com"
```

> **Importante:** Reemplaza los valores con los del JSON descargado. El `private_key` debe tener los saltos de linea como `\\n` (dos caracteres, no salto real).

**5. Reiniciar la app y re-indexar**
- Tras guardar los secrets, reinicia la app desde Streamlit Cloud
- Ve a Ajustes → "Probar descarga" para verificar
- Click "Re-indexar en background"
""")

# ─── Cerrar sesion ────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
if st.button("Cerrar sesion Pactora"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
