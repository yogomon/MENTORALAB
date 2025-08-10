# ==============================================================================
# SCRIPT PARA LA INTERFAZ DE CHAT RAG (GENERACIÓN AUMENTADA POR RECUPERACIÓN)
# MODIFICACIÓN: Refactorizado para un flujo de estado robusto y correcto.
# ==============================================================================
import streamlit as st
import psycopg2
import psycopg2.extras
import json
import logging
import os
from dotenv import load_dotenv
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI

# --- 1. Configuración y Parámetros ---
logger = logging.getLogger(__name__)
load_dotenv()
TOP_K_CHUNKS_FOR_RAG = 10

# --- Configuración de Clientes de API ---
try:
    openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    deepseek_client = OpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com/v1")
    logger.info("Clientes de OpenAI (embeddings) y DeepSeek (chat) configurados.")
except Exception as e:
    st.error(f"Error al configurar las APIs: {e}")
    st.stop()

# --- Prompt (Modificado para respuestas más detalladas) ---
PROMPT_RAG_CHAT = """
Eres un experto en Medicina de Laboratorio. Tu misión es responder a las preguntas del usuario de forma detallada y pedagógica, basándote ÚNICA Y EXCLUSIVAMENTE en el "Contexto del Manual" que se te proporciona.

Reglas estrictas:
1.  Cíñete al Contexto: Si la respuesta a la pregunta no se encuentra en el contexto, responde honestamente: "Lo siento, pero no he encontrado información sobre eso en el manual." No inventes información.
2.  Explica con Claridad: Responde de forma completa a la pregunta del usuario, explicando los conceptos clave y proporcionando el detalle necesario para una buena comprensión.


---
CONTEXTO DEL MANUAL:
{contexto_manual}
---
PREGUNTA DEL USUARIO:
{pregunta_usuario}
---
"""

# --- Funciones de BD y Lógica RAG ---
def get_db_connection():
    """Establece y devuelve una conexión a la base de datos PostgreSQL."""
    try:
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST'), port=os.environ.get('DB_PORT'),
            dbname=os.environ.get('DB_NAME'), user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            cursor_factory=psycopg2.extras.DictCursor
        )
        return conn
    except Exception as e:
        logger.error(f"No se pudo conectar a la base de datos en el chat RAG: {e}", exc_info=True)
        return None

def get_question_embedding(question_text):
    """Genera un embedding para la pregunta del usuario."""
    try:
        response = openai_client.embeddings.create(input=[question_text], model="text-embedding-3-small")
        return np.array(response.data[0].embedding)
    except Exception as e:
        logger.error(f"Error al generar embedding para la pregunta: {e}")
        return None

def find_relevant_chunks(conn, question_embedding, top_k):
    """Encuentra los chunks más relevantes en la base de datos."""
    if question_embedding is None:
        return ""
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT chunk_text, embedding FROM manual_chunks")
            all_chunks = cursor.fetchall()
        
        if not all_chunks:
            return ""

        chunk_vectors = np.array([json.loads(chunk['embedding']) for chunk in all_chunks])
        similarities = cosine_similarity(question_embedding.reshape(1, -1), chunk_vectors)[0]
        top_k_indices = np.argsort(similarities)[-top_k:][::-1]
        
        relevant_texts = [all_chunks[i]['chunk_text'] for i in top_k_indices]
        return "\n---\n".join(relevant_texts)
        
    except Exception as e:
        logger.error(f"Error al buscar chunks relevantes: {e}", exc_info=True)
        return ""

def stream_deepseek_response(question, context):
    """Llama a la API de DeepSeek y devuelve la respuesta en streaming."""
    prompt = PROMPT_RAG_CHAT.format(contexto_manual=context, pregunta_usuario=question)
    messages = [{"role": "user", "content": prompt}]
    
    try:
        response_stream = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=True,
            max_tokens=1024
        )
        for chunk in response_stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        logger.error(f"Error en la llamada a la API de chat de DeepSeek: {e}")
        yield "Lo siento, ha ocurrido un error al generar la respuesta."

# --- Función Principal de la Interfaz de Usuario ---
def display_rag_chat_section():
    """
    Muestra la interfaz completa del chat RAG con un flujo de estado robusto y correcto.
    """
    st.header("¿Tienes alguna duda?")
    st.markdown("Buscaremos la respuesta en el Manual de Medicina de Laboratorio")
    #st.markdown("¿Tienes alguna duda? Buscaré la respuesta en nuestro Manual.") 

    # --- INICIO DE LA CORRECCIÓN DEFINITIVA ---
    # Usamos los selectores exactos que nos has proporcionado para ocultar los avatares.
    st.markdown("""
        <style>
            div[data-testid="stChatMessageAvatarUser"],
            div[data-testid="stChatMessageAvatarAssistant"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)
    # --- FIN DE LA CORRECCIÓN ---
    
    if "rag_messages" not in st.session_state:
        st.session_state.rag_messages = []

    # 1. Mostrar todo el historial de mensajes
    for message in st.session_state.rag_messages:
        # Mantenemos avatar=None como buena práctica, aunque el CSS lo oculte
        with st.chat_message(message["role"], avatar=None):
            st.markdown(message["content"])

    # 2. Generar la respuesta del asistente si el último mensaje es del usuario
    if st.session_state.rag_messages and st.session_state.rag_messages[-1]["role"] == "user":
        last_prompt = st.session_state.rag_messages[-1]["content"]
        
        # Mantenemos avatar=None también aquí
        with st.chat_message("assistant", avatar=None):
            with st.spinner("Buscando en el Manual de Medicina de Laboratorio..."):
                conn = get_db_connection()
                if not conn:
                    full_response = "Error de conexión a la base de datos."
                    st.error(full_response)
                else:
                    question_embedding = get_question_embedding(last_prompt)
                    context = find_relevant_chunks(conn, question_embedding, TOP_K_CHUNKS_FOR_RAG)
                    conn.close()
                    
                    if not context:
                        full_response = "No he encontrado información relevante en el manual para tu pregunta."
                        st.markdown(full_response)
                    else:
                        response_generator = stream_deepseek_response(last_prompt, context)
                        full_response = st.write_stream(response_generator)
            
        # Añadir la respuesta completa del asistente al historial
        st.session_state.rag_messages.append({"role": "assistant", "content": full_response})
        # Recargar la página para "fijar" la respuesta y esperar la siguiente entrada del usuario
        st.rerun()

    # 3. Aceptar la entrada del usuario (siempre al final)
    if prompt := st.chat_input("Pregunta lo quieras"):
        # Añadir el mensaje del usuario al historial y recargar para iniciar el proceso de respuesta
        st.session_state.rag_messages.append({"role": "user", "content": prompt})
        st.rerun()