# -*- coding: utf-8 -*-
import face_recognition
import numpy as np
import json
import base64
import logging
from io import BytesIO
from PIL import Image
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class FaceRecognitionService:
    """
    Service xử lý nhận diện khuôn mặt
    Sử dụng face_recognition library (dlib-based)
    """
    
    # Thresholds for face matching (SECURITY CRITICAL)
    TOLERANCE = 0.50  # Ngưỡng nhận diện (càng thấp càng strict)
    MAX_DISTANCE = 0.50  # Khoảng cách tối đa để chấp nhận match (0.50 = ~75% confidence minimum)
    MIN_CONFIDENCE = 50.0  # Độ tin cậy tối thiểu (%)
    
    @staticmethod
    def decode_image(image_data):
        """
        Decode base64 image to numpy array
        
        Args:
            image_data: Base64 encoded image string
            
        Returns:
            numpy.ndarray: RGB image array
        """
        try:
            # Remove data:image prefix if exists
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            # Decode base64
            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes))
            
            # Convert to RGB (face_recognition requires RGB)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            return np.array(image)
            
        except Exception as e:
            _logger.error(f"Error decoding image: {str(e)}")
            raise ValidationError(f"Lỗi xử lý ảnh: {str(e)}")
    
    @staticmethod
    def register_face(image_data):
        """
        Đăng ký khuôn mặt từ ảnh
        
        Args:
            image_data: Base64 encoded image
            
        Returns:
            str: JSON string of face encoding
            
        Raises:
            ValidationError: Nếu không phát hiện được khuôn mặt hoặc có nhiều khuôn mặt
        """
        try:
            # Decode image
            image_np = FaceRecognitionService.decode_image(image_data)
            
            # Detect faces
            face_locations = face_recognition.face_locations(image_np)
            
            # Validation
            if len(face_locations) == 0:
                raise ValidationError("Không phát hiện khuôn mặt nào! Vui lòng chụp ảnh rõ mặt.")
            
            if len(face_locations) > 1:
                raise ValidationError("Phát hiện nhiều khuôn mặt! Vui lòng chỉ có 1 người trong ảnh.")
            
            # Extract face encoding
            face_encodings = face_recognition.face_encodings(
                image_np, 
                face_locations,
                num_jitters=2  # Accuracy improvement (default: 1)
            )
            
            # Convert to list and JSON
            encoding = face_encodings[0].tolist()
            
            _logger.info(f"Face registered successfully. Encoding dimensions: {len(encoding)}")
            
            return json.dumps(encoding)
            
        except ValidationError:
            raise
        except Exception as e:
            _logger.error(f"Error in register_face: {str(e)}")
            raise ValidationError(f"Lỗi đăng ký khuôn mặt: {str(e)}")
    
    @staticmethod
    def recognize_face(image_data, env):
        """
        Nhận diện khuôn mặt từ ảnh
        
        Args:
            image_data: Base64 encoded image
            env: Odoo environment object
            
        Returns:
            dict: {
                'success': bool,
                'nhan_vien_id': int (if success),
                'name': str (if success),
                'confidence': float (if success),
                'message': str (if not success)
            }
        """
        try:
            # Decode image
            image_np = FaceRecognitionService.decode_image(image_data)
            
            # Detect faces
            face_locations = face_recognition.face_locations(image_np)
            
            if len(face_locations) == 0:
                return {
                    'success': False,
                    'message': 'Không phát hiện khuôn mặt!'
                }
            
            # Extract encoding
            face_encodings = face_recognition.face_encodings(
                image_np,
                face_locations,
                num_jitters=1  # Faster for recognition
            )
            unknown_encoding = face_encodings[0]
            
            # Get all registered employees
            nhan_viens = env['nhan_vien'].search([
                ('face_encoding', '!=', False)
            ])
            
            if not nhan_viens:
                return {
                    'success': False,
                    'message': 'Chưa có nhân viên nào đăng ký khuôn mặt!'
                }
            
            # Compare with each employee
            best_match = None
            best_distance = float('inf')
            all_matches = []  # For logging
            
            _logger.info(f"Comparing with {len(nhan_viens)} registered employees...")
            
            for nv in nhan_viens:
                # Parse encoding
                known_encoding = np.array(json.loads(nv.face_encoding))
                
                # Calculate distance
                face_distances = face_recognition.face_distance(
                    [known_encoding],
                    unknown_encoding
                )
                distance = face_distances[0]
                confidence = (1 - distance) * 100
                
                # Log all comparisons for debugging
                all_matches.append({
                    'name': nv.name,
                    'distance': distance,
                    'confidence': confidence
                })
                
                # Check if this is the best match AND meets threshold
                if distance < best_distance:
                    best_distance = distance
                    if distance < FaceRecognitionService.MAX_DISTANCE:
                        best_match = nv
            
            # Log top 3 matches for debugging
            all_matches.sort(key=lambda x: x['distance'])
            _logger.info("Top 3 closest matches:")
            for i, match in enumerate(all_matches[:3]):
                _logger.info(
                    f"  {i+1}. {match['name']}: "
                    f"distance={match['distance']:.3f}, confidence={match['confidence']:.1f}%"
                )
            
            if best_match:
                confidence = (1 - best_distance) * 100
                
                # Additional confidence check
                if confidence < FaceRecognitionService.MIN_CONFIDENCE:
                    _logger.warning(
                        f"Match found but confidence too low: {best_match.name} "
                        f"({confidence:.1f}% < {FaceRecognitionService.MIN_CONFIDENCE}%)"
                    )
                    return {
                        'success': False,
                        'message': (
                            f'❌ Khuôn mặt không khớp với bất kỳ nhân viên nào!\n\n'
                            f'Người gần nhất: {best_match.name} ({confidence:.1f}%)\n'
                            f'Ngưỡng yêu cầu: {FaceRecognitionService.MIN_CONFIDENCE}%\n\n'
                            f'💡 Vui lòng đăng ký khuôn mặt trước khi sử dụng.'
                        )
                    }
                
                _logger.info(
                    f"✓ Face recognized: {best_match.name} "
                    f"(distance: {best_distance:.3f}, confidence: {confidence:.1f}%)"
                )
                
                return {
                    'success': True,
                    'nhan_vien_id': best_match.id,
                    'name': best_match.name,
                    'confidence': round(confidence, 1),
                    'distance': round(best_distance, 3)
                }
            else:
                _logger.warning(
                    f"✗ No match found! Best distance: {best_distance:.3f} "
                    f"(threshold: {FaceRecognitionService.MAX_DISTANCE})"
                )
                
                return {
                    'success': False,
                    'message': (
                        f'❌ Khuôn mặt không khớp với bất kỳ nhân viên nào!\n\n'
                        f'Khoảng cách gần nhất: {best_distance:.3f}\n'
                        f'Ngưỡng yêu cầu: {FaceRecognitionService.MAX_DISTANCE}\n\n'
                        f'💡 Vui lòng đăng ký khuôn mặt trước khi sử dụng.'
                    )
                }
                
        except ValidationError:
            raise
        except Exception as e:
            _logger.error(f"Error in recognize_face: {str(e)}")
            return {
                'success': False,
                'message': f'Lỗi nhận diện: {str(e)}'
            }