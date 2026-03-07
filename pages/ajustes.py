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
        st.caption(f"Conectado: {st.session_state.drive_root_id}")

st.markdown("---")

# ─── Diagnostico y re-indexacion ─────────────────────────────────────────────
if "drive_root_id" in st.session_state and st.session_state.get("drive_api_key", "") not in ("", "DEMO_KEY"):

    col_test, col_reindex = st.columns(2)

    with col_test:
        st.markdown("#### Test de descarga y extraccion")
        st.caption("Descarga el primer archivo y extrae texto para verificar que la indexacion funcionara.")
        if st.button("Probar descarga + extraccion", use_container_width=True):
            with st.spinner("Probando..."):
                try:
                    from utils.drive_manager import get_recursive_files, _do_download, _download_with_requests
                    from utils.auth_helper import get_drive_service_sa, get_drive_service
                    import io as _io

                    # Paso 1: Verificar SA
                    sa_service = get_drive_service_sa()
                    if sa_service:
                        st.success("Cuenta de Servicio cargada correctamente")
                    else:
                        st.error("Cuenta de Servicio NO cargada — revisa el formato de los secrets")

                    files = get_recursive_files(
                        st.session_state.drive_root_id,
                        api_key=st.session_state.drive_api_key
                    )
                    if not files:
                        st.warning("No se encontraron archivos PDF/DOCX.")
                    else:
                        test_file = files[0]
                        st.info(f"Probando: **{test_file['name']}** (id: {test_file['id'][:20]}...)")

                        # Paso 2: Descargar con SA
                        fio = None
                        if sa_service:
                            try:
                                fio = _do_download(sa_service, test_file["id"])
                                st.success(f"Descarga con SA exitosa: {len(fio.read()):,} bytes")
                                fio.seek(0)
                            except Exception as e:
                                st.error(f"SA descarga fallo: {e}")
                                fio = None

                        # Paso 3: Fallback con requests si SA fallo
                        if not fio:
                            st.warning("Intentando con requests + API Key...")
                            fio = _download_with_requests(test_file["id"], st.session_state.drive_api_key)
                            if fio:
                                st.success(f"requests OK: {len(fio.read()):,} bytes")
                                fio.seek(0)
                            else:
                                st.error("Ambos metodos fallaron. Verifica que compartiste la carpeta con la SA.")

                        # Paso 4: Extraer texto
                        if fio:
                            file_bytes = fio.read()
                            from utils.file_parser import _extract_pdf_bytes, _extract_with_gemini
                            pypdf_text = _extract_pdf_bytes(file_bytes)
                            if pypdf_text.strip():
                                st.success(f"pypdf extrajo **{len(pypdf_text):,} chars**")
                                st.text_area("Vista previa", value=pypdf_text[:500], height=120, disabled=True)
                            else:
                                st.warning("pypdf vacio (PDF escaneado). Probando Gemini OCR...")
                                gemini_key = st.session_state.get("gemini_api_key", "")
                                if gemini_key:
                                    with st.spinner("Gemini OCR..."):
                                        gemini_text = _extract_with_gemini(file_bytes, test_file["name"], gemini_key)
                                    if gemini_text.strip():
                                        st.success(f"Gemini extrajo **{len(gemini_text):,} chars**")
                                        st.text_area("Vista previa", value=gemini_text[:500], height=120, disabled=True)
                                    else:
                                        st.error("Gemini no extrajo texto.")
                                else:
                                    st.error("No hay Gemini API Key para OCR.")
                except Exception as e:
                    st.error(f"Error inesperado: {e}")

    with col_reindex:
        st.markdown("#### Re-indexar contratos")
        st.caption("Reinicia la indexacion en background (util tras cambiar credenciales).")
        if st.button("Re-indexar en background", use_container_width=True, type="primary"):
            from utils.shared import _get_chatbot
            _get_chatbot.clear()  # Fuerza recrear chatbot con nuevo modelo de embeddings
            st.session_state.chatbot = _get_chatbot(st.session_state.gemini_api_key)
            force_reindex(st.session_state.chatbot)
            _trigger_startup_index(
                st.session_state.chatbot,
                st.session_state.drive_root_id,
                st.session_state.drive_api_key,
            )
            st.success("Indexacion reiniciada en background. El contador aparecera en el banner superior.")
            st.rerun()

    st.markdown("---")

# ─── Debug: estado interno ────────────────────────────────────────────────────
if "drive_root_id" in st.session_state and st.session_state.get("drive_api_key", "") not in ("", "DEMO_KEY"):
    with st.expander("Debug: estado interno y prueba sincrona"):
        from utils.shared import _startup_index_progress
        p = _startup_index_progress
        st.json({
            "indexacion_status": p["status"],
            "total": p["total"],
            "downloaded": p["downloaded"],
            "indexed": p["indexed"],
            "last_file": p["last_file"],
            "error": p["error"],
            "chatbot_indexed_sources_count": len(st.session_state.chatbot._indexed_sources),
            "chromadb_docs": st.session_state.chatbot.get_stats()["total_docs"],
            "chromadb_chunks": st.session_state.chatbot.get_stats()["total_chunks"],
        })

        if st.button("Indexar primeros 5 archivos (sincrono — muestra resultado directo)"):
            from utils.drive_manager import get_recursive_files, download_file_to_io
            from utils.file_parser import extract_text_from_file
            with st.spinner("Procesando..."):
                files = get_recursive_files(
                    st.session_state.drive_root_id,
                    api_key=st.session_state.drive_api_key
                )
                st.write(f"Total archivos en Drive: {len(files)}")
                st.write(f"Ya en _indexed_sources: {len(st.session_state.chatbot._indexed_sources)}")
                gemini_key = st.session_state.chatbot.api_key
                docs = []
                for f in files[:5]:
                    fio = download_file_to_io(f["id"], api_key=st.session_state.drive_api_key)
                    if not fio:
                        st.error(f"Descarga fallo: {f['name']}")
                        continue
                    txt = extract_text_from_file(fio, f["name"], gemini_api_key=gemini_key)
                    if txt and not txt.startswith("Error"):
                        docs.append((txt, f["name"], {"drive_id": f["id"]}))
                        st.success(f"OK: {f['name']} — {len(txt):,} chars")
                    else:
                        st.warning(f"Sin texto: {f['name']}")
                if docs:
                    ok, msg = st.session_state.chatbot.vector_ingest_multiple(docs)
                    if ok:
                        st.success(f"Indexados en ChromaDB: {msg}")
                    else:
                        st.error(f"Error al indexar: {msg}")
                    st.write(f"Stats ahora: {st.session_state.chatbot.get_stats()}")
                else:
                    st.error("Ningun archivo produjo texto — todos fallaron extraccion.")

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
