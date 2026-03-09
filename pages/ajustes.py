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

# ─── Carga manual de contratos ────────────────────────────────────────────────
st.markdown("### Cargar contratos")
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

        if st.button("Indexar archivos cargados", type="primary", use_container_width=True):
            from utils.file_parser import extract_text_from_file

            docs = []
            errors = []
            progress = st.progress(0)
            status = st.empty()

            for i, (name, fio) in enumerate(new_files):
                status.text(f"Procesando {name}...")
                progress.progress(i / len(new_files))
                txt = extract_text_from_file(fio, name)
                if txt and not txt.startswith("Error"):
                    docs.append((txt, name, {}))
                else:
                    errors.append(f"{name}: {txt[:80] if txt else 'sin texto (PDF escaneado)'}")

            progress.progress(1.0)

            if docs:
                status.text("Indexando en ChromaDB...")
                ok, msg = st.session_state.chatbot.vector_ingest_multiple(docs)
                if ok:
                    stats = st.session_state.chatbot.get_stats()
                    status.empty()
                    st.success(
                        f"Indexados: {len(docs)} archivo(s). "
                        f"Total en bot: **{stats['total_docs']} contrato(s)**"
                    )
                else:
                    status.empty()
                    st.error(f"Error al indexar: {msg}")
            else:
                status.empty()
                st.error("Ningún archivo produjo texto válido.")

            for e in errors:
                st.warning(e)

            st.rerun()
    else:
        st.info("Todos los archivos seleccionados ya están indexados.")

# ─── Contratos indexados actualmente ──────────────────────────────────────────
st.markdown("---")
stats = st.session_state.chatbot.get_stats()
if stats["total_docs"] > 0:
    with st.expander(f"Contratos en JuanMitaBot ({stats['total_docs']})"):
        for src in stats["sources"]:
            st.write(f"• {src}")
        st.markdown("---")
        if st.button("Limpiar todos los contratos indexados", type="secondary"):
            import shutil, os
            chroma_dir = "./chroma_db"
            if os.path.exists(chroma_dir):
                shutil.rmtree(chroma_dir)
            from utils.shared import _get_chatbot
            _get_chatbot.clear()
            st.session_state.chatbot = _get_chatbot()
            st.success("ChromaDB limpiado. Vuelve a cargar los contratos.")
            st.rerun()

# ─── Google Drive (configuracion futura) ──────────────────────────────────────
st.markdown("---")
with st.expander("Conexion Google Drive (opcional — para indexacion automatica)"):
    st.caption("Conecta tu Drive para indexar contratos automaticamente. Requiere API Keys.")
    folder_id_input = st.text_input(
        "ID carpeta raiz de Drive",
        value=st.session_state.get("drive_root_id", ""),
        placeholder="Pega el ID de la carpeta de Drive...",
    )
    drive_key_input = st.text_input(
        "Drive API Key",
        value="",
        type="password",
        placeholder="API Key de Google Drive...",
    )
    if st.button("Guardar configuracion Drive"):
        if folder_id_input:
            st.session_state.drive_root_id = folder_id_input
            if drive_key_input:
                st.session_state.drive_api_key = drive_key_input
            st.session_state.current_folder_id = folder_id_input
            st.session_state.folder_history = [(folder_id_input, "Raiz Pactora")]
            st.success("Configuracion guardada.")
            st.rerun()
        else:
            st.error("Ingresa el ID de carpeta.")
    if "drive_root_id" in st.session_state:
        st.caption(f"Conectado: {st.session_state.drive_root_id}")
        if st.button("Re-indexar desde Drive", type="primary"):
            from utils.shared import _get_chatbot
            _get_chatbot.clear()
            st.session_state.chatbot = _get_chatbot()
            force_reindex(st.session_state.chatbot)
            _trigger_startup_index(
                st.session_state.chatbot,
                st.session_state.drive_root_id,
                st.session_state.get("drive_api_key", ""),
            )
            st.success("Indexacion reiniciada en background.")
            st.rerun()

# ─── Cerrar sesion ────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
if st.button("Cerrar sesion Pactora"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
