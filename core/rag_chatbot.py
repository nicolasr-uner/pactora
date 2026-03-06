import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from typing import List, Dict, Tuple, Optional, Any

# System prompt especializado en contratos energéticos
LEGAL_SYSTEM_PROMPT = """Eres JuanMita, agente legal y técnico especializada en contratos de energía de Unergy/Pactora.
Tienes acceso completo a todos los contratos indexados del Drive corporativo.

REGLAS ESTRICTAS:
1. Basa tus respuestas EXCLUSIVAMENTE en el contenido de los contratos indexados en el CONTEXTO.
2. Si la información NO está en el contexto, responde: "No encontré esa información en los contratos indexados."
3. Nunca inventes cláusulas, fechas, montos ni partes contractuales.
4. Cuando identifiques riesgos contractuales, usa el sistema de semáforo:
   - 🔴 ROJO: Incumplimiento regulatorio CREG o riesgo legal alto
   - 🟡 AMARILLO: Desviación frente al estándar comercial (>10%) o ambigüedad
   - 🟢 VERDE: Cláusula estándar, sin riesgos detectados
5. Estructura tus respuestas con secciones claras cuando analices contratos.
6. Cita siempre el nombre del documento entre corchetes, ej: [Contrato_AMC.pdf].
7. Si el usuario hace referencia a mensajes anteriores, mantén coherencia con las respuestas previas.

CONTEXTO DE CONTRATOS INDEXADOS:
{context}"""

class RAGChatbot:
    def __init__(self, persist_directory: str = "./chroma_db", api_key: Optional[str] = None):
        self.persist_directory = persist_directory
        self.embeddings = None
        self.llm = None
        self.vectorstore = None
        # Lazy init: will be called when needed
        self._init_models()

    def _init_models(self):
        """Initialize embeddings and LLM using the current environment variable.
        Safe to call multiple times — skips if already initialized."""
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key and self.embeddings is None:
            try:
                self.embeddings = GoogleGenerativeAIEmbeddings(
                    model="models/embedding-001",
                    google_api_key=api_key
                )
                self.llm = ChatGoogleGenerativeAI(
                    model="gemini-1.5-pro",
                    google_api_key=api_key,
                    temperature=0.2
                )
            except Exception as e:
                print(f"RAGChatbot model init error: {e}")

    def vector_ingest_multiple(self, documents_list: list):
        """
        Indexa una lista de (text_content, filename, metadata) en ChromaDB persistente.
        Devuelve (ok: bool, mensaje: str).
        """
        # Always re-attempt init in case dotenv loaded after object was created
        self._init_models()
        
        if not self.embeddings:
            return False, "GEMINI_API_KEY no configurada o incorrecta. Verifica tu archivo .env."
            
        try:
            all_splits = []
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            
            for text_content, filename in documents_list:
                # We save temporary text file to use TextLoader
                safe_name = "".join(c for c in filename if c.isalnum() or c in "-_")[:50]
                temp_file = f"temp_{safe_name}.txt"
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(text_content)
                    
                loader = TextLoader(temp_file, encoding="utf-8")
                documents = loader.load()
                splits = text_splitter.split_documents(documents)
                all_splits.extend(splits)
                if filename not in self._indexed_sources:
                    self._indexed_sources.append(filename)

            if not all_splits:
                return False, "No se extrajo texto válido de los documentos."

            if self.vectorstore is None:
                self.vectorstore = Chroma.from_documents(
                    documents=all_splits,
                    embedding=self.embeddings,
                    persist_directory=self.persist_directory
                )
            else:
                self.vectorstore.add_documents(all_splits)

            return True, f"✅ {len(documents_list)} documento(s) indexado(s) correctamente."

            # Reiniciar vectorstore para el nuevo contexto
            if os.path.exists(self.persist_directory):
                import shutil
                shutil.rmtree(self.persist_directory)
                
            self.vectorstore = Chroma.from_documents(
                documents=all_splits, 
                embedding=self.embeddings,
                persist_directory=self.persist_directory
            )
            
            return True, f"Se han vectorizado {len(documents_list)} documentos con éxito ({len(all_splits)} fragmentos)."
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return False, str(e)

    def vector_ingest(self, text_content: str, filename: str = "doc", metadata: Optional[Dict[str, Any]] = None):
        return self.vector_ingest_multiple([(text_content, filename, metadata or {})])

    def _retrieve_context(self, question: str, filter_metadata: Optional[Dict[str, Any]] = None) -> Tuple[str, List[str]]:
        """Recupera fragmentos relevantes del vectorstore. Retorna (context_text, sources)."""
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
        Consulta el vectorstore y responde basándose en los contratos indexados.
        Acepta historial de conversación para respuestas relacionadas entre sí.
        """
        if not self.llm:
            return "⚠️ Gemini no está inicializado. Configura tu API Key en Ajustes."

        context_text, sources = self._retrieve_context(question, filter_metadata)
        if sources and sources[0].startswith("ERROR:"):
            return f"⚠️ Error al consultar vectorstore: {sources[0][6:]}"

        # Construir mensajes con historial para respuestas relacionadas
        messages: List = [SystemMessage(content=LEGAL_SYSTEM_PROMPT.format(context=context_text))]
        if chat_history:
            for msg in chat_history[-8:]:  # últimos 8 mensajes para contexto
                if msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg.get("role") == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=question))

        try:
            response = self.llm.invoke(messages)
            answer = response.content
            if sources:
                answer += f"\n\n---\n📎 *Fuentes consultadas: {', '.join(sources)}*"
            return answer
        except Exception as e:
            return f"⚠️ Error al invocar Gemini: {e}"

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas reales del vectorstore para métricas (Bug 3)."""
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
