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

# --- FUNCIÓN DE DIÁLOGO PARA MOSTRAR PDF ---
@st.dialog(" ")
def mostrar_dialogo_pdf(pdf_url, title):
    """
    Muestra un archivo PDF desde una URL pública en un diálogo modal.
    Usa un iframe para una visualización más eficiente.
    """
    st.markdown("""
        <style>
            [data-testid="stDialog"] button[aria-label="Close"] { display: none; }
        </style>
    """, unsafe_allow_html=True)
    
    st.components.v1.iframe(pdf_url, height=800, scrolling=True)

    if st.button("Cerrar", key=f"close_dialog_{title}", use_container_width=True):
        if "pdf_a_mostrar" in st.session_state:
            del st.session_state["pdf_a_mostrar"]
        st.rerun()

# --- FUNCIÓN PRINCIPAL DE LA PÁGINA ---
def display_manuales_page():
    """Crea la interfaz para la página de la biblioteca usando Supabase Storage."""
    st.header("Consulta los Manuales")
    st.markdown("")
    
    # --- MODIFICACIÓN: Nombres de los buckets en Supabase ---
    bucket_map = {
        "preguntas": "Preguntas", # El botón "Manual de Preguntas" apunta al bucket "Preguntas"
        "manual": "Manual"      # El botón "Manual General" apunta al bucket "Manual"
    }

    col1, col2 = st.columns(2)
    with col1:
        is_preguntas_selected = (st.session_state.get("manual_view") == "preguntas")
        if st.button("Manual de Preguntas", use_container_width=True, type="primary" if is_preguntas_selected else "secondary"):
            st.session_state.manual_view = "preguntas"
            if "pdf_a_mostrar" in st.session_state: del st.session_state.pdf_a_mostrar
            st.rerun()
    
    with col2:
        is_manual_selected = (st.session_state.get("manual_view") == "manual")
        if st.button("Manual General", use_container_width=True, type="primary" if is_manual_selected else "secondary"):
            st.session_state.manual_view = "manual"
            if "pdf_a_mostrar" in st.session_state: del st.session_state.pdf_a_mostrar
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
                    # Generamos la URL pública del archivo en el bucket correspondiente
                    public_url = supabase.storage.from_(bucket_to_scan).get_public_url(filename)
                    st.session_state.pdf_a_mostrar = {"url": public_url, "title": chapter_title}
                    st.rerun()

    # --- Lógica para abrir el diálogo del visor de PDF ---
    if st.session_state.get("pdf_a_mostrar"):
        pdf_info = st.session_state.pdf_a_mostrar
        mostrar_dialogo_pdf(pdf_info["url"], pdf_info["title"])



