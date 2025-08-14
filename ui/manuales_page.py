import streamlit as st
import os
import base64
import logging
import glob

# Configurar un logger para esta página
logger = logging.getLogger(__name__)

# --- FUNCIONES AUXILIARES ---

@st.cache_data(show_spinner=False)
def get_manual_files(directory_path):
    """Escanea un directorio y devuelve una lista ordenada de archivos PDF."""
    try:
        if not os.path.isdir(directory_path):
            logger.warning(f"El directorio no existe: {directory_path}")
            return []
        
        files = [f for f in os.listdir(directory_path) if f.lower().endswith('.pdf')]
        return sorted(files)
    except Exception as e:
        logger.error(f"Error al leer el directorio {directory_path}: {e}")
        return []

@st.cache_data(show_spinner=False, ttl=300) # Cache por 5 minutos
def find_latest_report(prefix):
    """
    Busca en la carpeta 'data/informes' el archivo .pdf más reciente que coincida con un prefijo.
    """
    try:
        search_folder = os.path.join("data", "informes")
        search_pattern = os.path.join(search_folder, f"{prefix}*.pdf")
        
        files = glob.glob(search_pattern)
        
        if not files:
            logger.warning(f"No se encontraron informes .pdf con el prefijo: {prefix}")
            return None
        
        latest_file = max(files, key=os.path.getmtime)
        logger.info(f"Informe más reciente encontrado para '{prefix}': {latest_file}")
        return latest_file
    except Exception as e:
        logger.error(f"Error al buscar el último informe: {e}")
        return None

# --- FUNCIÓN DE DIÁLOGO UNIFICADA PARA MOSTRAR PDF ---
@st.dialog(" ")
def mostrar_dialogo_pdf(pdf_path, title, session_key):
    """
    Muestra un archivo PDF en un diálogo modal, ocultando la 'X' de cierre.
    Es genérica y funciona tanto para manuales como para informes.
    """
    st.markdown("""
        <style>
            [data-testid="stDialog"] button[aria-label="Close"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)

    try:
        with open(pdf_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        
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
                    const pdfData = atob('{base64_pdf}');
                    const pdfjsLib = window['pdfjs-dist/build/pdf'];
                    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.11.338/pdf.worker.min.js';

                    const loadingTask = pdfjsLib.getDocument({{data: pdfData}});
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

    except FileNotFoundError:
        st.error(f"Error: No se encontró el archivo en la ruta: {pdf_path}")
    except Exception as e:
        st.error(f"Ha ocurrido un error al cargar el PDF: {e}")

    if st.button("Cerrar", key=f"close_dialog_{session_key}_{title}", use_container_width=True):
        if session_key in st.session_state:
            del st.session_state[session_key]
        st.rerun()

# --- FUNCIÓN PRINCIPAL DE LA PÁGINA FUSIONADA ---
def display_manuales_page():
    """
    Crea la interfaz para la página de la biblioteca, que ahora incluye
    tanto los manuales como los informes de análisis estratégico.
    """
    # --- SECCIÓN 1: MANUALES ---
    st.header("Consulta los Manuales")
    st.markdown("")
    
    base_path = "data"
    manuales_paths = {
        "preguntas": os.path.join(base_path, "manuales", "preguntas"),
        "ml": os.path.join(base_path, "manuales", "ml")
    }

    col1, col2 = st.columns(2)
    with col1:
        is_preguntas_selected = (st.session_state.get("manual_view") == "preguntas")
        if st.button("Manual de Preguntas", use_container_width=True, type="primary" if is_preguntas_selected else "secondary"):
            st.session_state.manual_view = "preguntas"
            if "manual_a_mostrar" in st.session_state: del st.session_state.manual_a_mostrar
            st.rerun()
    
    with col2:
        is_ml_selected = (st.session_state.get("manual_view") == "ml")
        if st.button("Manual General", use_container_width=True, type="primary" if is_ml_selected else "secondary"):
            st.session_state.manual_view = "ml"
            if "manual_a_mostrar" in st.session_state: del st.session_state.manual_a_mostrar
            st.rerun()

    selected_view = st.session_state.get("manual_view")
    if selected_view:
        st.subheader("Capítulos disponibles:")
        path_to_scan = manuales_paths.get(selected_view)
        manual_files = get_manual_files(path_to_scan)

        if not manual_files:
            st.info(f"No se encontraron manuales en esta categoría.")
        else:
            for filename in manual_files:
                chapter_title = os.path.splitext(filename)[0]
                file_path = os.path.join(path_to_scan, filename)
                if st.button(chapter_title, key=f"btn_manual_{file_path}", use_container_width=True):
                    st.session_state.manual_a_mostrar = {"path": file_path, "title": chapter_title}
                    st.rerun()

    st.divider()


    

    # --- LÓGICA PARA ABRIR DIÁLOGOS ---
    # Se comprueba si se debe mostrar un manual
    if st.session_state.get("manual_a_mostrar"):
        manual_info = st.session_state.manual_a_mostrar
        mostrar_dialogo_pdf(manual_info["path"], manual_info["title"], "manual_a_mostrar")

   
