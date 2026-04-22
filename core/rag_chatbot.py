import os
import logging

# Deshabilitar telemetría de ChromaDB — debe ir antes de cualquier import de chromadb.
# app.py también lo setea al inicio, pero lo repetimos aquí como seguro extra.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY", "False")

from langchain_core.embeddings import Embeddings as BaseEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from typing import List, Dict, Tuple, Optional, Any

# Settings de ChromaDB sin telemetría — se pasan al cliente directamente
try:
    from chromadb.config import Settings as _ChromaSettings
    _CHROMA_SETTINGS = _ChromaSettings(anonymized_telemetry=False)
except Exception:
    _CHROMA_SETTINGS = None

_log = logging.getLogger("pactora")


class _LocalEmbeddings(BaseEmbeddings):
    """
    Embeddings locales via ChromaDB DefaultEmbeddingFunction (onnxruntime).
    Usa all-MiniLM-L6-v2 sin necesitar PyTorch — ya viene con chromadb.
    """

    def __init__(self):
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        self._fn = DefaultEmbeddingFunction()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        return [[float(x) for x in v] for v in self._fn(texts)]

    def embed_query(self, text: str) -> List[float]:
        return [float(x) for x in self._fn([text])[0]]


class RAGChatbot:
    def __init__(self, persist_directory: str = "./chroma_db", api_key: Optional[str] = None):
        self.persist_directory = persist_directory
        # api_key reservado para uso futuro (Gemini LLM)
        self.api_key = api_key
        self._indexed_sources: List[str] = []
        self.llm = None

        try:
            self.embeddings = _LocalEmbeddings()
        except Exception as e:
            _log.error("[rag] No se pudo cargar embeddings locales: %s", e)
            self.embeddings = None

        self.vectorstore: Any = None
        if self.embeddings:
            self._initialize_vectorstore()

    def _initialize_vectorstore(self):
        if self.embeddings and os.path.exists(self.persist_directory):
            try:
                kwargs = dict(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embeddings,
                )
                if _CHROMA_SETTINGS is not None:
                    kwargs["client_settings"] = _CHROMA_SETTINGS
                self.vectorstore = Chroma(**kwargs)
                try:
                    all_docs = self.vectorstore.get(include=["metadatas"])
                    sources = {m.get("source", "") for m in all_docs.get("metadatas", []) if m}
                    self._indexed_sources = sorted([s for s in sources if s])
                except Exception:
                    self._indexed_sources = []
            except Exception:
                self.vectorstore = None

    def vector_ingest_multiple(self, documents_list: List[Tuple], metadata_global: Optional[Dict[str, Any]] = None):
        """Indexa lista de (text, filename, metadata). Retorna (ok, mensaje)."""
        if not self.embeddings:
            return False, "sentence-transformers no disponible."
        try:
            all_splits = []
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=300)
            for doc_data in documents_list:
                text_content = doc_data[0]
                filename = doc_data[1]
                meta = doc_data[2] if len(doc_data) > 2 else {}
                if not text_content or not text_content.strip():
                    continue
                clean_meta = dict(meta) if isinstance(meta, dict) else {}
                if metadata_global:
                    clean_meta.update(metadata_global)
                clean_meta["source"] = filename
                splits = text_splitter.create_documents([text_content], metadatas=[clean_meta])
                all_splits.extend(splits)
                if filename not in self._indexed_sources:
                    self._indexed_sources.append(filename)
            if not all_splits:
                return False, "No se extrajo texto valido de los documentos."
            if self.vectorstore is None:
                from_kwargs = dict(
                    documents=all_splits,
                    embedding=self.embeddings,
                    persist_directory=self.persist_directory,
                )
                if _CHROMA_SETTINGS is not None:
                    from_kwargs["client_settings"] = _CHROMA_SETTINGS
                self.vectorstore = Chroma.from_documents(**from_kwargs)
            else:
                self.vectorstore.add_documents(all_splits)
            return True, f"{len(documents_list)} documento(s) indexado(s) correctamente."
        except Exception as e:
            _log.error("[rag] vector_ingest_multiple fallo: %s", e, exc_info=True)
            return False, f"Error al indexar: {e}"

    def vector_ingest(self, text_content: str, filename: str = "doc", metadata: Optional[Dict[str, Any]] = None):
        return self.vector_ingest_multiple([(text_content, filename, metadata or {})])

    def _retrieve_context(self, question: str, filter_metadata: Optional[Dict[str, Any]] = None) -> Tuple[str, List[str]]:
        context_text = ""
        sources: List[str] = []
        if self.vectorstore is None:
            return context_text, sources
        try:
            search_kwargs: Dict[str, Any] = {"k": 10}
            if filter_metadata:
                search_kwargs["filter"] = filter_metadata
            docs = self.vectorstore.similarity_search(question, **search_kwargs)
            if docs:
                parts = []
                for d in docs:
                    src = d.metadata.get("source", "Documento")
                    parts.append(f"[Fuente: {src}]\n{d.page_content}")
                    if src not in sources:
                        sources.append(src)
                context_text = "\n\n---\n\n".join(parts)
        except Exception as e:
            return "", [f"ERROR:{e}"]
        return context_text, sources

    def ask_question(
        self,
        question: str,
        filter_metadata: Optional[Dict[str, Any]] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Responde preguntas sobre contratos indexados.

        Modo LLM (cuando llm_service.LLM_AVAILABLE es True):
            Recupera fragmentos relevantes, construye prompt con system message +
            contexto + historial y llama a llm_service.generate_response() para
            obtener una respuesta en lenguaje natural generada por Gemini.

        Modo búsqueda semántica (fallback, modo actual):
            Retorna los fragmentos relevantes formateados directamente, sin
            generación LLM.  Es el comportamiento activo mientras no haya API key.

        Para activar el modo LLM basta con configurar GEMINI_API_KEY en el entorno
        o en .streamlit/secrets.toml — no se requiere ningún otro cambio de código.
        """
        if self.vectorstore is None:
            return "No hay contratos indexados. Ve a **Ajustes** y sube documentos para comenzar."

        context_text, sources = self._retrieve_context(question, filter_metadata)

        if not context_text:
            return "No encontré información relacionada en los contratos indexados."

        if sources and sources[0].startswith("ERROR:"):
            return f"Error al consultar la base de datos: {sources[0][6:]}"

        # --- Modo LLM (Gemini activo) ---
        try:
            from core.llm_service import LLM_AVAILABLE, generate_response
            if LLM_AVAILABLE:
                llm_answer = generate_response(
                    question=question,
                    context=context_text,
                    history=chat_history,
                )
                if llm_answer:
                    if sources:
                        llm_answer += f"\n\n---\n*Fuentes consultadas: {', '.join(sources)}*"
                    return llm_answer
        except Exception as e:
            _log.warning("[rag] generate_response falló, usando modo búsqueda: %s", e)

        # --- Modo búsqueda semántica (fallback) ---
        response = "**Fragmentos relevantes encontrados:**\n\n" + context_text
        if sources:
            response += f"\n\n---\n*Fuentes: {', '.join(sources)}*"
        return response

    def ask_question_stream(
        self,
        question: str,
        filter_metadata: Optional[Dict[str, Any]] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[Any, List[str]]:
        """
        Como ask_question pero retorna (stream_generator, sources).

        stream_generator es un generador de chunks de texto para usar con
        st.write_stream() en Streamlit, que muestra la respuesta progresivamente.

        Si el streaming no está disponible (sin LLM o error), retorna un iterador
        de un solo elemento con la respuesta completa — el caller no necesita
        distinguir entre ambos casos.

        Returns:
            (generator, sources): sources es la lista de archivos consultados.
            Las fuentes NO están embebidas en el generator; el caller es responsable
            de mostrar el footer de fuentes después de consumir el generator.
        """
        if self.vectorstore is None:
            return iter(["No hay contratos indexados. Ve a **Ajustes** y sube documentos para comenzar."]), []

        context_text, sources = self._retrieve_context(question, filter_metadata)

        if not context_text:
            return iter(["No encontré información relacionada en los contratos indexados."]), []

        if sources and sources[0].startswith("ERROR:"):
            return iter([f"Error al consultar la base de datos: {sources[0][6:]}"]), []

        # --- Modo LLM streaming (Gemini activo) ---
        try:
            from core.llm_service import LLM_AVAILABLE, generate_response_stream
            if LLM_AVAILABLE:
                stream_gen = generate_response_stream(
                    question=question,
                    context=context_text,
                    history=chat_history,
                )
                if stream_gen is not None:
                    return stream_gen, sources
        except Exception as e:
            _log.warning("[rag] generate_response_stream falló, usando fallback: %s", e)

        # --- Fallback: modo búsqueda semántica (sin LLM) ---
        # Las fuentes se embeben en el texto ya que no hay footer separado en fallback
        response = "**Fragmentos relevantes encontrados:**\n\n" + context_text
        if sources:
            response += f"\n\n---\n*Fuentes: {', '.join(sources)}*"
        return iter([response]), []  # sources ya embebidas → lista vacía para evitar footer duplicado

    def get_stats(self) -> Dict[str, Any]:
        if self.vectorstore is None:
            return {"total_chunks": 0, "total_docs": 0, "sources": []}
        try:
            data = self.vectorstore.get(include=["metadatas"])
            metadatas = data.get("metadatas", [])
            sources = {m.get("source", "") for m in metadatas if m}
            return {
                "total_chunks": len(metadatas),
                "total_docs": len([s for s in sources if s]),
                "sources": sorted([s for s in sources if s])
            }
        except Exception:
            return {"total_chunks": 0, "total_docs": len(self._indexed_sources), "sources": self._indexed_sources}

    def get_contract_registry(self) -> List[Dict[str, Any]]:
        """
        Retorna un registro estructurado de todos los contratos indexados.
        Cada entrada contiene: source, contract_type, drive_id, indexed_at.
        Usa los metadatos almacenados en ChromaDB — un dict por documento único.
        """
        if self.vectorstore is None:
            return []
        try:
            data = self.vectorstore.get(include=["metadatas"])
            metadatas = data.get("metadatas", [])
            seen: Dict[str, Dict[str, Any]] = {}
            for m in metadatas:
                if not m:
                    continue
                src = m.get("source", "")
                if not src or src in seen:
                    continue
                seen[src] = {
                    "source": src,
                    "contract_type": m.get("contract_type", "General"),
                    "drive_id": m.get("drive_id", ""),
                    "indexed_at": m.get("indexed_at", ""),
                }
            return sorted(seen.values(), key=lambda x: x["source"])
        except Exception:
            return []
