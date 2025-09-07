"""
Pantalla de reconocimiento facial para FaceGuard
Realiza reconocimiento en tiempo real y gestión de accesos
"""

import threading
import time
from enum import Enum
from datetime import datetime
import cv2
import numpy as np

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QFrame, QSpacerItem, QSizePolicy,
                            QTableWidget, QTableWidgetItem, QHeaderView,
                            QTabWidget, QGroupBox, QProgressBar)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot, QMutex, QWaitCondition
from PyQt5.QtGui import QFont, QPixmap, QImage, QColor

from ..core.camera_manager import CameraManager
from ..core.face_recognition_engine import FaceRecognitionEngine
from ..core.database_manager import DatabaseManager


class SystemState(Enum):
    """Estados del sistema de reconocimiento"""
    INACTIVE = "inactive"
    STARTING = "starting" 
    ACTIVE = "active"
    STOPPING = "stopping"
    ERROR = "error"


class RecognitionWorker(QThread):
    """Worker thread mejorado para el reconocimiento facial"""
    
    recognition_result = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, face_engine, frame):
        super().__init__()
        self.face_engine = face_engine
        self.frame = frame.copy() if frame is not None else None
        
        # Control de parada mejorado
        self._should_run = True
        self._mutex = QMutex()
        self._stop_condition = QWaitCondition()
        self._is_processing = False
        
        # Configurar thread
        self.setObjectName("RecognitionWorker")
    
    def run(self):
        """Ejecutar reconocimiento con control de parada mejorado"""
        if not self._should_run or self.frame is None:
            return
        
        try:
            # Marcar que estamos procesando
            self._mutex.lock()
            self._is_processing = True
            should_continue = self._should_run
            self._mutex.unlock()
            
            if not should_continue:
                return
            
            # Copiar frame para procesamiento
            frame_copy = self.frame.copy()
            
            # Verificar múltiples veces durante el procesamiento
            checkpoints = [0.0, 0.3, 0.6, 1.0]  # Porcentajes del procesamiento
            
            for i, checkpoint in enumerate(checkpoints[:-1]):
                self._mutex.lock()
                should_continue = self._should_run
                self._mutex.unlock()
                
                if not should_continue:
                    return
                
                # Simular progreso y dar oportunidad de cancelar
                if i > 0:  # No hacer sleep en el primer checkpoint
                    self.msleep(10)  # Pausa pequeña para dar oportunidad de cancelar
            
            # Realizar reconocimiento si aún debemos continuar
            self._mutex.lock()
            should_continue = self._should_run
            self._mutex.unlock()
            
            if should_continue:
                faces = self.face_engine.recognize_face(frame_copy)
                
                # Verificar antes de emitir resultado
                self._mutex.lock()
                should_emit = self._should_run
                self._mutex.unlock()
                
                if should_emit:
                    self.recognition_result.emit(faces)
            
        except Exception as e:
            # Verificar si aún debemos emitir error
            self._mutex.lock()
            should_emit = self._should_run
            self._mutex.unlock()
            
            if should_emit:
                self.error_occurred.emit(f"Error en reconocimiento: {str(e)}")
        
        finally:
            # Marcar que terminamos el procesamiento
            self._mutex.lock()
            self._is_processing = False
            self._stop_condition.wakeAll()
            self._mutex.unlock()
    
    def stop_worker(self):
        """Detener el worker de forma segura"""
        self._mutex.lock()
        self._should_run = False
        self._stop_condition.wakeAll()
        self._mutex.unlock()
        
        # Desconectar señales
        try:
            self.recognition_result.disconnect()
            self.error_occurred.disconnect()
        except:
            pass  # Ignorar si ya están desconectadas
    
    def wait_for_finish(self, timeout_ms=3000):
        """Esperar a que termine con timeout"""
        self._mutex.lock()
        
        if self._is_processing:
            # Esperar con timeout
            self._stop_condition.wait(self._mutex, timeout_ms)
        
        self._mutex.unlock()
        
        # Esperar que el thread termine
        return self.wait(timeout_ms)


class RecognitionScreen(QWidget):
    """Pantalla principal de reconocimiento facial"""
    
    # Señales
    back_clicked = pyqtSignal()
    access_granted = pyqtSignal(dict)
    access_denied = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        
        # Componentes principales
        self.camera_manager = CameraManager()
        self.face_engine = FaceRecognitionEngine()
        self.db_manager = DatabaseManager()
        
        # Estado del sistema
        self.system_state = SystemState.INACTIVE
        self.current_frame = None
        
        # Timers
        self.video_timer = QTimer()
        self.recognition_timer = QTimer()
        self.stats_timer = QTimer()
        
        # Worker de reconocimiento
        self.recognition_worker = None
        self.last_recognition_time = datetime.now()
        self.recognition_interval = 1.0  # Segundos entre reconocimientos
        
        # Flag para controlar el cierre
        self._is_closing = False
        self._cleanup_timer = None
        
        # Estadísticas
        self.stats = {
            'total_recognitions': 0,
            'successful_recognitions': 0,
            'failed_recognitions': 0,
            'session_start': datetime.now()
        }
        
        # Control de errores de cámara
        self.camera_error_count = 0
        self.max_camera_errors = 5
        
        # Inicialización
        self.init_ui()
        self.setup_timers()
        self.setup_camera()
        self.update_ui_state()
    
    def init_ui(self):
        """Inicializar la interfaz de usuario"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Panel izquierdo - Cámara y controles
        self.create_camera_panel(main_layout)
        
        # Panel derecho - Información y logs
        self.create_info_panel(main_layout)
    
    def create_camera_panel(self, main_layout):
        """Crear panel de la cámara"""
        camera_frame = QFrame()
        camera_frame.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 15px;
                padding: 20px;
            }
        """)
        
        camera_layout = QVBoxLayout(camera_frame)
        camera_layout.setSpacing(15)
        
        # Título
        title_label = QLabel("Reconocimiento Facial")
        title_label.setStyleSheet("""
            QLabel {
                color: #00d4aa;
                font-size: 24px;
                font-weight: bold;
                text-align: center;
                margin-bottom: 10px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        
        # Estado del sistema
        self.system_status_label = QLabel("Sistema Inactivo")
        self.system_status_label.setStyleSheet(self._get_status_style(SystemState.INACTIVE))
        self.system_status_label.setAlignment(Qt.AlignCenter)
        
        # Video display
        self.video_label = QLabel()
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("""
            QLabel {
                border: 2px solid #555;
                border-radius: 10px;
                background-color: #333;
            }
        """)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setText("Cámara inactiva")
        
        # Controles principales
        controls_layout = QHBoxLayout()
        
        self.btn_start_stop = QPushButton("▶ Iniciar Reconocimiento")
        self.btn_start_stop.setFixedSize(200, 45)
        self.btn_start_stop.setStyleSheet("""
            QPushButton {
                background-color: #00d4aa;
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #00b894;
            }
            QPushButton:disabled {
                background-color: #666;
            }
        """)
        self.btn_start_stop.clicked.connect(self.toggle_recognition)
        
        self.btn_settings = QPushButton("⚙ Configurar")
        self.btn_settings.setFixedSize(120, 45)
        self.btn_settings.setStyleSheet("""
            QPushButton {
                background-color: #666;
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #777;
            }
        """)
        
        controls_layout.addStretch()
        controls_layout.addWidget(self.btn_start_stop)
        controls_layout.addWidget(self.btn_settings)
        controls_layout.addStretch()
        
        # Información de último reconocimiento
        self.last_recognition_info = QLabel("Esperando reconocimiento...")
        self.last_recognition_info.setStyleSheet("""
            QLabel {
                color: #ccc;
                font-size: 14px;
                text-align: center;
                padding: 10px;
                border-radius: 8px;
                background-color: #333;
            }
        """)
        self.last_recognition_info.setAlignment(Qt.AlignCenter)
        
        # Botón volver
        self.btn_back = QPushButton("← Volver al Menú")
        self.btn_back.setFixedSize(150, 40)
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #666;
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #777;
            }
        """)
        self.btn_back.clicked.connect(self.back_clicked.emit)
        
        # Agregar elementos al layout
        camera_layout.addWidget(title_label)
        camera_layout.addWidget(self.system_status_label)
        camera_layout.addWidget(self.video_label)
        camera_layout.addLayout(controls_layout)
        camera_layout.addWidget(self.last_recognition_info)
        camera_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))
        camera_layout.addWidget(self.btn_back)
        
        main_layout.addWidget(camera_frame)
    
    def create_info_panel(self, main_layout):
        """Crear panel de información"""
        info_frame = QFrame()
        info_frame.setFixedWidth(400)
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 15px;
                padding: 20px;
            }
        """)
        
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(20)
        
        # Tabs para diferentes vistas
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #333;
                color: white;
                padding: 8px 16px;
                margin: 2px;
            }
            QTabBar::tab:selected {
                background-color: #00d4aa;
            }
        """)
        
        # Crear tabs
        stats_tab = self.create_stats_tab()
        tab_widget.addTab(stats_tab, "📊 Estadísticas")
        
        logs_tab = self.create_logs_tab()
        tab_widget.addTab(logs_tab, "📋 Logs Recientes")
        
        users_tab = self.create_users_tab()
        tab_widget.addTab(users_tab, "👥 Usuarios")
        
        info_layout.addWidget(tab_widget)
        main_layout.addWidget(info_frame)
    
    def create_stats_tab(self):
        """Crear tab de estadísticas"""
        stats_widget = QWidget()
        stats_layout = QVBoxLayout(stats_widget)
        stats_layout.setSpacing(15)
        
        # Grupo de estadísticas generales
        general_group = QGroupBox("Estadísticas Generales")
        general_group.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }
        """)
        
        general_layout = QVBoxLayout(general_group)
        
        self.stats_labels = {
            'total': QLabel("Total de reconocimientos: 0"),
            'successful': QLabel("Reconocimientos exitosos: 0"),
            'failed': QLabel("Reconocimientos fallidos: 0"),
            'accuracy': QLabel("Precisión: 0.0%"),
            'users_count': QLabel("Usuarios registrados: 0"),
            'last_access': QLabel("Último acceso: Ninguno")
        }
        
        for label in self.stats_labels.values():
            label.setStyleSheet("""
                QLabel {
                    color: #ccc;
                    font-size: 13px;
                    padding: 5px;
                }
            """)
            general_layout.addWidget(label)
        
        # Grupo de estado del sistema
        system_group = QGroupBox("Estado del Sistema")
        system_group.setStyleSheet(general_group.styleSheet())
        
        system_layout = QVBoxLayout(system_group)
        
        self.system_labels = {
            'camera_status': QLabel("Cámara: Desconectada"),
            'recognition_status': QLabel("Reconocimiento: Inactivo"),
            'database_status': QLabel("Base de datos: Conectada"),
            'last_update': QLabel("Última actualización: --")
        }
        
        for label in self.system_labels.values():
            label.setStyleSheet("""
                QLabel {
                    color: #ccc;
                    font-size: 13px;
                    padding: 5px;
                }
            """)
            system_layout.addWidget(label)
        
        stats_layout.addWidget(general_group)
        stats_layout.addWidget(system_group)
        stats_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        return stats_widget
    
    def create_logs_tab(self):
        """Crear tab de logs"""
        logs_widget = QWidget()
        logs_layout = QVBoxLayout(logs_widget)
        
        # Tabla de logs
        self.logs_table = QTableWidget()
        self.logs_table.setColumnCount(4)
        self.logs_table.setHorizontalHeaderLabels(["Hora", "Usuario", "Resultado", "Confianza"])
        
        # Configurar tabla
        header = self.logs_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        self.logs_table.setStyleSheet("""
            QTableWidget {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                gridline-color: #555;
            }
            QHeaderView::section {
                background-color: #444;
                color: white;
                padding: 8px;
                border: 1px solid #555;
            }
        """)
        
        # Botón para limpiar logs
        clear_logs_btn = QPushButton("🗑 Limpiar Logs")
        clear_logs_btn.setFixedHeight(35)
        clear_logs_btn.setStyleSheet("""
            QPushButton {
                background-color: #666;
                border: none;
                border-radius: 5px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #777;
            }
        """)
        
        logs_layout.addWidget(self.logs_table)
        logs_layout.addWidget(clear_logs_btn)
        
        return logs_widget
    
    def create_users_tab(self):
        """Crear tab de usuarios"""
        users_widget = QWidget()
        users_layout = QVBoxLayout(users_widget)
        
        # Lista de usuarios
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(3)
        self.users_table.setHorizontalHeaderLabels(["ID", "Nombre", "Email"])
        
        header = self.users_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        
        self.users_table.setStyleSheet(self.logs_table.styleSheet())
        
        # Botón para refrescar usuarios
        refresh_users_btn = QPushButton("🔄 Actualizar Lista")
        refresh_users_btn.setFixedHeight(35)
        refresh_users_btn.setStyleSheet("""
            QPushButton {
                background-color: #00d4aa;
                border: none;
                border-radius: 5px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00b894;
            }
        """)
        refresh_users_btn.clicked.connect(self.refresh_users_list)
        
        users_layout.addWidget(self.users_table)
        users_layout.addWidget(refresh_users_btn)
        
        return users_widget
    
    def setup_timers(self):
        """Configurar timers del sistema"""
        # Timer principal de video (30 FPS)
        self.video_timer.timeout.connect(self.update_video_display)
        
        # Timer de reconocimiento (cada segundo)
        self.recognition_timer.timeout.connect(self.trigger_recognition)
        
        # Timer de actualización de estadísticas (cada 5 segundos)
        self.stats_timer.timeout.connect(self.update_statistics)
        self.stats_timer.start(5000)
    
    def setup_camera(self):
        """Configurar la cámara"""
        if self._is_closing:
            return
            
        try:
            if self.camera_manager.initialize_camera():
                self._update_camera_status("Conectada", True)
                print("Cámara configurada correctamente")
            else:
                self._update_camera_status("Error", False)
                
        except Exception as e:
            print(f"Error configurando cámara: {e}")
            self._update_camera_status("Error", False)
    
    def _update_camera_status(self, status_text: str, is_connected: bool):
        """Actualizar estado de la cámara en UI"""
        color = "#51cf66" if is_connected else "#ff6b6b"
        self.system_labels['camera_status'].setText(f"Cámara: {status_text}")
        self.system_labels['camera_status'].setStyleSheet(f"""
            QLabel {{ color: {color}; font-size: 13px; padding: 5px; }}
        """)
    
    def _get_status_style(self, state: SystemState) -> str:
        """Obtener estilo CSS según el estado del sistema"""
        styles = {
            SystemState.INACTIVE: """
                QLabel {
                    color: #ff6b6b;
                    font-size: 16px;
                    font-weight: bold;
                    text-align: center;
                    padding: 10px;
                    border-radius: 8px;
                    background-color: #4d1f1f;
                }
            """,
            SystemState.STARTING: """
                QLabel {
                    color: #ffd43b;
                    font-size: 16px;
                    font-weight: bold;
                    text-align: center;
                    padding: 10px;
                    border-radius: 8px;
                    background-color: #4d3f1f;
                }
            """,
            SystemState.ACTIVE: """
                QLabel {
                    color: #51cf66;
                    font-size: 16px;
                    font-weight: bold;
                    text-align: center;
                    padding: 10px;
                    border-radius: 8px;
                    background-color: #2b4c3d;
                }
            """,
            SystemState.STOPPING: """
                QLabel {
                    color: #ffd43b;
                    font-size: 16px;
                    font-weight: bold;
                    text-align: center;
                    padding: 10px;
                    border-radius: 8px;
                    background-color: #4d3f1f;
                }
            """,
            SystemState.ERROR: """
                QLabel {
                    color: #ff6b6b;
                    font-size: 16px;
                    font-weight: bold;
                    text-align: center;
                    padding: 10px;
                    border-radius: 8px;
                    background-color: #4d1f1f;
                }
            """
        }
        return styles.get(state, styles[SystemState.INACTIVE])
    
    def update_ui_state(self):
        """Actualizar la UI según el estado actual"""
        state_texts = {
            SystemState.INACTIVE: "Sistema Inactivo",
            SystemState.STARTING: "Iniciando Sistema...",
            SystemState.ACTIVE: "Sistema Activo - Reconociendo",
            SystemState.STOPPING: "Deteniendo Sistema...",
            SystemState.ERROR: "Error del Sistema"
        }
        
        button_texts = {
            SystemState.INACTIVE: "▶ Iniciar Reconocimiento",
            SystemState.STARTING: "⏸ Iniciando...",
            SystemState.ACTIVE: "⏸ Detener Reconocimiento",
            SystemState.STOPPING: "⏸ Deteniendo...",
            SystemState.ERROR: "🔄 Reintentar"
        }
        
        recognition_status_texts = {
            SystemState.INACTIVE: "Reconocimiento: Inactivo",
            SystemState.STARTING: "Reconocimiento: Iniciando",
            SystemState.ACTIVE: "Reconocimiento: Activo",
            SystemState.STOPPING: "Reconocimiento: Deteniendo",
            SystemState.ERROR: "Reconocimiento: Error"
        }
        
        # Actualizar texto de estado
        self.system_status_label.setText(state_texts[self.system_state])
        self.system_status_label.setStyleSheet(self._get_status_style(self.system_state))
        
        # Actualizar botón
        self.btn_start_stop.setText(button_texts[self.system_state])
        self.btn_start_stop.setEnabled(self.system_state in [SystemState.INACTIVE, SystemState.ACTIVE, SystemState.ERROR] and not self._is_closing)
        
        # Actualizar estado de reconocimiento
        color = "#51cf66" if self.system_state == SystemState.ACTIVE else "#ff6b6b"
        self.system_labels['recognition_status'].setText(recognition_status_texts[self.system_state])
        self.system_labels['recognition_status'].setStyleSheet(f"""
            QLabel {{ color: {color}; font-size: 13px; padding: 5px; }}
        """)
    
    def toggle_recognition(self):
        """Alternar estado del reconocimiento"""
        if self._is_closing:
            return
            
        if self.system_state == SystemState.INACTIVE or self.system_state == SystemState.ERROR:
            self.start_recognition()
        elif self.system_state == SystemState.ACTIVE:
            self.stop_recognition()
    
    def start_recognition(self):
        """Iniciar reconocimiento facial"""
        if self._is_closing:
            return
            
        print("Iniciando reconocimiento...")
        
        # Cambiar estado
        self.system_state = SystemState.STARTING
        self.update_ui_state()
        
        # Verificar cámara
        if not self.camera_manager.is_initialized:
            print("Intentando reinicializar cámara...")
            if not self.camera_manager.initialize_camera():
                self.system_state = SystemState.ERROR
                self.update_ui_state()
                self._show_error("No se pudo inicializar la cámara")
                return
        
        # Reiniciar contadores de error
        self.camera_error_count = 0
        
        # Iniciar timers
        self.video_timer.start(33)  # ~30 FPS
        self.recognition_timer.start(int(self.recognition_interval * 1000))
        
        # Cambiar a estado activo
        self.system_state = SystemState.ACTIVE
        self.update_ui_state()
        
        print("Reconocimiento facial iniciado correctamente")
    
    def stop_recognition(self):
        """Detener reconocimiento facial"""
        print("Deteniendo reconocimiento...")
        
        # Cambiar estado
        self.system_state = SystemState.STOPPING
        self.update_ui_state()
        
        # Detener timers PRIMERO
        self.video_timer.stop()
        self.recognition_timer.stop()
        
        # Limpiar worker de forma segura
        self.cleanup_recognition_worker_safe()
        
        # Cambiar a estado inactivo
        self.system_state = SystemState.INACTIVE
        self.update_ui_state()
        
        # Limpiar video display
        self.video_label.setText("Reconocimiento detenido")
        self.video_label.clear()
        
        print("Reconocimiento detenido correctamente")
    
    def update_video_display(self):
        """Actualizar display de video"""
        if self.system_state != SystemState.ACTIVE or self._is_closing:
            return
        
        try:
            frame = self.camera_manager.get_frame()
            if frame is not None:
                self.camera_error_count = 0
                self.current_frame = frame.copy()
                self.display_frame(frame)
            else:
                self._handle_camera_error()
                
        except Exception as e:
            print(f"Error actualizando video: {e}")
            self._handle_camera_error()
    
    def trigger_recognition(self):
        """Disparar proceso de reconocimiento"""
        if (self.system_state != SystemState.ACTIVE or 
            self.current_frame is None or
            self._is_closing):
            return
        
        # Si hay un worker corriendo, no crear otro
        if self.recognition_worker and self.recognition_worker.isRunning():
            return
        
        # Limpiar worker anterior si existe
        if self.recognition_worker:
            self.cleanup_recognition_worker_safe()
        
        try:
            # Crear nuevo worker
            self.recognition_worker = RecognitionWorker(
                self.face_engine, 
                self.current_frame
            )
            
            # Conectar señales
            self.recognition_worker.recognition_result.connect(self.handle_recognition_result)
            self.recognition_worker.error_occurred.connect(self.handle_recognition_error)
            self.recognition_worker.finished.connect(self.on_recognition_worker_finished)
            
            # Iniciar
            self.recognition_worker.start()
            
        except Exception as e:
            print(f"Error iniciando reconocimiento: {e}")
    
    def cleanup_recognition_worker_safe(self):
        """Limpiar worker de reconocimiento de forma más segura"""
        if self.recognition_worker is not None:
            print("Limpiando recognition worker...")
            
            try:
                # Detener worker si está corriendo
                if self.recognition_worker.isRunning():
                    self.recognition_worker.stop_worker()
                    
                    # Esperar con timeout
                    if not self.recognition_worker.wait_for_finish(3000):
                        print("Recognition worker no terminó a tiempo")
                        self.recognition_worker.terminate()
                        self.recognition_worker.wait(1000)
                
                # Marcar para eliminación
                self.recognition_worker.deleteLater()
                self.recognition_worker = None
                print("Recognition worker limpiado correctamente")
                
            except Exception as e:
                print(f"Error limpiando recognition worker: {e}")
                # Forzar limpieza
                if self.recognition_worker:
                    self.recognition_worker.terminate()
                    self.recognition_worker.wait(1000)
                    self.recognition_worker.deleteLater()
                    self.recognition_worker = None
    
    @pyqtSlot()
    def on_recognition_worker_finished(self):
        """Manejar finalización del worker"""
        if not self._is_closing and self.recognition_worker:
            self.recognition_worker.deleteLater()
            self.recognition_worker = None
    
    def _handle_camera_error(self):
        """Manejar errores de cámara"""
        if self._is_closing:
            return
            
        self.camera_error_count += 1
        print(f"Error de cámara (count: {self.camera_error_count})")
        
        if self.camera_error_count >= self.max_camera_errors:
            print("Demasiados errores de cámara, intentando reinicializar...")
            
            # Detener reconocimiento temporalmente
            was_active = self.system_state == SystemState.ACTIVE
            if was_active:
                self.video_timer.stop()
                self.recognition_timer.stop()
            
            # Intentar reinicializar cámara
            if self.camera_manager.reinitialize_camera():
                print("Cámara reinicializada exitosamente")
                self.camera_error_count = 0
                self._update_camera_status("Conectada (recuperada)", True)
                
                # Reanudar si estaba activo
                if was_active and not self._is_closing:
                    QTimer.singleShot(500, self._resume_after_camera_recovery)
            else:
                print("No se pudo reinicializar la cámara")
                self.system_state = SystemState.ERROR
                self.update_ui_state()
                self._update_camera_status("Error crítico", False)
    
    def _resume_after_camera_recovery(self):
        """Reanudar reconocimiento después de recuperar cámara"""
        if self.system_state == SystemState.ACTIVE and not self._is_closing:
            self.video_timer.start(33)
            self.recognition_timer.start(int(self.recognition_interval * 1000))
    
    @pyqtSlot(list)
    def handle_recognition_result(self, faces):
        """Manejar resultado del reconocimiento"""
        if self.system_state != SystemState.ACTIVE or self._is_closing:
            return
            
        try:
            self.stats['total_recognitions'] += 1
            
            if not faces:
                self._update_recognition_display("No se detectan rostros", "warning")
                return
            
            # Procesar caras detectadas
            recognized_users = []
            unknown_faces = 0
            
            for face in faces:
                if face['is_known']:
                    self.stats['successful_recognitions'] += 1
                    recognized_users.append(face)
                    
                    # Registrar acceso en la base de datos
                    self.db_manager.log_access_attempt(
                        face['user_id'], 
                        'granted', 
                        face['confidence']
                    )
                    
                    # Emitir señal de acceso concedido
                    self.access_granted.emit(face)
                    
                else:
                    unknown_faces += 1
                    self.stats['failed_recognitions'] += 1
                    
                    # Registrar intento fallido
                    self.db_manager.log_access_attempt(
                        None, 
                        'denied', 
                        face['confidence']
                    )
                    
                    # Emitir señal de acceso denegado
                    self.access_denied.emit(face)
            
            # Actualizar display
            if recognized_users:
                if len(recognized_users) == 1:
                    user = recognized_users[0]
                    message = f"✅ {user['name']} - {user['confidence']:.1f}%"
                    self._update_recognition_display(message, "success")
                else:
                    message = f"✅ {len(recognized_users)} usuarios reconocidos"
                    self._update_recognition_display(message, "success")
            elif unknown_faces > 0:
                message = f"❌ {unknown_faces} rostro(s) no reconocido(s)"
                self._update_recognition_display(message, "error")
            
            # Actualizar logs
            if not self._is_closing:
                QTimer.singleShot(100, self.refresh_logs)
            
        except Exception as e:
            print(f"Error manejando resultado de reconocimiento: {e}")
    
    @pyqtSlot(str)
    def handle_recognition_error(self, error_message):
        """Manejar errores de reconocimiento"""
        if not self._is_closing:
            print(f"Error de reconocimiento: {error_message}")
            self._update_recognition_display("Error en reconocimiento", "error")
    
    def _update_recognition_display(self, message: str, message_type: str):
        """Actualizar display con resultado del reconocimiento"""
        if self._is_closing:
            return
            
        current_time = datetime.now().strftime("%H:%M:%S")
        full_message = f"{message} ({current_time})"
        
        styles = {
            "success": """
                QLabel {
                    color: #51cf66;
                    font-size: 14px;
                    text-align: center;
                    padding: 10px;
                    border-radius: 8px;
                    background-color: #2b4c3d;
                }
            """,
            "error": """
                QLabel {
                    color: #ff6b6b;
                    font-size: 14px;
                    text-align: center;
                    padding: 10px;
                    border-radius: 8px;
                    background-color: #4d1f1f;
                }
            """,
            "warning": """
                QLabel {
                    color: #ffd43b;
                    font-size: 14px;
                    text-align: center;
                    padding: 10px;
                    border-radius: 8px;
                    background-color: #4d3f1f;
                }
            """
        }
        
        self.last_recognition_info.setText(full_message)
        self.last_recognition_info.setStyleSheet(styles.get(message_type, styles["warning"]))
    
    def display_frame(self, frame):
        """Mostrar frame en el widget de video"""
        if self._is_closing:
            return
            
        try:
            # Convertir frame a RGB
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # Escalar imagen
            pixmap = QPixmap.fromImage(qt_image)
            scaled_pixmap = pixmap.scaled(
                self.video_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            self.video_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            print(f"Error mostrando frame: {e}")
    
    def update_statistics(self):
        """Actualizar estadísticas mostradas"""
        if self._is_closing:
            return
            
        try:
            # Calcular precisión
            if self.stats['total_recognitions'] > 0:
                accuracy = (self.stats['successful_recognitions'] / self.stats['total_recognitions']) * 100
            else:
                accuracy = 0.0
            
            # Obtener estadísticas de la base de datos
            db_stats = self.db_manager.get_database_stats()
            
            # Actualizar labels
            self.stats_labels['total'].setText(f"Total de reconocimientos: {self.stats['total_recognitions']}")
            self.stats_labels['successful'].setText(f"Reconocimientos exitosos: {self.stats['successful_recognitions']}")
            self.stats_labels['failed'].setText(f"Reconocimientos fallidos: {self.stats['failed_recognitions']}")
            self.stats_labels['accuracy'].setText(f"Precisión: {accuracy:.1f}%")
            self.stats_labels['users_count'].setText(f"Usuarios registrados: {db_stats.get('total_users', 0)}")
            
            if db_stats.get('last_access'):
                self.stats_labels['last_access'].setText(f"Último acceso: {db_stats['last_access']}")
            
            # Actualizar timestamp
            current_time = datetime.now().strftime("%H:%M:%S")
            self.system_labels['last_update'].setText(f"Última actualización: {current_time}")
            
        except Exception as e:
            print(f"Error actualizando estadísticas: {e}")
    
    def refresh_logs(self):
        """Actualizar tabla de logs"""
        if self._is_closing:
            return
            
        try:
            logs = self.db_manager.get_access_logs(20)  # Últimos 20 logs
            
            self.logs_table.setRowCount(len(logs))
            
            for row, log in enumerate(logs):
                log_id, user_name, access_type, confidence, timestamp = log
                
                # Formatear timestamp
                if timestamp:
                    time_str = datetime.fromisoformat(timestamp).strftime("%H:%M:%S")
                else:
                    time_str = "--"
                
                # Configurar items de la tabla
                time_item = QTableWidgetItem(time_str)
                user_item = QTableWidgetItem(user_name or "Desconocido")
                
                # Configurar item de resultado con color
                if access_type == 'granted':
                    result_item = QTableWidgetItem("✅ Concedido")
                    result_item.setForeground(QColor("#51cf66"))
                elif access_type == 'denied':
                    result_item = QTableWidgetItem("❌ Denegado")
                    result_item.setForeground(QColor("#ff6b6b"))
                else:
                    result_item = QTableWidgetItem("❓ Desconocido")
                    result_item.setForeground(QColor("#ffd43b"))
                
                confidence_item = QTableWidgetItem(f"{confidence:.1f}%" if confidence else "--")
                
                # Agregar items a la tabla
                self.logs_table.setItem(row, 0, time_item)
                self.logs_table.setItem(row, 1, user_item)
                self.logs_table.setItem(row, 2, result_item)
                self.logs_table.setItem(row, 3, confidence_item)
            
        except Exception as e:
            print(f"Error actualizando logs: {e}")
    
    def refresh_users_list(self):
        """Actualizar lista de usuarios"""
        if self._is_closing:
            return
            
        try:
            users = self.db_manager.get_all_users()
            
            self.users_table.setRowCount(len(users))
            
            for row, user in enumerate(users):
                user_id, name, email, _, _ = user
                
                id_item = QTableWidgetItem(str(user_id))
                name_item = QTableWidgetItem(name)
                email_item = QTableWidgetItem(email)
                
                self.users_table.setItem(row, 0, id_item)
                self.users_table.setItem(row, 1, name_item)
                self.users_table.setItem(row, 2, email_item)
            
        except Exception as e:
            print(f"Error actualizando lista de usuarios: {e}")
    
    def _show_error(self, message: str):
        """Mostrar mensaje de error"""
        if not self._is_closing:
            print(f"Error: {message}")
            self._update_recognition_display(f"Error: {message}", "error")
    
    def showEvent(self, event):
        """Evento cuando se muestra la pantalla"""
        super().showEvent(event)
        # Actualizar datos cuando se muestra la pantalla
        if not self._is_closing:
            self.update_statistics()
            self.refresh_logs()
            self.refresh_users_list()
    
    def closeEvent(self, event):
        """Manejar cierre mejorado de la ventana de forma segura"""
        print("Iniciando cierre de RecognitionScreen...")
        self._is_closing = True
        
        # Ignorar evento inicialmente para manejo seguro
        event.ignore()
        
        # Detener sistema
        if self.system_state in [SystemState.ACTIVE, SystemState.STARTING]:
            self.stop_recognition()
        
        # Detener todos los timers
        self.video_timer.stop()
        self.recognition_timer.stop()
        self.stats_timer.stop()
        
        # Limpiar worker
        self.cleanup_recognition_worker_safe()
        
        # Liberar cámara
        try:
            self.camera_manager.release_camera()
            print("Cámara liberada correctamente")
        except Exception as e:
            print(f"Error liberando cámara: {e}")
        
        # Usar timer para finalizar cierre de forma segura
        if not self._cleanup_timer:
            self._cleanup_timer = QTimer()
            self._cleanup_timer.setSingleShot(True)
            self._cleanup_timer.timeout.connect(lambda: self._finalize_close_safe(event))
            self._cleanup_timer.start(2000)  # Dar más tiempo para limpieza
    
    def _finalize_close_safe(self, event):
        """Finalizar cierre de forma más segura"""
        print("Finalizando cierre de RecognitionScreen...")
        
        # Verificación final de threads
        if self.recognition_worker is not None:
            if self.recognition_worker.isRunning():
                print("Advertencia: Recognition worker aún corriendo, terminando...")
                self.recognition_worker.terminate()
                self.recognition_worker.wait(2000)
            
            self.recognition_worker.deleteLater()
            self.recognition_worker = None
        
        # Limpiar timer de cleanup
        if self._cleanup_timer:
            self._cleanup_timer.deleteLater()
            self._cleanup_timer = None
        
        print("RecognitionScreen cerrada correctamente")
        event.accept()