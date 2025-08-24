import random
from collections import defaultdict
from utils.helpers import clave_ordenacion_natural # Asegúrate que esta importación sea correcta
import sys
import logging

# --- Configuración del Logger para este módulo ---
logger = logging.getLogger(__name__)

class DatabaseConnectionError(Exception):
    """Excepción personalizada para problemas al conectar con la base de datos."""
    pass

# --- Constantes ---
ID_MICROBIOLOGIA_INICIO = 1762
ESPECIALIDAD_BIOQUIMICA = 'BQ'

# --- Mock de Streamlit (ahora usando logger) ---
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

# --- Funciones de Obtención de Datos para Configuración ---
def obtener_temas_disponibles(conn, especialidad_usuario=None):
    temas_lista = []
    try:
        with conn.cursor() as cursor:
            query = "SELECT id, codigo, nombre, original_id FROM temas_manual WHERE codigo IS NOT NULL AND nombre IS NOT NULL AND nombre != ''"
            params = []
            if especialidad_usuario == ESPECIALIDAD_BIOQUIMICA:
                # CORRECCIÓN: El filtro ahora se aplica sobre la columna 'id' de temas_manual.
                query += " AND id < %s"
                params.append(ID_MICROBIOLOGIA_INICIO)
            query += " ORDER BY codigo"
            
            cursor.execute(query, tuple(params))
            resultados = cursor.fetchall()
            for row in resultados:
                temas_lista.append({
                    'id': int(row['id']), 
                    'codigo': str(row['codigo']), 
                    'nombre': row['nombre'],
                    'original_id': int(row['original_id'])
                })
    except Exception as e:
        logger.error(f"Error SQL al obtener temas: {e}", exc_info=True)
        st.error("Error al cargar la lista de temas desde la base de datos.") 
        return [] 
    return temas_lista


def obtener_examenes_disponibles(conn):
    examenes = []
    try:
        with conn.cursor() as cursor:
            query = "SELECT DISTINCT ano, comunidad_autonoma, especialidad FROM examenes_oficiales ORDER BY ano DESC, comunidad_autonoma ASC, especialidad ASC;"
            cursor.execute(query)
            resultados = cursor.fetchall()
            examenes = [dict(row) for row in resultados]
    except Exception as e:
        logger.error(f"Error SQL al obtener lista de exámenes: {e}", exc_info=True)
        st.error("Error al cargar la lista de exámenes desde la base de datos.")
        return []
    return examenes

# --- Funciones Auxiliares para Selección de Temas ---
def expandir_temas_ids(selected_ids, temas_lista):
    if not selected_ids or not temas_lista: 
        return set(selected_ids)
    try:
        id_to_codigo = {tema['id']: tema['codigo'] for tema in temas_lista}
        codigo_to_id = {v: k for k, v in id_to_codigo.items()}
        all_topic_codes_set = set(id_to_codigo.values())
        
        initial_selected_ids_set = set(selected_ids)
        expanded_ids_set = set(initial_selected_ids_set) 
        codes_to_expand = {id_to_codigo[sid] for sid in initial_selected_ids_set if sid in id_to_codigo}
        
        processed_codes = set()
        queue = list(codes_to_expand)

        while queue:
            code_str = queue.pop(0)
            if code_str in processed_codes: continue
            processed_codes.add(code_str)
            prefix = code_str + '.'
            for potential_child_code in all_topic_codes_set:
                if potential_child_code.startswith(prefix):
                    child_id = codigo_to_id.get(potential_child_code)
                    if child_id is not None:
                        expanded_ids_set.add(child_id)
                        if potential_child_code not in processed_codes:
                            queue.append(potential_child_code)
                            
        return expanded_ids_set
    except Exception as e:
        logger.error(f"Error inesperado en expandir_temas_ids: {e}", exc_info=True)
        return set(selected_ids)

def obtener_ids_completos(conn, selected_ids, temas_lista=None):
    if not conn:
        logger.error("Se requiere conexión a BD para obtener_ids_completos.")
        st.error("Error de conexión para obtener la lista completa de temas.")
        return set()

    local_temas_lista = temas_lista
    if local_temas_lista is None:
        local_temas_lista = obtener_temas_disponibles(conn)
        if not local_temas_lista:
            st.warning("No se pudieron obtener los temas disponibles para la expansión.")

    if not selected_ids: 
        return set()
        
    initial_selected_ids = set(selected_ids) 
    
    ids_finales = expandir_temas_ids(initial_selected_ids, local_temas_lista)
    
    if not ids_finales:
        return ids_finales

    #try:
        with conn.cursor() as cursor:
            related_group_ids = set()
            query_grupos = "SELECT DISTINCT grupo_id FROM tema_en_grupo WHERE tema_id = ANY(%s)"
            cursor.execute(query_grupos, (list(ids_finales),))
            related_group_ids.update(row['grupo_id'] for row in cursor.fetchall())

            if related_group_ids:
                query_temas_grupo = "SELECT DISTINCT tema_id FROM tema_en_grupo WHERE grupo_id = ANY(%s)"
                cursor.execute(query_temas_grupo, (list(related_group_ids),))
                newly_found_ids_from_groups = {row['tema_id'] for row in cursor.fetchall()}
                ids_finales.update(newly_found_ids_from_groups)

    #except Exception as e:
        logger.error(f"Error SQL buscando temas por grupo: {e}", exc_info=True)
        st.error("Error al buscar temas relacionados por grupo.") 
        return expandir_temas_ids(initial_selected_ids, local_temas_lista)
    
    logger.info(f"Expansión completa finalizada. Total de IDs de temas (de temas_manual): {len(ids_finales)}")
    return ids_finales

def format_topics_for_tree(temas_lista):
    if not temas_lista: 
        return []

    nodes_dict = {}
    id_to_codigo_map = {} 

    for tema in temas_lista:
        theme_id = tema.get('id')
        code_str = tema.get('codigo')
        nombre = tema.get('nombre', 'Nombre Desconocido')
        if theme_id is None or not code_str: 
            continue

        id_to_codigo_map[theme_id] = code_str
        nodes_dict[code_str] = {
            "label": f"{code_str} - {nombre}", 
            "value": str(theme_id), 
            "children": [],
            "showCheckbox": True, 
            "expanded": False 
        }

    root_nodes_list = []
    
    for code_str, node_data in nodes_dict.items():
        if '.' not in code_str:
            root_nodes_list.append(node_data)
        else:
            parent_code = code_str.rsplit('.', 1)[0]
            if '.' not in parent_code and parent_code in nodes_dict:
                nodes_dict[parent_code]['children'].append(node_data)

    for root_node in root_nodes_list:
        if root_node.get('children'):
            root_node['children'].sort(
                key=lambda n: clave_ordenacion_natural(
                    id_to_codigo_map.get(int(n.get('value','-1')), '')
                )
            )

    root_nodes_list.sort(
        key=lambda n: clave_ordenacion_natural(
            id_to_codigo_map.get(int(n.get('value','-1')), '')
        )
    )
    return root_nodes_list

