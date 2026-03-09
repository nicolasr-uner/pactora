import os
import logging
from langchain_core.embeddings import Embeddings as BaseEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from typing import List, Dict, Tuple, Optional, Any

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
        return [list(v) for v in self._fn(texts)]

    def embed_query(self, text: str) -> List[float]:
        return list(self._fn([text])[0])


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
                self.vectorstore = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embeddings
                )
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
                self.vectorstore = Chroma.from_documents(
                    documents=all_splits,
                    embedding=self.embeddings,
                    persist_directory=self.persist_directory
                )
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
            search_kwargs: Dict[str, Any] = {"k": 6}
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
        Busca fragmentos relevantes en los contratos indexados y los retorna formateados.
        Modo busqueda semantica — sin LLM externo requerido.
        Cuando se configure Gemini/Groq, esta funcion generara respuestas con IA.
        """
        if self.vectorstore is None:
            return "No hay contratos indexados. Ve a **Ajustes** y sube documentos para comenzar."

        context_text, sources = self._retrieve_context(question, filter_metadata)

        if not context_text:
            return "No encontre informacion relacionada en los contratos indexados."

        if sources and sources[0].startswith("ERROR:"):
            return f"Error al consultar la base de datos: {sources[0][6:]}"

        response = "**Fragmentos relevantes encontrados:**\n\n" + context_text
        if sources:
            response += f"\n\n---\n*Fuentes: {', '.join(sources)}*"
        return response

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
