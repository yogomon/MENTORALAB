# stats_handler.py
import logging
import datetime
from datetime import datetime as dt
from psycopg2 import sql

# MODIFICACIÓN: Importar desde los nuevos módulos refactorizados
from core.database import conectar_db
from .db_quiz_handler import get_temas_directos_pregunta, get_pregunta_detalle_por_id, obtener_total_respuestas_previas_usuario

# --- Configuración Global ---
TAMAÑO_BLOQUE_PREGUNTAS = 50

# --- Configuración del Logger ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - STATS_HANDLER - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- Funciones Auxiliares para Actualizar Estadísticas ---

def _registrar_respuesta_usuario_y_stats_pregunta(
    cursor, usuario_id, pregunta_id, respuesta_seleccionada_db, 
    es_correcta, tiempo_respuesta_ms, fecha_respuesta):
    """
    1. Inserta la respuesta individual en stats_respuestas_usuario.
    2. Actualiza las estadísticas agregadas para esa pregunta en stats_agregadas_pregunta.
    """
    respuesta_id_insertada = None
    try:
        sql_insert_respuesta = """
        INSERT INTO stats_respuestas_usuario 
            (usuario_id, pregunta_id, respuesta_seleccionada, es_correcta, tiempo_respuesta_ms, fecha_respuesta)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id;
        """
        cursor.execute(sql_insert_respuesta, (
            usuario_id, pregunta_id, respuesta_seleccionada_db, 
            es_correcta, tiempo_respuesta_ms, fecha_respuesta
        ))
        respuesta_id_insertada = cursor.fetchone()[0]

        tiempo_para_suma = tiempo_respuesta_ms if respuesta_seleccionada_db != 'TIMEOUT' and tiempo_respuesta_ms is not None else 0
        incremento_contador_tiempo = 1 if tiempo_para_suma > 0 else 0
        
        sql_update_stats_pregunta = """
        INSERT INTO stats_agregadas_pregunta 
            (pregunta_id, total_respuestas, total_correctas, total_incorrectas, 
             suma_tiempo_respuesta_ms, num_respuestas_con_tiempo)
        VALUES (%s, 1, %s, %s, %s, %s)
        ON CONFLICT (pregunta_id) DO UPDATE SET
            total_respuestas = stats_agregadas_pregunta.total_respuestas + 1,
            total_correctas = stats_agregadas_pregunta.total_correctas + EXCLUDED.total_correctas,
            total_incorrectas = stats_agregadas_pregunta.total_incorrectas + EXCLUDED.total_incorrectas,
            suma_tiempo_respuesta_ms = stats_agregadas_pregunta.suma_tiempo_respuesta_ms + EXCLUDED.suma_tiempo_respuesta_ms,
            num_respuestas_con_tiempo = stats_agregadas_pregunta.num_respuestas_con_tiempo + EXCLUDED.num_respuestas_con_tiempo;
        """
        cursor.execute(sql_update_stats_pregunta, (
            pregunta_id, 
            1 if es_correcta else 0, 
            1 if not es_correcta else 0, 
            tiempo_para_suma, 
            incremento_contador_tiempo
        ))
    except Exception as e_db:
        logger.error(f"Error en _registrar_respuesta_usuario_y_stats_pregunta para P_ID {pregunta_id}: {e_db}", exc_info=True)
        raise
    return respuesta_id_insertada

def _registrar_respuesta_tema_detalle(cursor, respuesta_usuario_id, pregunta_id, es_correcta, conn_db):
    """
    Inserta la relación entre la respuesta y sus temas en stats_respuestas_usuario_tema_detalle.
    """
    if respuesta_usuario_id is None:
        return

    temas_ids = get_temas_directos_pregunta(conn_db, pregunta_id)
    if not temas_ids:
        return

    sql_insert_tema_detalle = """
    INSERT INTO stats_respuestas_usuario_tema_detalle
        (respuesta_usuario_id, tema_id, es_correcta_en_contexto)
    VALUES (%s, %s, %s)
    ON CONFLICT (respuesta_usuario_id, tema_id) DO NOTHING;
    """
    for tema_id in temas_ids:
        try:
            cursor.execute(sql_insert_tema_detalle, (respuesta_usuario_id, tema_id, es_correcta))
        except Exception as e_db:
            logger.error(f"Error insertando en stats_respuestas_usuario_tema_detalle (resp_id {respuesta_usuario_id}, tema_id {tema_id}): {e_db}", exc_info=True)

def _actualizar_stats_agregadas_usuario_tema(
    cursor, usuario_id, temas_ids, es_correcta, 
    respuesta_seleccionada_db, tiempo_respuesta_ms):
    """
    Actualiza stats_agregadas_usuario_tema para los temas indicados.
    """
    if not temas_ids:
        return

    tiempo_para_suma = tiempo_respuesta_ms if respuesta_seleccionada_db != 'TIMEOUT' and tiempo_respuesta_ms is not None else 0
    incremento_contador_tiempo = 1 if tiempo_para_suma > 0 else 0

    sql_update_stats_tema = """
    INSERT INTO stats_agregadas_usuario_tema 
        (usuario_id, tema_id, total_respuestas, total_correctas, total_incorrectas, 
         suma_tiempo_respuesta_ms, num_respuestas_con_tiempo, ultimo_uso)
    VALUES (%s, %s, 1, %s, %s, %s, %s, CURRENT_TIMESTAMP)
    ON CONFLICT (usuario_id, tema_id) DO UPDATE SET
        total_respuestas = stats_agregadas_usuario_tema.total_respuestas + 1,
        total_correctas = stats_agregadas_usuario_tema.total_correctas + EXCLUDED.total_correctas,
        total_incorrectas = stats_agregadas_usuario_tema.total_incorrectas + EXCLUDED.total_incorrectas,
        suma_tiempo_respuesta_ms = stats_agregadas_usuario_tema.suma_tiempo_respuesta_ms + EXCLUDED.suma_tiempo_respuesta_ms,
        num_respuestas_con_tiempo = stats_agregadas_usuario_tema.num_respuestas_con_tiempo + EXCLUDED.num_respuestas_con_tiempo,
        ultimo_uso = CURRENT_TIMESTAMP;
    """
    for tema_id in temas_ids:
        try:
            cursor.execute(sql_update_stats_tema, (
                usuario_id, tema_id, 
                1 if es_correcta else 0, 
                1 if not es_correcta else 0, 
                tiempo_para_suma, 
                incremento_contador_tiempo
            ))
        except Exception as e_db:
            logger.error(f"Error actualizando stats_agregadas_usuario_tema (user {usuario_id}, tema {tema_id}): {e_db}", exc_info=True)
            raise

def _actualizar_stats_agregadas_usuario_global(cursor, usuario_id, es_correcta):
    """
    Actualiza stats_agregadas_usuario_global.
    """
    sql_update_stats_global = """
    INSERT INTO stats_agregadas_usuario_global 
        (usuario_id, total_respuestas, total_aciertos, total_errores, 
         porcentaje_aciertos, porcentaje_errores, ultima_actualizacion)
    VALUES (%s, 1, %s, %s, %s, %s, CURRENT_TIMESTAMP)
    ON CONFLICT (usuario_id) DO UPDATE SET
        total_respuestas = stats_agregadas_usuario_global.total_respuestas + 1,
        total_aciertos = stats_agregadas_usuario_global.total_aciertos + EXCLUDED.total_aciertos,
        total_errores = stats_agregadas_usuario_global.total_errores + EXCLUDED.total_errores,
        porcentaje_aciertos = ROUND(((stats_agregadas_usuario_global.total_aciertos + EXCLUDED.total_aciertos) * 100.0) / NULLIF(stats_agregadas_usuario_global.total_respuestas + 1, 0), 2),
        porcentaje_errores = ROUND(((stats_agregadas_usuario_global.total_errores + EXCLUDED.total_errores) * 100.0) / NULLIF(stats_agregadas_usuario_global.total_respuestas + 1, 0), 2),
        ultima_actualizacion = CURRENT_TIMESTAMP;
    """
    acierto_val = 1 if es_correcta else 0
    error_val = 1 if not es_correcta else 0
    porc_acierto_inicial = 100.0 if es_correcta else 0.0
    porc_error_inicial = 0.0 if es_correcta else 100.0
    try:
        cursor.execute(sql_update_stats_global, (
            usuario_id, acierto_val, error_val, 
            porc_acierto_inicial, porc_error_inicial
        ))
    except Exception as e_db:
        logger.error(f"Error actualizando stats_agregadas_usuario_global para user {usuario_id}: {e_db}", exc_info=True)
        raise

def _actualizar_estadisticas_temporales(cursor, usuario_id, es_correcta, fecha_respuesta, tipo_temporal):
    """
    Actualiza las estadísticas temporales (diarias, semanales, mensuales) para un usuario.
    """
    logger.debug(f"Actualizando stats {tipo_temporal} para usuario {usuario_id}.")
    
    if tipo_temporal == 'diario':
        fecha_periodo_actual = fecha_respuesta.date()
        fecha_periodo_anterior = fecha_periodo_actual - datetime.timedelta(days=1)
        tabla_stats, col_fecha, prefijo_cols = 'stats_usuario_tiempo_diario', 'fecha', 'dia'
    elif tipo_temporal == 'semanal':
        fecha_periodo_actual = fecha_respuesta.date() - datetime.timedelta(days=fecha_respuesta.weekday())
        fecha_periodo_anterior = fecha_periodo_actual - datetime.timedelta(weeks=1)
        tabla_stats, col_fecha, prefijo_cols = 'stats_usuario_tiempo_semanal', 'fecha_inicio_semana', 'semana'
    elif tipo_temporal == 'mensual':
        fecha_periodo_actual = fecha_respuesta.date().replace(day=1)
        ultimo_dia_mes_pasado = fecha_periodo_actual - datetime.timedelta(days=1)
        fecha_periodo_anterior = ultimo_dia_mes_pasado.replace(day=1)
        tabla_stats, col_fecha, prefijo_cols = 'stats_usuario_tiempo_mensual', 'fecha_inicio_mes', 'mes'
    else:
        logger.warning(f"Tipo temporal '{tipo_temporal}' no reconocido.")
        return

    resp_col = f"respuestas_{prefijo_cols}"
    aciertos_col = f"aciertos_{prefijo_cols}"
    errores_col = f"errores_{prefijo_cols}"
    p_aciertos_col = f"porcentaje_aciertos_{prefijo_cols}"
    p_errores_col = f"porcentaje_errores_{prefijo_cols}"
    var_p_aciertos_col = f"variacion_porcentaje_aciertos_{prefijo_cols}_anterior"
    var_p_errores_col = f"variacion_porcentaje_errores_{prefijo_cols}_anterior"

    porc_aciertos_anterior_db = 0.00
    sql_get_anterior = sql.SQL(
        "SELECT {col_p_aciertos} FROM {tabla} WHERE usuario_id = %s AND {col_fecha_ref} = %s"
    ).format(
        col_p_aciertos=sql.Identifier(p_aciertos_col),
        tabla=sql.Identifier(tabla_stats),
        col_fecha_ref=sql.Identifier(col_fecha)
    )
    try:
        cursor.execute(sql_get_anterior, (usuario_id, fecha_periodo_anterior.strftime('%Y-%m-%d')))
        res_anterior = cursor.fetchone()
        if res_anterior:
            porc_aciertos_anterior_db = res_anterior[0] if res_anterior[0] is not None else 0.00
    except Exception as e_get_ant:
        logger.warning(f"No se pudo obtener stats del periodo anterior para {tipo_temporal} {usuario_id}: {e_get_ant}")

    query_template = sql.SQL("""
    INSERT INTO {tabla} (
        usuario_id, {col_fecha_ref}, 
        {col_resp}, {col_aciertos}, {col_errores}, 
        {col_p_aciertos}, {col_p_errores},
        {col_var_p_aciertos}
    )
    VALUES (%s, %s, 1, %s, %s, %s, %s, %s)
    ON CONFLICT (usuario_id, {col_fecha_ref}) DO UPDATE SET
        {col_resp} = {tabla}.{col_resp} + 1,
        {col_aciertos} = {tabla}.{col_aciertos} + EXCLUDED.{col_aciertos},
        {col_errores} = {tabla}.{col_errores} + EXCLUDED.{col_errores},
        {col_p_aciertos} = ROUND((({tabla}.{col_aciertos} + EXCLUDED.{col_aciertos}) * 100.0) / ({tabla}.{col_resp} + 1), 2),
        {col_p_errores} = ROUND((({tabla}.{col_errores} + EXCLUDED.{col_errores}) * 100.0) / ({tabla}.{col_resp} + 1), 2),
        {col_var_p_aciertos} = ROUND((({tabla}.{col_aciertos} + EXCLUDED.{col_aciertos}) * 100.0) / ({tabla}.{col_resp} + 1), 2) - %s;
    """)
    
    final_query = query_template.format(
        tabla=sql.Identifier(tabla_stats), col_fecha_ref=sql.Identifier(col_fecha),
        col_resp=sql.Identifier(resp_col), col_aciertos=sql.Identifier(aciertos_col), col_errores=sql.Identifier(errores_col),
        col_p_aciertos=sql.Identifier(p_aciertos_col), col_p_errores=sql.Identifier(p_errores_col),
        col_var_p_aciertos=sql.Identifier(var_p_aciertos_col)
    )

    acierto_val = 1 if es_correcta else 0
    error_val = 1 if not es_correcta else 0
    p_acierto_inicial = 100.0 if es_correcta else 0.0
    p_error_inicial = 0.0 if es_correcta else 100.0
    var_p_acierto_inicial = p_acierto_inicial - porc_aciertos_anterior_db
    
    try:
        cursor.execute(final_query, (
            usuario_id, fecha_periodo_actual.strftime('%Y-%m-%d'),
            acierto_val, error_val,
            p_acierto_inicial, p_error_inicial,
            var_p_acierto_inicial,
            porc_aciertos_anterior_db
        ))
    except Exception as e_db:
        logger.error(f"Error actualizando stats temporales ({tipo_temporal}) para {usuario_id}: {e_db}", exc_info=True)
        raise

def _procesar_estadisticas_respuesta_individual(
    cursor, conn_db, usuario_id, pregunta_id, respuesta_seleccionada_original_ui, 
    tiempo_respuesta_ms, fecha_respuesta_dt_obj, global_question_seq_num):
    """
    Orquesta todas las actualizaciones de estadísticas para una sola respuesta.
    """
    pregunta_db_details = get_pregunta_detalle_por_id(conn_db, pregunta_id)
    if not pregunta_db_details or pregunta_db_details.get('respuesta_correcta') is None:
        logger.warning(f"No se pudieron obtener detalles para P_ID {pregunta_id}. Saltando stats.")
        return False 

    respuesta_correcta_db = pregunta_db_details.get('respuesta_correcta')
    es_correcta = False
    respuesta_seleccionada_db = 'TIMEOUT'

    if respuesta_seleccionada_original_ui is not None and str(respuesta_seleccionada_original_ui).strip() != "":
        respuesta_seleccionada_db = str(respuesta_seleccionada_original_ui).upper()
        if respuesta_seleccionada_db in ('A', 'B', 'C', 'D'):
            es_correcta = (respuesta_seleccionada_db == str(respuesta_correcta_db).upper())

    tiempo_efectivo_para_promedios = tiempo_respuesta_ms
    if respuesta_seleccionada_db == 'TIMEOUT':
        tiempo_efectivo_para_promedios = None 

    respuesta_id = _registrar_respuesta_usuario_y_stats_pregunta(
        cursor, usuario_id, pregunta_id, respuesta_seleccionada_db,
        es_correcta, tiempo_respuesta_ms, fecha_respuesta_dt_obj
    )
    if respuesta_id is None: return False

    temas_ids = get_temas_directos_pregunta(conn_db, pregunta_id)
    _registrar_respuesta_tema_detalle(cursor, respuesta_id, pregunta_id, es_correcta, conn_db)

    _actualizar_stats_agregadas_usuario_tema(
        cursor, usuario_id, temas_ids, es_correcta, 
        respuesta_seleccionada_db, tiempo_efectivo_para_promedios
    )
    _actualizar_stats_agregadas_usuario_global(cursor, usuario_id, es_correcta)
    
    for tipo_temp in ['diario', 'semanal', 'mensual']:
        _actualizar_estadisticas_temporales(cursor, usuario_id, es_correcta, fecha_respuesta_dt_obj, tipo_temp)

    return True

def procesar_respuestas_del_quiz_finalizado(usuario_id, respuestas_acumuladas_ui):
    logger.info(f"INICIO PROCESAMIENTO QUIZ para Usuario ID: {usuario_id}, {len(respuestas_acumuladas_ui)} respuestas.")
    if not respuestas_acumuladas_ui:
        logger.info("No hay respuestas para procesar.")
        return
        
    conn = None
    try:
        conn = conectar_db()
        
        global_question_count_before_quiz = obtener_total_respuestas_previas_usuario(conn, usuario_id)
        
        current_global_question_seq_num = global_question_count_before_quiz

        with conn.cursor() as cursor:
            for idx, resp_ui_data in enumerate(respuestas_acumuladas_ui):
                pregunta_id_raw = resp_ui_data.get('pregunta_id')
                fecha_respuesta_str = resp_ui_data.get('fecha_respuesta')

                if pregunta_id_raw is None or fecha_respuesta_str is None:
                    continue
                try:
                    pregunta_id = int(pregunta_id_raw)
                    fecha_respuesta_dt_obj = dt.fromisoformat(fecha_respuesta_str)
                except ValueError:
                    continue

                current_global_question_seq_num += 1
                
                _procesar_estadisticas_respuesta_individual(
                    cursor, conn, usuario_id, pregunta_id, 
                    resp_ui_data.get('respuesta_usuario'), resp_ui_data.get('tiempo_respuesta_ms'), fecha_respuesta_dt_obj,
                    current_global_question_seq_num
                )

        conn.commit()
        logger.info("COMMIT REALIZADO. Estadísticas del quiz procesadas.")

    except Exception as e_db_main:
        logger.critical(f"ERROR DE BD CRÍTICO durante procesamiento del quiz: {e_db_main}", exc_info=True)
        if conn:
            try: conn.rollback(); logger.info("ROLLBACK realizado.")
            except Exception as e_rb: logger.error(f"Error durante ROLLBACK: {e_rb}", exc_info=True)
    except Exception as e_main:
        logger.critical(f"ERROR GENERAL CRÍTICO durante procesamiento del quiz: {e_main}", exc_info=True)
        if conn:
            try: conn.rollback(); logger.info("ROLLBACK realizado.")
            except Exception as e_rb: logger.error(f"Error durante ROLLBACK: {e_rb}", exc_info=True)
    finally:
        if conn:
            try: 
                conn.close()
                logger.info("Conexión a BD cerrada.")
            except Exception as e_cl: logger.error(f"Error al cerrar conexión: {e_cl}", exc_info=True)
