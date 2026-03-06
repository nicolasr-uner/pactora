# core/rag_engine.py
import chromadb
import google.generativeai as genai
import streamlit as st
import uuid
import os

# Configuración del cliente Chroma local
chroma_client = chromadb.Client()
collection_name = "pactora_contracts"

def get_or_create_collection():
    try:
        return chroma_client.get_collection(name=collection_name)
    except:
        return chroma_client.create_collection(name=collection_name)

def vectorize_document(text_content):
    """
    Divide el documento en chunks y los vectoriza usando Gemini Embeddings
    en una colección de ChromaDB.
    """
    from core.gemini_engine import configure_gemini
    configure_gemini()
    
    collection = get_or_create_collection()
    
    # Simple chunking (e.g. 2000 chars)
    chunk_size = 2000
    chunks = [text_content[i:i+chunk_size] for i in range(0, len(text_content), chunk_size)]
    
    if not chunks:
        return False
        
    for chunk in chunks:
        # Generar embedding
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=chunk,
                task_type="retrieval_document"
            )
            embedding = result['embedding']
            
            # Guardar en ChromaDB
            collection.add(
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{"source": "contract"}],
                ids=[str(uuid.uuid4())]
            )
        except Exception as e:
            st.error(f"Error vectorizando chunk: {e}")
            return False
            
    return True

def query_rag(user_query):
    """
    Recupera el contexto de ChromaDB y usa Gemini 1.5 Pro para responder
    estrictamente basado en el documento y en la normativa CREG.
    """
    from core.gemini_engine import configure_gemini
    configure_gemini()
    
    collection = get_or_create_collection()
    
    # Embed the query
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=user_query,
            task_type="retrieval_query"
        )
        query_embedding = result['embedding']
        
        # Retrieve chunks
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3
        )
        
        context_docs = results['documents'][0] if results['documents'] else []
        context_text = "\n\n---\n\n".join(context_docs)
        
        # Prompt Gemini with context
        prompt = f"""
Eres Pactora, el Cerebro Sectorial Energético (Experto Legal y Técnico en Energía Solar).
Tu tarea es responder la pregunta del usuario utilizando ESTRICTAMENTE el contexto del contrato proporcionado a continuación.
Debes identificar si hay riesgos regulatorios relacionados con la normativa CREG o manual BMA. Si detectas riesgo de incumplimiento, clasifícalo como SEMÁFORO ROJO. Si hay desviaciones frente al estándar comercial (>10%), clasifícalo como SEMÁFORO AMARILLO. De lo contrario, SEMÁFORO VERDE.

Contexto extraído del contrato:
{context_text}

Pregunta del analista legal:
{user_query}

Responde de manera estructurada y profesional:
"""
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"Error en RAG: {e}"
