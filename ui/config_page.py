import streamlit as st
import random
import logging

# MODIFICACIÓN: Actualizar las importaciones para apuntar a los nuevos scripts.
from core.db_quiz_loader import (
    obtener_examenes_disponibles,
    format_topics_for_tree
)
from core.database import conectar_db
from core.db_quiz_handler import (
    obtener_preguntas_para_cuestionario,
    obtener_datos_examen,
    obtener_texto_escenario
)
from utils.helpers import _remove_empty_children_recursive

try:
    from streamlit_tree_select import tree_select
except ImportError:
    if 'treeselect_warning_shown' not in st.session_state:
        st.error("Instala 'streamlit-tree-select'. Selección de temas no funcionará.")
        st.session_state.treeselect_warning_shown = True
    tree_select = None
except Exception as e:
    if 'treeselect_warning_shown' not in st.session_state:
        st.error(f"Error importando streamlit_tree_select: {e}")
        st.session_state.treeselect_warning_shown = True
    tree_select = None

logger = logging.getLogger(__name__)

def display_config_section():
        
    st.header("Configura tu cuestionario")
    st.markdown("")

    col_modo1, col_modo2 = st.columns(2)
    with col_modo1:
        if st.button("Libre", key="btn_mode_libre_sel", use_container_width=True, type=('primary' if st.session_state.modo_seleccionado == "Entrenamiento Libre" else 'secondary')):
            if st.session_state.modo_seleccionado != "Entrenamiento Libre":
                st.session_state.modo_seleccionado = "Entrenamiento Libre"
                st.session_state.entrenamiento_libre_submodo = "Aleatorio"
                st.session_state.config_temas_seleccionados = []
                st.rerun()
    with col_modo2:
        if st.button("Examen Oficial", key="btn_mode_oficial_sel", use_container_width=True, type=('primary' if st.session_state.modo_seleccionado == "Simular Examen Oficial" else 'secondary')):
            if st.session_state.modo_seleccionado != "Simular Examen Oficial":
                st.session_state.modo_seleccionado = "Simular Examen Oficial"
                st.session_state.config_examen_ano = None
                st.session_state.config_examen_ca = None
                st.session_state.config_examen_esp = None
                st.rerun()

    if st.session_state.modo_seleccionado is not None:
        if st.session_state.modo_seleccionado == "Entrenamiento Libre":
            st.subheader("Modo Entrenamiento Libre")
            submodo_options = ["Aleatorio", "Personalizado"]
            cols_submodo = st.columns(len(submodo_options))
            for i, sub_opt in enumerate(submodo_options):
                with cols_submodo[i]:
                    is_selected = (st.session_state.entrenamiento_libre_submodo == sub_opt)
                    button_label = f" {sub_opt}"
                    if st.button(button_label, key=f"btn_submodo_{sub_opt}", use_container_width=True, type=('primary' if is_selected else 'secondary')):
                        if not is_selected:
                            st.session_state.entrenamiento_libre_submodo = sub_opt
                            st.rerun()
            
            config_actual = {}
            if st.session_state.entrenamiento_libre_submodo == "Aleatorio":
                st.markdown("<br>", unsafe_allow_html=True)
                config_actual = {"modo": "Libre-Aleatorio", "numero_preguntas": st.session_state.get("config_num_preg_aleatorio", 20)}

                if st.button("🚀 Comenzar", key="start_button_aleatorio", use_container_width=True):
                    logger.info(f"Botón Empezar (Aleatorio) pulsado. Config: {config_actual}")
                    with st.spinner("Preparando tu cuestionario..."):
                        conn_quiz = None
                        try:
                            conn_quiz = conectar_db()
                            if conn_quiz:
                                temas_para_funcion = st.session_state.get('temas_disponibles_lista', [])
                                especialidad_usuario = st.session_state.user_info.get('especialidad')
                                
                                preguntas_seleccionadas_raw = obtener_preguntas_para_cuestionario(conn_quiz, config_actual, temas_para_funcion, especialidad_usuario)
                                
                                if preguntas_seleccionadas_raw:
                                    logger.info(f"Enriqueciendo {len(preguntas_seleccionadas_raw)} preguntas para modo Aleatorio...")
                                    enriched_preguntas = []
                                    for preg_dict in preguntas_seleccionadas_raw:
                                        enriched_preg = preg_dict.copy()
                                        examen_id = preg_dict.get('examen_oficial_id')
                                        escenario_id = preg_dict.get('escenario_id')
                                        if examen_id:
                                            enriched_preg['datos_examen_completos'] = obtener_datos_examen(conn_quiz, examen_id)
                                        if escenario_id:
                                            enriched_preg['texto_escenario_completo'] = obtener_texto_escenario(conn_quiz, escenario_id)
                                        enriched_preguntas.append(enriched_preg)
                                    st.session_state.cuestionario_actual = enriched_preguntas
                                    
                                    st.session_state.pregunta_actual_idx = 0
                                    st.session_state.respuestas_usuario = {}
                                    st.session_state.estado_app = 'cuestionario'
                                    logger.info("Cambiando a estado 'cuestionario' (Aleatorio).")
                                    st.rerun()
                                else:
                                    st.warning("No se encontraron preguntas para el modo Aleatorio con los criterios actuales.")
                            else:
                                st.error("Error de conexión. No se pudo iniciar el cuestionario.")
                        except Exception as e:
                            logger.error(f"Error al iniciar cuestionario Aleatorio: {e}", exc_info=True)
                            st.error("Ocurrió un error al preparar el cuestionario.")
                        finally:
                            if conn_quiz:
                                conn_quiz.close()
                                logger.debug("Conexión (Aleatorio) cerrada.")

            elif st.session_state.entrenamiento_libre_submodo == "Personalizado":
                st.markdown("")
                col_pers1, col_pers2 = st.columns(2)
                with col_pers1:
                    st.markdown("Número de preguntas")
                    opciones_num_preguntas = [20, 50, 100]
                    if st.session_state.get('config_num_preguntas', 20) not in opciones_num_preguntas:
                        st.session_state.config_num_preguntas = 20
                    for num_opt in opciones_num_preguntas:
                        is_selected = (st.session_state.config_num_preguntas == num_opt)
                        if st.button(label=str(num_opt), key=f"btn_num_{num_opt}", use_container_width=True, type=('primary' if is_selected else 'secondary')):
                            if not is_selected: st.session_state.config_num_preguntas = num_opt; st.rerun()
                    config_num_preguntas_actual = st.session_state.config_num_preguntas
                
                with col_pers2:
                    st.markdown("Tipo de preguntas")
                    opciones_tipo_pregunta = ["Teóricas", "Prácticas", "Ambas"]
                    if st.session_state.get('config_tipo_pregunta') not in opciones_tipo_pregunta:
                        st.session_state.config_tipo_pregunta = "Ambas"
                    for tipo_opt in opciones_tipo_pregunta:
                        is_selected = (st.session_state.config_tipo_pregunta == tipo_opt)
                        if st.button(label=tipo_opt, key=f"btn_tipo_{tipo_opt}", use_container_width=True, type=('primary' if is_selected else 'secondary')):
                            if not is_selected: st.session_state.config_tipo_pregunta = tipo_opt; st.rerun()
                    config_tipo_pregunta_actual = st.session_state.config_tipo_pregunta
                
                st.markdown("Contenidos")
                if 'tree_select_key_suffix' not in st.session_state:
                    st.session_state.tree_select_key_suffix = 0

                if st.button("Marcar todo", key="btn_toggle_all_temas", help="Marca o desmarca TODOS los temas disponibles"):
                    if st.session_state.get('temas_disponibles_lista'):
                        all_theme_ids = [t['id'] for t in st.session_state.temas_disponibles_lista]
                        current_selection_set = set(st.session_state.get('config_temas_seleccionados', []))
                        all_theme_ids_set = set(all_theme_ids)
                        if current_selection_set == all_theme_ids_set: 
                            st.session_state.config_temas_seleccionados = []
                        else: 
                            st.session_state.config_temas_seleccionados = sorted(list(all_theme_ids_set))
                        st.session_state.tree_select_key_suffix += 1
                        st.rerun()
                    else:
                        st.warning("No hay temas disponibles para marcar/desmarcar.")
                st.write("")

                if tree_select and st.session_state.get('temas_disponibles_lista'):
                    nodos_arbol = format_topics_for_tree(st.session_state.temas_disponibles_lista)
                    if nodos_arbol:
                        dynamic_tree_key = f"tema_tree_select_{st.session_state.tree_select_key_suffix}"
                        seleccion_arbol = tree_select(
                            nodes=nodos_arbol,
                            checked=[str(id_int) for id_int in st.session_state.get('config_temas_seleccionados', [])],
                            expanded=st.session_state.get('tree_expanded_nodes', []),
                            check_model='all',
                            only_leaf_checkboxes=False,
                            show_expand_all=False, 
                            key=dynamic_tree_key
                        )
                        
                        returned_checked_str = seleccion_arbol.get('checked', [])
                        ids_seleccionados_int = [int(val_str) for val_str in returned_checked_str if val_str.isdigit()]
                        
                        st.session_state.tree_expanded_nodes = seleccion_arbol.get('expanded', [])

                        if set(ids_seleccionados_int) != set(st.session_state.get('config_temas_seleccionados', [])):
                            st.session_state.config_temas_seleccionados = ids_seleccionados_int
                            st.rerun()
                        config_temas_seleccionados_actual = st.session_state.config_temas_seleccionados
                    else: st.write("No se pudieron formatear temas para el árbol.")
                elif not tree_select: st.warning("Componente tree-select no disponible.")
                else: st.write("No hay temas disponibles para mostrar en el árbol.")

                st.markdown("")
                config_actual = {
                    "modo": "Libre-Personalizado", 
                    "numero_preguntas": config_num_preguntas_actual, 
                    "tipo_pregunta": config_tipo_pregunta_actual, 
                    "temas_codigos": st.session_state.get('config_temas_seleccionados', [])
                }
                
                if st.button("🚀 Comenzar", key="start_button_personalizado", use_container_width=True):
                    if not config_actual.get('temas_codigos'):
                        st.warning("Selecciona al menos un contenido.")
                    else:
                        logger.info(f"Botón Empezar (Personalizado) pulsado. Config: {config_actual}")
                        with st.spinner("Preparando tu cuestionario..."):
                            conn_quiz = None
                            try:
                                conn_quiz = conectar_db()
                                if conn_quiz:
                                    temas_para_funcion = st.session_state.get('temas_disponibles_lista', [])
                                    especialidad_usuario = st.session_state.user_info.get('especialidad')
                                    
                                    preguntas_seleccionadas_raw = obtener_preguntas_para_cuestionario(conn_quiz, config_actual, temas_para_funcion, especialidad_usuario)
                                    
                                    if preguntas_seleccionadas_raw:
                                        logger.info(f"Enriqueciendo {len(preguntas_seleccionadas_raw)} preguntas para modo Personalizado...")
                                        enriched_preguntas = []
                                        for preg_dict in preguntas_seleccionadas_raw:
                                            enriched_preg = preg_dict.copy()
                                            examen_id = preg_dict.get('examen_oficial_id')
                                            escenario_id = preg_dict.get('escenario_id')
                                            if examen_id:
                                                enriched_preg['datos_examen_completos'] = obtener_datos_examen(conn_quiz, examen_id)
                                            if escenario_id:
                                                enriched_preg['texto_escenario_completo'] = obtener_texto_escenario(conn_quiz, escenario_id)
                                            enriched_preguntas.append(enriched_preg)
                                        st.session_state.cuestionario_actual = enriched_preguntas

                                        st.session_state.pregunta_actual_idx = 0
                                        st.session_state.respuestas_usuario = {}
                                        st.session_state.estado_app = 'cuestionario'
                                        logger.info("Cambiando al estado 'cuestionario' (Personalizado).")
                                        st.rerun()
                                    else:
                                        st.warning("No se encontraron preguntas que cumplan los criterios seleccionados.")
                                else:
                                    st.error("Error de conexión. No se pudo iniciar el cuestionario.")
                            except Exception as e:
                                logger.error(f"Error al iniciar cuestionario Personalizado: {e}", exc_info=True)
                                st.error("Ocurrió un error al preparar el cuestionario.")
                            finally:
                                if conn_quiz:
                                    conn_quiz.close()
                                    logger.debug("Conexión (Personalizado) cerrada.")

        elif st.session_state.modo_seleccionado == "Simular Examen Oficial":
            st.subheader("Modo Examen Oficial")
            conn_exam_meta = None
            try:
                conn_exam_meta = conectar_db()
                if conn_exam_meta:
                    lista_examenes = obtener_examenes_disponibles(conn_exam_meta)
                else:
                    lista_examenes = []
                    st.error("Error de conexión. No se pueden cargar los exámenes.")
            except Exception as e_meta:
                logger.error(f"Error obteniendo lista de exámenes: {e_meta}", exc_info=True)
                lista_examenes = []
                st.error("Error al cargar la lista de exámenes.")
            finally:
                if conn_exam_meta:
                    conn_exam_meta.close()
                    logger.debug("Conexión para metadatos de examen cerrada.")

            if not lista_examenes and conn_exam_meta :
                st.info("No hay exámenes oficiales disponibles en este momento.")
            elif lista_examenes :
                opciones_esp = sorted(list(set(ex['especialidad'] for ex in lista_examenes)))
                opciones_ano = sorted(list(set(ex['ano'] for ex in lista_examenes)), reverse=True)
                opciones_ca = sorted(list(set(ex['comunidad_autonoma'] for ex in lista_examenes)))
                
                sel_esp = st.selectbox("Especialidad:", options=opciones_esp, index=opciones_esp.index(st.session_state.get('config_examen_esp')) if st.session_state.get('config_examen_esp') in opciones_esp else 0, key="sel_exam_esp")
                if sel_esp != st.session_state.get('config_examen_esp'): st.session_state.config_examen_esp = sel_esp; st.rerun()
                
                sel_ca = st.selectbox("Comunidad Autónoma:", options=opciones_ca, index=opciones_ca.index(st.session_state.get('config_examen_ca')) if st.session_state.get('config_examen_ca') in opciones_ca else 0, key="sel_exam_ca")
                if sel_ca != st.session_state.get('config_examen_ca'): st.session_state.config_examen_ca = sel_ca; st.rerun()
                
                sel_ano = st.selectbox("Año:", options=opciones_ano, index=opciones_ano.index(st.session_state.get('config_examen_ano')) if st.session_state.get('config_examen_ano') in opciones_ano else 0, key="sel_exam_ano")
                if sel_ano != st.session_state.get('config_examen_ano'): st.session_state.config_examen_ano = sel_ano; st.rerun()
                
                st.markdown("<br>", unsafe_allow_html=True)

                if st.session_state.config_examen_ano and st.session_state.config_examen_ca and st.session_state.config_examen_esp:
                    if st.button("🚀 Comenzar", key="start_button_oficial", use_container_width=True):
                        config_actual = {"modo": "Oficial", "ano": st.session_state.config_examen_ano, "ca": st.session_state.config_examen_ca, "esp": st.session_state.config_examen_esp}
                        logger.info(f"Botón Empezar (Oficial) pulsado. Config: {config_actual}")
                        with st.spinner("Cargando examen..."):
                            conn_quiz = None
                            try:
                                conn_quiz = conectar_db()
                                if conn_quiz:
                                    preguntas_seleccionadas_raw = obtener_preguntas_para_cuestionario(conn_quiz, config_actual, especialidad_usuario=st.session_state.user_info.get('especialidad')) 
                                    
                                    if preguntas_seleccionadas_raw:
                                        logger.info(f"Enriqueciendo {len(preguntas_seleccionadas_raw)} preguntas para modo Oficial...")
                                        enriched_preguntas = []
                                        for preg_dict in preguntas_seleccionadas_raw:
                                            enriched_preg = preg_dict.copy()
                                            escenario_id = preg_dict.get('escenario_id')
                                            if escenario_id:
                                                enriched_preg['texto_escenario_completo'] = obtener_texto_escenario(conn_quiz, escenario_id)
                                            enriched_preguntas.append(enriched_preg)
                                        st.session_state.cuestionario_actual = enriched_preguntas
                                        
                                        st.session_state.pregunta_actual_idx = 0
                                        st.session_state.respuestas_usuario = {}
                                        st.session_state.estado_app = 'cuestionario'
                                        logger.info("Cambiando al estado 'cuestionario' (Oficial).")
                                        st.rerun()
                                    else:
                                        st.warning("No se encontraron preguntas para el examen oficial seleccionado.")
                                else:
                                    st.error("Error de conexión. No se pudo iniciar el cuestionario.")
                            except Exception as e:
                                logger.error(f"Error al iniciar cuestionario Oficial: {e}", exc_info=True)
                                st.error("Ocurrió un error al preparar el cuestionario.")
                            finally:
                                if conn_quiz:
                                    conn_quiz.close()
                                    logger.debug("Conexión (Oficial) cerrada.")
                else: 
                    st.info("Selecciona todos los campos del examen para comenzar.")