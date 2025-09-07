"""
Gestor de base de datos para FaceGuard
Maneja todas las operaciones de persistencia de datos
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Tuple, Optional


class DatabaseManager:
    """Clase para manejar todas las operaciones de base de datos"""
    
    def __init__(self, db_path: str = "data/database/faceguard.db"):
        self.db_path = db_path
        self.ensure_database_directory()
    
    def ensure_database_directory(self):
        """Asegurar que el directorio de la base de datos existe"""
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
    
    def get_connection(self) -> sqlite3.Connection:
        """Obtener conexión a la base de datos"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Para acceder a columnas por nombre
        return conn
    
    def initialize_database(self):
        """Inicializar la base de datos y crear las tablas necesarias"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Tabla de usuarios
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        face_encoding_path TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Tabla de logs de acceso
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS access_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        access_type TEXT NOT NULL,  -- 'granted', 'denied', 'unknown'
                        confidence REAL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                # Tabla de configuración del sistema
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS system_config (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Insertar configuración por defecto si no existe
                cursor.execute('''
                    INSERT OR IGNORE INTO system_config (key, value)
                    VALUES ('recognition_tolerance', '0.6')
                ''')
                
                cursor.execute('''
                    INSERT OR IGNORE INTO system_config (key, value)
                    VALUES ('system_initialized', 'true')
                ''')
                
                conn.commit()
                print("Base de datos inicializada correctamente")
                
        except Exception as e:
            print(f"Error inicializando la base de datos: {e}")
            raise
    
    def add_user(self, name: str, email: str, face_encoding_path: str) -> Optional[int]:
        """
        Agregar un nuevo usuario al sistema
        
        Args:
            name: Nombre del usuario
            email: Email del usuario
            face_encoding_path: Ruta al archivo de encoding facial
            
        Returns:
            ID del usuario creado o None si hubo error
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO users (name, email, face_encoding_path)
                    VALUES (?, ?, ?)
                ''', (name, email, face_encoding_path))
                
                user_id = cursor.lastrowid
                conn.commit()
                
                print(f"Usuario {name} agregado con ID: {user_id}")
                return user_id
                
        except sqlite3.IntegrityError as e:
            print(f"Error de integridad: {e}")
            return None
        except Exception as e:
            print(f"Error agregando usuario: {e}")
            return None
    
    def get_user(self, user_id: int) -> Optional[Tuple]:
        """
        Obtener un usuario por su ID
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Tupla con datos del usuario o None si no existe
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, name, email, face_encoding_path, created_at
                    FROM users WHERE id = ?
                ''', (user_id,))
                
                return cursor.fetchone()
                
        except Exception as e:
            print(f"Error obteniendo usuario: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Tuple]:
        """
        Obtener un usuario por su email
        
        Args:
            email: Email del usuario
            
        Returns:
            Tupla con datos del usuario o None si no existe
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, name, email, face_encoding_path, created_at
                    FROM users WHERE email = ?
                ''', (email,))
                
                return cursor.fetchone()
                
        except Exception as e:
            print(f"Error obteniendo usuario por email: {e}")
            return None
    
    def get_all_users(self) -> List[Tuple]:
        """
        Obtener todos los usuarios del sistema
        
        Returns:
            Lista de tuplas con datos de usuarios
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, name, email, face_encoding_path, created_at
                    FROM users ORDER BY name
                ''')
                
                return cursor.fetchall()
                
        except Exception as e:
            print(f"Error obteniendo usuarios: {e}")
            return []
    
    def update_user(self, user_id: int, name: str = None, email: str = None) -> Tuple[bool, str]:
        """
        Actualizar datos de un usuario
        
        Args:
            user_id: ID del usuario
            name: Nuevo nombre (opcional)
            email: Nuevo email (opcional)
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            if not name and not email:
                return False, "No hay datos para actualizar"
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Construir query dinámicamente
                updates = []
                params = []
                
                if name:
                    updates.append("name = ?")
                    params.append(name)
                
                if email:
                    updates.append("email = ?")
                    params.append(email)
                
                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.append(user_id)
                
                query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
                
                cursor.execute(query, params)
                
                if cursor.rowcount > 0:
                    conn.commit()
                    return True, "Usuario actualizado correctamente"
                else:
                    return False, "Usuario no encontrado"
                    
        except sqlite3.IntegrityError as e:
            return False, f"Error de integridad: {e}"
        except Exception as e:
            return False, f"Error actualizando usuario: {e}"
    
    def delete_user(self, user_id: int) -> Tuple[bool, str]:
        """
        Eliminar un usuario del sistema
        
        Args:
            user_id: ID del usuario a eliminar
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Primero obtener la ruta del archivo de encoding para eliminarlo
                cursor.execute('''
                    SELECT face_encoding_path FROM users WHERE id = ?
                ''', (user_id,))
                
                result = cursor.fetchone()
                if not result:
                    return False, "Usuario no encontrado"
                
                face_encoding_path = result[0]
                
                # Eliminar registros de logs relacionados
                cursor.execute('''
                    DELETE FROM access_logs WHERE user_id = ?
                ''', (user_id,))
                
                # Eliminar usuario
                cursor.execute('''
                    DELETE FROM users WHERE id = ?
                ''', (user_id,))
                
                conn.commit()
                
                # Eliminar archivo de encoding si existe
                if face_encoding_path and os.path.exists(face_encoding_path):
                    try:
                        os.remove(face_encoding_path)
                    except Exception as e:
                        print(f"Warning: No se pudo eliminar el archivo {face_encoding_path}: {e}")
                
                return True, "Usuario eliminado correctamente"
                
        except Exception as e:
            return False, f"Error eliminando usuario: {e}"
    
    def log_access_attempt(self, user_id: Optional[int], access_type: str, confidence: float = 0.0):
        """
        Registrar un intento de acceso
        
        Args:
            user_id: ID del usuario (None para desconocido)
            access_type: Tipo de acceso ('granted', 'denied', 'unknown')
            confidence: Nivel de confianza del reconocimiento
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO access_logs (user_id, access_type, confidence)
                    VALUES (?, ?, ?)
                ''', (user_id, access_type, confidence))
                
                conn.commit()
                
        except Exception as e:
            print(f"Error registrando log de acceso: {e}")
    
    def get_access_logs(self, limit: int = 100) -> List[Tuple]:
        """
        Obtener logs de acceso recientes
        
        Args:
            limit: Número máximo de registros a retornar
            
        Returns:
            Lista de tuplas con logs de acceso
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT al.id, u.name, al.access_type, al.confidence, al.timestamp
                    FROM access_logs al
                    LEFT JOIN users u ON al.user_id = u.id
                    ORDER BY al.timestamp DESC
                    LIMIT ?
                ''', (limit,))
                
                return cursor.fetchall()
                
        except Exception as e:
            print(f"Error obteniendo logs de acceso: {e}")
            return []
    
    def get_config_value(self, key: str) -> Optional[str]:
        """
        Obtener un valor de configuración
        
        Args:
            key: Clave de configuración
            
        Returns:
            Valor de configuración o None si no existe
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT value FROM system_config WHERE key = ?
                ''', (key,))
                
                result = cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            print(f"Error obteniendo configuración: {e}")
            return None
    
    def set_config_value(self, key: str, value: str) -> bool:
        """
        Establecer un valor de configuración
        
        Args:
            key: Clave de configuración
            value: Valor a establecer
            
        Returns:
            True si fue exitoso
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO system_config (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (key, value))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error estableciendo configuración: {e}")
            return False
    
    def get_database_stats(self) -> dict:
        """
        Obtener estadísticas de la base de datos
        
        Returns:
            Diccionario con estadísticas
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Contar usuarios
                cursor.execute('SELECT COUNT(*) FROM users')
                user_count = cursor.fetchone()[0]
                
                # Contar logs de acceso
                cursor.execute('SELECT COUNT(*) FROM access_logs')
                log_count = cursor.fetchone()[0]
                
                # Obtener último acceso
                cursor.execute('''
                    SELECT MAX(timestamp) FROM access_logs
                ''')
                last_access = cursor.fetchone()[0]
                
                return {
                    'total_users': user_count,
                    'total_access_logs': log_count,
                    'last_access': last_access,
                    'database_path': self.db_path
                }
                
        except Exception as e:
            print(f"Error obteniendo estadísticas: {e}")
            return {
                'total_users': 0,
                'total_access_logs': 0,
                'last_access': None,
                'database_path': self.db_path
            }