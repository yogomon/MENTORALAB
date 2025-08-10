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
import time
import logging
from ui.analisis_page import display_analysis_page
from ui.manuales_page import display_manuales_page

# Configuración del logging
logging.basicConfig(
    level=logging.DEBUG, # O logging.INFO para menos detalle
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# --- Importaciones de tus nuevos módulos ---
from core.db_quiz_loader import conectar_db, obtener_temas_disponibles
from ui.styles import CSS_STRING
from core import auth_handler
from utils.helpers import COMUNIDAD_MAP, ESPECIALIDAD_MAP, get_key_from_value

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

# --- MODIFICACIÓN: Se elimina el CSS específico para el ancho de la barra lateral ---

# --- Inicialización de st.session_state (Claves Globales) ---
# Estados para Autenticación
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'view' not in st.session_state:
    st.session_state.view = 'login'

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


# --- GESTIÓN DE AUTENTICACIÓN Y FLUJO PRINCIPAL DE LA APLICACIÓN ---

def display_login_form():
    # Este código no se ha modificado
    st.subheader("Bienvenido de nuevo")
    with st.form(key='login_form'):
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Contraseña", type="password", key="login_pass")
        submit_button = st.form_submit_button(label='Iniciar Sesión')

        if submit_button:
            auth_response = auth_handler.autenticar_usuario(login_email, login_password)
            
            if auth_response['status'] == 'success':
                st.session_state.user_info = auth_response['user_info']
                st.session_state.view = 'app'
                st.session_state.estado_app = 'seleccion_modo'
                st.rerun()
            else:
                st.error(auth_response.get('message', 'Error de autenticación desconocido.'))
    
    _, col_nav_derecha = st.columns([2, 1.1])
    with col_nav_derecha:
        if st.button(" Crear cuenta nueva", key="nav_to_register_btn_login_form", use_container_width=True):
            st.session_state.view = 'register'
            st.rerun()

def display_registration_form():
    # Este código no se ha modificado
    st.subheader("Crea tu cuenta")
    with st.form("registration_form", clear_on_submit=False):
        st.markdown("Introduce tus datos para crear una cuenta:")
        reg_nombre = st.text_input("Nombre de Usuario", key="reg_nombre_usuario")
        reg_email = st.text_input("Email", key="reg_email_usuario")
        col_pass1, col_pass2 = st.columns(2)
        with col_pass1:
            reg_password = st.text_input("Contraseña", type="password", key="reg_password_usuario")
        with col_pass2:
            reg_password_confirm = st.text_input("Confirmar Contraseña", type="password", key="reg_password_confirm_usuario")
        reg_comunidad_nombre = st.selectbox("Comunidad Autónoma", options=list(COMUNIDAD_MAP.values()), key="reg_comunidad_nombre")
        reg_especialidad_nombre = st.selectbox("Especialidad (elige la principal si tienes varias)", options=list(ESPECIALIDAD_MAP.values()), key="reg_especialidad_nombre")
        st.markdown("""<small>Requisitos...</small>""", unsafe_allow_html=True)
        submitted_registro = st.form_submit_button("Registrarme")
        if submitted_registro:
            if reg_password != reg_password_confirm:
                st.error("Las contraseñas no coinciden.")
            else:
                # Obtenemos las claves de los diccionarios para pasarlas a la función
                reg_comunidad_clave = get_key_from_value(COMUNIDAD_MAP, reg_comunidad_nombre)
                reg_especialidad_clave = get_key_from_value(ESPECIALIDAD_MAP, reg_especialidad_nombre)
                
                # Llamamos a la función de registro
                usuario_id, error_msg = auth_handler.registrar_nuevo_usuario(
                    reg_nombre, 
                    reg_password, 
                    reg_email, 
                    reg_comunidad_clave, 
                    reg_especialidad_clave
                )
                
                # Mostramos el resultado al usuario
                if error_msg:
                    st.error(error_msg)
                else:
                    st.success("¡Usuario registrado con éxito! Ahora puedes iniciar sesión.")
                    time.sleep(2) # Pausa para que el usuario lea el mensaje
                    st.session_state.view = 'login'
                    st.rerun()
    if st.button("¿Ya tienes cuenta? Inicia Sesión", key="nav_to_login_btn_reg_form"):
        st.session_state.view = 'login'
        st.rerun()


# --- Lógica Principal de la Aplicación ---
if 'user_info' not in st.session_state or st.session_state.user_info is None:
    # Lógica de autenticación sin cambios...
    current_view = st.session_state.get('view', 'login')
    if current_view == 'login':
        display_login_form()
    elif current_view == 'register':
        display_registration_form()
    else:
        st.session_state.view = 'login'
        display_login_form()
else: # --- Usuario SÍ Autenticado ---

    # Botón de Cerrar Sesión global en la parte superior derecha
    _, col_logout = st.columns([0.85, 0.15]) 
    with col_logout:
        if st.button("Salir", key="logout_button_global"):
            keys_to_clear = list(st.session_state.keys())
            for key in keys_to_clear:
                del st.session_state[key]
            st.session_state.view = 'login'
            st.rerun()    
    
    user_nombre = st.session_state.user_info.get('nombre_usuario', 'Usuario')
    st.subheader(f"Hola, {user_nombre}")

    # --- MODIFICACIÓN: ESTRUCTURA DE PESTAÑAS ---
    tab_cuestionarios, tab_manuales, tab_chat = st.tabs(["Cuestionarios", "Biblioteca", "Asistente",])

    # --- PESTAÑA 1: CUESTIONARIOS ---
    with tab_cuestionarios:
        if 'temas_disponibles_lista' not in st.session_state:
            print("DEBUG MAIN_APP (AUTH): Cargando temas disponibles para usuario autenticado...")
            conn_temp_auth = None
            try:
                conn_temp_auth = conectar_db()
                if conn_temp_auth:
                    especialidad_actual = st.session_state.user_info.get('especialidad')
                    st.session_state.temas_disponibles_lista = obtener_temas_disponibles(conn_temp_auth, especialidad_actual)
                    if not st.session_state.temas_disponibles_lista:
                        st.warning("No se encontraron temas disponibles para esta especialidad.")
                else:
                    st.error("No se pudo conectar a la base de datos para cargar temas (AUTH).")
                    st.session_state.temas_disponibles_lista = []
            except Exception as e_auth:
                st.error(f"Error al cargar temas disponibles (AUTH): {e_auth}")
                st.session_state.temas_disponibles_lista = []
            finally:
                if conn_temp_auth:
                    conn_temp_auth.close()

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
    
    #with tab_estrategia:
        #display_analysis_page()
    
    with tab_manuales:
        display_manuales_page()
