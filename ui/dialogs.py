import streamlit as st
import time
import logging

logger = logging.getLogger(__name__)

# --- FUNCIÓN para Diálogo de Revisión (sin cambios) ---
@st.dialog(" ")
def mostrar_dialogo_revision(
    idx_pregunta, 
    cuestionario_completo, 
    respuestas_usuario_dict,
    texto_escenario_recibido
    ):
    """ Muestra el contenido detallado de una pregunta en un diálogo modal. """
    if not (0 <= idx_pregunta < len(cuestionario_completo)):
        st.error("Error: Índice de pregunta inválido para revisión.")
        if st.button("Cerrar Error", key=f"close_review_error_dialog_{idx_pregunta}_{time.time()}"): 
            if 'pregunta_a_revisar_idx' in st.session_state:
                st.session_state.pregunta_a_revisar_idx = None 
            st.rerun()
        return

    q_review = cuestionario_completo[idx_pregunta]
    pid_review = q_review.get('id', f"indice_{idx_pregunta}")

    st.header(f"Pregunta {idx_pregunta + 1}")
    st.markdown("---")

    if texto_escenario_recibido:
        with st.expander("Caso Práctico de la Pregunta", expanded=True):
            st.markdown(texto_escenario_recibido)
    
    st.markdown(f"{q_review.get('enunciado', 'N/A')}")
    #st.markdown("---")

    opciones_rev = {'A': q_review.get('opcion_a'), 'B': q_review.get('opcion_b'), 'C': q_review.get('opcion_c'), 'D': q_review.get('opcion_d')}
    respuesta_usuario_rev = respuestas_usuario_dict.get(pid_review)
    respuesta_correcta_rev = q_review.get('respuesta_correcta')
    pregunta_fue_respondida = (respuesta_usuario_rev is not None)

    for key, text in opciones_rev.items():
        if text:
            label = f"{key}) {text}"
            if pregunta_fue_respondida:
                if key == respuesta_correcta_rev: st.success(label)
                elif key == respuesta_usuario_rev: st.error(label)
                else: st.markdown(label)
            else:
                st.markdown(label)

    #st.divider()
    if st.button("Cerrar", key=f"close_review_dialog_{pid_review}"):
        st.session_state.pregunta_a_revisar_idx = None
        st.rerun()


# --- FUNCIÓN para Diálogo de Explicación (MODIFICADA) ---
@st.dialog(" ") 
def mostrar_dialogo_explicacion_ia_maqueta_v2( 
    pregunta_actual_dict,
    texto_escenario_actual,
    idx_pregunta_en_cuestionario,
    respuestas_usuario_del_cuestionario,
    explicacion_cargada=None
):
    """
    Muestra la explicación pre-generada de una pregunta.
    MODIFICACIÓN: Incluye CSS para deshabilitar la selección de texto.
    """
    id_pregunta_para_keys = pregunta_actual_dict.get('id', f"dialog_expl_{idx_pregunta_en_cuestionario}")

    # --- Mostrar la pregunta y el feedback de la respuesta ---
    if texto_escenario_actual:
        with st.expander("Caso Práctico:", expanded=True):
            st.markdown(texto_escenario_actual)
    
    enunciado_display = pregunta_actual_dict.get('enunciado', 'N/A')
    st.markdown(enunciado_display) 
    st.markdown("---")
    
    opciones_dict_display = {
        'A': pregunta_actual_dict.get('opcion_a'), 'B': pregunta_actual_dict.get('opcion_b'),
        'C': pregunta_actual_dict.get('opcion_c'), 'D': pregunta_actual_dict.get('opcion_d')
    }
    respuesta_usuario = respuestas_usuario_del_cuestionario.get(id_pregunta_para_keys)
    respuesta_correcta_sistema = pregunta_actual_dict.get('respuesta_correcta')
    
    for opt_key, opt_text in opciones_dict_display.items():
        if opt_text:
            label_opcion_con_texto = f"{opt_key}) {opt_text}"
            if opt_key == respuesta_correcta_sistema:
                st.success(label_opcion_con_texto)
            elif opt_key == respuesta_usuario:
                st.error(label_opcion_con_texto)
            else:
                st.markdown(label_opcion_con_texto)
    st.write("") 
    st.markdown("---") 

    # --- Lógica para mostrar la explicación pre-cargada ---
    st.subheader("Análisis de la pregunta")

    if explicacion_cargada:
        justificacion = explicacion_cargada.get('justificacion_breve', 'Justificación no disponible.')
        explicacion = explicacion_cargada.get('explicacion_magistral', 'Explicación no disponible.')
        
        # --- MODIFICACIÓN: Aplicar CSS para deshabilitar la selección de texto ---
        css_no_copy = """
        <style>
            /* Esta línea oculta el botón 'X' del diálogo */
            [data-testid="stDialog"] button[aria-label="Close"] {
                display: none;
            }
            .no-select-text {
                -webkit-user-select: none;  /* Safari */
                -moz-user-select: none;     /* Firefox */
                -ms-user-select: none;      /* Internet Explorer/Edge */
                user-select: none;          /* Standard syntax */
            }
        </style>
        """
        html_justificacion = f"<div class='no-select-text'>{justificacion}</div>"
        html_explicacion = f"<div class='no-select-text'>{explicacion}</div>"

        st.markdown("#### Justificación")
        # Se inyecta el CSS una sola vez, pero se aplica la clase a ambos elementos
        st.markdown(css_no_copy + html_justificacion, unsafe_allow_html=True)
        
        st.markdown("#### Explicación")
        st.markdown(html_explicacion, unsafe_allow_html=True)
        # --- FIN DE LA MODIFICACIÓN ---
    else:
        st.warning("La explicación para esta pregunta no se encontró en la base de datos.")

    # --- Botón "Cerrar" General del Diálogo ---
    #st.divider()
    if st.button("Cerrar", key=f"cerrar_dialogo_main_{id_pregunta_para_keys}", use_container_width=True):
        clave_dialogo_abierto = f'dialogo_explicacion_esta_abierto_{id_pregunta_para_keys}'
        if clave_dialogo_abierto in st.session_state:
            st.session_state[clave_dialogo_abierto] = False
        st.rerun()