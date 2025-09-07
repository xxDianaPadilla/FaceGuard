"""
Ventana principal corregida del sistema FaceGuard
Con inicialización automática de cámara en RegistrationScreen
"""

from PyQt5.QtWidgets import (QMainWindow, QStackedWidget, QVBoxLayout, 
                            QWidget, QLabel, QHBoxLayout, QPushButton, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QCloseEvent
from ..core.camera_manager import CameraManager
from ..gui.welcome_screen import WelcomeScreen
from ..gui.registration_screen import RegistrationScreen
from ..gui.recognition_screen import RecognitionScreen


class MainWindow(QMainWindow):
    """Ventana principal mejorada de la aplicación"""
    
    window_closed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FaceGuard - Sistema de Reconocimiento Facial")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(800, 600)
        
        # Flag para controlar el cierre
        self._is_closing = False
        self._cleanup_timer = None
        
        # Obtener instancia singleton de cámara
        self.camera_manager = CameraManager()
        
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
        
        print("Ventana principal inicializada con CameraManager singleton")
    
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
        
        logo_label = QLabel("◆")
        logo_label.setStyleSheet("""
            QLabel {
                color: #00d4aa;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        
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
        """Inicializar todas las pantallas con el CameraManager singleton"""
        try:
            # Pantalla de bienvenida
            self.welcome_screen = WelcomeScreen()
            self.welcome_screen.register_clicked.connect(self.show_registration_screen)
            self.welcome_screen.recognize_clicked.connect(self.show_recognition_screen)
            
            # Pantalla de registro - Reemplazar camera_manager con singleton
            self.registration_screen = RegistrationScreen()
            self.registration_screen.back_clicked.connect(self.show_welcome_screen)
            self.registration_screen.camera_manager = self.camera_manager
            # Agregar ID de pantalla para el sistema de usuarios
            self.registration_screen._screen_id = "registration_screen"
            
            # Pantalla de reconocimiento - Reemplazar camera_manager con singleton  
            self.recognition_screen = RecognitionScreen()
            self.recognition_screen.back_clicked.connect(self.show_welcome_screen)
            self.recognition_screen.camera_manager = self.camera_manager
            # Agregar ID de pantalla para el sistema de usuarios
            self.recognition_screen._screen_id = "recognition_screen"
            
            # Agregar pantallas al stack
            self.stacked_widget.addWidget(self.welcome_screen)
            self.stacked_widget.addWidget(self.registration_screen)
            self.stacked_widget.addWidget(self.recognition_screen)
            
            print("Pantallas inicializadas con CameraManager singleton")
            
        except Exception as e:
            print(f"Error inicializando pantallas: {e}")
    
    def show_welcome_screen(self):
        """Mostrar pantalla de bienvenida"""
        if not self._is_closing:
            print("Cambiando a pantalla de bienvenida...")
            # Desregistrar usuarios de pantallas anteriores
            self._cleanup_previous_screen()
            
            self.stacked_widget.setCurrentWidget(self.welcome_screen)
            self.update_nav_buttons("home")
            self.setWindowTitle("FaceGuard - Inicio")
    
    def show_registration_screen(self):
        """Mostrar pantalla de registro"""
        if not self._is_closing:
            print("Cambiando a pantalla de registro...")
            self._cleanup_previous_screen()
            
            # Cambiar a la pantalla PRIMERO
            self.stacked_widget.setCurrentWidget(self.registration_screen)
            self.update_nav_buttons("register")
            self.setWindowTitle("FaceGuard - Registro de Usuario")
            
            # Luego inicializar la cámara con un pequeño delay
            QTimer.singleShot(300, self._setup_registration_camera)
    
    def _setup_registration_camera(self):
        """Configurar cámara específicamente para la pantalla de registro"""
        if not self._is_closing:
            print("Configurando cámara para pantalla de registro...")
            try:
                # Registrar como usuario activo
                self.camera_manager.register_user("registration_screen")
                
                # Llamar al método de configuración de la pantalla
                if hasattr(self.registration_screen, 'setup_camera_for_screen'):
                    self.registration_screen.setup_camera_for_screen()
                else:
                    # Fallback al método original
                    self.registration_screen.setup_camera()
                    
            except Exception as e:
                print(f"Error configurando cámara para registro: {e}")
    
    def show_recognition_screen(self):
        """Mostrar pantalla de reconocimiento"""
        if not self._is_closing:
            print("Cambiando a pantalla de reconocimiento...")
            self._cleanup_previous_screen()
            
            # Registrar como usuario activo de la cámara
            self.camera_manager.register_user("recognition_screen")
            
            self.stacked_widget.setCurrentWidget(self.recognition_screen)
            self.update_nav_buttons("recognize")
            self.setWindowTitle("FaceGuard - Reconocimiento Facial")
            
            # La pantalla de reconocimiento maneja su propia inicialización de cámara
    
    def _cleanup_previous_screen(self):
        """Limpiar pantalla anterior"""
        try:
            print("Limpiando pantalla anterior...")
            
            # Detener timers de la pantalla de registro
            if hasattr(self, 'registration_screen') and hasattr(self.registration_screen, 'timer'):
                if self.registration_screen.timer.isActive():
                    self.registration_screen.timer.stop()
                    print("Timer de registro detenido")
            
            # Detener reconocimiento si está activo
            if hasattr(self, 'recognition_screen'):
                if hasattr(self.recognition_screen, 'system_state'):
                    try:
                        from .recognition_screen import SystemState
                        if (hasattr(self.recognition_screen, 'system_state') and 
                            self.recognition_screen.system_state == SystemState.ACTIVE):
                            print("Deteniendo reconocimiento al cambiar pantalla...")
                            self.recognition_screen.stop_recognition()
                    except ImportError:
                        if hasattr(self.recognition_screen, 'stop_recognition'):
                            self.recognition_screen.stop_recognition()
            
            # Desregistrar usuarios después de un pequeño delay para evitar conflictos
            QTimer.singleShot(100, self._unregister_all_users)
                        
        except Exception as e:
            print(f"Error limpiando pantalla anterior: {e}")
    
    def _unregister_all_users(self):
        """Desregistrar todos los usuarios con delay"""
        try:
            self.camera_manager.unregister_user("registration_screen")
            self.camera_manager.unregister_user("recognition_screen")
            print("Usuarios desregistrados de la cámara")
        except Exception as e:
            print(f"Error desregistrando usuarios: {e}")
    
    def update_nav_buttons(self, active_button):
        """Actualizar el estado visual de los botones de navegación"""
        if self._is_closing:
            return
            
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
    
    def safe_close(self):
        """Cerrar la aplicación de forma segura"""
        if self._is_closing:
            return
            
        print("Iniciando cierre seguro de la ventana principal...")
        self._is_closing = True
        
        try:
            # Limpiar todas las pantallas
            self._cleanup_all_screens()
            
            # Liberar CameraManager singleton forzosamente
            print("Liberando CameraManager singleton...")
            self.camera_manager.force_release_camera()
            
            # Usar timer para cierre diferido
            if not self._cleanup_timer:
                self._cleanup_timer = QTimer()
                self._cleanup_timer.setSingleShot(True)
                self._cleanup_timer.timeout.connect(self._finalize_close)
                self._cleanup_timer.start(1000)
            
        except Exception as e:
            print(f"Error durante el cierre seguro: {e}")
            self._finalize_close()
    
    def _cleanup_all_screens(self):
        """Limpiar recursos de todas las pantallas"""
        try:
            print("Limpiando recursos de todas las pantallas...")
            
            # Desregistrar todos los usuarios
            self.camera_manager.unregister_user("registration_screen")
            self.camera_manager.unregister_user("recognition_screen")
            
            # Limpiar pantalla de reconocimiento
            if hasattr(self, 'recognition_screen'):
                if hasattr(self.recognition_screen, '_is_closing'):
                    self.recognition_screen._is_closing = True
                
                # Detener sistema si está activo
                try:
                    from .recognition_screen import SystemState
                    if (hasattr(self.recognition_screen, 'system_state') and
                        self.recognition_screen.system_state in [SystemState.ACTIVE, SystemState.STARTING]):
                        self.recognition_screen.stop_recognition()
                except ImportError:
                    # Fallback
                    if hasattr(self.recognition_screen, 'stop_recognition'):
                        self.recognition_screen.stop_recognition()
                
                # Detener timers
                for timer_name in ['video_timer', 'recognition_timer', 'stats_timer']:
                    if hasattr(self.recognition_screen, timer_name):
                        timer = getattr(self.recognition_screen, timer_name)
                        if hasattr(timer, 'stop'):
                            timer.stop()
                
                # Limpiar workers
                if hasattr(self.recognition_screen, 'cleanup_recognition_worker_safe'):
                    self.recognition_screen.cleanup_recognition_worker_safe()
            
            # Limpiar pantalla de registro
            if hasattr(self, 'registration_screen'):
                if hasattr(self.registration_screen, '_is_closing'):
                    self.registration_screen._is_closing = True
                
                # Detener timer si existe
                if hasattr(self.registration_screen, 'timer'):
                    self.registration_screen.timer.stop()
                
                # Limpiar worker si existe
                if hasattr(self.registration_screen, 'cleanup_registration_worker'):
                    self.registration_screen.cleanup_registration_worker()
            
            print("Limpieza de pantallas completada")
            
        except Exception as e:
            print(f"Error limpiando pantallas: {e}")
    
    def _finalize_close(self):
        """Finalizar cierre"""
        try:
            print("Finalizando cierre de aplicación...")
            
            # Limpiar timer
            if self._cleanup_timer:
                self._cleanup_timer.deleteLater()
                self._cleanup_timer = None
            
            # Cerrar ventana
            self.close()
            self.window_closed.emit()
            
            print("Aplicación cerrada correctamente")
            
        except Exception as e:
            print(f"Error finalizando cierre: {e}")
            # Intentar cerrar de todas formas
            try:
                self.close()
                self.window_closed.emit()
            except:
                pass
    
    def closeEvent(self, event: QCloseEvent):
        """Manejar evento de cierre de ventana"""
        if self._is_closing:
            event.accept()
            return
        
        print("Evento de cierre de ventana recibido")
        event.ignore()
        
        QTimer.singleShot(100, self._handle_close_event)
    
    def _handle_close_event(self):
        """Manejar cierre de forma asíncrona"""
        try:
            reply = QMessageBox.question(
                self,
                'Confirmar Salida',
                '¿Está seguro de que desea salir de FaceGuard?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.safe_close()
            
        except Exception as e:
            print(f"Error manejando evento de cierre: {e}")
            self.safe_close()