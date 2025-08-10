import streamlit as st
import os
import time 
import streamlit.components.v1 as components
from datetime import datetime, timedelta 
import threading
import logging

# Importaciones de tus módulos refactorizados
from core.database import conectar_db
from core.db_quiz_handler import obtener_datos_examen, obtener_texto_escenario, obtener_explicacion_pregunta
from ui.dialogs import mostrar_dialogo_explicacion_ia_maqueta_v2 
from core import stats_handler 

logger = logging.getLogger(__name__)

# Helper function to accumulate response data
def _acumular_respuesta_actual_para_stats_finales(pregunta_id):
    current_start_time = st.session_state.get('current_question_start_time')
    if not isinstance(current_start_time, datetime):
        print(f"WARN UI: current_question_start_time no es un datetime válido para {pregunta_id}, usando fallback.")
        current_start_time = datetime.now() - timedelta(seconds=10) 

    respuesta_seleccionada = st.session_state.respuestas_usuario.get(pregunta_id) 
    fecha_resp = datetime.now()
    tiempo_resp_ms = round((fecha_resp - current_start_time).total_seconds() * 1000)
    
    data_to_append = {
        'pregunta_id': pregunta_id,
        'respuesta_usuario': respuesta_seleccionada,
        'tiempo_respuesta_ms': tiempo_resp_ms,
        'fecha_respuesta': fecha_resp.isoformat() 
    }
    st.session_state.respuestas_para_stats_finales.append(data_to_append)
    print(f"DEBUG UI: Acumulada respuesta para {pregunta_id}: {respuesta_seleccionada} (Total acumuladas: {len(st.session_state.respuestas_para_stats_finales)}) SessionStart: {current_start_time.isoformat()}, FechaResp: {fecha_resp.isoformat()}, TiempoMs: {tiempo_resp_ms}")

def display_quiz_session_section():
    if 'respuestas_para_stats_finales' not in st.session_state:
        st.session_state.respuestas_para_stats_finales = []
        print("DEBUG UI: 'respuestas_para_stats_finales' inicializado por primera vez.")

    if st.session_state.pregunta_actual_idx == 0 and not st.session_state.get('quiz_stats_list_initialized_for_current_quiz', False):
        st.session_state.respuestas_para_stats_finales = [] 
        st.session_state.quiz_stats_list_initialized_for_current_quiz = True 
        print("DEBUG UI: 'respuestas_para_stats_finales' reseteado para nuevo cuestionario.")
    elif st.session_state.pregunta_actual_idx != 0:
        st.session_state.quiz_stats_list_initialized_for_current_quiz = False

    cuestionario_list = st.session_state.get('cuestionario_actual', [])

    if not cuestionario_list or st.session_state.pregunta_actual_idx >= len(cuestionario_list):
        st.error("Error: No hay preguntas válidas o índice fuera de rango.")
        if st.button("⬅️ Volver al Inicio", key="btn_volver_inicio_error_quiz"):
            st.session_state.estado_app = 'seleccion_modo'; st.session_state.modo_seleccionado = None; st.session_state.cuestionario_actual = []; st.session_state.respuestas_usuario = {}; st.session_state.entrenamiento_libre_submodo = "Aleatorio"; st.session_state.pregunta_a_revisar_idx = None
            st.session_state.respuestas_para_stats_finales = [] 
            st.session_state.quiz_stats_list_initialized_for_current_quiz = False 
            st.rerun()
    else:
        idx = st.session_state.pregunta_actual_idx
        total_preguntas = len(cuestionario_list)
        pregunta_actual = cuestionario_list[idx]
        pregunta_id_actual = pregunta_actual.get('id', f"indice_{idx}") 

        if st.session_state.get('start_time_recorded_for_idx') != idx:
            st.session_state.current_question_start_time = datetime.now()
            st.session_state.start_time_recorded_for_idx = idx 
            print(f"DEBUG UI: Tiempo de inicio registrado para pregunta con idx {idx} ({pregunta_id_actual})")

        info_line_parts = []

        datos_examen = pregunta_actual.get('datos_examen_completos') 
        texto_escenario = pregunta_actual.get('texto_escenario_completo')
        escenario_id_ui = pregunta_actual.get('escenario_id')
        
        # --- MODIFICACIÓN: Obtener el número de la pregunta en su examen original ---
        numero_pregunta_examen = pregunta_actual.get('numero_pregunta')

        if total_preguntas > 0:
            progreso_percent = int(((idx + 1) / total_preguntas) * 100)
            st.progress(progreso_percent, text=f"Pregunta {idx + 1} de {total_preguntas}")
        st.write("") 

        if datos_examen:
            info_line_parts.append(f"{datos_examen.get('especialidad', '')} - {datos_examen.get('comunidad_autonoma', '')} ({datos_examen.get('ano', '')})")
        
        # --- MODIFICACIÓN: Añadir el número de la pregunta a la línea de información ---
        if numero_pregunta_examen:
            info_line_parts.append(f"Pregunta {numero_pregunta_examen}")

        if pregunta_id_actual:
            info_line_parts.append(f"ID{pregunta_id_actual}")

        if info_line_parts:
            st.caption(" | ".join(info_line_parts))

        if texto_escenario:
            with st.expander("Caso Práctico", expanded=True):
                st.markdown(texto_escenario)
        elif escenario_id_ui and not texto_escenario: 
            st.warning(f"Texto del escenario ID: {escenario_id_ui} no fue pre-cargado o no existe.")

        st.markdown('<div class="enunciado-pregunta">', unsafe_allow_html=True)
        st.markdown(f"{idx + 1}. {pregunta_actual.get('enunciado', 'Error: Sin enunciado')}")
        st.markdown('</div>', unsafe_allow_html=True)

        nombre_imagen_completo = pregunta_actual.get('nombre_imagen')
        if nombre_imagen_completo:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            directorio_imagenes = os.path.join(project_root, 'data', 'imagenes')
            ruta_imagen = os.path.join(directorio_imagenes, nombre_imagen_completo)
            if os.path.exists(ruta_imagen):
                col_img_izq, col_img_der = st.columns([1, 2]) 
                with col_img_izq:
                    st.image(ruta_imagen, use_container_width=True)
            else:
                st.caption(f"[Error: Archivo '{nombre_imagen_completo}' no en '{directorio_imagenes}']")

        opciones_dict = {'A': pregunta_actual.get('opcion_a'), 'B': pregunta_actual.get('opcion_b'), 'C': pregunta_actual.get('opcion_c'), 'D': pregunta_actual.get('opcion_d')}
        opciones_validas = {k: v for k, v in opciones_dict.items() if v}

        if not opciones_validas:
            st.error("Error: Pregunta sin opciones.")
            if st.button("Saltar Pregunta Inválida", key=f"skip_invalid_{pregunta_id_actual}"):
                if idx < total_preguntas - 1: st.session_state.pregunta_actual_idx += 1
                else: st.session_state.estado_app = 'resultados'; st.session_state.pregunta_a_revisar_idx = None
                st.rerun()
        else: 
            respuesta_guardada = st.session_state.respuestas_usuario.get(pregunta_id_actual, Ellipsis)
            respuesta_correcta = pregunta_actual.get('respuesta_correcta')
            tiene_respuesta_concreta_registrada = respuesta_guardada not in [Ellipsis, None]

            st.markdown('<div class="quiz-options-container">', unsafe_allow_html=True)
            for key, text in opciones_validas.items():
                label = f"{key}) {text}"
                button_key = f"btn_q_{pregunta_id_actual}_{key}"

                if not tiene_respuesta_concreta_registrada:
                    if st.button(label, key=button_key, use_container_width=True, type="secondary"):
                        st.session_state.respuestas_usuario[pregunta_id_actual] = key
                        st.rerun()
                else: 
                    seleccion_usuario = respuesta_guardada
                    if key == respuesta_correcta: 
                        st.success(label)
                    elif key == seleccion_usuario: 
                        st.error(label) 
                    else: 
                        st.markdown(label)
                        
            st.markdown('</div>', unsafe_allow_html=True)

            clave_dialogo_abierto = f"dialogo_explicacion_esta_abierto_{pregunta_id_actual}"
            clave_vista_interna = f"dialog_view_mode_{pregunta_id_actual}"

            if tiene_respuesta_concreta_registrada:
                if st.button("💡 Explicación", key=f"btn_expl_{pregunta_id_actual}", use_container_width=True, help="Ver solución y explicación."):
                    st.session_state[clave_dialogo_abierto] = True      
                    st.session_state[clave_vista_interna] = 'initial_explanation' 
                    st.rerun()                                          

            if st.session_state.get(clave_dialogo_abierto, False):
                explicacion_key = f"explicacion_data_{pregunta_id_actual}"
                if explicacion_key not in st.session_state:
                    st.session_state[explicacion_key] = None
                    conn = None
                    try:
                        conn = conectar_db()
                        explicacion_data = obtener_explicacion_pregunta(conn, pregunta_id_actual)
                        st.session_state[explicacion_key] = explicacion_data
                    except Exception as e:
                        st.error("No se pudo cargar la explicación.")
                        logger.error(f"Fallo al obtener explicación para {pregunta_id_actual}: {e}", exc_info=True)
                    finally:
                        if conn:
                            conn.close()
                
                explicacion_cargada = st.session_state[explicacion_key]

                mostrar_dialogo_explicacion_ia_maqueta_v2( 
                    pregunta_actual,      
                    texto_escenario,      
                    st.session_state.pregunta_actual_idx, 
                    st.session_state.respuestas_usuario,
                    explicacion_cargada=explicacion_cargada
                )

            st.write("") 

            es_ultima_pregunta = (idx == total_preguntas - 1)
            texto_boton_siguiente = "⏹️ Finalizar Cuestionario" if es_ultima_pregunta else "Siguiente Pregunta >"

            if st.button(texto_boton_siguiente, key="btn_siguiente", use_container_width=True, type="primary"):
                if pregunta_id_actual not in st.session_state.respuestas_usuario: 
                    st.session_state.respuestas_usuario[pregunta_id_actual] = None
                
                _acumular_respuesta_actual_para_stats_finales(pregunta_id_actual) 

                if not es_ultima_pregunta: st.session_state.pregunta_actual_idx += 1
                else: 
                    if st.session_state.get('respuestas_para_stats_finales'):
                        user_id_actual = st.session_state.user_info.get('id') if st.session_state.get('user_info') else None
                        if user_id_actual:
                            respuestas_a_procesar = st.session_state.respuestas_para_stats_finales[:]
                            if respuestas_a_procesar:
                                try:
                                    processing_thread = threading.Thread(
                                        target=stats_handler.procesar_respuestas_del_quiz_finalizado,
                                        args=(user_id_actual, respuestas_a_procesar),
                                        daemon=True
                                    )
                                    processing_thread.start()
                                except Exception as e_thread_start:
                                    st.error(f"Error al iniciar el hilo de procesamiento de estadísticas: {e_thread_start}")
                        else:
                            st.warning("USER ID no encontrado, no se pueden procesar stats finales.")
                        st.session_state.respuestas_para_stats_finales = [] 
                    
                    st.session_state.estado_app = 'resultados'; st.session_state.pregunta_a_revisar_idx = None
                st.rerun()

            st.divider() 
            cols_otras_acciones = st.columns(3)
            with cols_otras_acciones[0]:
                if idx > 0:
                    if st.button("< Pregunta Anterior", key="btn_anterior", use_container_width=True):
                        if 'explicacion_mostrada_actual' in st.session_state:
                            del st.session_state.explicacion_mostrada_actual
                        st.session_state.pregunta_actual_idx -= 1; st.rerun()
            with cols_otras_acciones[1]:
                if st.button("Terminar", key="btn_terminar_ahora", help="Termina ya y ve a resultados", use_container_width=True):
                    if pregunta_id_actual not in [item['pregunta_id'] for item in st.session_state.get('respuestas_para_stats_finales', [])]:
                        _acumular_respuesta_actual_para_stats_finales(pregunta_id_actual)
                    
                    if 'explicacion_mostrada_actual' in st.session_state: del st.session_state.explicacion_mostrada_actual 
                    print("DEBUG: Cuestionario terminado manualmente, iniciando procesamiento de estadísticas en segundo plano.")
                    if st.session_state.get('respuestas_para_stats_finales'):
                        user_id_actual = st.session_state.user_info.get('id') if st.session_state.get('user_info') else None
                        if user_id_actual:
                            respuestas_a_procesar_terminar = st.session_state.respuestas_para_stats_finales[:]
                            if respuestas_a_procesar_terminar:
                                try:
                                    print(f"DEBUG UI: Iniciando hilo para {len(respuestas_a_procesar_terminar)} respuestas (Terminar).")
                                    processing_thread_terminar = threading.Thread(
                                        target=stats_handler.procesar_respuestas_del_quiz_finalizado,
                                        args=(user_id_actual, respuestas_a_procesar_terminar),
                                        daemon=True
                                    )
                                    processing_thread_terminar.start()
                                except Exception as e_thread_start_term:
                                    st.error(f"Error al iniciar el hilo de procesamiento de estadísticas (Terminar): {e_thread_start_term}")
                            
                        else:
                            st.warning("USER ID no encontrado, no se pueden procesar stats finales (Terminar).")
                        st.session_state.respuestas_para_stats_finales = [] 
                        print("DEBUG UI: 'respuestas_para_stats_finales' limpiado (Terminar).")
                        
                    st.session_state.pregunta_a_revisar_idx = None; st.session_state.estado_app = 'resultados'; st.rerun()
            with cols_otras_acciones[2]:
                if st.button("Volver a Configuración", key="btn_volver_inicio_quiz", help="Cancela y vuelve a la configuración", use_container_width=True): 
                    if 'explicacion_mostrada_actual' in st.session_state: del st.session_state.explicacion_mostrada_actual 
                    print("DEBUG: Cuestionario cancelado. Limpiando estado.")
                    st.session_state.estado_app = 'seleccion_modo'; st.session_state.modo_seleccionado = None; st.session_state.cuestionario_actual = []; st.session_state.respuestas_usuario = {}; st.session_state.entrenamiento_libre_submodo = "Aleatorio"; st.session_state.pregunta_a_revisar_idx = None
                    st.session_state.respuestas_para_stats_finales = [] 
                    st.session_state.quiz_stats_list_initialized_for_current_quiz = False 
                    st.rerun()

            try:
                js_scroll_script = """
                    <script>
                        setTimeout(function() {
                            window.parent.document.body.scrollTop = 0;
                            window.parent.document.documentElement.scrollTop = 0;
                        }, 10);
                    </script>
                """
                components.html(js_scroll_script, height=0)
            except Exception as e_comp:
                print(f"Error renderizando scroll: {e_comp}")