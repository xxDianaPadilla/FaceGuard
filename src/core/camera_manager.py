# =============================================================================
# 1. VERSIÓN SINGLETON DE CAMERA MANAGER
# =============================================================================

"""
Gestor de cámara Singleton para FaceGuard
Asegura una sola instancia para evitar conflictos
"""

import threading
import time
import cv2
import numpy as np
from enum import Enum
from typing import Optional, Tuple, List


class CameraState(Enum):
    """Estados de la cámara"""
    DISCONNECTED = "disconnected"
    INITIALIZING = "initializing"
    CONNECTED = "connected"
    ERROR = "error"


class CameraManagerSingleton:
    """Clase Singleton para manejar todas las operaciones de cámara"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, camera_index: int = 0):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, camera_index: int = 0):
        # Solo inicializar una vez
        if self._initialized:
            return
            
        self.camera_index = camera_index
        self.cap = None
        self.state = CameraState.DISCONNECTED
        self.frame_width = 640
        self.frame_height = 480
        self.fps = 30

        # Threading y control de acceso
        self._camera_lock = threading.RLock()
        self.last_frame = None
        self.frame_timestamp = 0
        self.max_init_attempts = 3
        
        # Configuración de calidad
        self._enhancement_enabled = True
        self._quality_mode = "normal"
        
        # Control de liberación y usuarios activos
        self._is_releasing = False
        self._active_users = set()  # Rastrea qué pantallas usan la cámara
        self._user_lock = threading.Lock()
        
        self._initialized = True
        print("CameraManager Singleton creado")
    
    def register_user(self, user_id: str):
        """Registrar un usuario de la cámara"""
        with self._user_lock:
            self._active_users.add(user_id)
            print(f"Usuario registrado: {user_id}. Usuarios activos: {len(self._active_users)}")
    
    def unregister_user(self, user_id: str):
        """Desregistrar un usuario de la cámara"""
        with self._user_lock:
            self._active_users.discard(user_id)
            print(f"Usuario desregistrado: {user_id}. Usuarios activos: {len(self._active_users)}")
            
            # Si no hay usuarios activos, liberar cámara
            if len(self._active_users) == 0 and not self._is_releasing:
                print("No hay usuarios activos, liberando cámara...")
                self._release_camera_internal()
    
    def has_active_users(self) -> bool:
        """Verificar si hay usuarios activos"""
        with self._user_lock:
            return len(self._active_users) > 0
    
    @property
    def is_initialized(self) -> bool:
        """Propiedad para verificar si la cámara está inicializada"""
        with self._camera_lock:
            return (self.state == CameraState.CONNECTED and 
                   self.cap is not None and 
                   self.cap.isOpened() and 
                   not self._is_releasing)

    def _cleanup_camera_resources(self):
        """Limpiar recursos de cámara de forma segura"""
        try:
            if self.cap is not None:
                if self.cap.isOpened():
                    self.cap.release()
                self.cap = None
                
            self.state = CameraState.DISCONNECTED
            print("Recursos de cámara limpiados")
            
            # Limpiar OpenCV windows si existen
            cv2.destroyAllWindows()
            
        except Exception as e:
            print(f"Error limpiando recursos de cámara: {e}")
            self.cap = None
            self.state = CameraState.ERROR
        
        finally:
            # Pausa para que el SO libere recursos
            time.sleep(0.1)
    
    def initialize_camera(self, user_id: str = None) -> bool:
        """Inicializar la cámara"""
        if user_id:
            self.register_user(user_id)
        
        with self._camera_lock:
            if self._is_releasing:
                return False
            
            # Si ya está conectada, solo retornar True
            if self.state == CameraState.CONNECTED and self.cap and self.cap.isOpened():
                print("Cámara ya está inicializada")
                return True
                
            # Limpiar recursos existentes
            self._cleanup_camera_resources()
            self.state = CameraState.INITIALIZING
        
        for attempt in range(self.max_init_attempts):
            try:
                print(f"Intento {attempt + 1} de inicialización de cámara...")
                
                if attempt > 0:
                    time.sleep(1.0)
                
                with self._camera_lock:
                    if self._is_releasing:
                        return False
                        
                    # Crear nueva captura
                    self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
                    
                    if not self.cap.isOpened():
                        print(f"No se pudo abrir cámara en intento {attempt + 1}")
                        self._cleanup_camera_resources()
                        continue
                    
                    # Configurar propiedades
                    success = self._configure_camera_properties()
                    if not success:
                        print(f"Error configurando propiedades en intento {attempt + 1}")
                        self._cleanup_camera_resources()
                        continue
                
                # Test de captura
                success = self._test_camera_capture()
                if success:
                    with self._camera_lock:
                        if not self._is_releasing:
                            self.state = CameraState.CONNECTED
                            print(f"Cámara inicializada correctamente en intento {attempt + 1}")
                            return True
                        else:
                            self._cleanup_camera_resources()
                            return False
                else:
                    with self._camera_lock:
                        self._cleanup_camera_resources()
                
            except Exception as e:
                print(f"Error en intento {attempt + 1}: {e}")
                with self._camera_lock:
                    self._cleanup_camera_resources()
                continue
        
        with self._camera_lock:
            self.state = CameraState.ERROR
        print("No se pudo inicializar la cámara después de todos los intentos")
        return False
    
    def _configure_camera_properties(self) -> bool:
        """Configurar propiedades de la cámara"""
        try:
            if self._is_releasing or self.cap is None:
                return False
                
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
            self.cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.5)
            self.cap.set(cv2.CAP_PROP_CONTRAST, 0.5)
            self.cap.set(cv2.CAP_PROP_SATURATION, 0.5)
            
            return True
            
        except Exception as e:
            print(f"Error configurando propiedades: {e}")
            return False
    
    def _test_camera_capture(self) -> bool:
        """Probar captura de la cámara"""
        try:
            for test_attempt in range(5):
                if self._is_releasing:
                    return False
                    
                with self._camera_lock:
                    if self.cap is None or not self.cap.isOpened() or self._is_releasing:
                        return False
                    ret, frame = self.cap.read()
                
                if ret and frame is not None and frame.size > 0:
                    with self._camera_lock:
                        if not self._is_releasing:
                            self.last_frame = frame.copy()
                            self.frame_timestamp = time.time()
                        return not self._is_releasing
                time.sleep(0.1)
            
            return False
            
        except Exception as e:
            print(f"Error probando captura: {e}")
            return False
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Capturar un frame de la cámara"""
        if self.state != CameraState.CONNECTED or self._is_releasing:
            with self._camera_lock:
                if self.last_frame is not None and not self._is_releasing:
                    return self.last_frame.copy()
                return None
        
        try:
            with self._camera_lock:
                if (self.cap is None or 
                    not self.cap.isOpened() or 
                    self._is_releasing):
                    if self.last_frame is not None:
                        return self.last_frame.copy()
                    return None
                
                ret, frame = None, None
                for _ in range(2):
                    if self._is_releasing:
                        break
                    ret, frame = self.cap.read()
                    if not ret:
                        break
            
            if ret and frame is not None and frame.size > 0 and not self._is_releasing:
                if self._enhancement_enabled:
                    frame = self.enhance_frame(frame)
                
                with self._camera_lock:
                    if not self._is_releasing:
                        self.last_frame = frame.copy()
                        self.frame_timestamp = time.time()
                
                return frame
            else:
                if not self._is_releasing:
                    print("Error capturando frame")
                with self._camera_lock:
                    if self.last_frame is not None and not self._is_releasing:
                        return self.last_frame.copy()
                    return None
                
        except Exception as e:
            if not self._is_releasing:
                print(f"Excepción capturando frame: {e}")
            with self._camera_lock:
                if not self._is_releasing:
                    self.state = CameraState.ERROR
                if self.last_frame is not None and not self._is_releasing:
                    return self.last_frame.copy()
                return None
    
    def enhance_frame(self, frame: np.ndarray) -> np.ndarray:
        """Aplicar mejoras básicas a la imagen"""
        if frame is None or frame.size == 0 or self._is_releasing:
            return frame
        
        try:
            enhanced_frame = cv2.flip(frame, 1)
            
            lab = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2LAB)
            l_channel, a, b = cv2.split(lab)

            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            cl = clahe.apply(l_channel)

            enhanced_lab = cv2.merge((cl, a, b))
            enhanced_frame = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

            return enhanced_frame
        
        except Exception as e:
            if not self._is_releasing:
                print(f"Error mejorando frame: {e}")
            return frame
    
    def is_camera_healthy(self) -> bool:
        """Verificar si la cámara está funcionando correctamente"""
        if self._is_releasing:
            return False
            
        with self._camera_lock:
            if self.state != CameraState.CONNECTED or self.cap is None or self._is_releasing:
                return False
        
        try:
            with self._camera_lock:
                if not self.cap.isOpened() or self._is_releasing:
                    return False
                ret, frame = self.cap.read()
            
            return ret and frame is not None and frame.size > 0 and not self._is_releasing
            
        except Exception as e:
            if not self._is_releasing:
                print(f"Error verificando salud de cámara: {e}")
            with self._camera_lock:
                if not self._is_releasing:
                    self.state = CameraState.ERROR
            return False
    
    def reinitialize_camera(self) -> bool:
        """Reinicializar la cámara en caso de error"""
        if self._is_releasing:
            return False
            
        print("Reinicializando cámara...")
        return self.initialize_camera()
    
    def _release_camera_internal(self):
        """Liberación interna de cámara"""
        with self._camera_lock:
            print("Liberando cámara internamente...")
            self._is_releasing = True
            self._cleanup_camera_resources()
            self.last_frame = None
            self.frame_timestamp = 0
            self._is_releasing = False
            print("Cámara liberada internamente")
    
    def force_release_camera(self):
        """Liberar recursos de la cámara forzosamente"""
        print("Forzando liberación de cámara...")
        
        with self._user_lock:
            self._active_users.clear()
        
        self._release_camera_internal()
    
    @classmethod
    def reset_instance(cls):
        """Resetear la instancia singleton (solo para testing)"""
        with cls._lock:
            if cls._instance:
                try:
                    cls._instance.force_release_camera()
                except:
                    pass
            cls._instance = None


# Usar el singleton como CameraManager
CameraManager = CameraManagerSingleton