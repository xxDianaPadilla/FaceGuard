"""
Pantalla de registro de usuarios para FaceGuard
Permite capturar datos y foto del usuario
"""

import cv2
import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QLineEdit, QFrame, QSpacerItem, 
                            QSizePolicy, QMessageBox, QProgressBar)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot, QMutex, QWaitCondition
from PyQt5.QtGui import QFont, QPixmap, QImage

from ..core.camera_manager import CameraManager
from ..core.face_recognition_engine import FaceRecognitionEngine


class RegistrationWorker(QThread):
    """Worker thread mejorado para el registro de usuario"""
    
    registration_complete = pyqtSignal(bool, str)
    
    def __init__(self, face_engine, image, name, email):
        super().__init__()
        self.face_engine = face_engine
        self.image = image
        self.name = name
        self.email = email
        
        # Control de parada mejorado
        self._should_run = True
        self._mutex = QMutex()
        self._stop_condition = QWaitCondition()
        self._is_processing = False
        
        # Configurar thread
        self.setObjectName("RegistrationWorker")
    
    def run(self):
        """Ejecutar el registro en hilo separado con control de parada"""
        if not self._should_run:
            return
            
        try:
            # Marcar que estamos procesando
            self._mutex.lock()
            self._is_processing = True
            should_continue = self._should_run
            self._mutex.unlock()
            
            if not should_continue:
                return
            
            # Verificar múltiples veces durante el procesamiento
            for i in range(3):
                self._mutex.lock()
                should_continue = self._should_run
                self._mutex.unlock()
                
                if not should_continue:
                    return
                
                # Pequeña pausa para dar oportunidad de cancelar
                if i > 0:
                    self.msleep(50)
            
            # Realizar registro si aún debemos continuar
            self._mutex.lock()
            should_continue = self._should_run
            self._mutex.unlock()
            
            if should_continue:
                success, message = self.face_engine.register_face(
                    self.image, self.name, self.email
                )
                
                # Verificar antes de emitir resultado
                self._mutex.lock()
                should_emit = self._should_run
                self._mutex.unlock()
                
                if should_emit:
                    self.registration_complete.emit(success, message)
                
        except Exception as e:
            # Verificar si aún debemos emitir error
            self._mutex.lock()
            should_emit = self._should_run
            self._mutex.unlock()
            
            if should_emit:
                error_msg = f"Error en registro: {str(e)}"
                self.registration_complete.emit(False, error_msg)
        
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
        
        # Desconectar señales para evitar emisiones tardías
        try:
            self.registration_complete.disconnect()
        except:
            pass  # Ignorar si ya está desconectado
    
    def wait_for_finish(self, timeout_ms=3000):
        """Esperar a que termine con timeout"""
        self._mutex.lock()
        
        if self._is_processing:
            # Esperar con timeout
            self._stop_condition.wait(self._mutex, timeout_ms)
        
        self._mutex.unlock()
        
        # Esperar que el thread termine
        return self.wait(timeout_ms)


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
        self._is_closing = False
        self._cleanup_timer = None
        
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
        if self._is_closing:
            return
            
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
        if self._is_closing:
            return
            
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
        if self._is_closing:
            return
            
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
        
        # Limpiar worker anterior si existe
        self.cleanup_registration_worker()
        
        # Deshabilitar botones y mostrar progreso
        self.btn_register.setEnabled(False)
        self.btn_back.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Progreso indeterminado
        
        # Crear y configurar nuevo worker
        self.registration_worker = RegistrationWorker(
            self.face_engine, 
            self.current_frame, 
            name, 
            email
        )
        
        # Conectar señales
        self.registration_worker.registration_complete.connect(self.on_registration_complete)
        self.registration_worker.finished.connect(self.on_registration_worker_finished)
        
        # Iniciar worker
        self.registration_worker.start()
    
    def cleanup_registration_worker(self):
        """Limpiar worker de registro de forma segura"""
        if self.registration_worker is not None:
            print("Limpiando registration worker...")
            
            try:
                # Detener worker si está corriendo
                if self.registration_worker.isRunning():
                    self.registration_worker.stop_worker()
                    
                    # Esperar con timeout
                    if not self.registration_worker.wait_for_finish(3000):
                        print("Registration worker no terminó a tiempo, terminando forzosamente")
                        self.registration_worker.terminate()
                        self.registration_worker.wait(1000)
                
                # Marcar para eliminación
                self.registration_worker.deleteLater()
                self.registration_worker = None
                print("Registration worker limpiado correctamente")
                
            except Exception as e:
                print(f"Error limpiando registration worker: {e}")
                # Forzar limpieza
                if self.registration_worker:
                    self.registration_worker.terminate()
                    self.registration_worker.wait(1000)
                    self.registration_worker.deleteLater()
                    self.registration_worker = None
    
    @pyqtSlot(bool, str)
    def on_registration_complete(self, success, message):
        """Manejar completación del registro"""
        if self._is_closing:
            return
            
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
    
    @pyqtSlot()
    def on_registration_worker_finished(self):
        """Manejar finalización del worker"""
        if not self._is_closing and self.registration_worker:
            self.registration_worker.deleteLater()
            self.registration_worker = None
    
    def toggle_camera(self):
        """Alternar estado de la cámara"""
        if self._is_closing:
            return
            
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
        if not self._is_closing:
            QMessageBox.critical(self, "Error", message)
    
    def closeEvent(self, event):
        """Manejar cierre mejorado de la ventana"""
        print("Cerrando Registration Screen...")
        self._is_closing = True
        
        # Ignorar evento inicialmente para manejo seguro
        event.ignore()
        
        # Detener timer si está activo
        if self.timer.isActive():
            self.timer.stop()
        
        # Limpiar worker
        self.cleanup_registration_worker()
        
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
            self._cleanup_timer.timeout.connect(lambda: self._finalize_close(event))
            self._cleanup_timer.start(1000)  # Esperar 1 segundo
    
    def _finalize_close(self, event):
        """Finalizar el cierre después de limpiar recursos"""
        print("Finalizando cierre de Registration Screen...")
        
        # Verificación final de threads
        if self.registration_worker is not None:
            if self.registration_worker.isRunning():
                print("Warning: Registration worker aún corriendo, terminando...")
                self.registration_worker.terminate()
                self.registration_worker.wait(2000)
            
            self.registration_worker.deleteLater()
            self.registration_worker = None
        
        # Limpiar timer de cleanup
        if self._cleanup_timer:
            self._cleanup_timer.deleteLater()
            self._cleanup_timer = None
        
        print("Registration Screen cerrada correctamente")
        event.accept()