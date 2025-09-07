"""
Motor principal de reconocimiento facial para FaceGuard
Utiliza face_recognition y OpenCV para procesamiento de imágenes
"""

import face_recognition
import cv2
import numpy as np
import os
import pickle
from typing import List, Tuple, Optional, Dict
from datetime import datetime

from .database_manager import DatabaseManager


class FaceRecognitionEngine:
    """Clase principal para el reconocimiento facial"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []
        self.tolerance = 0.6  # Tolerancia para el reconocimiento (0.6 es un buen balance)
        self.load_known_faces()
    
    def load_known_faces(self):
        """Cargar todas las caras conocidas desde la base de datos"""
        try:
            users = self.db_manager.get_all_users()
            self.known_face_encodings = []
            self.known_face_names = []
            self.known_face_ids = []
            
            for user in users:
                user_id, name, email, face_encoding_path, created_at = user
                
                if face_encoding_path and os.path.exists(face_encoding_path):
                    with open(face_encoding_path, 'rb') as f:
                        face_encoding = pickle.load(f)
                        self.known_face_encodings.append(face_encoding)
                        self.known_face_names.append(name)
                        self.known_face_ids.append(user_id)
            
            print(f"Cargadas {len(self.known_face_encodings)} caras conocidas")
            
        except Exception as e:
            print(f"Error cargando caras conocidas: {e}")
    
    def register_face(self, image: np.ndarray, name: str, email: str) -> Tuple[bool, str]:
        """
        Registrar una nueva cara en el sistema
        
        Args:
            image: Imagen numpy array (BGR format)
            name: Nombre del usuario
            email: Email del usuario
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            # Convertir BGR a RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Detectar caras en la imagen
            face_locations = face_recognition.face_locations(rgb_image)
            
            if len(face_locations) == 0:
                return False, "No se detectó ninguna cara en la imagen"
            
            if len(face_locations) > 1:
                return False, "Se detectaron múltiples caras. Asegúrate de que solo haya una persona en la imagen"
            
            # Obtener encoding de la cara
            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
            
            if len(face_encodings) == 0:
                return False, "No se pudo procesar la cara detectada"
            
            face_encoding = face_encodings[0]
            
            # Verificar si la cara ya existe
            if self.known_face_encodings:
                matches = face_recognition.compare_faces(
                    self.known_face_encodings, 
                    face_encoding, 
                    tolerance=self.tolerance
                )
                
                if True in matches:
                    match_index = matches.index(True)
                    existing_name = self.known_face_names[match_index]
                    return False, f"Esta cara ya está registrada para el usuario: {existing_name}"
            
            # Crear directorio para datos del usuario si no existe
            user_data_dir = os.path.join("data", "users")
            os.makedirs(user_data_dir, exist_ok=True)
            
            # Generar nombre único para el archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            encoding_filename = f"face_encoding_{timestamp}_{name.replace(' ', '_')}.pkl"
            encoding_path = os.path.join(user_data_dir, encoding_filename)
            
            # Guardar encoding en archivo
            with open(encoding_path, 'wb') as f:
                pickle.dump(face_encoding, f)
            
            # Guardar usuario en la base de datos
            user_id = self.db_manager.add_user(name, email, encoding_path)
            
            if user_id:
                # Actualizar listas en memoria
                self.known_face_encodings.append(face_encoding)
                self.known_face_names.append(name)
                self.known_face_ids.append(user_id)
                
                return True, f"Usuario {name} registrado exitosamente"
            else:
                # Eliminar archivo si falló la inserción en DB
                if os.path.exists(encoding_path):
                    os.remove(encoding_path)
                return False, "Error al guardar el usuario en la base de datos"
                
        except Exception as e:
            return False, f"Error durante el registro: {str(e)}"
    
    def recognize_face(self, image: np.ndarray) -> List[Dict]:
        """
        Reconocer caras en una imagen
        
        Args:
            image: Imagen numpy array (BGR format)
            
        Returns:
            Lista de diccionarios con información de las caras reconocidas
        """
        try:
            # Convertir BGR a RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Redimensionar imagen para mayor velocidad (opcional)
            small_image = cv2.resize(rgb_image, (0, 0), fx=0.25, fy=0.25)
            
            # Detectar caras
            face_locations = face_recognition.face_locations(small_image)
            face_encodings = face_recognition.face_encodings(small_image, face_locations)
            
            recognized_faces = []
            
            for face_encoding, face_location in zip(face_encodings, face_locations):
                # Escalar las coordenadas de vuelta al tamaño original
                top, right, bottom, left = face_location
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4
                
                # Comparar con caras conocidas
                matches = face_recognition.compare_faces(
                    self.known_face_encodings, 
                    face_encoding, 
                    tolerance=self.tolerance
                )
                
                name = "Desconocido"
                user_id = None
                confidence = 0.0
                
                # Calcular distancias para obtener la mejor coincidencia
                if self.known_face_encodings:
                    face_distances = face_recognition.face_distance(
                        self.known_face_encodings, 
                        face_encoding
                    )
                    
                    best_match_index = np.argmin(face_distances)
                    
                    if matches[best_match_index]:
                        name = self.known_face_names[best_match_index]
                        user_id = self.known_face_ids[best_match_index]
                        # Convertir distancia a porcentaje de confianza
                        confidence = max(0, (1 - face_distances[best_match_index]) * 100)
                
                recognized_faces.append({
                    'name': name,
                    'user_id': user_id,
                    'confidence': confidence,
                    'location': (top, right, bottom, left),
                    'is_known': name != "Desconocido"
                })
            
            return recognized_faces
            
        except Exception as e:
            print(f"Error durante el reconocimiento: {e}")
            return []
    
    def draw_recognition_results(self, image: np.ndarray, recognized_faces: List[Dict]) -> np.ndarray:
        """
        Dibujar los resultados del reconocimiento en la imagen
        
        Args:
            image: Imagen original (BGR format)
            recognized_faces: Lista de caras reconocidas
            
        Returns:
            Imagen con las anotaciones dibujadas
        """
        result_image = image.copy()
        
        for face in recognized_faces:
            top, right, bottom, left = face['location']
            name = face['name']
            confidence = face['confidence']
            is_known = face['is_known']
            
            # Color del rectángulo (verde para conocidos, rojo para desconocidos)
            color = (0, 255, 0) if is_known else (0, 0, 255)
            
            # Dibujar rectángulo alrededor de la cara
            cv2.rectangle(result_image, (left, top), (right, bottom), color, 2)
            
            # Preparar texto
            if is_known:
                label = f"{name} ({confidence:.1f}%)"
            else:
                label = "Desconocido"
            
            # Calcular dimensiones del texto
            font = cv2.FONT_HERSHEY_DUPLEX
            font_scale = 0.6
            thickness = 1
            (text_width, text_height), _ = cv2.getTextSize(label, font, font_scale, thickness)
            
            # Dibujar fondo para el texto
            cv2.rectangle(
                result_image, 
                (left, bottom - text_height - 10),
                (left + text_width, bottom), 
                color, 
                cv2.FILLED
            )
            
            # Dibujar texto
            cv2.putText(
                result_image, 
                label, 
                (left + 6, bottom - 6), 
                font, 
                font_scale, 
                (255, 255, 255), 
                thickness
            )
        
        return result_image
    
    def get_face_quality_score(self, image: np.ndarray) -> Tuple[float, str]:
        """
        Evaluar la calidad de la imagen para el reconocimiento facial
        
        Args:
            image: Imagen numpy array (BGR format)
            
        Returns:
            Tuple[float, str]: (puntuación 0-100, mensaje descriptivo)
        """
        try:
            # Convertir a escala de grises para análisis
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detectar caras
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_image)
            
            if len(face_locations) == 0:
                return 0, "No se detectó ninguna cara"
            
            if len(face_locations) > 1:
                return 30, "Múltiples caras detectadas"
            
            # Obtener región de la cara
            top, right, bottom, left = face_locations[0]
            face_region = gray[top:bottom, left:right]
            
            if face_region.size == 0:
                return 0, "Región facial inválida"
            
            # Calcular métricas de calidad
            scores = []
            
            # 1. Tamaño de la cara (debería ser al menos 100x100 píxeles)
            face_width = right - left
            face_height = bottom - top
            size_score = min(100, (min(face_width, face_height) / 100) * 100)
            scores.append(size_score)
            
            # 2. Nitidez (usando varianza del Laplaciano)
            laplacian_var = cv2.Laplacian(face_region, cv2.CV_64F).var()
            sharpness_score = min(100, laplacian_var / 500 * 100)
            scores.append(sharpness_score)
            
            # 3. Iluminación (distribución de valores de píxeles)
            mean_brightness = np.mean(face_region)
            # Penalizar imágenes muy oscuras o muy brillantes
            if 50 <= mean_brightness <= 200:
                brightness_score = 100
            elif mean_brightness < 50:
                brightness_score = (mean_brightness / 50) * 100
            else:
                brightness_score = ((255 - mean_brightness) / 55) * 100
            scores.append(brightness_score)
            
            # 4. Contraste
            contrast = np.std(face_region)
            contrast_score = min(100, (contrast / 50) * 100)
            scores.append(contrast_score)
            
            # Calcular puntuación final
            final_score = np.mean(scores)
            
            # Generar mensaje descriptivo
            if final_score >= 80:
                message = "Excelente calidad"
            elif final_score >= 60:
                message = "Buena calidad"
            elif final_score >= 40:
                message = "Calidad aceptable"
            elif final_score >= 20:
                message = "Calidad baja"
            else:
                message = "Calidad muy baja"
            
            return final_score, message
            
        except Exception as e:
            return 0, f"Error evaluando calidad: {str(e)}"
    
    def update_tolerance(self, new_tolerance: float):
        """Actualizar la tolerancia para el reconocimiento"""
        if 0.1 <= new_tolerance <= 1.0:
            self.tolerance = new_tolerance
            print(f"Tolerancia actualizada a: {new_tolerance}")
        else:
            print("La tolerancia debe estar entre 0.1 y 1.0")
    
    def delete_user_face(self, user_id: int) -> Tuple[bool, str]:
        """
        Eliminar un usuario del sistema de reconocimiento
        
        Args:
            user_id: ID del usuario a eliminar
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            # Buscar el usuario en las listas
            if user_id in self.known_face_ids:
                index = self.known_face_ids.index(user_id)
                
                # Obtener información antes de eliminar
                name = self.known_face_names[index]
                
                # Eliminar de las listas en memoria
                del self.known_face_encodings[index]
                del self.known_face_names[index]
                del self.known_face_ids[index]
                
                # Eliminar de la base de datos
                success, message = self.db_manager.delete_user(user_id)
                
                if success:
                    return True, f"Usuario {name} eliminado exitosamente"
                else:
                    # Recargar desde base de datos en caso de error
                    self.load_known_faces()
                    return False, f"Error eliminando usuario: {message}"
            else:
                return False, "Usuario no encontrado en el sistema"
                
        except Exception as e:
            # Recargar desde base de datos en caso de error
            self.load_known_faces()
            return False, f"Error eliminando usuario: {str(e)}"
    
    def get_recognition_stats(self) -> Dict:
        """
        Obtener estadísticas del sistema de reconocimiento
        
        Returns:
            Diccionario con estadísticas
        """
        return {
            'total_users': len(self.known_face_encodings),
            'tolerance': self.tolerance,
            'users_list': list(zip(self.known_face_ids, self.known_face_names))
        }