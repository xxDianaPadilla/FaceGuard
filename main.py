#!/usr/bin/env python3
"""
FaceGuard - Sistema de Reconocimiento Facial
Archivo principal de la aplicación
"""

import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

# Agregar el directorio src al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.gui.main_window import MainWindow
from src.core.database_manager import DatabaseManager


def main():
    """Función principal de la aplicación"""
    # Crear la aplicación Qt
    app = QApplication(sys.argv)
    app.setApplicationName("FaceGuard")
    app.setApplicationVersion("1.0.0")
    
    # Configurar estilo oscuro
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2b2b2b;
            color: white;
        }
        QWidget {
            background-color: #2b2b2b;
            color: white;
            font-family: 'Arial', sans-serif;
        }
        QPushButton {
            background-color: #00d4aa;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            font-weight: bold;
            color: white;
        }
        QPushButton:hover {
            background-color: #00b894;
        }
        QPushButton:pressed {
            background-color: #00a085;
        }
        QLineEdit {
            padding: 10px;
            border: 1px solid #555;
            border-radius: 5px;
            background-color: #3b3b3b;
        }
        QLabel {
            color: white;
        }
    """)
    
    # Inicializar la base de datos
    db_manager = DatabaseManager()
    db_manager.initialize_database()
    
    # Crear y mostrar la ventana principal
    main_window = MainWindow()
    main_window.show()
    
    # Ejecutar la aplicación
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()