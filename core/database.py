#database.py
import streamlit as st
import psycopg2
import psycopg2.extras  # <-- IMPORTANTE: Añadir esta importación
import os
import logging

logger = logging.getLogger(__name__)

def conectar_db():
    """
    ÚNICA función para conectarse a la BD.
    Funciona en la nube (st.secrets) y en local (os.environ).
    Ahora incluye DictCursor para devolver diccionarios.
    """
    try:
        # Intenta usar los secretos de Streamlit (para la nube)
        conn = psycopg2.connect(
            st.secrets["db_connection_uri"],
            cursor_factory=psycopg2.extras.DictCursor  # <-- AÑADIDO AQUÍ
        )
        logger.info("Conexión a la BD en la nube establecida con éxito.")
        return conn
    except Exception:
        logger.warning("No se pudo conectar con st.secrets. Intentando con variables de entorno locales...")
        try:
            # Si falla, usa las variables de entorno (para desarrollo local)
            conn = psycopg2.connect(
                host=os.environ.get('DB_HOST'),
                port=os.environ.get('DB_PORT'),
                dbname=os.environ.get('DB_NAME'),
                user=os.environ.get('DB_USER'),
                password=os.environ.get('DB_PASSWORD'),
                cursor_factory=psycopg2.extras.DictCursor  # <-- Y AÑADIDO AQUÍ
            )
            logger.info("Conexión a la BD local establecida con éxito.")
            return conn
        except Exception as e_local:
            logger.critical(f"Error fatal al conectar a la BD: {e_local}")
            return None