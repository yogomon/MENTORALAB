# core/auth_handler.py

from passlib.context import CryptContext
import re

# MODIFICACIÓN: Importar las funciones directamente desde el nuevo módulo 'db_quiz_loader'.
from core.db_quiz_loader import (
    crear_usuario, 
    obtener_usuario_por_nombre, 
    obtener_usuario_por_email
)
from core.database import conectar_db

# --- Configuración de Passlib ---
# Usamos bcrypt como el esquema de hashing principal.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Funciones de Hashing de Contraseñas ---

def hashear_contrasena(contrasena_plana):
    """Hashea una contraseña plana usando bcrypt."""
    try:
        return pwd_context.hash(contrasena_plana)
    except Exception as e:
        print(f"Error al hashear contraseña: {e}")
        return None

def verificar_contrasena(contrasena_plana, contrasena_hash_almacenada):
    """Verifica una contraseña plana contra un hash almacenado."""
    if not contrasena_plana or not contrasena_hash_almacenada:
        return False
    try:
        return pwd_context.verify(contrasena_plana, contrasena_hash_almacenada)
    except Exception as e:
        print(f"Error al verificar contraseña: {e}")
        return False

def es_contrasena_segura(contrasena):
    """Verifica si la contraseña cumple con los criterios de seguridad."""
    if len(contrasena) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres."
    if not re.search(r"[A-Z]", contrasena):
        return False, "La contraseña debe contener al menos una letra mayúscula."
    if not re.search(r"[a-z]", contrasena):
        return False, "La contraseña debe contener al menos una letra minúscula."
    if not re.search(r"\d", contrasena):
        return False, "La contraseña debe contener al menos un número."
    return True, "Contraseña segura."

# --- Funciones de Autenticación y Registro ---

def registrar_nuevo_usuario(nombre_usuario, contrasena, email, comunidad_autonoma, especialidad):
    """Registra un nuevo usuario en el sistema."""
    if not all([nombre_usuario, contrasena, email, comunidad_autonoma, especialidad]):
        return None, "Error de registro: Faltan campos obligatorios."

    segura, mensaje_seguridad = es_contrasena_segura(contrasena)
    if not segura:
        return None, mensaje_seguridad

    password_hash = hashear_contrasena(contrasena)
    if not password_hash:
        return None, "Error de registro: Fallo al hashear la contraseña."

    conn = None
    try:
        conn = conectar_db()
        if not conn:
            return None, "Error de registro: No se pudo conectar a la base de datos."
        
        # MODIFICACIÓN: Llamar a la función importada directamente.
        usuario_id = crear_usuario(conn, nombre_usuario, password_hash, email, comunidad_autonoma, especialidad)
        
        if usuario_id:
            return usuario_id, None # Éxito
        else:
            return None, "Error al crear el usuario. El nombre de usuario o email podrían ya existir."
            
    except Exception as e:
        return None, f"Error inesperado durante el registro: {e}"
    finally:
        if conn:
            conn.close()

def autenticar_usuario(email, contrasena_plana):
    """Autentica un usuario por su email y contraseña."""
    if not email or not contrasena_plana:
        return {'status': 'error', 'reason': 'empty_credentials'}

    conn = None
    try:
        conn = conectar_db()
        if not conn:
            return {'status': 'error', 'reason': 'db_connection_error'}

        # MODIFICACIÓN: Llamar a la función importada directamente.
        usuario_data = obtener_usuario_por_email(conn, email)

        if not usuario_data:
            return {'status': 'error', 'reason': 'email_not_found'}

        if not usuario_data.get('activo', False):
            return {'status': 'error', 'reason': 'user_inactive'}

        if verificar_contrasena(contrasena_plana, usuario_data['password_hash']):
            datos_sesion = {
                'id': usuario_data['id'],
                'nombre_usuario': usuario_data['nombre_usuario'],
                'email': usuario_data['email'],
                'rol': usuario_data['rol'],
                'comunidad_autonoma': usuario_data['comunidad_autonoma'],
                'especialidad': usuario_data['especialidad']
            }
            return {'status': 'success', 'user_info': datos_sesion}
        else:
            return {'status': 'error', 'reason': 'incorrect_password'}
            
    except Exception as e:
        return {'status': 'error', 'reason': 'unexpected_error', 'message': str(e)}
    finally:
        if conn:
            conn.close()
