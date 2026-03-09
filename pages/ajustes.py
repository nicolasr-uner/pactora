import streamlit as st
from utils.shared import apply_styles, page_header, init_session_state, api_status_banner

apply_styles()
init_session_state()
page_header()
api_status_banner()

st.markdown("## Ajustes")
st.caption("Configura tu workspace: carga contratos, gestiona el índice y conecta integraciones externas.")

# ─── Banner de seguridad — sin autenticación de usuarios ──────────────────────
try:
    _user_auth_active = st.user.is_logged_in
except Exception:
    _user_auth_active = False  # st.user no disponible en esta versión o sin auth configurada

if not _user_auth_active:
    st.warning(
        "**⚠️ App sin autenticación de usuarios activa.** "
        "Cualquier persona con la URL puede acceder a todos los contratos y configuraciones. "
        "Configura Streamlit Auth en `.streamlit/secrets.toml` para proteger la aplicación en producción.",
        icon="🔒"
    )

# ─── Sección 1: Cargar contratos ──────────────────────────────────────────────
sec1_hrow = st.columns([9, 1])
sec1_hrow[0].markdown("### 📂 Cargar Contratos")
with sec1_hrow[1].popover("ℹ️"):
    st.markdown(
        "Sube tus contratos en formato **PDF** o **DOCX** para indexarlos localmente. "
        "También puedes subir un **ZIP** con múltiples archivos.\\n\\n"
        "Los archivos se procesan localmente — no se envían a ningún servidor externo."
    )

st.caption("Sube PDFs o DOCXs desde tu computador. Para una carpeta completa: comprímela en ZIP.")

uploaded_files = st.file_uploader(
    "Selecciona archivos",
    type=["pdf", "docx", "zip"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)

if uploaded_files:
    import io as _io, zipfile

    expanded = []
    for uf in uploaded_files:
        if uf.name.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(_io.BytesIO(uf.read())) as zf:
                    for entry in zf.namelist():
                        if entry.lower().endswith((".pdf", ".docx")) and not entry.startswith("__MACOSX"):
                            fname = entry.split("/")[-1]
                            expanded.append((fname, _io.BytesIO(zf.read(entry))))
                st.info(f"ZIP **{uf.name}**: {len(expanded)} archivo(s) extraído(s)")
            except Exception as e:
                st.error(f"No se pudo abrir {uf.name}: {e}")
        else:
            expanded.append((uf.name, _io.BytesIO(uf.read())))

    already = set(st.session_state.chatbot._indexed_sources)
    new_files = [(name, fio) for name, fio in expanded if name not in already]
    skipped = [name for name, _ in expanded if name in already]

    if skipped:
        st.info(f"Ya indexados (se omiten): {', '.join(skipped)}")

    if new_files:
        st.write(f"**{len(new_files)} archivo(s) nuevos listos para indexar:**")
        for name, _ in new_files[:10]:
            st.write(f"  • {name}")
        if len(new_files) > 10:
            st.write(f"  … y {len(new_files) - 10} más")

        if st.button("📥 Indexar archivos cargados", type="primary", use_container_width=True):
            from utils.file_parser import extract_text_from_file

            docs = []
            errors = []
            progress = st.progress(0)
            status = st.empty()

            for i, (name, fio) in enumerate(new_files):
                status.text(f"Procesando {name}...")
                progress.progress((i + 1) / len(new_files))
                try:
                    txt = extract_text_from_file(fio, name)
                except Exception as ex:
                    txt = f"Error: {ex}"
                if txt and not txt.startswith("Error"):
                    docs.append((txt, name, {}))
                    status.text(f"✓ {name} — {len(txt):,} caracteres extraídos")
                else:
                    reason = txt[:120] if txt else "sin texto (PDF escaneado o imagen sin OCR)"
                    errors.append(f"**{name}**: {reason}")

            progress.empty()

            if docs:
                status.text("Indexando en ChromaDB...")
                ok, msg = st.session_state.chatbot.vector_ingest_multiple(docs)
                status.empty()
                if ok:
                    stats_result = st.session_state.chatbot.get_stats()
                    st.success(
                        f"✅ Indexados: {len(docs)} archivo(s). "
                        f"Total en JuanMitaBot: **{stats_result['total_docs']} contrato(s)**"
                    )
                    for e in errors:
                        st.warning(e)
                    st.rerun()
                else:
                    st.error(f"Error al indexar en ChromaDB: {msg}")
                    for e in errors:
                        st.warning(e)
            else:
                status.empty()
                st.error(
                    "⚠️ Ningún archivo produjo texto extraíble. "
                    "Asegúrate de que los PDFs tengan texto seleccionable (no sean imágenes escaneadas)."
                )
                for e in errors:
                    st.warning(e)
    else:
        st.info("Todos los archivos seleccionados ya están indexados.")

# ─── Sección 2: Contratos indexados ───────────────────────────────────────────
st.markdown("---")
sec2_hrow = st.columns([9, 1])
sec2_hrow[0].markdown("### 📋 Contratos Indexados")
with sec2_hrow[1].popover("ℹ️"):
    st.markdown(
        "Lista de todos los contratos actualmente en el índice local (ChromaDB). "
        "Puedes limpiar el índice completo si necesitas empezar de cero.\\n\\n"
        "⚠️ Limpiar el índice eliminará todos los contratos y no se puede deshacer."
    )

stats = st.session_state.chatbot.get_stats()

if stats["total_docs"] > 0:
    st.success(f"**{stats['total_docs']} contrato(s)** indexados y listos para búsqueda.")
    with st.expander(f"Ver contratos ({len(stats['sources'])})"):
        for src in stats["sources"]:
            ext = src.lower().split(".")[-1] if "." in src else ""
            icon = "📄" if ext == "pdf" else "📝" if ext == "docx" else "📁"
            st.write(f"{icon} {src}")
        st.markdown("---")
        if st.button("🗑 Limpiar todos los contratos indexados", type="secondary"):
            import shutil, os
            chroma_dir = "./chroma_db"
            if os.path.exists(chroma_dir):
                shutil.rmtree(chroma_dir)
            from utils.shared import _get_chatbot
            _get_chatbot.clear()
            st.session_state.chatbot = _get_chatbot()
            st.success("ChromaDB limpiado. Vuelve a cargar los contratos.")
            st.rerun()
else:
    st.info("No hay contratos indexados aún. Carga archivos en la sección de arriba.")

# ─── Sección 3: Google Drive (Próximamente) ────────────────────────────────────
st.markdown("---")
sec3_hrow = st.columns([9, 1])
sec3_hrow[0].markdown("### ☁️ Google Drive  `Próximamente`")
with sec3_hrow[1].popover("ℹ️"):
    st.markdown(
        "Conecta una carpeta de Google Drive para indexar contratos automáticamente "
        "cada vez que se agreguen nuevos archivos.\\n\\n"
        "Requiere configurar una cuenta de servicio de Google Cloud con permisos de lectura. "
        "**Esta funcionalidad estará disponible en una próxima versión.**"
    )

with st.container():
    st.markdown(
        '<div style="background:#f5f5f5;border:1px dashed #ccc;border-radius:10px;'
        'padding:20px;opacity:0.6;pointer-events:none;">',
        unsafe_allow_html=True
    )
    col_drive, col_info = st.columns([3, 1])
    with col_drive:
        st.text_input(
            "ID carpeta raíz de Drive",
            placeholder="Ej: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs...",
            disabled=True,
            key="drive_folder_disabled"
        )
    with col_info:
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("Conectar Drive", disabled=True, use_container_width=True)
    st.caption("🔒 Requiere cuenta de servicio Google Cloud con acceso a la carpeta compartida.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
        '<div style="margin-top:8px;padding:8px 12px;background:#fff3e0;border-radius:6px;'
        'border-left:3px solid #FF9800;font-size:13px;">'
        '🔮 <b>Próximamente:</b> indexación automática desde Google Drive. '
        'Los contratos se sincronizarán al detectar archivos nuevos.'
        '</div>',
        unsafe_allow_html=True
    )

# ─── Sección 4: Gemini API (Próximamente) ─────────────────────────────────────
st.markdown("---")
sec4_hrow = st.columns([9, 1])
sec4_hrow[0].markdown("### 🤖 Gemini API  `Próximamente`")
with sec4_hrow[1].popover("ℹ️"):
    st.markdown(
        "Conecta la API de Gemini (Google AI) para habilitar:\\n\\n"
        "- Respuestas generadas por IA en JuanMitaChat\\n"
        "- Extracción semántica de fechas en el Calendario\\n"
        "- Análisis de riesgo inteligente en Métricas\\n"
        "- Comparación avanzada de contratos en Análisis Legal\\n\\n"
        "**Esta funcionalidad estará disponible en una próxima versión.**"
    )

with st.container():
    st.markdown(
        '<div style="background:#f5f5f5;border:1px dashed #ccc;border-radius:10px;'
        'padding:20px;opacity:0.6;pointer-events:none;">',
        unsafe_allow_html=True
    )
    col_gem1, col_gem2 = st.columns([3, 1])
    with col_gem1:
        st.text_input(
            "Gemini API Key",
            placeholder="AIza...",
            type="password",
            disabled=True,
            key="gemini_key_disabled"
        )
    with col_gem2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("Activar IA", disabled=True, use_container_width=True)
    st.caption("Obtén tu API Key en Google AI Studio (aistudio.google.com). Plan gratuito disponible.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
        '<div style="margin-top:8px;padding:8px 12px;background:#f3e5f5;border-radius:6px;'
        'border-left:3px solid #9C27B0;font-size:13px;">'
        '🔮 <b>Próximamente:</b> análisis semántico con IA para mayor precisión en '
        'extracción de cláusulas, fechas y análisis de riesgo.'
        '</div>',
        unsafe_allow_html=True
    )

# ─── Sección 5: Cerrar sesión ──────────────────────────────────────────────────
st.markdown("---")
sec5_hrow = st.columns([9, 1])
sec5_hrow[0].markdown("### ⚙️ Sesión")
with sec5_hrow[1].popover("ℹ️"):
    st.markdown(
        "Limpia todos los datos de la sesión actual (contratos cargados, historial de búsqueda, eventos). "
        "El índice de ChromaDB **no se borra** con esta acción — solo el estado de la sesión."
    )

col_ses1, col_ses2 = st.columns([3, 1])
with col_ses1:
    st.caption("Reinicia la sesión de Pactora. El índice local de contratos se mantiene.")
with col_ses2:
    if st.button("Cerrar sesión", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
