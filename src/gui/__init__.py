# src/gui/__init__.py
"""
Módulo GUI - Interfaz gráfica de usuario para FaceGuard
"""

from .main_window import MainWindow
from .welcome_screen import WelcomeScreen
from .registration_screen import RegistrationScreen
from .recognition_screen import RecognitionScreen

__all__ = [
    'MainWindow',
    'WelcomeScreen', 
    'RegistrationScreen',
    'RecognitionScreen'
]