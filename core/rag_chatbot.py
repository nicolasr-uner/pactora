import os
import google.generativeai as genai
from langchain_core.embeddings import Embeddings as BaseEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from typing import List, Dict, Tuple, Optional, Any

LEGAL_SYSTEM_PROMPT = """Eres JuanMitaBot, agente legal y técnico especializada en contratos de energía de Unergy/Pactora.
Tienes acceso completo a todos los contratos indexados del Drive corporativo.

REGLAS ESTRICTAS:
1. Basa tus respuestas EXCLUSIVAMENTE en el contenido de los contratos indexados en el CONTEXTO.
2. Si la información NO está en el contexto, responde: "No encontré esa información en los contratos indexados."
3. Nunca inventes cláusulas, fechas, montos ni partes contractuales.
4. Cuando identifiques riesgos contractuales, usa el sistema de semáforo:
   - ROJO: Incumplimiento regulatorio CREG o riesgo legal alto
   - AMARILLO: Desviación frente al estándar comercial (>10%) o ambigüedad
   - VERDE: Cláusula estándar, sin riesgos detectados
5. Estructura tus respuestas con secciones claras cuando analices contratos.
6. Cita siempre el nombre del documento entre corchetes, ej: [Contrato_AMC.pdf].
7. Si el usuario hace referencia a mensajes anteriores, mantén coherencia con las respuestas previas.

CONTEXTO DE CONTRATOS INDEXADOS:
{context}"""


class _GeminiEmbeddings(BaseEmbeddings):
    """Embeddings via REST API v1 — compatible con text-embedding-004."""

    def __init__(self, api_key: str, model: str = "models/text-embedding-004"):
        self._api_key = api_key
        self._model = model
        self._model_id = model.split("/")[-1]

    def _batch_embed(self, texts: List[str], task_type: str) -> List[List[float]]:
        import requests as _req
        url = (
            f"https://generativelanguage.googleapis.com/v1/models/"
            f"{self._model_id}:batchEmbedContents?key={self._api_key}"
        )
        body = {
            "requests": [
                {
                    "model": self._model,
                    "content": {"parts": [{"text": t}]},
                    "taskType": task_type,
                }
                for t in texts
            ]
        }
        resp = _req.post(url, json=body, timeout=60)
        resp.raise_for_status()
        return [e["values"] for e in resp.json()["embeddings"]]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        BATCH = 100
        result = []
        for i in range(0, len(texts), BATCH):
            result.extend(self._batch_embed(texts[i: i + BATCH], "RETRIEVAL_DOCUMENT"))
        return result

    def embed_query(self, text: str) -> List[float]:
        return self._batch_embed([text], "RETRIEVAL_QUERY")[0]


class RAGChatbot:
    def __init__(self, persist_directory: str = "./chroma_db", api_key: Optional[str] = None):
        self.persist_directory = persist_directory
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self._indexed_sources: List[str] = []
        self.embeddings = None
        self.llm = None
        self.vectorstore: Any = None

        if self.api_key:
            self.embeddings = _GeminiEmbeddings(api_key=self.api_key)
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                google_api_key=self.api_key,
                temperature=0.1
            )
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
            return False, "API Key de Gemini no configurada."
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
            import logging
            logging.getLogger("pactora").error("[rag] vector_ingest_multiple fallo: %s", e, exc_info=True)
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
        if not self.llm:
            return "Gemini no esta inicializado. Configura tu API Key en Ajustes."

        context_text, sources = self._retrieve_context(question, filter_metadata)
        if sources and sources[0].startswith("ERROR:"):
            return f"Error al consultar vectorstore: {sources[0][6:]}"

        messages: List = [SystemMessage(content=LEGAL_SYSTEM_PROMPT.format(context=context_text))]
        if chat_history:
            for msg in chat_history[-8:]:
                if msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg.get("role") == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=question))

        try:
            response = self.llm.invoke(messages)
            answer = response.content
            if sources:
                answer += f"\n\n---\n*Fuentes consultadas: {', '.join(sources)}*"
            return answer
        except Exception as e:
            return f"Error al invocar Gemini: {e}"

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
