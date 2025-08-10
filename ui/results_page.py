import streamlit as st

# Importaciones de tus módulos refactorizados
from core.database import conectar_db
from core.db_quiz_handler import obtener_texto_escenario 
from ui.dialogs import mostrar_dialogo_revision 

# --- Función Principal de la Sección de Resultados ---
def display_results_section():
    st.header("Resultados ")
    st.write("")

    # --- Recuperar datos del estado ---
    cuestionario = st.session_state.get('cuestionario_actual', [])
    respuestas = st.session_state.get('respuestas_usuario', {})
    total_preguntas_quiz = len(cuestionario)
    
    # Asegurar inicialización de estado para esta pantalla
    if 'pregunta_a_revisar_idx' not in st.session_state: st.session_state.pregunta_a_revisar_idx = None
    if 'review_filter' not in st.session_state: st.session_state.review_filter = "incorrecta"

    # --- Manejo si no hay cuestionario ---
    if not cuestionario:
        st.warning("No hay datos del cuestionario para mostrar resultados.")
        if st.button("Volver a Configuración", key="btn_volver_a_config_no_q"):
            st.session_state.estado_app = 'configuracion'
            st.session_state.cuestionario_actual = []
            st.session_state.pregunta_actual_idx = 0
            st.session_state.respuestas_usuario = {}
            st.rerun()
    else:
        # --- Calcular Estadísticas Agregadas Básicas ---
        total_correctas = 0
        total_incorrectas = 0
        total_sin_responder = 0
        
        for i, pregunta in enumerate(cuestionario):
            pid = pregunta.get('id', f"idx_{i}")
            r_correcta = pregunta.get('respuesta_correcta')
            r_user = respuestas.get(pid)
            status = 'sin_responder'
            if r_user is not None:
                status = 'correcta' if r_user == r_correcta else 'incorrecta'

            if status == 'correcta': total_correctas += 1
            elif status == 'incorrecta': total_incorrectas += 1
            else: total_sin_responder += 1

        # --- Resumen General (Texto en Columnas) ---
        perc_c = 0.0
        perc_i = 0.0
        perc_s = 0.0
        if total_preguntas_quiz > 0:
            perc_c = (total_correctas / total_preguntas_quiz) * 100
            perc_i = (total_incorrectas / total_preguntas_quiz) * 100
            perc_s = (total_sin_responder / total_preguntas_quiz) * 100
        
        col1, col2, col3 = st.columns(3)
        with col1: st.markdown(f'<div class="metric-container"><p class="metric-label">🟢 Correctas</p><p class="metric-perc">{perc_c:.1f}%</p><p class="metric-count">{total_correctas} de {total_preguntas_quiz}</p></div>', unsafe_allow_html=True)
        with col2: st.markdown(f'<div class="metric-container"><p class="metric-label">🔴 Incorrectas</p><p class="metric-perc">{perc_i:.1f}%</p><p class="metric-count">{total_incorrectas} de {total_preguntas_quiz}</p></div>', unsafe_allow_html=True)
        with col3: st.markdown(f'<div class="metric-container"><p class="metric-label">⚪ Sin Responder</p><p class="metric-perc">{perc_s:.1f}%</p><p class="metric-count">{total_sin_responder} de {total_preguntas_quiz}</p></div>', unsafe_allow_html=True)
        
        st.divider()

        # --- MODIFICACIÓN: Contenido de Revisión Individual (sin pestañas) ---
        st.subheader("Revisión de preguntas")
        #st.markdown("Filtrar Revisión")
        filter_options = ["Todas", "🟢 Correctas", "🔴 Incorrectas", "⚪ Sin Responder"]
        filter_map = {"Todas":"Todas", "🟢 Correctas":"correcta", "🔴 Incorrectas":"incorrecta", "⚪ Sin Responder":"sin_responder"}
        current_filter_val = st.session_state.review_filter
        
        cols_filter = st.columns(len(filter_options))
        for i, option_label in enumerate(filter_options):
            with cols_filter[i]:
                filter_key = filter_map[option_label]
                is_active = (current_filter_val == filter_key)
                if st.button(option_label, key=f"btn_filter_{filter_key}", use_container_width=True, type=('primary' if is_active else 'secondary')):
                    if not is_active:
                        st.session_state.review_filter = filter_key
                        st.session_state.pregunta_a_revisar_idx = None
                        st.rerun()

        # Filtrar preguntas
        preguntas_a_mostrar = []
        filtro_activo = st.session_state.review_filter
        for i, p in enumerate(cuestionario):
            pid = p.get('id', f"idx_{i}")
            r_user = respuestas.get(pid)
            r_corr = p.get('respuesta_correcta')
            status = "sin_responder"
            if r_user is not None:
                status = "correcta" if r_user == r_corr else "incorrecta"
            if filtro_activo == "Todas" or filtro_activo == status:
                preguntas_a_mostrar.append((i, p))

        st.markdown("---")

        # Generar cuadrícula
        if not preguntas_a_mostrar:
            st.info(f"No hay preguntas en la categoría '{filtro_activo}'.")
        else:
            # --- MODIFICACIÓN: Cambiado a 2 columnas ---
            num_cols_grid = 2
            num_preguntas_filtradas = len(preguntas_a_mostrar)
            num_rows = (num_preguntas_filtradas + num_cols_grid - 1) // num_cols_grid
            
            for row_num in range(num_rows):
                cols = st.columns(num_cols_grid)
                for col_num in range(num_cols_grid):
                    item_index = row_num * num_cols_grid + col_num
                    if item_index < num_preguntas_filtradas:
                        original_idx, pregunta = preguntas_a_mostrar[item_index]
                        pid = pregunta.get('id', f"idx_{original_idx}")
                        r_user = respuestas.get(pid)
                        r_corr = pregunta.get('respuesta_correcta')
                        status = "sin_responder"
                        if r_user is not None:
                            status = "correcta" if r_user == r_corr else "incorrecta"
                        
                        with cols[col_num]:
                            label_btn = f"🟢 {original_idx+1}" if status=="correcta" else (f"🔴 {original_idx+1}" if status=="incorrecta" else f"⚪ {original_idx+1}")
                            # --- CORRECCIÓN: Se añade el índice original a la clave para garantizar unicidad ---
                            if st.button(label_btn, key=f"review_btn_{pid}_{original_idx}", use_container_width=True):
                                st.session_state.pregunta_a_revisar_idx = original_idx
                                st.rerun()
                    else:
                        with cols[col_num]:
                            pass # No mostrar nada en columnas vacías

        # Diálogo de Revisión (llamada condicional)
        idx_para_revisar = st.session_state.get('pregunta_a_revisar_idx')
        if idx_para_revisar is not None:
            pregunta_para_dialogo = cuestionario[idx_para_revisar] 
            id_escenario_para_dialogo = pregunta_para_dialogo.get('escenario_id')
            texto_escenario_obtenido_para_dialogo = None

            if id_escenario_para_dialogo:
                conn_dialog_rev_esc = None
                try:
                    conn_dialog_rev_esc = conectar_db()
                    if conn_dialog_rev_esc:
                        texto_escenario_obtenido_para_dialogo = obtener_texto_escenario(
                            conn_dialog_rev_esc, 
                            id_escenario_para_dialogo
                        )
                        if not texto_escenario_obtenido_para_dialogo:
                            print(f"WARN RESULTS_PAGE: No se encontró texto para escenario ID {id_escenario_para_dialogo} en revisión.")
                except Exception as e_dlg_esc:
                    print(f"Error obteniendo escenario para diálogo de revisión: {e_dlg_esc}")
                finally:
                    if conn_dialog_rev_esc and not conn_dialog_rev_esc.closed:
                        conn_dialog_rev_esc.close()
            
            mostrar_dialogo_revision(
                idx_para_revisar,
                cuestionario,
                respuestas,
                texto_escenario_obtenido_para_dialogo
            )

        # --- Botón Final Volver ---
        st.divider()
        col_nav_res1, col_nav_res2 = st.columns([3, 1])
        with col_nav_res1: pass
        with col_nav_res2:
            if st.button("Volver a Configuración", key="btn_volver_a_config_tabs", use_container_width=True):
                st.session_state.estado_app = 'configuracion'
                st.session_state.cuestionario_actual = []
                st.session_state.pregunta_actual_idx = 0
                st.session_state.respuestas_usuario = {}
                st.session_state.pregunta_a_revisar_idx = None
                st.rerun()