import streamlit as st
import os
import logging
from supabase import create_client, Client

# Configurar un logger para esta página
logger = logging.getLogger(__name__)

# --- INICIO: Conexión al cliente de Supabase ---
try:
    supabase_url = st.secrets["supabase_url"]
    supabase_key = st.secrets["supabase_key"]
    supabase: Client = create_client(supabase_url, supabase_key)
except Exception as e:
    st.error("Error al conectar con Supabase Storage. Asegúrate de que las claves 'supabase_url' y 'supabase_key' están en tus secretos.")
    st.stop()

# --- FUNCIÓN AUXILIAR PARA OBTENER LOS ARCHIVOS DESDE SUPABASE ---
@st.cache_data(show_spinner="Cargando lista de manuales...", ttl=300)
def get_files_from_supabase(bucket_name: str):
    """Obtiene una lista de archivos de un bucket de Supabase."""
    try:
        response = supabase.storage.from_(bucket_name).list()
        pdf_files = [file['name'] for file in response if file['name'].lower().endswith('.pdf')]
        return sorted(pdf_files)
    except Exception as e:
        logger.error(f"Error al listar archivos del bucket '{bucket_name}': {e}")
        st.error(f"No se pudo cargar la lista de archivos del bucket '{bucket_name}'.")
        return []

# --- MODIFICACIÓN: Visor de PDF que renderiza en Canvas para evitar copia ---
def display_pdf_viewer(pdf_url, title):
    """
    Muestra un archivo PDF desde una URL renderizando cada página en un canvas
    para evitar la selección y copia de texto.
    """
    #st.header(title)
    
    if st.button("⬅️ Volver", key=f"back_btn_{title}"):
        del st.session_state["pdf_a_mostrar"]
        st.rerun()

    # Este HTML ahora usa JavaScript para buscar el PDF en la URL y dibujarlo
    html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.11.338/pdf.min.js"></script>
            <style>
                body {{ margin: 0; padding: 0; background-color: #f0f2f6; }}
                #pdf-container {{ display: flex; flex-direction: column; align-items: center; gap: 1rem; padding: 1rem; }}
                canvas {{ border: 1px solid #ccc; box-shadow: 0 4px 8px rgba(0,0,0,0.1); max-width: 100%; height: auto; }}
            </style>
        </head>
        <body>
            <div id="pdf-container"></div>
            <script>
                const pdfUrl = '{pdf_url}';
                const pdfjsLib = window['pdfjs-dist/build/pdf'];
                pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.11.338/pdf.worker.min.js';

                const loadingTask = pdfjsLib.getDocument(pdfUrl);
                loadingTask.promise.then(function(pdf) {{
                    const container = document.getElementById('pdf-container');
                    for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {{
                        pdf.getPage(pageNum).then(function(page) {{
                            const scale = 1.5;
                            const viewport = page.getViewport({{scale: scale}});
                            const canvas = document.createElement('canvas');
                            const context = canvas.getContext('2d');
                            canvas.height = viewport.height;
                            canvas.width = viewport.width;
                            container.appendChild(canvas);
                            const renderContext = {{ canvasContext: context, viewport: viewport }};
                            page.render(renderContext);
                        }});
                    }}
                }});
            </script>
        </body>
        </html>
    '''
    st.components.v1.html(html_content, height=800, scrolling=True)

# --- FUNCIÓN PRINCIPAL DE LA PÁGINA ---
def display_manuales_page():
    """Crea la interfaz para la página de la biblioteca usando Supabase Storage."""
    
    if st.session_state.get("pdf_a_mostrar"):
        pdf_info = st.session_state.pdf_a_mostrar
        display_pdf_viewer(pdf_info["url"], pdf_info["title"])
    else:
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

                        public_url = supabase.storage.from_(bucket_to_scan).get_public_url(filename)
                        st.session_state.pdf_a_mostrar = {"url": public_url, "title": chapter_title}
                        st.rerun()
