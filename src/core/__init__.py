# src/core/__init__.py
"""
Módulo Core - Lógica principal del sistema FaceGuard
"""

from .face_recognition_engine import FaceRecognitionEngine
from .camera_manager import CameraManager
from .database_manager import DatabaseManager

__all__ = [
    'FaceRecognitionEngine',
    'CameraManager', 
    'DatabaseManager'
]