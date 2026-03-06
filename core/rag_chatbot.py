import os
import streamlit as st
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

class RAGChatbot:
    def __init__(self, persist_directory="./chroma_db"):
        self.persist_directory = persist_directory
        if GEMINI_API_KEY:
            self.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GEMINI_API_KEY)
            self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=GEMINI_API_KEY, temperature=0.2)
        else:
            self.embeddings = None
            self.llm = None
        
        self.vectorstore = None
        
    def vector_ingest(self, text_content: str):
        """
        Takes raw text from the contract, splits it, and saves it into ChromaDB.
        """
        if not self.embeddings:
            return False, "GEMINI_API_KEY no configurada."
            
        try:
            # We save temporary text file to use TextLoader
            temp_file = "temp_contract.txt"
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(text_content)
                
            loader = TextLoader(temp_file, encoding="utf-8")
            documents = loader.load()
            
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            splits = text_splitter.split_documents(documents)
            
            self.vectorstore = Chroma.from_documents(
                documents=splits, 
                embedding=self.embeddings,
                persist_directory=self.persist_directory
            )
            
            # Clean up
            os.remove(temp_file)
            return True, "El contrato ha sido vectorizado correctamente para consultas."
            
        except Exception as e:
            return False, str(e)
            
    def ask_question(self, question: str) -> str:
        """
        Queries the vector database strictly returning answers based on context.
        """
        if not self.vectorstore or not self.llm:
            return "El chatbot no ha sido inicializado o no hay un documento cargado."
            
        system_prompt = (
            "Eres un asistente legal experto en contratos de energía. "
            "Usa los siguientes fragmentos de contexto recuperado para responder la pregunta. "
            "Si no sabes la respuesta o no está en el documento, di que no lo sabes. "
            "Usa un tono profesional, preciso y legalmente responsable.\n\n"
            "{context}"
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
        ])
        
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})
        question_answer_chain = create_stuff_documents_chain(self.llm, prompt)
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)
        
        try:
            response = rag_chain.invoke({"input": question})
            return response["answer"]
        except Exception as e:
            return f"Error procesando la consulta RAG: {e}"
