#!/usr/bin/env python3
"""
FaceGuard - Sistema de Reconocimiento Facial
Archivo principal de la aplicación
"""

import sys
import os
import time
import signal
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon

# Agregar el directorio src al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.gui.main_window import MainWindow
from src.core.database_manager import DatabaseManager


class FaceGuardApplication(QApplication):
    """Clase personalizada de aplicación para manejo mejorado de eventos"""
    
    def __init__(self, argv):
        super().__init__(argv)
        self.main_window = None
        self._is_shutting_down = False
        
        # Configurar manejo de señales del sistema
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Timer para procesar señales de interrupción en Windows
        self.signal_timer = QTimer()
        self.signal_timer.timeout.connect(lambda: None)
        self.signal_timer.start(500)
    
    def _signal_handler(self, signum, frame):
        """Manejar señales del sistema (Ctrl+C, etc.)"""
        print(f"\nSeñal recibida: {signum}")
        self.safe_quit()
    
    def safe_quit(self):
        """Cerrar aplicación de forma segura"""
        if self._is_shutting_down:
            return
            
        print("Iniciando cierre seguro de la aplicación...")
        self._is_shutting_down = True
        
        # Detener timer de señales
        if hasattr(self, 'signal_timer'):
            self.signal_timer.stop()
        
        # Cerrar ventana principal
        if self.main_window is not None:
            try:
                self.main_window.safe_close()
            except Exception as e:
                print(f"Error cerrando ventana principal: {e}")
        
        # Procesar eventos pendientes
        self.processEvents()
        
        # Salir de la aplicación
        QTimer.singleShot(1000, self.quit)


def main():
    """Función principal de la aplicación"""
    # Crear la aplicación Qt personalizada
    app = FaceGuardApplication(sys.argv)
    app.setApplicationName("FaceGuard")
    app.setApplicationVersion("1.0.0")
    
    # IMPORTANTE: Configurar para que la app no termine automáticamente
    app.setQuitOnLastWindowClosed(False)  # Cambiar a False para control manual
    
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
    try:
        db_manager = DatabaseManager()
        db_manager.initialize_database()
        print("Base de datos inicializada correctamente")
    except Exception as e:
        print(f"Error inicializando base de datos: {e}")
        return 1
    
    # Crear y mostrar la ventana principal
    exit_code = 1
    
    try:
        main_window = MainWindow()
        app.main_window = main_window  # Asignar referencia
        
        # Conectar señal de cierre de ventana con cierre de aplicación
        main_window.window_closed.connect(app.safe_quit)
        
        main_window.show()
        
        print("Aplicación iniciada correctamente")
        
        # Ejecutar la aplicación
        exit_code = app.exec_()
        
        print("Aplicación terminada con código:", exit_code)
        
    except Exception as e:
        print(f"Error en la aplicación: {e}")
        exit_code = 1
    
    finally:
        # Limpiar recursos de forma explícita
        print("Limpiando recursos...")
        
        if hasattr(app, 'main_window') and app.main_window is not None:
            try:
                # Asegurar que la ventana se cierre correctamente
                app.main_window.safe_close()
                app.main_window.deleteLater()
            except Exception as e:
                print(f"Error cerrando ventana principal: {e}")
        
        # Procesar eventos pendientes
        try:
            app.processEvents()
        except:
            pass
        
        # Dar tiempo para que los threads terminen
        time.sleep(1.0)
        
        print("Limpieza completada")
    
    return exit_code


if __name__ == "__main__":
    try:
        exit_code = main()
        print(f"Saliendo con código: {exit_code}")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"Error fatal: {e}")
        sys.exit(1)