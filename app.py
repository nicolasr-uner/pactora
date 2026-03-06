import sys

# Fix: Python 3.14 PEP 649 breaks pydantic v1 metaclass annotation reading.
if sys.version_info >= (3, 14):
    import pydantic.v1.main as _pv1m
    _orig_metaclass_new = _pv1m.ModelMetaclass.__new__
    def _patched_metaclass_new(mcs, name, bases, namespace, **kwargs):
        if '__annotate_func__' in namespace and '__annotations__' not in namespace:
            try:
                namespace['__annotations__'] = namespace['__annotate_func__'](1)
            except Exception:
                pass
        return _orig_metaclass_new(mcs, name, bases, namespace, **kwargs)
    _pv1m.ModelMetaclass.__new__ = _patched_metaclass_new

import streamlit as st
import os
import copy

# --- HELPER FUNCTIONS ---

def render_side_chat_panel(panel_col):
    """Chatbot contextual en columna lateral."""
    with panel_col:
        st.markdown(f"""
        <div style="background:white; padding:16px; border-radius:16px;
             box-shadow:-4px 0 12px rgba(0,0,0,0.05); border-left:3px solid #915BD8;">
            <h4 style="color:#2C2039; margin:0 0 4px 0;">🧠 JuanMita Contextual</h4>
            <p style="font-size:0.75em; color:#915BD8; margin:0;">
                <b>Contexto:</b> {st.session_state.get('sidebar_chat_title','Workspace')}
            </p>
        </div>
        """, unsafe_allow_html=True)

        chat_container = st.container(height=480)
        with chat_container:
            if 'sidebar_chat_history' not in st.session_state:
                st.session_state.sidebar_chat_history = []
            for msg in st.session_state.sidebar_chat_history:
                avatar = "🤖" if msg['role'] == "assistant" else None
                with st.chat_message(msg['role'], avatar=avatar):
                    st.markdown(msg['content'])

        user_input = st.chat_input("Pregunta sobre este documento...", key="side_panel_input")
        if user_input:
            st.session_state.sidebar_chat_history.append({"role": "user", "content": user_input})
            st.rerun()

        if (st.session_state.sidebar_chat_history
                and st.session_state.sidebar_chat_history[-1]["role"] == "user"):
            last_q = st.session_state.sidebar_chat_history[-1]["content"]
            # Historial previo (excluye el último mensaje de usuario que acabamos de añadir)
            history_for_llm = st.session_state.sidebar_chat_history[:-1]
            with chat_container:
                with st.chat_message("assistant", avatar="🤖"):
                    with st.spinner("JuanMita analizando contratos..."):
                        filter_meta = st.session_state.get('sidebar_chat_filter')
                        ans = st.session_state.chatbot.ask_question(
                            last_q,
                            filter_metadata=filter_meta,
                            chat_history=history_for_llm
                        )
                        st.markdown(ans)
            st.session_state.sidebar_chat_history.append({"role": "assistant", "content": ans})
            st.rerun()

        if st.button("✕ Cerrar", use_container_width=True):
            st.session_state.sidebar_chat_open = False
            st.rerun()


def main():
    st.set_page_config(page_title="Pactora CLM - Unergy", layout="wide")

    # --- IMPORTS ---
    from core.rag_chatbot import RAGChatbot

    # --- SESSION STATE ---
    if 'gemini_api_key' not in st.session_state:
        st.session_state.gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")

    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = RAGChatbot(api_key=st.session_state.gemini_api_key)

    if 'current_folder_id' not in st.session_state:
        st.session_state.current_folder_id = "1sF8_SuiiFdiWq_9htA-cNZP1Gp0djc4N"
    if 'folder_history' not in st.session_state:
        st.session_state.folder_history = [(st.session_state.current_folder_id, "Raíz Pactora")]
    if 'sidebar_chat_open' not in st.session_state:
        st.session_state.sidebar_chat_open = False
    # Bug 2 fix: nav persiste entre reruns
    if 'nav_opt' not in st.session_state:
        st.session_state.nav_opt = "🏠 Inicio"
    # Feature 4: almacenamiento de versiones
    if 'doc_versions' not in st.session_state:
        st.session_state.doc_versions = {}   # {filename: {"original": str, "draft": str, "history": [str]}}

    # --- ESTILOS ---
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Lato:wght@400;700;900&display=swap');
    .stApp { background-color: #FDFAF7; font-family: 'Lato', sans-serif; color: #212121; }
    .top-nav { position: fixed; top: 20px; right: 40px; z-index: 1000; display: flex; gap: 20px;
        background: rgba(255,255,255,0.85); padding: 10px 20px; border-radius: 30px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.06); backdrop-filter: blur(6px); }
    .top-nav a { text-decoration: none; color: #915BD8; font-weight: 700; font-size: 16px; }
    .pactora-header { font-family:'Lato',sans-serif; font-weight:900; font-size:52px;
        color:#2C2039; text-align:center; margin-top:-30px; }
    .pactora-tagline { text-align:center; color:#915BD8; font-weight:600; margin-bottom:24px; }
    section[data-testid="stSidebar"] { background-color: #2C2039 !important; width: 250px !important; }
    [data-testid="stSidebar"] * { color: #FDFAF7 !important; }
    .factora-card { background:rgba(255,255,255,0.85); border-radius:16px; padding:20px;
        box-shadow:0 6px 24px rgba(145,91,216,0.07); border:1px solid rgba(145,91,216,0.12);
        margin-bottom:16px; }
    .card-title { font-size:18px; font-weight:900; color:#2C2039; margin-bottom:14px;
        border-left:4px solid #915BD8; padding-left:10px; }
    .metric-card { background:white; border-radius:12px; padding:16px; text-align:center;
        box-shadow:0 4px 16px rgba(145,91,216,0.08); border:1px solid rgba(145,91,216,0.1); }
    .metric-val { font-size:32px; font-weight:900; color:#915BD8; }
    .metric-lbl { font-size:12px; color:#666; margin-top:4px; }
    .version-badge { background:#915BD8; color:white; border-radius:4px; padding:2px 8px;
        font-size:11px; font-weight:700; }
    div[data-testid="stButton"] > button { background-color:#915BD8; color:white; border:none;
        border-radius:8px; font-weight:700; padding:8px 20px; transition:background 0.2s; }
    div[data-testid="stButton"] > button:hover { background-color:#7a48c0; color:white; }
    </style>
    """, unsafe_allow_html=True)

    # --- SIDEBAR ---
    with st.sidebar:
        # Bug 2 fix: usar key vinculado a session_state
        nav_choice = st.radio(
            "Menú",
            ["🏠 Inicio", "📅 Calendario", "📊 Métricas", "📄 Plantillas",
             "⚖️ Análisis Legal", "🧠 Chatbot", "⚙️ Ajustes"],
            index=["🏠 Inicio", "📅 Calendario", "📊 Métricas", "📄 Plantillas",
                   "⚖️ Análisis Legal", "🧠 Chatbot", "⚙️ Ajustes"].index(
                       st.session_state.nav_opt),
            label_visibility="collapsed",
            key="nav_radio"
        )
        # Sincronizar sin rerun innecesario
        if nav_choice != st.session_state.nav_opt:
            st.session_state.nav_opt = nav_choice
            # Limpiar estado de chat lateral al cambiar de sección
            st.session_state.sidebar_chat_open = False

        st.divider()
        if 'drive_root_id' in st.session_state:
            st.caption(f"☁️ {st.session_state.get('drive_root_name','Drive')}")

        # Mostrar docs indexados en sidebar
        stats = st.session_state.chatbot.get_stats()
        if stats['total_docs'] > 0:
            st.caption(f"📂 {stats['total_docs']} doc(s) indexados")

        st.session_state.agent_active = st.toggle(
            "🤖 JuanMita activa",
            value=st.session_state.get('agent_active', True)
        )
        if st.session_state.agent_active:
            st.success("JuanMita lista\npara analizar contratos.")

    nav_opt = st.session_state.nav_opt

    # --- LAYOUT ---
    if st.session_state.get('sidebar_chat_open'):
        col_main, col_side = st.columns([2.5, 1])
    else:
        col_main = st.container()
        col_side = None

    with col_main:
        st.markdown(
            '<div class="top-nav">'
            '<a href="#">🏠 Inicio</a>'
            '<a href="#">🤖 JuanMita</a>'
            '<a href="#">⚙️ Ajustes</a>'
            '</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            '<div class="pactora-header">Pactora</div>'
            '<div class="pactora-tagline">by Unergy</div>',
            unsafe_allow_html=True
        )

        # ============================================================
        # 🏠 INICIO
        # ============================================================
        if nav_opt == "🏠 Inicio":
            search_query = st.text_input(
                "🔍",
                placeholder="Buscar en contratos indexados… Ej: cláusulas de terminación Suno Solar",
                label_visibility="collapsed"
            )
            if search_query:
                with st.spinner("JuanMita consultando contratos..."):
                    ans = st.session_state.chatbot.ask_question(search_query)
                st.info(f"🤖 **JuanMita:**\n\n{ans}")

            c1, c2 = st.columns(2)
            with c1:
                st.markdown('<div class="factora-card"><div class="card-title">📁 Explorador de Archivos</div>', unsafe_allow_html=True)
                if 'drive_root_id' in st.session_state:
                    from utils.drive_manager import get_folder_contents, download_file_to_io, get_recursive_files
                    from utils.file_parser import extract_text_from_file

                    drive_api_key = st.session_state.get('drive_api_key')
                    is_demo = drive_api_key == "DEMO_KEY"

                    # Breadcrumb + back button
                    history = st.session_state.folder_history
                    breadcrumb = " › ".join(name for _, name in history)
                    st.caption(f"📍 {breadcrumb}")
                    if len(history) > 1:
                        if st.button("⬅ Volver", key="back_btn", type="secondary"):
                            history.pop()
                            st.session_state.current_folder_id = history[-1][0]
                            st.rerun()

                    if is_demo and 'mock_items' in st.session_state:
                        items = st.session_state.mock_items
                    else:
                        items = get_folder_contents(
                            st.session_state.current_folder_id,
                            api_key=drive_api_key
                        )

                    for item in items[:15]:
                        is_folder = item['mimeType'] == 'application/vnd.google-apps.folder'
                        icon = "📁" if is_folder else "📄"
                        row = st.columns([1, 7, 1])
                        row[0].write(icon)
                        if row[1].button(item['name'], key=f"f_{item['id']}", use_container_width=True):
                            if is_folder:
                                st.session_state.current_folder_id = item['id']
                                st.session_state.folder_history.append((item['id'], item['name']))
                                st.rerun()
                        help_txt = "Analizar carpeta con JuanMita" if is_folder else "Preguntar a JuanMita sobre este archivo"
                        if row[2].button("🤖", key=f"ia_{item['id']}", help=help_txt):
                            chatbot = st.session_state.chatbot
                            if not is_demo:
                                if is_folder:
                                    with st.spinner(f"Indexando archivos de '{item['name']}'..."):
                                        files = get_recursive_files(item['id'], api_key=drive_api_key)
                                        docs = []
                                        for f in files:
                                            fio = download_file_to_io(f['id'], api_key=drive_api_key)
                                            if fio:
                                                txt = extract_text_from_file(fio, f['name'])
                                                if txt and not txt.startswith("Error"):
                                                    docs.append((txt, f['name'], {}))
                                        if docs:
                                            chatbot.vector_ingest_multiple(docs)
                                else:
                                    if item['name'] not in chatbot._indexed_sources:
                                        with st.spinner(f"Indexando '{item['name']}'..."):
                                            fio = download_file_to_io(item['id'], api_key=drive_api_key)
                                            if fio:
                                                txt = extract_text_from_file(fio, item['name'])
                                                if txt and not txt.startswith("Error"):
                                                    chatbot.vector_ingest(txt, filename=item['name'])
                            st.session_state.sidebar_chat_open = True
                            st.session_state.sidebar_chat_title = item['name']
                            st.session_state.sidebar_chat_history = []
                            st.session_state.sidebar_chat_filter = None if is_folder else {"source": item['name']}
                            st.rerun()
                else:
                    st.info("Conecta tu Google Drive en ⚙️ Ajustes para explorar archivos.")
                st.markdown('</div>', unsafe_allow_html=True)

            with c2:
                st.markdown('<div class="factora-card"><div class="card-title">📊 Estado del Workspace</div>', unsafe_allow_html=True)
                stats = st.session_state.chatbot.get_stats()
                m1, m2 = st.columns(2)
                m1.markdown(f'<div class="metric-card"><div class="metric-val">{stats["total_docs"]}</div><div class="metric-lbl">Contratos indexados</div></div>', unsafe_allow_html=True)
                m2.markdown(f'<div class="metric-card"><div class="metric-val">{stats["total_chunks"]}</div><div class="metric-lbl">Fragmentos en RAG</div></div>', unsafe_allow_html=True)

                if stats['sources']:
                    st.caption("📄 Contratos en JuanMita:")
                    for s in stats['sources'][:8]:
                        st.markdown(f"• {s}")
                else:
                    st.caption("Sin documentos indexados aún.")

                # Botón para indexar todo el Drive desde el card de inicio
                if 'drive_root_id' in st.session_state:
                    if st.button("🔄 Indexar todos los contratos del Drive", use_container_width=True, key="ws_index_all"):
                        from utils.drive_manager import get_recursive_files, download_file_to_io
                        from utils.file_parser import extract_text_from_file
                        drive_key = st.session_state.get('drive_api_key')
                        with st.spinner("Indexando todos los contratos del Drive en JuanMita…"):
                            all_f = get_recursive_files(st.session_state.drive_root_id, api_key=drive_key)
                            docs = []
                            errors = []
                            for f in all_f:
                                fio = download_file_to_io(f['id'], api_key=drive_key)
                                if fio:
                                    txt = extract_text_from_file(fio, f['name'])
                                    if txt and not txt.startswith("Error"):
                                        docs.append((txt, f['name'], {}))
                                else:
                                    errors.append(f['name'])
                            if docs:
                                ok, msg = st.session_state.chatbot.vector_ingest_multiple(docs)
                                st.success(f"✅ {len(docs)} contratos indexados en JuanMita.")
                            else:
                                st.warning("No se encontraron archivos descargables. Verifica que tu API Key tenga acceso a los archivos.")
                            if errors:
                                st.caption(f"⚠️ No se pudo descargar: {', '.join(errors[:5])}")
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        # ============================================================
        # 📅 CALENDARIO
        # ============================================================
        elif nav_opt == "📅 Calendario":
            st.header("📅 Calendario Operativo")
            view = st.radio("Vista", ["Mensual", "Semanal", "Diario"], horizontal=True)
            st.info(f"Vista {view} — Conecta Google Calendar en Ajustes para ver eventos reales.")

        # ============================================================
        # 📊 MÉTRICAS — Bug 3: datos reales del vectorstore
        # ============================================================
        elif nav_opt == "📊 Métricas":
            st.header("📊 Métricas de Cumplimiento")
            import pandas as pd

            stats = st.session_state.chatbot.get_stats()

            # KPIs reales
            k1, k2, k3 = st.columns(3)
            k1.markdown(f'<div class="metric-card"><div class="metric-val">{stats["total_docs"]}</div><div class="metric-lbl">Contratos indexados</div></div>', unsafe_allow_html=True)
            k2.markdown(f'<div class="metric-card"><div class="metric-val">{stats["total_chunks"]}</div><div class="metric-lbl">Fragmentos en RAG</div></div>', unsafe_allow_html=True)
            versiones = sum(len(v.get('history', [])) for v in st.session_state.doc_versions.values())
            k3.markdown(f'<div class="metric-card"><div class="metric-val">{versiones}</div><div class="metric-lbl">Versiones guardadas</div></div>', unsafe_allow_html=True)

            st.markdown("---")

            if stats['sources']:
                # Gráfico con documentos reales
                doc_data = {"Documento": [s[:30] for s in stats['sources']], "Fragmentos RAG": []}
                try:
                    all_meta = st.session_state.chatbot.vectorstore.get(include=["metadatas"])
                    metas = all_meta.get("metadatas", [])
                    for src in stats['sources']:
                        count = sum(1 for m in metas if m and m.get("source") == src)
                        doc_data["Fragmentos RAG"].append(count)
                    df = pd.DataFrame(doc_data)
                    st.subheader("Fragmentos indexados por documento")
                    st.bar_chart(df.set_index("Documento"))
                except Exception:
                    st.info("Indexa documentos para ver métricas detalladas.")

                st.subheader("📄 Documentos indexados")
                for i, src in enumerate(stats['sources'], 1):
                    st.markdown(f"`{i}.` **{src}**")
            else:
                st.info("No hay documentos indexados. Ve a ⚖️ Análisis Legal o ⚙️ Ajustes para indexar contratos.")

        # ============================================================
        # 📄 PLANTILLAS
        # ============================================================
        elif nav_opt == "📄 Plantillas":
            st.header("📄 Biblioteca de Plantillas")
            plantillas = [
                {"nombre": "PPA_Standard_V2.docx", "tipo": "PPA", "version": "v2.1"},
                {"nombre": "EPC_Contrato_Base.docx", "tipo": "EPC", "version": "v1.3"},
                {"nombre": "O&M_Marco_General.docx", "tipo": "O&M", "version": "v1.0"},
            ]
            for p in plantillas:
                col_a, col_b, col_c = st.columns([5, 2, 2])
                col_a.markdown(f"📄 **{p['nombre']}** `{p['tipo']}`")
                col_b.markdown(f'<span class="version-badge">{p["version"]}</span>', unsafe_allow_html=True)
                col_c.button("Descargar", key=f"dl_{p['nombre']}")

        # ============================================================
        # ⚖️ ANÁLISIS LEGAL — Feature 4: control de versiones
        # ============================================================
        elif nav_opt == "⚖️ Análisis Legal":
            st.header("⚖️ Análisis de Riesgos y Contratos")

            tab_upload, tab_editor, tab_versions = st.tabs(
                ["📤 Cargar Contrato", "✏️ Editor de Borrador", "🗂️ Historial de Versiones"]
            )

            # --- TAB 1: Biblioteca de Google Drive (Drive-First) ---
            with tab_upload:
                st.subheader("☁️ Biblioteca de Contratos (Google Drive)")
                st.write("Busca y selecciona un contrato directamente desde la nube de Unergy.")

                # Search Interface
                search_col1, search_col2 = st.columns([3, 1])
                with search_col1:
                    drive_query = st.text_input("🔍 Nombre del documento", placeholder="Ej: PPA-GranjaSolar", key="drive_lib_query")
                with search_col2:
                    if st.button("Buscar en Biblioteca", use_container_width=True):
                        with st.spinner("Conectando con Google Drive..."):
                            results = search_documents(query=drive_query)
                            st.session_state['lib_search_results'] = results

                        # Feature 4: guardar versión original intocable
                        if up.name not in st.session_state.doc_versions:
                            st.session_state.doc_versions[up.name] = {
                                "original": text,
                                "draft": text,
                                "history": []
                            }
                            # Auto-indexar en RAG (Bug 1 fix)
                            with st.spinner("Indexando en JuanMita..."):
                                ok, msg = st.session_state.chatbot.vector_ingest(
                                    text, up.name, {"file_type": up.name.split(".")[-1]}
                                )
                            st.info(msg)
                        else:
                            st.info("Este documento ya estaba indexado. Ve a ✏️ Editor para editarlo.")

                    if st.button("🚀 Cargar e Indexar en JuanMita", type="primary"):
                        with st.spinner(f"Descargando e indexando {selected_file['name']}..."):
                            # 1. Fetch from Drive
                            file_bytes = fetch_document(selected_file['id'])
                            
                            if file_bytes:
                                # 2. Extract Text
                                from utils.file_parser import extract_text_from_file
                                import io
                                text = extract_text_from_file(io.BytesIO(file_bytes), selected_file['name'])

                        # Análisis automático con JuanMita
                        if st.button("🔍 Analizar riesgos con JuanMita"):
                            with st.spinner("JuanMita analizando el contrato..."):
                                analysis = st.session_state.chatbot.ask_question(
                                    f"Analiza los riesgos, obligaciones principales, partes y fechas clave del contrato '{up.name}'. "
                                    "Usa el sistema de semáforo para clasificar los riesgos.",
                                    filter_metadata={"source": up.name}
                                )
                            st.markdown("### 📋 Análisis de Riesgos")
                            st.markdown(analysis)
                    else:
                        st.info("Ingresa un nombre arriba para buscar documentos en la biblioteca de Unergy.")


            # --- TAB 2: Editor de borrador (Feature 4) ---
            with tab_editor:
                if not st.session_state.doc_versions:
                    st.info("Carga un contrato en la pestaña '📤 Cargar Contrato' para empezar a editar.")
                else:
                    doc_sel = st.selectbox(
                        "Selecciona documento a editar",
                        list(st.session_state.doc_versions.keys()),
                        key="doc_sel_editor"
                    )
                    ver = st.session_state.doc_versions[doc_sel]

                    col_orig, col_draft = st.columns(2)
                    with col_orig:
                        st.markdown("#### 🔒 Original (solo lectura)")
                        st.text_area(
                            "original",
                            value=ver["original"][:3000],
                            height=400,
                            disabled=True,
                            label_visibility="collapsed"
                        )

                    with col_draft:
                        st.markdown("#### ✏️ Borrador de trabajo")
                        new_draft = st.text_area(
                            "draft",
                            value=ver["draft"],
                            height=400,
                            key=f"draft_{doc_sel}",
                            label_visibility="collapsed"
                        )

                    col_save, col_reset, col_export = st.columns(3)
                    with col_save:
                        if st.button("💾 Guardar versión"):
                            # Feature 4: push a historial antes de sobreescribir
                            import datetime
                            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                            st.session_state.doc_versions[doc_sel]["history"].append({
                                "timestamp": timestamp,
                                "content": ver["draft"]
                            })
                            st.session_state.doc_versions[doc_sel]["draft"] = new_draft
                            st.success(f"✅ Versión guardada ({timestamp})")
                            st.rerun()

                    with col_reset:
                        if st.button("↩️ Restaurar original"):
                            st.session_state.doc_versions[doc_sel]["draft"] = ver["original"]
                            st.success("Borrador restaurado al original.")
                            st.rerun()

                    with col_export:
                        st.download_button(
                            "⬇️ Exportar borrador",
                            data=new_draft.encode("utf-8"),
                            file_name=f"BORRADOR_{doc_sel.replace('.docx','').replace('.pdf','')}.txt",
                            mime="text/plain"
                        )

                    # Preguntar sobre diferencias
                    if st.button("🤖 JuanMita: ¿qué cambié?"):
                        orig_words = set(ver["original"].split())
                        draft_words = set(new_draft.split())
                        added = draft_words - orig_words
                        removed = orig_words - draft_words
                        diff_context = f"Palabras añadidas: {', '.join(list(added)[:50])}\nPalabras eliminadas: {', '.join(list(removed)[:50])}"
                        with st.spinner("Analizando cambios..."):
                            analysis = st.session_state.chatbot.ask_question(
                                f"Evalúa las siguientes modificaciones realizadas al contrato '{doc_sel}' "
                                f"e indica si representan riesgos legales.\n{diff_context}"
                            )
                        st.markdown("#### 🔎 Análisis de cambios")
                        st.markdown(analysis)

            # --- TAB 3: Historial de versiones (Feature 4) ---
            with tab_versions:
                if not any(v["history"] for v in st.session_state.doc_versions.values()):
                    st.info("No hay versiones guardadas aún. Edita un documento y guarda versiones.")
                else:
                    for doc_name, ver in st.session_state.doc_versions.items():
                        if ver["history"]:
                            st.markdown(f"#### 📄 {doc_name}")
                            for i, snap in enumerate(reversed(ver["history"])):
                                with st.expander(f"🕐 Versión {len(ver['history'])-i} — {snap['timestamp']}"):
                                    st.text(snap['content'][:1000] + ("..." if len(snap['content']) > 1000 else ""))
                                    if st.button(f"↩️ Restaurar esta versión", key=f"restore_{doc_name}_{i}"):
                                        st.session_state.doc_versions[doc_name]["draft"] = snap["content"]
                                        st.success("Borrador restaurado a esta versión.")
                                        st.rerun()

        # ============================================================
        # 🧠 CHATBOT
        # ============================================================
        elif nav_opt == "🧠 Chatbot":
            st.header("🧠 JuanMita — Agente de Contratos")

            stats = st.session_state.chatbot.get_stats()
            if stats['total_docs'] > 0:
                st.success(f"✅ JuanMita tiene contexto de **{stats['total_docs']} contrato(s)** — {', '.join(stats['sources'][:3])}{'…' if len(stats['sources']) > 3 else ''}")
            else:
                st.warning("⚠️ JuanMita no tiene contratos indexados aún. Haz clic en **🔄 Indexar todos los contratos del Drive** en la página de Inicio, o carga documentos en ⚖️ Análisis Legal.")

            if 'chat_history' not in st.session_state:
                st.session_state.chat_history = []

            # Botón para limpiar historial
            if st.session_state.chat_history:
                if st.button("🗑️ Limpiar conversación", key="clear_chat"):
                    st.session_state.chat_history = []
                    st.rerun()

            for m in st.session_state.chat_history:
                avatar = "🤖" if m['role'] == "assistant" else None
                with st.chat_message(m['role'], avatar=avatar):
                    st.markdown(m['content'])

            prompt = st.chat_input("Pregunta sobre los contratos indexados...")
            if prompt:
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                with st.chat_message("assistant", avatar="🤖"):
                    with st.spinner("JuanMita analizando contratos..."):
                        # Pasar historial para respuestas relacionadas
                        history_for_llm = st.session_state.chat_history[:-1]
                        res = st.session_state.chatbot.ask_question(prompt, chat_history=history_for_llm)
                    st.markdown(res)
                st.session_state.chat_history.append({"role": "assistant", "content": res})

        # ============================================================
        # ⚙️ AJUSTES
        # ============================================================
        elif nav_opt == "⚙️ Ajustes":
            st.markdown('<p class="pactora-header" style="font-size:36px;">⚙️ Configuración</p>', unsafe_allow_html=True)
            st.markdown("---")

            col_gemini, col_drive = st.columns(2)

            with col_gemini:
                st.markdown("""
                <div style="background:white; border-radius:16px; padding:24px;
                     box-shadow:0 4px 20px rgba(145,91,216,0.08);
                     border:1px solid rgba(145,91,216,0.15); min-height:200px;">
                    <h3 style="color:#2C2039; margin-top:0; border-left:4px solid #915BD8; padding-left:10px;">
                        🤖 Gemini API
                    </h3>
                </div>""", unsafe_allow_html=True)
                k = st.text_input(
                    "API Key",
                    value=st.session_state.gemini_api_key,
                    type="password",
                    label_visibility="collapsed",
                    placeholder="Ingresa tu Gemini API Key…"
                )
                if st.button("Guardar Key"):
                    st.session_state.gemini_api_key = k
                    st.session_state.chatbot = RAGChatbot(api_key=k)
                    st.success("✅ API Key guardada y chatbot reiniciado.")
                    st.rerun()

            with col_drive:
                st.markdown("""
                <div style="background:white; border-radius:16px; padding:24px;
                     box-shadow:0 4px 20px rgba(145,91,216,0.08);
                     border:1px solid rgba(145,91,216,0.15); min-height:200px;">
                    <h3 style="color:#2C2039; margin-top:0; border-left:4px solid #915BD8; padding-left:10px;">
                        ☁️ Conexión Drive
                    </h3>
                </div>""", unsafe_allow_html=True)
                folder_id_input = st.text_input(
                    "ID carpeta",
                    value=st.session_state.get('drive_root_id', "1sF8_SuiiFdiWq_9htA-cNZP1Gp0djc4N"),
                    label_visibility="collapsed",
                    placeholder="ID de carpeta raíz de Drive…"
                )
                drive_key_input = st.text_input(
                    "Drive API Key",
                    value=st.session_state.get('drive_api_key', ''),
                    type="password",
                    label_visibility="collapsed",
                    placeholder="API Key o credencial de servicio…"
                )
                if st.button("Conectar Drive"):
                    if folder_id_input:
                        st.session_state.drive_root_id = folder_id_input
                        st.session_state.drive_api_key = drive_key_input or "DEMO_KEY"
                        st.session_state.current_folder_id = folder_id_input
                        st.session_state.folder_history = [(folder_id_input, "Raíz Pactora")]
                        st.session_state.drive_root_name = "Raíz Pactora"
                        st.session_state.mock_items = [
                            {'id': 'doc1', 'name': 'Contrato_Suno_Solar_v1.docx',
                             'mimeType': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'},
                            {'id': 'doc2', 'name': 'EPC_Pactora_Final.docx',
                             'mimeType': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'},
                            {'id': 'fold1', 'name': 'Anexos_Legales',
                             'mimeType': 'application/vnd.google-apps.folder'}
                        ]
                        st.success("✅ Drive conectado.")
                        st.rerun()
                    else:
                        st.error("Ingresa un ID de carpeta.")

            st.markdown("---")

            with st.expander("🧠 Indexar Workspace Completo desde Drive"):
                st.caption("Descarga y vectoriza todos los PDF/DOCX de la carpeta raíz conectada.")
                if st.button("Iniciar indexación"):
                    if 'drive_root_id' not in st.session_state:
                        st.error("Conecta Drive primero.")
                    else:
                        with st.spinner("Indexando workspace..."):
                            from utils.drive_manager import get_recursive_files, download_file_to_io
                            from utils.file_parser import extract_text_from_file
                            all_f = get_recursive_files(
                                st.session_state.drive_root_id,
                                api_key=st.session_state.drive_api_key
                            )
                            ingest = []
                            for f in all_f:
                                io_f = download_file_to_io(f['id'], api_key=st.session_state.drive_api_key)
                                if io_f:
                                    txt = extract_text_from_file(io_f, f['name'])
                                    ingest.append((txt, f['name'], {
                                        "file_id": f['id'],
                                        "folder_id": f.get('parents', [''])[0]
                                    }))
                            if ingest:
                                ok, msg = st.session_state.chatbot.vector_ingest_multiple(ingest)
                                if ok:
                                    st.success(msg)
                                else:
                                    st.error(msg)
                            else:
                                st.warning("No se encontraron archivos PDF/DOCX en la carpeta.")

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚪 Cerrar Sesión Pactora"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

    # --- Panel lateral ---
    if col_side:
        render_side_chat_panel(col_side)


if __name__ == "__main__":
    main()
