"""
Pantalla de registro de usuarios para FaceGuard
Permite capturar datos y foto del usuario
"""

import cv2
import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QLineEdit, QFrame, QSpacerItem, 
                            QSizePolicy, QMessageBox, QProgressBar)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QPixmap, QImage

from ..core.camera_manager import CameraManager
from ..core.face_recognition_engine import FaceRecognitionEngine


class RegistrationWorker(QThread):
    """Worker thread para el registro de usuario"""
    
    registration_complete = pyqtSignal(bool, str)
    
    def __init__(self, face_engine, image, name, email):
        super().__init__()
        self.face_engine = face_engine
        self.image = image
        self.name = name
        self.email = email
    
    def run(self):
        """Ejecutar el registro en hilo separado"""
        success, message = self.face_engine.register_face(self.image, self.name, self.email)
        self.registration_complete.emit(success, message)


class RegistrationScreen(QWidget):
    """Pantalla de registro de nuevos usuarios"""
    
    # Señales
    back_clicked = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.camera_manager = CameraManager()
        self.face_engine = FaceRecognitionEngine()
        self.current_frame = None
        self.timer = QTimer()
        self.registration_worker = None
        
        self.init_ui()
        self.setup_camera()
    
    def init_ui(self):
        """Inicializar la interfaz de usuario"""
        # Layout principal
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Panel izquierdo - Formulario
        self.create_form_panel(main_layout)
        
        # Panel derecho - Cámara
        self.create_camera_panel(main_layout)
    
    def create_form_panel(self, main_layout):
        """Crear panel del formulario"""
        form_frame = QFrame()
        form_frame.setFixedWidth(400)
        form_frame.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 15px;
                padding: 20px;
            }
        """)
        
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(20)
        
        # Título
        title_label = QLabel("Registrar Nuevo Usuario")
        title_label.setStyleSheet("""
            QLabel {
                color: #00d4aa;
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 10px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        
        # Descripción
        desc_label = QLabel(
            "Complete los datos del usuario y capture una foto clara del rostro.\n\n"
            "Asegúrese de que haya buena iluminación y que el rostro esté completamente visible."
        )
        desc_label.setStyleSheet("""
            QLabel {
                color: #ccc;
                font-size: 14px;
                line-height: 1.4;
            }
        """)
        desc_label.setWordWrap(True)
        
        # Campos del formulario
        # Nombre
        name_label = QLabel("Nombre completo:")
        name_label.setStyleSheet("color: white; font-weight: bold;")
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ingrese el nombre completo")
        self.name_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 2px solid #555;
                border-radius: 8px;
                background-color: #3b3b3b;
                color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #00d4aa;
            }
        """)
        
        # Email
        email_label = QLabel("Correo electrónico:")
        email_label.setStyleSheet("color: white; font-weight: bold;")
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("usuario@ejemplo.com")
        self.email_input.setStyleSheet(self.name_input.styleSheet())
        
        # Estado de calidad de imagen
        quality_label = QLabel("Calidad de imagen:")
        quality_label.setStyleSheet("color: white; font-weight: bold;")
        
        self.quality_status = QLabel("Esperando captura...")
        self.quality_status.setStyleSheet("""
            QLabel {
                color: #999;
                font-size: 14px;
                padding: 8px;
                border-radius: 5px;
                background-color: #333;
            }
        """)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #00d4aa;
                border-radius: 3px;
            }
        """)
        
        # Botones
        buttons_layout = QHBoxLayout()
        
        self.btn_back = QPushButton("← Volver")
        self.btn_back.setFixedSize(120, 45)
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
        
        self.btn_register = QPushButton("Registrar Usuario")
        self.btn_register.setFixedSize(200, 45)
        self.btn_register.setStyleSheet("""
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
                background-color: #555;
                color: #999;
            }
        """)
        self.btn_register.clicked.connect(self.register_user)
        
        buttons_layout.addWidget(self.btn_back)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_register)
        
        # Agregar todos los elementos al layout
        form_layout.addWidget(title_label)
        form_layout.addWidget(desc_label)
        form_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))
        form_layout.addWidget(name_label)
        form_layout.addWidget(self.name_input)
        form_layout.addWidget(email_label)
        form_layout.addWidget(self.email_input)
        form_layout.addWidget(quality_label)
        form_layout.addWidget(self.quality_status)
        form_layout.addWidget(self.progress_bar)
        form_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        form_layout.addLayout(buttons_layout)
        
        main_layout.addWidget(form_frame)
    
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
        
        # Título de la cámara
        camera_title = QLabel("Vista previa de la cámara")
        camera_title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 18px;
                font-weight: bold;
                text-align: center;
            }
        """)
        camera_title.setAlignment(Qt.AlignCenter)
        
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
        self.video_label.setText("Iniciando cámara...")
        
        # Botones de cámara
        camera_buttons_layout = QHBoxLayout()
        
        self.btn_capture = QPushButton("📸 Capturar Foto")
        self.btn_capture.setFixedSize(150, 40)
        self.btn_capture.setStyleSheet("""
            QPushButton {
                background-color: #00d4aa;
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00b894;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
        """)
        self.btn_capture.clicked.connect(self.capture_photo)
        self.btn_capture.setEnabled(False)
        
        self.btn_toggle_camera = QPushButton("🔄 Reiniciar Cámara")
        self.btn_toggle_camera.setFixedSize(150, 40)
        self.btn_toggle_camera.setStyleSheet("""
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
        self.btn_toggle_camera.clicked.connect(self.toggle_camera)
        
        camera_buttons_layout.addStretch()
        camera_buttons_layout.addWidget(self.btn_capture)
        camera_buttons_layout.addWidget(self.btn_toggle_camera)
        camera_buttons_layout.addStretch()
        
        # Status de detección
        self.detection_status = QLabel("🔍 Buscando rostros...")
        self.detection_status.setStyleSheet("""
            QLabel {
                color: #999;
                font-size: 14px;
                text-align: center;
                padding: 8px;
                border-radius: 5px;
                background-color: #333;
            }
        """)
        self.detection_status.setAlignment(Qt.AlignCenter)
        
        camera_layout.addWidget(camera_title)
        camera_layout.addWidget(self.video_label)
        camera_layout.addLayout(camera_buttons_layout)
        camera_layout.addWidget(self.detection_status)
        
        main_layout.addWidget(camera_frame)
    
    def setup_camera(self):
        """Configurar y iniciar la cámara"""
        try:
            if self.camera_manager.initialize_camera():
                self.timer.timeout.connect(self.update_frame)
                self.timer.start(30)  # ~33 FPS
                self.btn_capture.setEnabled(True)
                print("Cámara iniciada correctamente")
            else:
                self.show_error("No se pudo inicializar la cámara")
                
        except Exception as e:
            self.show_error(f"Error configurando cámara: {str(e)}")
    
    def update_frame(self):
        """Actualizar frame de la cámara"""
        try:
            frame = self.camera_manager.get_frame()
            if frame is not None:
                self.current_frame = frame.copy()
                
                # Detectar caras para feedback visual
                faces = self.face_engine.recognize_face(frame)
                
                # Dibujar rectángulos de detección
                display_frame = self.face_engine.draw_recognition_results(frame, faces)
                
                # Actualizar estado de detección
                if len(faces) == 0:
                    self.detection_status.setText("🔍 No se detectan rostros")
                    self.detection_status.setStyleSheet("""
                        QLabel {
                            color: #ff6b6b;
                            background-color: #4d1f1f;
                            font-size: 14px;
                            text-align: center;
                            padding: 8px;
                            border-radius: 5px;
                        }
                    """)
                elif len(faces) == 1:
                    # Evaluar calidad de la imagen
                    quality_score, quality_msg = self.face_engine.get_face_quality_score(frame)
                    
                    if quality_score >= 70:
                        self.detection_status.setText(f"✅ Rostro detectado - {quality_msg}")
                        self.detection_status.setStyleSheet("""
                            QLabel {
                                color: #51cf66;
                                background-color: #2b4c3d;
                                font-size: 14px;
                                text-align: center;
                                padding: 8px;
                                border-radius: 5px;
                            }
                        """)
                    else:
                        self.detection_status.setText(f"⚠️ Rostro detectado - {quality_msg}")
                        self.detection_status.setStyleSheet("""
                            QLabel {
                                color: #ffd43b;
                                background-color: #4d3f1f;
                                font-size: 14px;
                                text-align: center;
                                padding: 8px;
                                border-radius: 5px;
                            }
                        """)
                    
                    self.quality_status.setText(f"{quality_msg} ({quality_score:.1f}%)")
                    
                else:
                    self.detection_status.setText("⚠️ Múltiples rostros detectados")
                    self.detection_status.setStyleSheet("""
                        QLabel {
                            color: #ffd43b;
                            background-color: #4d3f1f;
                            font-size: 14px;
                            text-align: center;
                            padding: 8px;
                            border-radius: 5px;
                        }
                    """)
                
                # Convertir frame a QImage y mostrar
                rgb_image = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                
                # Escalar imagen para ajustar al widget
                pixmap = QPixmap.fromImage(qt_image)
                scaled_pixmap = pixmap.scaled(
                    self.video_label.size(), 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                
                self.video_label.setPixmap(scaled_pixmap)
                
        except Exception as e:
            print(f"Error actualizando frame: {e}")
    
    def capture_photo(self):
        """Capturar foto actual"""
        if self.current_frame is not None:
            # Evaluar calidad antes de permitir captura
            quality_score, quality_msg = self.face_engine.get_face_quality_score(self.current_frame)
            
            if quality_score < 40:
                QMessageBox.warning(
                    self, 
                    "Calidad Insuficiente",
                    f"La calidad de la imagen es muy baja ({quality_msg}).\n"
                    "Por favor, mejore la iluminación y posición del rostro."
                )
                return
            
            # Mostrar preview de la foto capturada
            self.show_capture_preview()
        else:
            QMessageBox.warning(self, "Error", "No hay imagen disponible para capturar")
    
    def show_capture_preview(self):
        """Mostrar preview de la foto capturada"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Foto Capturada")
        msg_box.setText("¿Desea usar esta foto para el registro?")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.Yes)
        
        # Agregar imagen al mensaje
        if self.current_frame is not None:
            rgb_image = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            pixmap = QPixmap.fromImage(qt_image)
            scaled_pixmap = pixmap.scaled(300, 225, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            msg_box.setIconPixmap(scaled_pixmap)
        
        if msg_box.exec_() == QMessageBox.Yes:
            self.quality_status.setText("✅ Foto capturada correctamente")
            self.quality_status.setStyleSheet("""
                QLabel {
                    color: #51cf66;
                    background-color: #2b4c3d;
                    font-size: 14px;
                    padding: 8px;
                    border-radius: 5px;
                }
            """)
    
    def register_user(self):
        """Registrar nuevo usuario"""
        # Validar campos
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Error", "Por favor, ingrese el nombre completo")
            self.name_input.setFocus()
            return
        
        if not email or '@' not in email:
            QMessageBox.warning(self, "Error", "Por favor, ingrese un email válido")
            self.email_input.setFocus()
            return
        
        if self.current_frame is None:
            QMessageBox.warning(self, "Error", "No hay imagen disponible. Capture una foto primero")
            return
        
        # Verificar calidad mínima
        quality_score, quality_msg = self.face_engine.get_face_quality_score(self.current_frame)
        if quality_score < 50:
            reply = QMessageBox.question(
                self, 
                "Calidad Baja", 
                f"La calidad de la imagen es baja ({quality_msg}).\n"
                "¿Desea continuar con el registro de todos modos?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # Deshabilitar botones y mostrar progreso
        self.btn_register.setEnabled(False)
        self.btn_back.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Progreso indeterminado
        
        # Iniciar registro en hilo separado
        self.registration_worker = RegistrationWorker(
            self.face_engine, 
            self.current_frame, 
            name, 
            email
        )
        self.registration_worker.registration_complete.connect(self.on_registration_complete)
        self.registration_worker.start()
    
    @pyqtSlot(bool, str)
    def on_registration_complete(self, success, message):
        """Manejar completación del registro"""
        # Ocultar progreso y rehabilitar botones
        self.progress_bar.setVisible(False)
        self.btn_register.setEnabled(True)
        self.btn_back.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Éxito", message)
            # Limpiar formulario
            self.name_input.clear()
            self.email_input.clear()
            self.quality_status.setText("Esperando captura...")
            self.quality_status.setStyleSheet("""
                QLabel {
                    color: #999;
                    font-size: 14px;
                    padding: 8px;
                    border-radius: 5px;
                    background-color: #333;
                }
            """)
        else:
            QMessageBox.critical(self, "Error", f"Error en el registro:\n{message}")
        
        # Limpiar worker
        if self.registration_worker:
            self.registration_worker.deleteLater()
            self.registration_worker = None
    
    def toggle_camera(self):
        """Alternar estado de la cámara"""
        self.timer.stop()
        self.camera_manager.release_camera()
        
        # Reiniciar cámara
        if self.camera_manager.initialize_camera():
            self.timer.start(30)
            self.btn_capture.setEnabled(True)
        else:
            self.show_error("No se pudo reiniciar la cámara")
    
    def show_error(self, message):
        """Mostrar mensaje de error"""
        QMessageBox.critical(self, "Error", message)
    
    def closeEvent(self, event):
        """Manejar cierre de la ventana"""
        if self.timer.isActive():
            self.timer.stop()
        
        if self.registration_worker and self.registration_worker.isRunning():
            self.registration_worker.quit()
            self.registration_worker.wait()
        
        self.camera_manager.release_camera()
        event.accept()