#smain_app.py
# ---- ESTE BLOQUE DEBE SER LO PRIMERO EN TODO EL ARCHIVO ----
import sys
import os

# Obtiene la ruta absoluta del directorio donde está este script (la raíz del proyecto)
project_root = os.path.dirname(os.path.abspath(__file__))

# Si esa ruta no está en la lista de búsqueda de Python, la añade al principio.
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ---- FIN DEL BLOQUE DE CORRECCIÓN DE RUTA ----


# ---- AHORA, EL RESTO DE IMPORTS ----
import streamlit as st
from dotenv import load_dotenv
import logging

# Configuración del logging
logging.basicConfig(
    level=logging.DEBUG, # O logging.INFO para menos detalle
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# --- Importaciones de tus nuevos módulos ---
from core.db_quiz_loader import obtener_temas_disponibles
from core.database import conectar_db
from ui.styles import CSS_STRING
from utils.helpers import ESPECIALIDAD_MAP, get_key_from_value

# Importar las funciones que renderizarán cada "página"
from ui.config_page import display_config_section
from ui.quiz_session_page import display_quiz_session_section
from ui.results_page import display_results_section
# MODIFICACIÓN: Cambiar el nombre de la función importada para reflejar su nueva ubicación
from ui.chat_RAG import display_rag_chat_section

# --- INICIO: Carga de Variables de Entorno ---
print("DEBUG MAIN_APP: Script main_app.py iniciado.")
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, '.env')

load_dotenv(dotenv_path=dotenv_path, override=True, verbose=True)
# --- FIN: Carga de Variables de Entorno ---

# --- Configuración Inicial de Página Streamlit ---
st.set_page_config(layout="centered", page_title="MENTORA")

# --- CSS Personalizado (Importado) ---
st.markdown(CSS_STRING, unsafe_allow_html=True)

# --- Inicialización de st.session_state (Claves Globales) ---
if 'specialty_selected' not in st.session_state:
    st.session_state.specialty_selected = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

if 'estado_app' not in st.session_state: 
    st.session_state.estado_app = 'seleccion_modo'

if 'modo_seleccionado' not in st.session_state: st.session_state.modo_seleccionado = None
if 'entrenamiento_libre_submodo' not in st.session_state: st.session_state.entrenamiento_libre_submodo = "Aleatorio"
if 'config_num_preguntas' not in st.session_state: st.session_state.config_num_preguntas = 20
if 'config_tipo_pregunta' not in st.session_state: st.session_state.config_tipo_pregunta = "Teóricas"
if 'config_temas_seleccionados' not in st.session_state: st.session_state.config_temas_seleccionados = []
if 'config_examen_ano' not in st.session_state: st.session_state.config_examen_ano = None
if 'config_examen_ca' not in st.session_state: st.session_state.config_examen_ca = None
if 'config_examen_esp' not in st.session_state: st.session_state.config_examen_esp = None
if 'cuestionario_actual' not in st.session_state: st.session_state.cuestionario_actual = []
if 'pregunta_actual_idx' not in st.session_state: st.session_state.pregunta_actual_idx = 0
if 'respuestas_usuario' not in st.session_state: st.session_state.respuestas_usuario = {}
if 'review_filter' not in st.session_state: st.session_state.review_filter = "incorrecta"
if 'pregunta_a_revisar_idx' not in st.session_state: st.session_state.pregunta_a_revisar_idx = None


# --- GESTIÓN DE SELECCIÓN DE ESPECIALIDAD ---

def display_specialty_selection():
    """Muestra el selector de especialidad."""
    st.subheader("¿Cuál es tu especialidad?")
    
    selected_specialty_name = st.selectbox(
        #"Selecciona tu especialidad para continuar",
        options=list(ESPECIALIDAD_MAP.values()),
        key="specialty_selection_dropdown",
        index=None, # Para que no haya nada seleccionado por defecto
        placeholder="Elige una opción..."
    )

    if st.button("Acceder", key="specialty_submit_btn"):
        if selected_specialty_name:
            specialty_key = get_key_from_value(ESPECIALIDAD_MAP, selected_specialty_name)
            if specialty_key:
                st.session_state.user_info = {'especialidad': specialty_key, 'nombre_usuario': 'Usuario'}
                st.session_state.specialty_selected = True
                st.rerun()
            else:
                st.error("Error interno: Clave de especialidad no encontrada.")
        else:
            st.warning("Por favor, selecciona una especialidad para acceder.")


# --- Lógica Principal de la Aplicación ---
if not st.session_state.get('specialty_selected'):
    display_specialty_selection()
else: # --- Especialidad SÍ seleccionada ---

    st.subheader("Bienvenido/a!")

    # --- MODIFICACIÓN: ESTRUCTURA DE PESTAÑAS ---
    tab_cuestionarios, tab_chat = st.tabs(["Cuestionarios", "Asistente"])

    # --- PESTAÑA 1: CUESTIONARIOS ---
    with tab_cuestionarios:
        if 'temas_disponibles_lista' not in st.session_state:
            print("DEBUG MAIN_APP: Cargando temas disponibles para la especialidad...")
            conn_temp = None
            try:
                conn_temp = conectar_db()
                if conn_temp:
                    especialidad_actual = st.session_state.user_info.get('especialidad')
                    st.session_state.temas_disponibles_lista = obtener_temas_disponibles(conn_temp, especialidad_actual)
                    if not st.session_state.temas_disponibles_lista:
                        st.warning("No se encontraron temas disponibles para esta especialidad.")
                else:
                    st.error("No se pudo conectar a la base de datos para cargar temas.")
                    st.session_state.temas_disponibles_lista = []
            except Exception as e:
                st.error(f"Error al cargar temas disponibles: {e}")
                st.session_state.temas_disponibles_lista = []
            finally:
                if conn_temp:
                    conn_temp.close()

        # --- Enrutador de Vistas ---
        if st.session_state.estado_app in ['seleccion_modo', 'configuracion_libre', 'configuracion_oficial']:
            display_config_section() 
        elif st.session_state.estado_app == 'cuestionario':
            display_quiz_session_section()
        elif st.session_state.estado_app == 'resultados':
            display_results_section()
        else: 
            print(f"WARN MAIN_APP: Estado de app desconocido o inválido: '{st.session_state.estado_app}'. Reseteando.")
            st.session_state.estado_app = 'seleccion_modo'
            st.rerun()

    # --- PESTAÑA 2: ASISTENTE DE ESTUDIO (CHAT RAG) ---
    with tab_chat:
        display_rag_chat_section()
    
 
