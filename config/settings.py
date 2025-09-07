"""
Configuración global del sistema FaceGuard
Centraliza todas las configuraciones de la aplicación
"""

import os
from pathlib import Path

# Directorios base
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"
LOG_DIR = BASE_DIR / "logs"

# Configuración de base de datos
DATABASE_CONFIG = {
    'path': DATA_DIR / "database" / "faceguard.db",
    'timeout': 30.0,
    'check_same_thread': False
}

# Configuración de cámara
CAMERA_CONFIG = {
    'default_index': 0,
    'frame_width': 640,
    'frame_height': 480,
    'fps': 30,
    'auto_exposure': 0.25,
    'brightness': 0.5,
    'contrast': 0.5,
    'saturation': 0.5
}

# Configuración de reconocimiento facial
FACE_RECOGNITION_CONFIG = {
    'tolerance': 0.6,  # Tolerancia para el reconocimiento (menor = más estricto)
    'model': 'hog',    # 'hog' o 'cnn' (cnn es más preciso pero más lento)
    'upsample_times': 1,  # Número de veces que se amplía la imagen para detección
    'num_jitters': 1,     # Número de veces que se re-muestrea la cara para encoding
    'min_face_size': 100, # Tamaño mínimo de cara en píxeles
    'max_face_distance': 0.6,  # Distancia máxima para considerar una coincidencia
    'confidence_threshold': 50.0  # Umbral mínimo de confianza (0-100)
}

# Configuración de calidad de imagen
IMAGE_QUALITY_CONFIG = {
    'min_sharpness': 100,      # Mínima nitidez (varianza del Laplaciano)
    'min_brightness': 50,      # Brillo mínimo
    'max_brightness': 200,     # Brillo máximo
    'min_contrast': 20,        # Contraste mínimo
    'quality_threshold': 70,   # Umbral para considerar imagen de buena calidad
    'excellent_threshold': 80, # Umbral para considerar imagen excelente
    'enable_clahe': True,      # Habilitar mejora de contraste adaptivo
    'clahe_clip_limit': 2.0,   # Límite de recorte para CLAHE
    'clahe_tile_size': (8, 8)  # Tamaño de tile para CLAHE
}

# Configuración de la interfaz de usuario
UI_CONFIG = {
    'window_title': 'FaceGuard - Sistema de Reconocimiento Facial',
    'window_size': (1200, 800),
    'min_window_size': (800, 600),
    'theme': 'dark',
    'primary_color': '#00d4aa',
    'secondary_color': '#1e1e1e',
    'background_color': '#2b2b2b',
    'text_color': '#ffffff',
    'error_color': '#ff6b6b',
    'success_color': '#51cf66',
    'warning_color': '#ffd43b',
    'font_family': 'Arial, sans-serif',
    'font_size': 14
}

# Configuración de archivos y directorios
FILE_CONFIG = {
    'user_data_dir': DATA_DIR / "users",
    'logs_dir': LOG_DIR,
    'temp_dir': DATA_DIR / "temp",
    'backup_dir': DATA_DIR / "backup",
    'encoding_file_prefix': 'face_encoding_',
    'encoding_file_extension': '.pkl',
    'image_formats': ['.jpg', '.jpeg', '.png', '.bmp'],
    'max_file_size_mb': 10,  # Tamaño máximo de archivo en MB
    'cleanup_temp_on_exit': True
}

# Configuración de logging
LOGGING_CONFIG = {
    'level': 'INFO',  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file_handler': True,
    'console_handler': True,
    'max_file_size_mb': 5,
    'backup_count': 3,
    'log_file': LOG_DIR / 'faceguard.log'
}

# Configuración de seguridad y acceso
SECURITY_CONFIG = {
    'max_failed_attempts': 3,     # Máximo número de intentos fallidos
    'lockout_duration': 300,      # Duración del bloqueo en segundos (5 min)
    'session_timeout': 3600,      # Tiempo de sesión en segundos (1 hora)
    'require_admin_for_delete': True,  # Requerir permisos de admin para eliminar
    'log_all_attempts': True,     # Registrar todos los intentos de acceso
    'enable_backup': True,        # Habilitar backup automático
    'backup_interval': 86400,     # Intervalo de backup en segundos (24 horas)
    'encrypt_face_data': False    # Encriptar datos de rostros (requiere cryptography)
}

# Configuración de notificaciones
NOTIFICATION_CONFIG = {
    'show_notifications': True,
    'notification_duration': 5000,  # Duración en milisegundos
    'sound_enabled': False,
    'notification_position': 'top-right'  # top-left, top-right, bottom-left, bottom-right
}

# Configuración de rendimiento
PERFORMANCE_CONFIG = {
    'max_concurrent_recognitions': 1,  # Máximo reconocimientos simultáneos
    'frame_skip': 1,                   # Saltar frames para mejor rendimiento (1 = no saltar)
    'resize_factor': 0.25,             # Factor de redimensión para procesamiento rápido
    'enable_gpu': False,               # Habilitar aceleración GPU (requiere dlib con CUDA)
    'max_faces_per_frame': 10,         # Máximo número de caras a procesar por frame
    'cache_encodings': True,           # Cachear encodings en memoria
    'preload_users': True              # Precargar usuarios al iniciar
}

# Rutas de archivos importantes
PATHS = {
    'database': DATABASE_CONFIG['path'],
    'user_data': FILE_CONFIG['user_data_dir'],
    'logs': FILE_CONFIG['logs_dir'],
    'temp': FILE_CONFIG['temp_dir'],
    'backup': FILE_CONFIG['backup_dir'],
    'assets': ASSETS_DIR,
    'styles': ASSETS_DIR / 'styles',
    'icons': ASSETS_DIR / 'images' / 'icons',
    'logo': ASSETS_DIR / 'images' / 'logo.png'
}

# Crear directorios si no existen
def ensure_directories():
    """Crear todos los directorios necesarios"""
    directories = [
        DATA_DIR,
        FILE_CONFIG['user_data_dir'],
        FILE_CONFIG['logs_dir'],
        FILE_CONFIG['temp_dir'],
        FILE_CONFIG['backup_dir'],
        DATABASE_CONFIG['path'].parent,
        ASSETS_DIR / 'images',
        ASSETS_DIR / 'images' / 'icons',
        ASSETS_DIR / 'styles'
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

# Validar configuración
def validate_config():
    """Validar que la configuración sea válida"""
    errors = []
    
    # Validar tolerancia de reconocimiento
    if not 0.1 <= FACE_RECOGNITION_CONFIG['tolerance'] <= 1.0:
        errors.append("La tolerancia de reconocimiento debe estar entre 0.1 y 1.0")
    
    # Validar configuración de cámara
    if CAMERA_CONFIG['frame_width'] <= 0 or CAMERA_CONFIG['frame_height'] <= 0:
        errors.append("Las dimensiones de frame deben ser positivas")
    
    # Validar umbrales de calidad
    if IMAGE_QUALITY_CONFIG['quality_threshold'] > IMAGE_QUALITY_CONFIG['excellent_threshold']:
        errors.append("El umbral de calidad debe ser menor que el umbral de excelencia")
    
    # Validar configuración de archivos
    if FILE_CONFIG['max_file_size_mb'] <= 0:
        errors.append("El tamaño máximo de archivo debe ser positivo")
    
    # Validar configuración de seguridad
    if SECURITY_CONFIG['max_failed_attempts'] <= 0:
        errors.append("El número máximo de intentos fallidos debe ser positivo")
    
    if errors:
        raise ValueError("Errores de configuración encontrados:\n" + "\n".join(errors))

# Funciones de utilidad para configuración
def get_config_value(section: str, key: str, default=None):
    """Obtener valor de configuración de forma segura"""
    config_sections = {
        'database': DATABASE_CONFIG,
        'camera': CAMERA_CONFIG,
        'face_recognition': FACE_RECOGNITION_CONFIG,
        'image_quality': IMAGE_QUALITY_CONFIG,
        'ui': UI_CONFIG,
        'file': FILE_CONFIG,
        'logging': LOGGING_CONFIG,
        'security': SECURITY_CONFIG,
        'notification': NOTIFICATION_CONFIG,
        'performance': PERFORMANCE_CONFIG
    }
    
    section_config = config_sections.get(section, {})
    return section_config.get(key, default)

def update_config_value(section: str, key: str, value):
    """Actualizar valor de configuración"""
    config_sections = {
        'database': DATABASE_CONFIG,
        'camera': CAMERA_CONFIG,
        'face_recognition': FACE_RECOGNITION_CONFIG,
        'image_quality': IMAGE_QUALITY_CONFIG,
        'ui': UI_CONFIG,
        'file': FILE_CONFIG,
        'logging': LOGGING_CONFIG,
        'security': SECURITY_CONFIG,
        'notification': NOTIFICATION_CONFIG,
        'performance': PERFORMANCE_CONFIG
    }
    
    if section in config_sections and key in config_sections[section]:
        config_sections[section][key] = value
        return True
    return False

# Configuración específica por entorno
ENVIRONMENT = os.getenv('FACEGUARD_ENV', 'production')

if ENVIRONMENT == 'development':
    # Configuraciones para desarrollo
    LOGGING_CONFIG['level'] = 'DEBUG'
    FACE_RECOGNITION_CONFIG['model'] = 'hog'  # Más rápido para desarrollo
    PERFORMANCE_CONFIG['enable_gpu'] = False
    UI_CONFIG['window_size'] = (1000, 700)
    
elif ENVIRONMENT == 'testing':
    # Configuraciones para testing
    DATABASE_CONFIG['path'] = DATA_DIR / "database" / "test_faceguard.db"
    LOGGING_CONFIG['level'] = 'WARNING'
    FILE_CONFIG['cleanup_temp_on_exit'] = True
    SECURITY_CONFIG['log_all_attempts'] = False

elif ENVIRONMENT == 'production':
    # Configuraciones para producción
    LOGGING_CONFIG['level'] = 'INFO'
    FACE_RECOGNITION_CONFIG['model'] = 'hog'  # Balance entre velocidad y precisión
    SECURITY_CONFIG['log_all_attempts'] = True
    PERFORMANCE_CONFIG['cache_encodings'] = True

# Configuración de estilos CSS/QSS
STYLES = {
    'main_window': """
        QMainWindow {
            background-color: #2b2b2b;
            color: white;
        }
    """,
    
    'primary_button': f"""
        QPushButton {{
            background-color: {UI_CONFIG['primary_color']};
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            font-weight: bold;
            color: white;
            font-size: {UI_CONFIG['font_size']}px;
        }}
        QPushButton:hover {{
            background-color: #00b894;
        }}
        QPushButton:pressed {{
            background-color: #00a085;
        }}
        QPushButton:disabled {{
            background-color: #555;
            color: #999;
        }}
    """,
    
    'secondary_button': """
        QPushButton {
            background-color: transparent;
            border: 2px solid #00d4aa;
            padding: 10px 20px;
            border-radius: 5px;
            font-weight: bold;
            color: #00d4aa;
        }
        QPushButton:hover {
            background-color: #00d4aa;
            color: white;
        }
    """,
    
    'input_field': """
        QLineEdit {
            padding: 10px;
            border: 1px solid #555;
            border-radius: 5px;
            background-color: #3b3b3b;
            color: white;
            font-size: 14px;
        }
        QLineEdit:focus {
            border-color: #00d4aa;
        }
    """,
    
    'panel': """
        QFrame {
            background-color: #1e1e1e;
            border-radius: 15px;
            padding: 20px;
        }
    """
}

# Inicialización
if __name__ == "__main__":
    # Crear directorios y validar configuración al importar
    ensure_directories()
    validate_config()
    print("Configuración de FaceGuard cargada correctamente")
    print(f"Entorno: {ENVIRONMENT}")
    print(f"Base de datos: {DATABASE_CONFIG['path']}")
    print(f"Directorio de usuarios: {FILE_CONFIG['user_data_dir']}")
else:
    # Asegurar directorios cuando se importa el módulo
    ensure_directories()