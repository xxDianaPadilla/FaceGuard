"""
Ventana principal del sistema FaceGuard
Maneja la navegación entre diferentes pantallas
"""

from PyQt5.QtWidgets import (QMainWindow, QStackedWidget, QVBoxLayout, 
                            QWidget, QLabel, QHBoxLayout, QPushButton)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap

from .welcome_screen import WelcomeScreen
from .registration_screen import RegistrationScreen
from .recognition_screen import RecognitionScreen


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FaceGuard - Sistema de Reconocimiento Facial")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(800, 600)
        
        # Configurar el widget central
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Layout principal
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Crear header
        self.create_header()
        
        # Crear stack de pantallas
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)
        
        # Inicializar pantallas
        self.init_screens()
        
        # Mostrar pantalla de bienvenida
        self.show_welcome_screen()
    
    def create_header(self):
        """Crear el header de la aplicación"""
        header_widget = QWidget()
        header_widget.setFixedHeight(70)
        header_widget.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border-bottom: 2px solid #00d4aa;
            }
        """)
        
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        # Logo y título
        title_layout = QHBoxLayout()
        
        # Logo (placeholder)
        logo_label = QLabel("◆")
        logo_label.setStyleSheet("""
            QLabel {
                color: #00d4aa;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        
        # Título
        title_label = QLabel("FaceGuard")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 18px;
                font-weight: bold;
                margin-left: 10px;
            }
        """)
        
        title_layout.addWidget(logo_label)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # Botones de navegación
        nav_layout = QHBoxLayout()
        
        self.btn_home = QPushButton("Inicio")
        self.btn_register = QPushButton("Registrar")
        self.btn_recognize = QPushButton("Reconocer")
        
        nav_buttons = [self.btn_home, self.btn_register, self.btn_recognize]
        
        for btn in nav_buttons:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    padding: 10px 20px;
                    color: #ccc;
                    font-weight: normal;
                }
                QPushButton:hover {
                    color: #00d4aa;
                    background-color: #333;
                }
                QPushButton:pressed {
                    color: white;
                    background-color: #00d4aa;
                }
            """)
            nav_layout.addWidget(btn)
        
        # Conectar botones
        self.btn_home.clicked.connect(self.show_welcome_screen)
        self.btn_register.clicked.connect(self.show_registration_screen)
        self.btn_recognize.clicked.connect(self.show_recognition_screen)
        
        header_layout.addLayout(title_layout)
        header_layout.addLayout(nav_layout)
        
        self.main_layout.addWidget(header_widget)
    
    def init_screens(self):
        """Inicializar todas las pantallas"""
        # Pantalla de bienvenida
        self.welcome_screen = WelcomeScreen()
        self.welcome_screen.register_clicked.connect(self.show_registration_screen)
        self.welcome_screen.recognize_clicked.connect(self.show_recognition_screen)
        
        # Pantalla de registro
        self.registration_screen = RegistrationScreen()
        self.registration_screen.back_clicked.connect(self.show_welcome_screen)
        
        # Pantalla de reconocimiento
        self.recognition_screen = RecognitionScreen()
        self.recognition_screen.back_clicked.connect(self.show_welcome_screen)
        
        # Agregar pantallas al stack
        self.stacked_widget.addWidget(self.welcome_screen)
        self.stacked_widget.addWidget(self.registration_screen)
        self.stacked_widget.addWidget(self.recognition_screen)
    
    def show_welcome_screen(self):
        """Mostrar pantalla de bienvenida"""
        self.stacked_widget.setCurrentWidget(self.welcome_screen)
        self.update_nav_buttons("home")
    
    def show_registration_screen(self):
        """Mostrar pantalla de registro"""
        self.stacked_widget.setCurrentWidget(self.registration_screen)
        self.update_nav_buttons("register")
    
    def show_recognition_screen(self):
        """Mostrar pantalla de reconocimiento"""
        self.stacked_widget.setCurrentWidget(self.recognition_screen)
        self.update_nav_buttons("recognize")
    
    def update_nav_buttons(self, active_button):
        """Actualizar el estado visual de los botones de navegación"""
        buttons = {
            "home": self.btn_home,
            "register": self.btn_register,
            "recognize": self.btn_recognize
        }
        
        for name, btn in buttons.items():
            if name == active_button:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #00d4aa;
                        border: none;
                        padding: 10px 20px;
                        color: white;
                        font-weight: bold;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        padding: 10px 20px;
                        color: #ccc;
                        font-weight: normal;
                    }
                    QPushButton:hover {
                        color: #00d4aa;
                        background-color: #333;
                    }
                """)