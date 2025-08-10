import streamlit as st
import os
import logging
import glob
from datetime import datetime
import base64

# Configurar un logger para esta página
logger = logging.getLogger(__name__)

# --- FUNCIÓN AUXILIAR PARA ENCONTRAR EL INFORME MÁS RECIENTE ---
@st.cache_data(show_spinner=False, ttl=300) # Cache por 5 minutos
def find_latest_report(prefix):
    """
    Busca en la carpeta 'data/informes' el archivo .pdf más reciente que coincida con un prefijo.
    """
    try:
        # MODIFICADO: La ruta ahora apunta a data/informes
        search_folder = os.path.join("data", "informes")
        # MODIFICADO: Buscamos archivos .pdf
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

# --- FUNCIÓN DE DIÁLOGO PARA MOSTRAR EL PDF CON PDF.js ---
@st.dialog(" ")
def mostrar_dialogo_pdf(pdf_path, title):
    """
    Muestra un archivo PDF en un diálogo modal renderizando cada página
    en un canvas HTML, ocultando la 'X' de cierre.
    """
    # Inyectamos el CSS para ocultar el botón 'X' del diálogo
    st.markdown("""
        <style>
            [data-testid="stDialog"] button[aria-label="Close"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)

    #st.header(title)
    #st.markdown("---")

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
        st.error(f"Error: No se encontró el archivo del informe en la ruta: {pdf_path}")
    except Exception as e:
        st.error(f"Ha ocurrido un error al cargar el PDF: {e}")

    if st.button("Cerrar", key=f"close_report_dialog_{title}", use_container_width=True):
        if "informe_a_mostrar" in st.session_state:
            del st.session_state["informe_a_mostrar"]
        st.rerun()

# --- FUNCIÓN PRINCIPAL DE LA PÁGINA DE ANÁLISIS ---
def display_analysis_page():
    """
    Crea la interfaz para la página de análisis de rentabilidad.
    """
    st.header("Análisis estratégico")
    st.markdown("Selecciona una especialidad para visualizar las 'zonas calientes' del temario.") 

    # --- Prefijos para buscar los archivos de informe ---
    report_prefixes = {
        "bioquimica": "Informe Rentabilidad - Bioquimica Clinica",
        "analisis": "Informe Rentabilidad - Analisis Clinicos",
        "conjunto": "Informe Rentabilidad - Conjunto"
    }

    # --- SECCIÓN DE BOTONES ---
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Bioquímica Clínica", use_container_width=True, type="secondary"):
            st.session_state.informe_a_mostrar = "bioquimica"
            st.rerun()
    
    with col2:
        if st.button("Análisis Clínicos", use_container_width=True, type="secondary"):
            st.session_state.informe_a_mostrar = "analisis"
            st.rerun()
            
    with col3:
        if st.button("Análisis Conjunto", use_container_width=True, type="secondary"):
            st.session_state.informe_a_mostrar = "conjunto"
            st.rerun()

    # --- Lógica para abrir el diálogo ---
    if st.session_state.get("informe_a_mostrar"):
        report_key = st.session_state.informe_a_mostrar
        
        titles = {
            "bioquimica": "Bioquímica Clínica",
            "analisis": "Análisis Clínicos",
            "conjunto": "Análisis Conjunto"
        }
        
        with st.spinner("Buscando y procesando el último informe..."):
            pdf_path_to_show = find_latest_report(report_prefixes[report_key])
        
        if pdf_path_to_show and os.path.exists(pdf_path_to_show):
            dialog_was_closed = mostrar_dialogo_pdf(pdf_path_to_show, titles[report_key])
            if dialog_was_closed:
                if "informe_a_mostrar" in st.session_state:
                    del st.session_state["informe_a_mostrar"]
                st.rerun()
        else:
            st.error(f"No se ha encontrado ningún informe para '{titles[report_key]}'. Por favor, genera primero el informe desde el script correspondiente.")
            if "informe_a_mostrar" in st.session_state:
                del st.session_state["informe_a_mostrar"]


