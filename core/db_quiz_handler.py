import random
from collections import defaultdict
import sys
import logging
import math

# --- Importaciones de módulos locales ---
from core.db_quiz_loader import obtener_ids_completos, obtener_temas_disponibles

# --- Configuración del Logger para este módulo ---
logger = logging.getLogger(__name__)

# --- Constantes ---
ID_MICROBIOLOGIA_INICIO = 1762
ESPECIALIDAD_BIOQUIMICA = 'BQ'
TAMAÑO_BLOQUE_PREGUNTAS_DB = 50

# --- Mock de Streamlit ---
try:
    import streamlit as st
except ImportError:
    logger.warning("Streamlit no encontrado. Funciones st.error/info/stop usarán logger.")
    class _MockStreamlit:
        def error(self, msg):
            logger.error(f"STREAMLIT_MOCK_ERROR: {msg}")
        def info(self, msg):
            logger.info(f"STREAMLIT_MOCK_INFO: {msg}")
        def warning(self, msg):
            logger.warning(f"STREAMLIT_MOCK_WARNING: {msg}")
        def stop(self):
            logger.critical("STREAMLIT_MOCK_CRITICAL: st.stop() fue llamado.")
            sys.exit(1) 
    st = _MockStreamlit()

# --- Funciones de Obtención de Datos para la Sesión de Quiz ---

def obtener_datos_examen(conn, examen_id):
    if examen_id is None: return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT ano, comunidad_autonoma, especialidad FROM examenes_oficiales WHERE id = %s", (examen_id,))
            resultado = cursor.fetchone()
            return dict(resultado) if resultado else None
    except Exception as e:
        logger.error(f"Error SQL obteniendo datos examen {examen_id}: {e}", exc_info=True)
        st.error("Error al obtener los datos del examen.")
        return None

def obtener_texto_escenario(conn, escenario_id):
    if escenario_id is None: return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT texto_escenario FROM escenarios WHERE id = %s", (escenario_id,))
            resultado = cursor.fetchone()
            return resultado['texto_escenario'] if resultado else None
    except Exception as e:
        logger.error(f"Error SQL obteniendo escenario {escenario_id}: {e}", exc_info=True)
        st.error("Error al obtener el caso práctico.")
        return None

# --- Funciones de Selección de Preguntas ---

def _seleccionar_ids_practicas_por_bloques(conn, n_objetivo, temas_lista=None, topic_ids=None, especialidad_usuario=None):
    if n_objetivo == 0: return []
    
    base_query = "FROM preguntas_contenido P"
    joins = []
    where_conditions = ["P.escenario_id IS NOT NULL"]
    params = []

    if especialidad_usuario == ESPECIALIDAD_BIOQUIMICA:
        # El filtro se aplica directamente sobre el tema_id de pregunta_tema.
        joins.append("JOIN pregunta_tema PT_esp ON P.id = PT_esp.pregunta_id")
        where_conditions.append("PT_esp.tema_id < %s")
        params.append(ID_MICROBIOLOGIA_INICIO)

    if topic_ids:
        ids_completos = obtener_ids_completos(conn, topic_ids, temas_lista)
        if not ids_completos:
            return []
        joins.append("JOIN pregunta_tema PT ON P.id = PT.pregunta_id")
        where_conditions.append("PT.tema_id = ANY(%s)")
        params.append(list(ids_completos))

    final_query_candidatos = f"SELECT DISTINCT P.id, P.escenario_id {base_query} {' '.join(joins)} WHERE {' AND '.join(where_conditions)}"
    
    preguntas_candidatas_raw = []
    try:
        with conn.cursor() as cursor:
            cursor.execute(final_query_candidatos, tuple(params))
            preguntas_candidatas_raw = cursor.fetchall()
    except Exception as e:
        logger.error(f"Error SQL al seleccionar candidatos prácticos: {e}", exc_info=True)
        raise

    if not preguntas_candidatas_raw:
        return []
    
    escenarios = defaultdict(list)
    for row in preguntas_candidatas_raw: 
        escenarios[row['escenario_id']].append(row['id'])
    
    lista_escenario_ids_barajados = list(escenarios.keys())
    random.shuffle(lista_escenario_ids_barajados)
    
    ids_seleccionados_final = []
    limite = float('inf') if n_objetivo == -1 else n_objetivo
    for esc_id in lista_escenario_ids_barajados:
        if len(ids_seleccionados_final) >= limite: break
        preguntas_del_escenario = sorted(escenarios[esc_id])
        for preg_id in preguntas_del_escenario:
            if len(ids_seleccionados_final) >= limite: break
            ids_seleccionados_final.append(preg_id)
            
    return ids_seleccionados_final

def _seleccionar_ids_teoricas_random(conn, n_objetivo, temas_lista=None, topic_ids=None, excluir_ids=None, especialidad_usuario=None):
    if n_objetivo == 0:
        return []

    # --- Construcción de la consulta (igual que antes) ---
    base_query = "FROM preguntas_contenido P"
    joins, where_conditions, params = [], ["P.escenario_id IS NULL"], []

    if especialidad_usuario == ESPECIALIDAD_BIOQUIMICA:
        joins.append("JOIN pregunta_tema PT_esp ON P.id = PT_esp.pregunta_id")
        where_conditions.append("PT_esp.tema_id < %s")
        params.append(ID_MICROBIOLOGIA_INICIO)

    if topic_ids:
        ids_completos = obtener_ids_completos(conn, topic_ids, temas_lista)
        if not ids_completos:
            return []
        joins.append("JOIN pregunta_tema PT ON P.id = PT.pregunta_id")
        where_conditions.append("PT.tema_id = ANY(%s)")
        params.append(list(ids_completos))

    if excluir_ids:
        where_conditions.append("P.id <> ALL(%s)")
        params.append(list(excluir_ids))

    # --- Lógica de selección con la consulta SQL corregida ---
    limit_clause = ""
    if n_objetivo > 0:
        limit_clause = "LIMIT %s"
        params.append(n_objetivo)

    # Consulta interna para obtener los IDs únicos que cumplen los filtros
    inner_query = f"""
        SELECT DISTINCT P.id 
        FROM preguntas_contenido P
        {' '.join(joins)}
        WHERE {' AND '.join(where_conditions)}
    """
    
    # Consulta externa que ordena aleatoriamente y limita los resultados de la interna
    final_query = f"""
        SELECT id FROM ({inner_query}) as distinct_ids
        ORDER BY RANDOM()
        {limit_clause}
    """
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(final_query, tuple(params))
            return [row['id'] for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error SQL al seleccionar preguntas teóricas: {e}", exc_info=True)
        raise

def _seleccionar_bloques_practicos_cualificados(conn, topic_ids, temas_lista):
    """
    Selecciona bloques de preguntas prácticas garantizando su integridad temática.
    Un bloque se considera "cualificado" si más del 50% de sus preguntas 
    pertenecen a los temas especificados (incluyendo temas hijos).
    """
    if not topic_ids:
        logger.warning("No se proporcionaron topic_ids para cualificar bloques prácticos.")
        return {}

    ids_completos_jerarquia = obtener_ids_completos(conn, topic_ids, temas_lista)
    if not ids_completos_jerarquia:
        logger.warning("La jerarquía de temas no devolvió IDs, no se pueden cualificar bloques.")
        return {}

    logger.info(f"Cualificando bloques prácticos para la jerarquía de temas: {ids_completos_jerarquia}")
    
    sql_mapa_escenarios = """
        SELECT p.id as pregunta_id, p.escenario_id, pt.tema_id
        FROM preguntas_contenido p
        JOIN pregunta_tema pt ON p.id = pt.pregunta_id
        WHERE p.escenario_id IS NOT NULL;
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql_mapa_escenarios)
            mapa_escenarios_raw = cursor.fetchall()
    except Exception as e:
        logger.error(f"Error SQL en pre-búsqueda de mapa de escenarios: {e}", exc_info=True)
        st.error("Error al analizar los casos prácticos.")
        return {}

    if not mapa_escenarios_raw: return {}

    escenarios_data = defaultdict(lambda: {'miembros': set(), 'temas': []})
    for row in mapa_escenarios_raw:
        escenarios_data[row['escenario_id']]['miembros'].add(row['pregunta_id'])
        escenarios_data[row['escenario_id']]['temas'].append(row['tema_id'])
    
    bloques_cualificados = {}
    for esc_id, data in escenarios_data.items():
        total_preguntas_en_bloque = len(data['miembros'])
        if total_preguntas_en_bloque == 0: continue
        
        coincidencias = sum(1 for tema in data['temas'] if tema in ids_completos_jerarquia)
        
        if (coincidencias / total_preguntas_en_bloque) >= 0.5:
            bloques_cualificados[esc_id] = sorted(list(data['miembros']))
            
    logger.info(f"Se cualificaron {len(bloques_cualificados)} bloques prácticos.")
    return bloques_cualificados

def obtener_preguntas_para_cuestionario(conn, config_quiz, temas_lista=None, especialidad_usuario=None):
    """
    Función principal que construye y devuelve la lista de preguntas para un quiz.
    """
    logger.info(f"Obteniendo preguntas para config: {config_quiz}, Esp: {especialidad_usuario}")
    if temas_lista is None: temas_lista = [] 

    lista_preguntas_final = []
    modo = config_quiz.get('modo')
    
    try:
        if modo == "Oficial":
            ano = config_quiz.get('ano'); ca = config_quiz.get('ca'); esp = config_quiz.get('esp')
            if not (ano and ca and esp):
                logger.warning("Faltan datos para cargar examen oficial.")
                st.error("Faltan datos para cargar el examen oficial.")
                return []

            with conn.cursor() as cursor:
                sql_oficial = """
                    SELECT
                        pc.*,
                        ep.examen_id as examen_oficial_id,
                        ep.numero_pregunta
                    FROM preguntas_contenido pc
                    JOIN examen_pregunta ep ON pc.id = ep.pregunta_id
                    JOIN examenes_oficiales eo ON ep.examen_id = eo.id
                    WHERE eo.ano = %s AND eo.comunidad_autonoma = %s AND eo.especialidad = %s
                    ORDER BY ep.numero_pregunta ASC;
                """
                cursor.execute(sql_oficial, (ano, ca, esp))
                lista_preguntas_final = [dict(row) for row in cursor.fetchall()]
                
                if not lista_preguntas_final:
                    logger.warning(f"No se encontraron preguntas para el examen {ano}-{ca}-{esp}")
                    st.error(f"No se encontraron preguntas para el examen oficial especificado.")
                else:
                    logger.info(f"Modo Oficial: Obtenidas {len(lista_preguntas_final)} preguntas.")
            
            return lista_preguntas_final

        num_preg_solicitado = config_quiz.get('numero_preguntas')
        tipo_preg = config_quiz.get('tipo_pregunta') 
        topic_ids = config_quiz.get('temas_codigos') 

        N_total = 20
        # 1. PRIMERO, comprobamos si estamos en el modo especial "Aleatorio".
        if modo == "Libre-Aleatorio":
            N_total = random.choice([20, 50, 100])
            config_quiz['numero_preguntas'] = N_total # Actualizamos el config para consistencia
        
        # 2. SI NO, entonces comprobamos si el usuario ha especificado un número o "Todas".
        elif num_preg_solicitado == "Todas":
            N_total = -1  # Valor especial para indicar "todas las preguntas"
        elif isinstance(num_preg_solicitado, int) and num_preg_solicitado > 0:
            N_total = num_preg_solicitado
        
        ids_preguntas_seleccionadas = []
        order_by_clause_final_fetch = ""

        if modo == "Libre-Personalizado":
            if tipo_preg == "Teóricas":
                ids_preguntas_seleccionadas = _seleccionar_ids_teoricas_random(conn, N_total, temas_lista, topic_ids, especialidad_usuario=especialidad_usuario)
            elif tipo_preg == "Prácticas":
                # 1. Obtenemos TODOS los bloques cualificados usando nuestra nueva función inteligente.
                bloques_candidatos = _seleccionar_bloques_practicos_cualificados(conn, topic_ids, temas_lista)

                # 2. Barajamos los bloques para que la selección sea aleatoria.
                lista_bloques = list(bloques_candidatos.values())
                random.shuffle(lista_bloques)

                # 3. Construimos la lista final de IDs, respetando el orden barajado.
                ids_seleccionadas_temp = []
                for bloque in lista_bloques:
                    ids_seleccionadas_temp.extend(bloque)

                # 4. Aseguramos que el quiz final no tenga más preguntas de las solicitadas.
                if N_total == -1:
                    ids_preguntas_seleccionadas = ids_seleccionadas_temp
                else:
                    ids_preguntas_seleccionadas = ids_seleccionadas_temp[:N_total]
                
            elif tipo_preg == "Ambas":
                # --- PASO 1: OBTENER TODOS LOS CANDIDATOS DISPONIBLES ---
                bloques_practicos_candidatos = _seleccionar_bloques_practicos_cualificados(conn, topic_ids, temas_lista)
                ids_practicos_candidatos_flat = {pid for block in bloques_practicos_candidatos.values() for pid in block}
                ids_teoricos_candidatos = _seleccionar_ids_teoricas_random(
                    conn, -1, temas_lista, topic_ids, 
                    excluir_ids=list(ids_practicos_candidatos_flat), 
                    especialidad_usuario=especialidad_usuario
                )

                # --- PASO 2: CREAR Y BARAJAR UNA LISTA ÚNICA DE "UNIDADES" ---
                unidades_practicas = list(bloques_practicos_candidatos.values())
                unidades_teoricas = [[id_teo] for id_teo in ids_teoricos_candidatos]

                todas_las_unidades = unidades_practicas + unidades_teoricas
                random.shuffle(todas_las_unidades)

                # --- PASO 3: CONSTRUIR EL QUIZ HASTA LLENARLO ---
                ids_preguntas_seleccionadas = []
                for unidad in todas_las_unidades:
                    # Si N_total es -1, siempre añadimos. Si no, comprobamos que quepa.
                    if N_total == -1 or (len(ids_preguntas_seleccionadas) + len(unidad) <= N_total):
                        ids_preguntas_seleccionadas.extend(unidad)
                    
                    # Paramos si hemos alcanzado el número deseado (y no es -1)
                    if N_total != -1 and len(ids_preguntas_seleccionadas) >= N_total:
                        ids_preguntas_seleccionadas = ids_preguntas_seleccionadas[:N_total]
                        break
                    
        elif modo == "Libre-Aleatorio":
            # --- PASO 1: OBTENER TODOS LOS CANDIDATOS (SIN FILTRO DE TEMA) ---
            # Para obtener todos los bloques, llamamos a la función con una lista vacía de temas.
            # Necesitamos una pequeña adaptación para que _seleccionar_bloques_practicos_cualificados devuelva todos si no hay topic_ids.
            # (Asumiremos por ahora que tenemos una función _obtener_todos_los_bloques_practicos)
            
            # Vamos a simplificarlo por ahora: obtenemos todos los IDs y los agrupamos.
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, escenario_id FROM preguntas_contenido WHERE escenario_id IS NOT NULL")
                rows = cursor.fetchall()
            
            bloques_practicos_candidatos = defaultdict(list)
            for row in rows:
                bloques_practicos_candidatos[row['escenario_id']].append(row['id'])

            ids_practicos_candidatos_flat = {pid for block in bloques_practicos_candidatos.values() for pid in block}
            
            # Obtenemos todos los teóricos, sin filtro de tema y excluyendo los prácticos.
            ids_teoricos_candidatos = _seleccionar_ids_teoricas_random(
                conn, -1, temas_lista, None, 
                excluir_ids=list(ids_practicos_candidatos_flat), 
                especialidad_usuario=especialidad_usuario
            )

            # --- PASO 2: APLICAR LA MISMA LÓGICA DE "OLLA" ---
            unidades_practicas = list(bloques_practicos_candidatos.values())
            unidades_teoricas = [[id_teo] for id_teo in ids_teoricos_candidatos]

            todas_las_unidades = unidades_practicas + unidades_teoricas
            random.shuffle(todas_las_unidades)

            # --- PASO 3: CONSTRUIR EL QUIZ HASTA LLENARLO ---
            ids_preguntas_seleccionadas = []
            for unidad in todas_las_unidades:
                if len(ids_preguntas_seleccionadas) + len(unidad) <= N_total:
                    ids_preguntas_seleccionadas.extend(unidad)
                
                if len(ids_preguntas_seleccionadas) == N_total:
                    break

        if ids_preguntas_seleccionadas:
            final_select_query = """
            SELECT P.*, ep.examen_id as examen_oficial_id
            FROM preguntas_contenido P
            LEFT JOIN examen_pregunta ep ON P.id = ep.pregunta_id
            WHERE P.id = ANY(%s)
            """
            query_final_con_orden = f"{final_select_query} {order_by_clause_final_fetch if order_by_clause_final_fetch else ''}"
            
            with conn.cursor() as cursor:
                cursor.execute(query_final_con_orden, (list(ids_preguntas_seleccionadas),))
                lista_preguntas_final = [dict(row) for row in cursor.fetchall()]

            if not order_by_clause_final_fetch and modo != "Oficial":
                preg_map = {p['id']: p for p in lista_preguntas_final}
                lista_preguntas_final = [preg_map[id_val] for id_val in ids_preguntas_seleccionadas if id_val in preg_map]

            
        else:
            logger.info("No se seleccionaron IDs de preguntas según los criterios.")
            if modo and modo != "Libre-Aleatorio": 
                st.warning("No se encontraron preguntas que cumplan los criterios seleccionados.")
            
    except Exception as e:
        logger.error(f"Error SQL general en obtener_preguntas: {e}", exc_info=True)
        st.error(f"Error de base de datos al obtener preguntas.")
        return []
    
    logger.info(f"obtener_preguntas_para_cuestionario devolviendo {len(lista_preguntas_final)} preguntas.")
    return lista_preguntas_final

def get_temas_directos_pregunta(conn, pregunta_id):
    """Obtiene los IDs de los temas directamente asociados a una pregunta."""
    tema_ids = []
    try:
        with conn.cursor() as cursor:
            query = "SELECT tema_id FROM pregunta_tema WHERE pregunta_id = %s;"
            cursor.execute(query, (pregunta_id,))
            resultados = cursor.fetchall()
            tema_ids = [row['tema_id'] for row in resultados]
    except Exception as e:
        logger.error(f"Error SQL al obtener temas directos para P_ID {pregunta_id}: {e}", exc_info=True)
        return []
    return tema_ids

def get_pregunta_detalle_por_id(conn, pregunta_id):
    """Obtiene los detalles esenciales de una pregunta para la lógica de stats."""
    try:
        with conn.cursor() as cursor:
            query = "SELECT id, enunciado, respuesta_correcta FROM preguntas_contenido WHERE id = %s"
            cursor.execute(query, (pregunta_id,))
            pregunta = cursor.fetchone()
            return dict(pregunta) if pregunta else None
    except Exception as e:
        logger.error(f"Error SQL en get_pregunta_detalle_por_id para {pregunta_id}: {e}", exc_info=True)
        return None

def obtener_total_respuestas_previas_usuario(conn, usuario_id):
    """Obtiene el número total de respuestas que un usuario ha dado."""
    try:
        with conn.cursor() as cursor:
            query = "SELECT total_respuestas FROM stats_agregadas_usuario_global WHERE usuario_id = %s"
            cursor.execute(query, (usuario_id,))
            resultado = cursor.fetchone()
            return resultado['total_respuestas'] if resultado and resultado['total_respuestas'] is not None else 0
    except Exception as e:
        logger.error(f"Error obteniendo total_respuestas_previas para {usuario_id}: {e}", exc_info=True)
        st.error("Error crítico al obtener el historial de respuestas del usuario.")
        raise

def obtener_explicacion_pregunta(conn, pregunta_id):
    """Obtiene la explicación pre-generada para una pregunta específica."""
    if pregunta_id is None:
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT explicacion FROM explained_questions WHERE pregunta_id = %s", (pregunta_id,))
            resultado = cursor.fetchone()
            if resultado and resultado['explicacion']:
                # El campo 'explicacion' es JSONB, psycopg2 lo decodifica automáticamente
                return resultado['explicacion']
            else:
                logger.warning(f"No se encontró explicación en la BD para la pregunta ID: {pregunta_id}")
                return None # No se encontró explicación
    except Exception as e:
        logger.error(f"Error SQL obteniendo explicación para pregunta {pregunta_id}: {e}", exc_info=True)
        st.error("Error al obtener la explicación de la pregunta.")
        return None    