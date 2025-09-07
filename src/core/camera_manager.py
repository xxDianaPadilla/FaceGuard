"""
Gestor de cámara para FaceGuard
Maneja la captura de video y configuración de la cámara
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List


class CameraManager:
    """Clase para manejar todas las operaciones de cámara"""
    
    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.cap = None
        self.is_initialized = False
        self.frame_width = 640
        self.frame_height = 480
        self.fps = 30
    
    def initialize_camera(self) -> bool:
        """
        Inicializar la cámara
        
        Returns:
            bool: True si se inicializó correctamente
        """
        try:
            # Liberar cámara si ya está inicializada
            if self.cap is not None:
                self.cap.release()
            
            # Intentar inicializar cámara
            self.cap = cv2.VideoCapture(self.camera_index)
            
            if not self.cap.isOpened():
                print(f"No se pudo abrir la cámara con índice {self.camera_index}")
                return False
            
            # Configurar propiedades de la cámara
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Configuraciones adicionales para mejor calidad
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Desactivar auto exposición
            self.cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.5)
            self.cap.set(cv2.CAP_PROP_CONTRAST, 0.5)
            self.cap.set(cv2.CAP_PROP_SATURATION, 0.5)
            
            # Verificar que la cámara funcione
            ret, frame = self.cap.read()
            if not ret or frame is None:
                print("No se pudo capturar frame de la cámara")
                self.cap.release()
                return False
            
            self.is_initialized = True
            print(f"Cámara inicializada: {self.get_camera_info()}")
            return True
            
        except Exception as e:
            print(f"Error inicializando cámara: {e}")
            if self.cap is not None:
                self.cap.release()
            return False
    
    def get_frame(self) -> Optional[np.ndarray]:
        """
        Capturar un frame de la cámara
        
        Returns:
            Imagen numpy array en formato BGR o None si hay error
        """
        if not self.is_initialized or self.cap is None:
            return None
        
        try:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                # Aplicar mejoras básicas de imagen
                frame = self.enhance_frame(frame)
                return frame
            else:
                return None
                
        except Exception as e:
            print(f"Error capturando frame: {e}")
            return None
    
    def enhance_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Aplicar mejoras básicas a la imagen
        
        Args:
            frame: Frame original
            
        Returns:
            Frame mejorado
        """
        try:
            # Voltear horizontalmente para efecto espejo
            frame = cv2.flip(frame, 1)
            
            # Ajuste automático de contraste y brillo
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l_channel, a, b = cv2.split(lab)
            
            # Aplicar CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(l_channel)
            
            # Recombinar canales
            enhanced_lab = cv2.merge((cl, a, b))
            enhanced_frame = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
            
            return enhanced_frame
            
        except Exception as e:
            print(f"Error mejorando frame: {e}")
            return frame
    
    def capture_high_quality_frame(self) -> Optional[np.ndarray]:
        """
        Capturar un frame de alta calidad
        Toma múltiples frames y selecciona el mejor
        
        Returns:
            Frame de mejor calidad o None si hay error
        """
        if not self.is_initialized:
            return None
        
        try:
            frames = []
            scores = []
            
            # Capturar múltiples frames
            for _ in range(5):
                frame = self.get_frame()
                if frame is not None:
                    frames.append(frame)
                    # Calcular score de calidad (nitidez)
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    score = cv2.Laplacian(gray, cv2.CV_64F).var()
                    scores.append(score)
            
            if not frames:
                return None
            
            # Seleccionar frame con mejor score
            best_index = np.argmax(scores)
            return frames[best_index]
            
        except Exception as e:
            print(f"Error capturando frame de alta calidad: {e}")
            return None
    
    def set_camera_properties(self, brightness: float = None, 
                             contrast: float = None, 
                             saturation: float = None,
                             exposure: float = None) -> bool:
        """
        Configurar propiedades de la cámara
        
        Args:
            brightness: Brillo (0.0 - 1.0)
            contrast: Contraste (0.0 - 1.0)
            saturation: Saturación (0.0 - 1.0)
            exposure: Exposición (-7.0 - 0.0)
            
        Returns:
            True si se configuraron correctamente
        """
        if not self.is_initialized or self.cap is None:
            return False
        
        try:
            if brightness is not None:
                self.cap.set(cv2.CAP_PROP_BRIGHTNESS, brightness)
            
            if contrast is not None:
                self.cap.set(cv2.CAP_PROP_CONTRAST, contrast)
            
            if saturation is not None:
                self.cap.set(cv2.CAP_PROP_SATURATION, saturation)
            
            if exposure is not None:
                self.cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
            
            return True
            
        except Exception as e:
            print(f"Error configurando propiedades de cámara: {e}")
            return False
    
    def get_camera_info(self) -> dict:
        """
        Obtener información de la cámara
        
        Returns:
            Diccionario con información de la cámara
        """
        if not self.is_initialized or self.cap is None:
            return {}
        
        try:
            info = {
                'index': self.camera_index,
                'width': int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'fps': self.cap.get(cv2.CAP_PROP_FPS),
                'brightness': self.cap.get(cv2.CAP_PROP_BRIGHTNESS),
                'contrast': self.cap.get(cv2.CAP_PROP_CONTRAST),
                'saturation': self.cap.get(cv2.CAP_PROP_SATURATION),
                'exposure': self.cap.get(cv2.CAP_PROP_EXPOSURE),
                'auto_exposure': self.cap.get(cv2.CAP_PROP_AUTO_EXPOSURE)
            }
            return info
            
        except Exception as e:
            print(f"Error obteniendo información de cámara: {e}")
            return {}
    
    def save_frame(self, frame: np.ndarray, filename: str) -> bool:
        """
        Guardar un frame en archivo
        
        Args:
            frame: Frame a guardar
            filename: Nombre del archivo
            
        Returns:
            True si se guardó correctamente
        """
        try:
            return cv2.imwrite(filename, frame)
        except Exception as e:
            print(f"Error guardando frame: {e}")
            return False
    
    def test_camera_resolutions(self) -> List[Tuple[int, int]]:
        """
        Probar diferentes resoluciones soportadas por la cámara
        
        Returns:
            Lista de resoluciones soportadas
        """
        if not self.is_initialized:
            return []
        
        test_resolutions = [
            (320, 240),
            (640, 480),
            (800, 600),
            (1024, 768),
            (1280, 720),
            (1920, 1080)
        ]
        
        supported_resolutions = []
        
        for width, height in test_resolutions:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            if actual_width == width and actual_height == height:
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    supported_resolutions.append((width, height))
        
        # Restaurar resolución original
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        
        return supported_resolutions
    
    def change_camera(self, new_index: int) -> bool:
        """
        Cambiar a una cámara diferente
        
        Args:
            new_index: Índice de la nueva cámara
            
        Returns:
            True si se cambió correctamente
        """
        try:
            # Liberar cámara actual
            self.release_camera()
            
            # Cambiar índice y reinicializar
            self.camera_index = new_index
            return self.initialize_camera()
            
        except Exception as e:
            print(f"Error cambiando cámara: {e}")
            return False
    
    @staticmethod
    def get_available_cameras() -> List[int]:
        """
        Obtener lista de cámaras disponibles
        
        Returns:
            Lista de índices de cámaras disponibles
        """
        available_cameras = []
        
        # Probar hasta 10 cámaras
        for index in range(10):
            try:
                cap = cv2.VideoCapture(index)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        available_cameras.append(index)
                cap.release()
            except:
                continue
        
        return available_cameras
    
    def release_camera(self):
        """Liberar recursos de la cámara"""
        try:
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            
            self.is_initialized = False
            print("Cámara liberada")
            
        except Exception as e:
            print(f"Error liberando cámara: {e}")
    
    def __del__(self):
        """Destructor - liberar recursos"""
        self.release_camera()