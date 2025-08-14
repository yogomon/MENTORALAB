import streamlit as st
import os
import logging
from supabase import create_client, Client

# Configurar un logger para esta página
logger = logging.getLogger(__name__)

# --- INICIO: Conexión al cliente de Supabase ---
# Este bloque se conecta a Supabase usando las claves guardadas en los secretos de Streamlit.
try:
    supabase_url = st.secrets["supabase_url"]
    supabase_key = st.secrets["supabase_key"]
    supabase: Client = create_client(supabase_url, supabase_key)
except Exception as e:
    st.error("Error al conectar con Supabase Storage. Asegúrate de que las claves 'supabase_url' y 'supabase_key' están en tus secretos.")
    # Detenemos la ejecución si no podemos conectar, ya que la página no puede funcionar.
    st.stop()

# --- FUNCIÓN AUXILIAR PARA OBTENER LOS ARCHIVOS DESDE SUPABASE ---
@st.cache_data(show_spinner="Cargando lista de manuales...", ttl=300) # Cache por 5 minutos
def get_files_from_supabase(bucket_name: str):
    """Obtiene una lista de archivos de un bucket de Supabase."""
    try:
        response = supabase.storage.from_(bucket_name).list()
        # Filtramos para asegurarnos de que solo procesamos archivos PDF
        pdf_files = [file['name'] for file in response if file['name'].lower().endswith('.pdf')]
        return sorted(pdf_files)
    except Exception as e:
        logger.error(f"Error al listar archivos del bucket '{bucket_name}': {e}")
        st.error(f"No se pudo cargar la lista de archivos del bucket '{bucket_name}'.")
        return []

# --- MODIFICACIÓN: La función ya no es un diálogo, sino un visor integrado ---
def display_pdf_viewer(pdf_url, title):
    """
    Muestra un archivo PDF desde una URL pública directamente en la página.
    """
    st.header(title)
    
    # Botón para volver a la lista de manuales
    if st.button("⬅️ Volver a la lista", key=f"back_btn_{title}"):
        del st.session_state["pdf_a_mostrar"]
        st.rerun()

    st.components.v1.iframe(pdf_url, height=800, scrolling=True)


# --- FUNCIÓN PRINCIPAL DE LA PÁGINA ---
def display_manuales_page():
    """Crea la interfaz para la página de la biblioteca usando Supabase Storage."""
    
    # --- MODIFICACIÓN: Lógica condicional para mostrar la lista o el visor ---
    if st.session_state.get("pdf_a_mostrar"):
        # Si hay un PDF seleccionado, muestra solo el visor
        pdf_info = st.session_state.pdf_a_mostrar
        display_pdf_viewer(pdf_info["url"], pdf_info["title"])
    else:
        # Si no hay ningún PDF seleccionado, muestra la página de selección
        st.header("Consulta los Manuales")
        st.markdown("")
        
        bucket_map = {
            "preguntas": "Preguntas",
            "manual": "Manual"
        }

        col1, col2 = st.columns(2)
        with col1:
            is_preguntas_selected = (st.session_state.get("manual_view") == "preguntas")
            if st.button("Manual de Preguntas", use_container_width=True, type="primary" if is_preguntas_selected else "secondary"):
                st.session_state.manual_view = "preguntas"
                st.rerun()
        
        with col2:
            is_manual_selected = (st.session_state.get("manual_view") == "manual")
            if st.button("Manual General", use_container_width=True, type="primary" if is_manual_selected else "secondary"):
                st.session_state.manual_view = "manual"
                st.rerun()

        st.markdown("")

        selected_view = st.session_state.get("manual_view")
        if selected_view:
            bucket_to_scan = bucket_map.get(selected_view)
            manual_files = get_files_from_supabase(bucket_to_scan)

            if not manual_files:
                st.info(f"No se encontraron manuales en esta categoría.")
            else:
                for filename in manual_files:
                    chapter_title = os.path.splitext(filename)[0]
                    if st.button(chapter_title, key=f"btn_manual_{filename}", use_container_width=True):
                        public_url = supabase.storage.from_(bucket_to_scan).get_public_url(filename)
                        st.session_state.pdf_a_mostrar = {"url": public_url, "title": chapter_title}
                        st.rerun()
