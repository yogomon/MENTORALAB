# utils/helpers.py

COMUNIDAD_MAP = {
    'AND': 'Andalucía', 'ARA': 'Aragón', 'AST': 'Asturias, Principado de',
    'BAL': 'Balears, Illes', 'CAN': 'Canarias', 'CNT': 'Cantabria',
    'CYL': 'Castilla y León', 'CLM': 'Castilla-La Mancha', 'CAT': 'Cataluña',
    'VAL': 'Comunitat Valenciana', 'EXT': 'Extremadura', 'GAL': 'Galicia',
    'MAD': 'Madrid, Comunidad de', 'MUR': 'Murcia, Región de',
    'NAV': 'Navarra, Comunidad Foral de', 'VAS': 'País Vasco', 'RIO': 'Rioja, La',
    'CEU': 'Ceuta', 'MEL': 'Melilla'
}

ESPECIALIDAD_MAP = {
    'BQ': 'Bioquímica Clínica', 
    'AC': 'Análisis Clínicos',
}

def clave_ordenacion_natural(codigo_str):
    """ Convierte un código de tema (ej: '1.10.2') en una tupla para ordenación natural. """
    try:
        # Asegurarse que el input es string
        codigo_str = str(codigo_str)
        return tuple(int(part) for part in codigo_str.split('.'))
    except ValueError:
        print(f"Advertencia: Código tema no numérico o formato inesperado '{codigo_str}' durante ordenación.")
        return (-1,) # Poner al principio o final

def _remove_empty_children_recursive(nodes_list):
    """ Función recursiva interna para limpiar nodos de árbol sin hijos. """
    if not isinstance(nodes_list, list): return
    nodes_to_remove = []
    for node in nodes_list:
        # Procesar hijos recursivamente primero
        if 'children' in node:
            if node['children']: # Solo procesar si la lista existe y no está vacía
                _remove_empty_children_recursive(node['children'])
            # Comprobar si la lista de hijos está ahora vacía
            if not node.get('children'): # Usar get para evitar KeyError si se eliminó
                 nodes_to_remove.append(node)
        # else: Si no tiene clave 'children', no hacer nada

    # Eliminar nodos marcados (mejor iterar por índice o crear nueva lista)
    # Iterar por copia para eliminar de forma segura
    for node in nodes_to_remove:
        if node in nodes_list: # Asegurarse que aún está
             nodes_list.remove(node)

def get_key_from_value(dictionary, value_to_find):
    """Devuelve la clave de un diccionario dado su valor."""
    for key, value in dictionary.items():
        if value == value_to_find:
            return key
    return None # Retorna None si el valor no se encuentra

# Puedes añadir más funciones de utilidad pequeñas aquí si las identificas.