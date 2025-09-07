"""
Pantalla de reconocimiento facial para FaceGuard
Realiza reconocimiento en tiempo real y gestión de accesos
"""

import cv2
import numpy as np
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QFrame, QSpacerItem, QSizePolicy,
                            QTableWidget, QTableWidgetItem, QHeaderView,
                            QTabWidget, QGroupBox, QProgressBar)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QPixmap, QImage, QColor

from ..core.camera_manager import CameraManager
from ..core.face_recognition_engine import FaceRecognitionEngine
from ..core.database_manager import DatabaseManager


class RecognitionWorker(QThread):
    """Worker thread para el reconocimiento facial"""
    
    recognition_result = pyqtSignal(list)
    
    def __init__(self, face_engine, frame):
        super().__init__()
        self.face_engine = face_engine
        self.frame = frame
        self.running = True
    
    def run(self):
        """Ejecutar reconocimiento en hilo separado"""
        if self.running and self.frame is not None:
            faces = self.face_engine.recognize_face(self.frame)
            if self.running:
                self.recognition_result.emit(faces)
    
    def stop(self):
        self.running = False


class RecognitionScreen(QWidget):
    """Pantalla principal de reconocimiento facial"""
    
    # Señales
    back_clicked = pyqtSignal()
    access_granted = pyqtSignal(dict)
    access_denied = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.camera_manager = CameraManager()
        self.face_engine = FaceRecognitionEngine()
        self.db_manager = DatabaseManager()
        
        self.current_frame = None
        self.timer = QTimer()
        self.recognition_worker = None
        self.last_recognition_time = datetime.now()
        self.recognition_interval = 1.0  # Segundos entre reconocimientos
        
        # Estado del sistema
        self.is_active = False
        self.total_recognitions = 0
        self.successful_recognitions = 0
        self.failed_recognitions = 0
        
        self.init_ui()
        self.setup_camera()
    
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
        self.system_status = QLabel("Sistema Inactivo")
        self.system_status.setStyleSheet("""
            QLabel {
                color: #ff6b6b;
                font-size: 16px;
                font-weight: bold;
                text-align: center;
                padding: 10px;
                border-radius: 8px;
                background-color: #4d1f1f;
            }
        """)
        self.system_status.setAlignment(Qt.AlignCenter)
        
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
            QPushButton:checked {
                background-color: #ff6b6b;
            }
        """)
        self.btn_start_stop.setCheckable(True)
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
        camera_layout.addWidget(self.system_status)
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
        
        # Tab 1: Estadísticas
        stats_tab = self.create_stats_tab()
        tab_widget.addTab(stats_tab, "📊 Estadísticas")
        
        # Tab 2: Logs recientes
        logs_tab = self.create_logs_tab()
        tab_widget.addTab(logs_tab, "📋 Logs Recientes")
        
        # Tab 3: Usuarios registrados
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
    
    def setup_camera(self):
        """Configurar la cámara"""
        try:
            if self.camera_manager.initialize_camera():
                self.system_labels['camera_status'].setText("Cámara: Conectada")
                self.system_labels['camera_status'].setStyleSheet("""
                    QLabel { color: #51cf66; font-size: 13px; padding: 5px; }
                """)
                print("Cámara configurada correctamente")
            else:
                self.system_labels['camera_status'].setText("Cámara: Error")
                self.system_labels['camera_status'].setStyleSheet("""
                    QLabel { color: #ff6b6b; font-size: 13px; padding: 5px; }
                """)
                
        except Exception as e:
            print(f"Error configurando cámara: {e}")
    
    def toggle_recognition(self):
        """Alternar estado del reconocimiento"""
        if self.is_active:
            self.stop_recognition()
        else:
            self.start_recognition()
    
    def start_recognition(self):
        """Iniciar reconocimiento facial"""
        if not self.camera_manager.is_initialized:
            if not self.camera_manager.initialize_camera():
                self.show_error("No se pudo inicializar la cámara")
                return
        
        self.is_active = True
        self.timer.timeout.connect(self.update_recognition)
        self.timer.start(33)  # ~30 FPS
        
        # Actualizar UI
        self.btn_start_stop.setText("⏸ Detener Reconocimiento")
        self.btn_start_stop.setChecked(True)
        self.system_status.setText("Sistema Activo - Reconociendo")
        self.system_status.setStyleSheet("""
            QLabel {
                color: #51cf66;
                font-size: 16px;
                font-weight: bold;
                text-align: center;
                padding: 10px;
                border-radius: 8px;
                background-color: #2b4c3d;
            }
        """)
        
        self.system_labels['recognition_status'].setText("Reconocimiento: Activo")
        self.system_labels['recognition_status'].setStyleSheet("""
            QLabel { color: #51cf66; font-size: 13px; padding: 5px; }
        """)
        
        print("Reconocimiento facial iniciado")
    
    def stop_recognition(self):
        """Detener reconocimiento facial"""
        self.is_active = False
        self.timer.stop()
        
        # Detener worker si está ejecutándose
        if self.recognition_worker and self.recognition_worker.isRunning():
            self.recognition_worker.stop()
            self.recognition_worker.quit()
            self.recognition_worker.wait()
        
        # Actualizar UI
        self.btn_start_stop.setText("▶ Iniciar Reconocimiento")
        self.btn_start_stop.setChecked(False)
        self.system_status.setText("Sistema Inactivo")
        self.system_status.setStyleSheet("""
            QLabel {
                color: #ff6b6b;
                font-size: 16px;
                font-weight: bold;
                text-align: center;
                padding: 10px;
                border-radius: 8px;
                background-color: #4d1f1f;
            }
        """)
        
        self.system_labels['recognition_status'].setText("Reconocimiento: Inactivo")
        self.system_labels['recognition_status'].setStyleSheet("""
            QLabel { color: #ff6b6b; font-size: 13px; padding: 5px; }
        """)
        
        self.video_label.setText("Reconocimiento detenido")
        print("Reconocimiento facial detenido")
    
    def update_recognition(self):
        """Actualizar reconocimiento en tiempo real"""
        try:
            frame = self.camera_manager.get_frame()
            if frame is not None:
                self.current_frame = frame.copy()
                
                # Verificar si es tiempo de hacer reconocimiento
                current_time = datetime.now()
                time_diff = (current_time - self.last_recognition_time).total_seconds()
                
                if time_diff >= self.recognition_interval:
                    # Iniciar reconocimiento en hilo separado
                    if not self.recognition_worker or not self.recognition_worker.isRunning():
                        self.recognition_worker = RecognitionWorker(self.face_engine, frame)
                        self.recognition_worker.recognition_result.connect(self.handle_recognition_result)
                        self.recognition_worker.start()
                        self.last_recognition_time = current_time
                
                # Mostrar frame actual (sin procesar para mejor rendimiento)
                self.display_frame(frame)
                
        except Exception as e:
            print(f"Error en actualización de reconocimiento: {e}")
    
    @pyqtSlot(list)
    def handle_recognition_result(self, faces):
        """Manejar resultado del reconocimiento"""
        try:
            self.total_recognitions += 1
            
            if not faces:
                # No se detectaron caras
                self.last_recognition_info.setText("🔍 No se detectan rostros")
                self.last_recognition_info.setStyleSheet("""
                    QLabel {
                        color: #ffd43b;
                        font-size: 14px;
                        text-align: center;
                        padding: 10px;
                        border-radius: 8px;
                        background-color: #4d3f1f;
                    }
                """)
                return
            
            # Procesar caras detectadas
            recognized_users = []
            unknown_faces = 0
            
            for face in faces:
                if face['is_known']:
                    self.successful_recognitions += 1
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
                    self.failed_recognitions += 1
                    
                    # Registrar intento fallido
                    self.db_manager.log_access_attempt(
                        None, 
                        'denied', 
                        face['confidence']
                    )
                    
                    # Emitir señal de acceso denegado
                    self.access_denied.emit(face)
            
            # Actualizar información mostrada
            self.update_recognition_display(recognized_users, unknown_faces)
            
            # Actualizar estadísticas
            self.update_statistics()
            
            # Actualizar logs
            self.refresh_logs()
            
        except Exception as e:
            print(f"Error manejando resultado de reconocimiento: {e}")
    
    def update_recognition_display(self, recognized_users, unknown_faces):
        """Actualizar display con resultado del reconocimiento"""
        current_time = datetime.now().strftime("%H:%M:%S")
        
        if recognized_users:
            if len(recognized_users) == 1:
                user = recognized_users[0]
                message = f"✅ {user['name']} - {user['confidence']:.1f}% ({current_time})"
                style = """
                    QLabel {
                        color: #51cf66;
                        font-size: 14px;
                        text-align: center;
                        padding: 10px;
                        border-radius: 8px;
                        background-color: #2b4c3d;
                    }
                """
            else:
                message = f"✅ {len(recognized_users)} usuarios reconocidos ({current_time})"
                style = """
                    QLabel {
                        color: #51cf66;
                        font-size: 14px;
                        text-align: center;
                        padding: 10px;
                        border-radius: 8px;
                        background-color: #2b4c3d;
                    }
                """
        elif unknown_faces > 0:
            message = f"❌ {unknown_faces} rostro(s) no reconocido(s) ({current_time})"
            style = """
                QLabel {
                    color: #ff6b6b;
                    font-size: 14px;
                    text-align: center;
                    padding: 10px;
                    border-radius: 8px;
                    background-color: #4d1f1f;
                }
            """
        else:
            message = f"🔍 Analizando... ({current_time})"
            style = """
                QLabel {
                    color: #ffd43b;
                    font-size: 14px;
                    text-align: center;
                    padding: 10px;
                    border-radius: 8px;
                    background-color: #4d3f1f;
                }
            """
        
        self.last_recognition_info.setText(message)
        self.last_recognition_info.setStyleSheet(style)
    
    def display_frame(self, frame):
        """Mostrar frame en el widget de video"""
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
        try:
            # Calcular precisión
            if self.total_recognitions > 0:
                accuracy = (self.successful_recognitions / self.total_recognitions) * 100
            else:
                accuracy = 0.0
            
            # Obtener estadísticas de la base de datos
            db_stats = self.db_manager.get_database_stats()
            
            # Actualizar labels
            self.stats_labels['total'].setText(f"Total de reconocimientos: {self.total_recognitions}")
            self.stats_labels['successful'].setText(f"Reconocimientos exitosos: {self.successful_recognitions}")
            self.stats_labels['failed'].setText(f"Reconocimientos fallidos: {self.failed_recognitions}")
            self.stats_labels['accuracy'].setText(f"Precisión: {accuracy:.1f}%")
            self.stats_labels['users_count'].setText(f"Usuarios registrados: {db_stats['total_users']}")
            
            if db_stats['last_access']:
                self.stats_labels['last_access'].setText(f"Último acceso: {db_stats['last_access']}")
            
            # Actualizar timestamp
            current_time = datetime.now().strftime("%H:%M:%S")
            self.system_labels['last_update'].setText(f"Última actualización: {current_time}")
            
        except Exception as e:
            print(f"Error actualizando estadísticas: {e}")
    
    def refresh_logs(self):
        """Actualizar tabla de logs"""
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
    
    def showEvent(self, event):
        """Evento cuando se muestra la pantalla"""
        super().showEvent(event)
        # Actualizar datos cuando se muestra la pantalla
        self.update_statistics()
        self.refresh_logs()
        self.refresh_users_list()
    
    def closeEvent(self, event):
        """Manejar cierre de la ventana"""
        if self.is_active:
            self.stop_recognition()
        
        if self.recognition_worker and self.recognition_worker.isRunning():
            self.recognition_worker.stop()
            self.recognition_worker.quit()
            self.recognition_worker.wait()
        
        self.camera_manager.release_camera()
        event.accept()