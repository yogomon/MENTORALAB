import streamlit as st
import psycopg2
import psycopg2.extras
import os
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# --- FUNCIÓN PARA LA CONEXIÓN A LA BASE DE DATOS (PostgreSQL) ---
def conectar_db():
    """
    ÚNICA función para conectarse a la BD PostgreSQL.
    Funciona en la nube (st.secrets) y en local (os.environ).
    """
    try:
        # Intenta usar los secretos de Streamlit (para la nube)
        conn = psycopg2.connect(
            st.secrets["db_connection_uri"],
            cursor_factory=psycopg2.extras.DictCursor
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
                cursor_factory=psycopg2.extras.DictCursor
            )
            logger.info("Conexión a la BD local establecida con éxito.")
            return conn
        except Exception as e_local:
            logger.critical(f"Error fatal al conectar a la BD localmente: {e_local}")
            st.error("No se pudo conectar a la base de datos local.")
            return None

# --- FUNCIÓN PARA LA CONEXIÓN A SUPABASE STORAGE ---
def get_supabase_client():
    """
    ÚNICA función para inicializar el cliente de Supabase.
    Funciona en la nube (st.secrets) y en local (os.environ).
    """
    supabase_url = None
    supabase_key = None
    try:
        # Intenta usar los secretos de Streamlit (para la nube)
        supabase_url = st.secrets["supabase_url"]
        supabase_key = st.secrets["supabase_key"]
        logger.info("Cliente de Supabase configurado con st.secrets.")
    except Exception:
        logger.warning("No se pudo configurar Supabase con st.secrets. Intentando con variables de entorno locales...")
        # Si falla, usa las variables de entorno (para desarrollo local)
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        logger.info("Cliente de Supabase configurado con variables de entorno.")

    if supabase_url and supabase_key:
        try:
            return create_client(supabase_url, supabase_key)
        except Exception as e:
            logger.critical(f"Error fatal al inicializar el cliente de Supabase: {e}")
            st.error("Error al inicializar el cliente de Supabase.")
            return None
    else:
        logger.critical("Faltan las claves 'supabase_url' o 'supabase_key' en la configuración.")
        st.error("Error de configuración: Faltan las claves de Supabase.")
        return None
            return conn
        except Exception as e_local:
            logger.critical(f"Error fatal al conectar a la BD: {e_local}")
            return None
