"""
Pantalla de bienvenida del sistema FaceGuard
Basada en los diseños proporcionados
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QFrame, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap


class WelcomeScreen(QWidget):
    """Pantalla de bienvenida principal"""
    
    # Señales
    register_clicked = pyqtSignal()
    recognize_clicked = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Inicializar la interfaz de usuario"""
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Contenedor central
        central_frame = QFrame()
        central_frame.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
            }
        """)
        
        central_layout = QVBoxLayout(central_frame)
        central_layout.setContentsMargins(50, 50, 50, 50)
        central_layout.setSpacing(30)
        
        # Spacer superior
        central_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # Logo y título
        self.create_logo_section(central_layout)
        
        # Descripción
        self.create_description_section(central_layout)
        
        # Botones principales
        self.create_buttons_section(central_layout)
        
        # Spacer inferior
        central_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        main_layout.addWidget(central_frame)
    
    def create_logo_section(self, layout):
        """Crear la sección del logo"""
        logo_layout = QVBoxLayout()
        logo_layout.setAlignment(Qt.AlignCenter)
        logo_layout.setSpacing(20)
        
        # Logo principal (diamond shape como en los diseños)
        logo_container = QWidget()
        logo_container.setFixedSize(120, 120)
        logo_container.setStyleSheet("""
            QWidget {
                background-color: #00d4aa;
                border-radius: 15px;
            }
        """)
        
        logo_inner_layout = QVBoxLayout(logo_container)
        logo_inner_layout.setAlignment(Qt.AlignCenter)
        
        # Símbolo del logo (diamond)
        logo_symbol = QLabel("◆")
        logo_symbol.setAlignment(Qt.AlignCenter)
        logo_symbol.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 48px;
                font-weight: bold;
                background: transparent;
            }
        """)
        logo_inner_layout.addWidget(logo_symbol)
        
        # Centrar el logo
        logo_h_layout = QHBoxLayout()
        logo_h_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        logo_h_layout.addWidget(logo_container)
        logo_h_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        # Título
        title_label = QLabel("FaceGuard")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 32px;
                font-weight: bold;
                margin-top: 10px;
            }
        """)
        
        logo_layout.addLayout(logo_h_layout)
        logo_layout.addWidget(title_label)
        
        layout.addLayout(logo_layout)
    
    def create_description_section(self, layout):
        """Crear la sección de descripción"""
        desc_layout = QVBoxLayout()
        desc_layout.setAlignment(Qt.AlignCenter)
        desc_layout.setSpacing(15)
        
        # Título de bienvenida
        welcome_title = QLabel("Bienvenido a FaceGuard")
        welcome_title.setAlignment(Qt.AlignCenter)
        welcome_title.setStyleSheet("""
            QLabel {
                color: #00d4aa;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        
        # Descripción
        description = QLabel(
            "Sistema avanzado de reconocimiento facial\n"
            "para control de acceso y seguridad.\n\n"
            "Registra nuevos usuarios o inicia el\n"
            "reconocimiento facial para acceder al sistema."
        )
        description.setAlignment(Qt.AlignCenter)
        description.setStyleSheet("""
            QLabel {
                color: #ccc;
                font-size: 16px;
                line-height: 1.5;
            }
        """)
        description.setWordWrap(True)
        
        desc_layout.addWidget(welcome_title)
        desc_layout.addWidget(description)
        
        layout.addLayout(desc_layout)
    
    def create_buttons_section(self, layout):
        """Crear la sección de botones principales"""
        buttons_layout = QVBoxLayout()
        buttons_layout.setAlignment(Qt.AlignCenter)
        buttons_layout.setSpacing(20)
        
        # Botón de registro
        register_btn = QPushButton("Registrar Nuevo Usuario")
        register_btn.setFixedSize(300, 50)
        register_btn.setStyleSheet("""
            QPushButton {
                background-color: #00d4aa;
                border: none;
                border-radius: 25px;
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00b894;
                transform: scale(1.02);
            }
            QPushButton:pressed {
                background-color: #00a085;
            }
        """)
        register_btn.clicked.connect(self.register_clicked.emit)
        
        # Botón de reconocimiento
        recognize_btn = QPushButton("Iniciar Reconocimiento")
        recognize_btn.setFixedSize(300, 50)
        recognize_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 2px solid #00d4aa;
                border-radius: 25px;
                color: #00d4aa;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00d4aa;
                color: white;
            }
            QPushButton:pressed {
                background-color: #00a085;
                border-color: #00a085;
            }
        """)
        recognize_btn.clicked.connect(self.recognize_clicked.emit)
        
        buttons_layout.addWidget(register_btn)
        buttons_layout.addWidget(recognize_btn)
        
        layout.addLayout(buttons_layout)