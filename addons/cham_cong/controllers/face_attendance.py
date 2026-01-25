# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from datetime import datetime, date
import logging

_logger = logging.getLogger(__name__)


class FaceAttendanceController(http.Controller):
    """
    Controller xử lý API cho Face Recognition Attendance
    """
    
    @http.route('/api/face/register', type='json', auth='user', methods=['POST'])
    def register_face(self, nhan_vien_id, image_data):
        """
        API đăng ký khuôn mặt cho nhân viên
        
        Params:
            nhan_vien_id: ID của nhân viên
            image_data: Base64 encoded image
            
        Returns:
            {'success': bool, 'message': str}
        """
        try:
            from odoo.addons.cham_cong.models.face_recognition_service import FaceRecognitionService
            
            # Get employee
            nhan_vien = request.env['nhan_vien'].browse(nhan_vien_id)
            
            if not nhan_vien.exists():
                return {'success': False, 'message': 'Nhân viên không tồn tại!'}
            
            # Extract face encoding
            encoding = FaceRecognitionService.register_face(image_data)
            
            # Extract pure base64 (remove data URI prefix if exists)
            image_base64 = image_data
            if ',' in image_data:
                image_base64 = image_data.split(',')[1]
            
            # Save to database
            nhan_vien.write({
                'face_image': image_base64,
                'face_encoding': encoding,
                'face_registered_date': datetime.now()
            })
            
            _logger.info(f"Face registered for employee: {nhan_vien.name} (ID: {nhan_vien_id})")
            
            return {
                'success': True,
                'message': f'Đăng ký khuôn mặt thành công cho {nhan_vien.name}!'
            }
            
        except Exception as e:
            _logger.error(f"Error in register_face API: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    @http.route('/api/face/checkin', type='json', auth='public', methods=['POST'], csrf=False)
    def face_checkin(self, image_data):
        """
        API check-in bằng nhận diện khuôn mặt
        
        Params:
            image_data: Base64 encoded image
            
        Returns:
            {'success': bool, 'message': str, 'data': dict}
        """
        try:
            from odoo.addons.cham_cong.models.face_recognition_service import FaceRecognitionService
            
            # Recognize face
            result = FaceRecognitionService.recognize_face(image_data, request.env)
            
            if not result['success']:
                return result
            
            nhan_vien_id = result['nhan_vien_id']
            nhan_vien_name = result['name']
            today = date.today()
            
            # Check if already checked in today
            existing = request.env['bang_cham_cong'].sudo().search([
                ('nhan_vien_id', '=', nhan_vien_id),
                ('ngay_cham_cong', '=', today),
                ('gio_vao', '!=', False)
            ], limit=1)
            
            if existing:
                # Check if also checked out
                if existing.gio_ra:
                    return {
                        'success': False,
                        'message': f'❌ {nhan_vien_name} đã check-in lúc {existing.gio_vao.strftime("%H:%M")} và check-out lúc {existing.gio_ra.strftime("%H:%M")}\n\n⚠️ Không thể check-in lại trong cùng ngày!'
                    }
                else:
                    return {
                        'success': False,
                        'message': f'⚠️ {nhan_vien_name} đã check-in hôm nay lúc {existing.gio_vao.strftime("%H:%M")}!\n\nVui lòng check-out trước khi check-in lại.'
                    }
            
            # Create attendance record (model constraint will validate shift registration)
            try:
                bang_cc = request.env['bang_cham_cong'].sudo().create({
                    'nhan_vien_id': nhan_vien_id,
                    'ngay_cham_cong': today,
                    'gio_vao': datetime.now(),
                })
            except Exception as e:
                # Handle shift registration validation error
                if 'chưa đăng ký ca làm' in str(e):
                    return {
                        'success': False,
                        'message': str(e).split('\n')[0]  # Get first line of error
                    }
                raise
            
            # Get shift info for display
            shift_registration = request.env['dang_ky_ca_lam_theo_ngay'].sudo().search([
                ('nhan_vien_id', '=', nhan_vien_id),
                ('ngay_lam', '=', today),
            ], limit=1)
            
            shift_name = shift_registration.ca_lam if shift_registration and shift_registration.ca_lam else 'Không xác định'
            
            _logger.info(
                f"Face check-in successful: {nhan_vien_name} "
                f"(shift: {shift_name}, confidence: {result.get('confidence', 0)}%)"
            )
            
            # Convert UTC time to user timezone for display
            import pytz
            user_tz = pytz.timezone('Asia/Ho_Chi_Minh')
            gio_vao_local = pytz.UTC.localize(bang_cc.gio_vao).astimezone(user_tz)
            
            return {
                'success': True,
                'message': f"✅ Chào {nhan_vien_name}!\nCa làm: {shift_name}\nCheck-in: {gio_vao_local.strftime('%H:%M:%S')}",
                'data': {
                    'record_id': bang_cc.id,
                    'time': gio_vao_local.strftime('%H:%M:%S'),
                    'shift': shift_name,
                    'confidence': result.get('confidence', 0)
                }
            }
            
        except Exception as e:
            _logger.error(f"Error in face_checkin API: {str(e)}")
            return {'success': False, 'message': f'❌ Lỗi check-in: {str(e)}'}
    
    @http.route('/api/face/checkout', type='json', auth='public', methods=['POST'], csrf=False)
    def face_checkout(self, image_data):
        """
        API checkout bằng nhận diện khuôn mặt
        
        Params:
            image_data: Base64 encoded image
            
        Returns:
            {'success': bool, 'message': str, 'data': dict}
        """
        try:
            from odoo.addons.cham_cong.models.face_recognition_service import FaceRecognitionService
            
            # Recognize face
            result = FaceRecognitionService.recognize_face(image_data, request.env)
            
            if not result['success']:
                return result
            
            nhan_vien_id = result['nhan_vien_id']
            nhan_vien_name = result['name']
            today = date.today()
            
            # Find today's check-in record without check-out
            bang_cc = request.env['bang_cham_cong'].sudo().search([
                ('nhan_vien_id', '=', nhan_vien_id),
                ('ngay_cham_cong', '=', today),
                ('gio_vao', '!=', False),
                ('gio_ra', '=', False)
            ], limit=1)
            
            if not bang_cc:
                # Check if already fully checked out
                already_out = request.env['bang_cham_cong'].sudo().search([
                    ('nhan_vien_id', '=', nhan_vien_id),
                    ('ngay_cham_cong', '=', today),
                    ('gio_ra', '!=', False)
                ], limit=1)
                
                if already_out:
                    return {
                        'success': False,
                        'message': f'⚠️ {nhan_vien_name} đã check-out hôm nay lúc {already_out.gio_ra.strftime("%H:%M")}!\n\nKhông thể check-out lại.'
                    }
                else:
                    return {
                        'success': False,
                        'message': f'❌ {nhan_vien_name} chưa check-in hôm nay!\n\nVui lòng check-in trước.'
                    }
            
            # Update check-out time
            bang_cc.sudo().write({'gio_ra': datetime.now()})
            
            _logger.info(
                f"Face check-out successful: {nhan_vien_name} "
                f"(confidence: {result.get('confidence', 0)}%)"
            )
            
            # Convert UTC times to user timezone for display
            import pytz
            user_tz = pytz.timezone('Asia/Ho_Chi_Minh')
            gio_vao_local = pytz.UTC.localize(bang_cc.gio_vao).astimezone(user_tz)
            gio_ra_local = pytz.UTC.localize(bang_cc.gio_ra).astimezone(user_tz)
            
            return {
                'success': True,
                'message': f"👋 Tạm biệt {nhan_vien_name}! Check-out thành công lúc {gio_ra_local.strftime('%H:%M:%S')}",
                'data': {
                    'record_id': bang_cc.id,
                    'check_in': gio_vao_local.strftime('%H:%M:%S'),
                    'check_out': gio_ra_local.strftime('%H:%M:%S'),
                    'confidence': result.get('confidence', 0)
                }
            }
            
        except Exception as e:
            _logger.error(f"Error in face_checkout API: {str(e)}")
            return {'success': False, 'message': f'❌ Lỗi check-out: {str(e)}'}
    
    @http.route('/api/face/auto_checkin', type='json', auth='public', methods=['POST'], csrf=False)
    def auto_checkin(self, image_data):
        """
        API tự động check-in hoặc check-out dựa trên trạng thái hiện tại
        Không cần user chọn - hệ thống tự quyết định
        
        Params:
            image_data: Base64 encoded image
            
        Returns:
            {
                'success': bool,
                'action': 'checkin'|'checkout'|'already_complete'|'error',
                'message': str,
                'data': dict (if success)
            }
        """
        try:
            from odoo.addons.cham_cong.models.face_recognition_service import FaceRecognitionService
            
            # Recognize face
            result = FaceRecognitionService.recognize_face(image_data, request.env)
            
            if not result['success']:
                return {
                    'success': False,
                    'action': 'error',
                    'message': result['message']
                }
            
            nhan_vien_id = result['nhan_vien_id']
            nhan_vien_name = result['name']
            confidence = result.get('confidence', 0)
            today = date.today()
            
            # Check current attendance state
            existing = request.env['bang_cham_cong'].sudo().search([
                ('nhan_vien_id', '=', nhan_vien_id),
                ('ngay_cham_cong', '=', today)
            ], limit=1)
            
            # Get shift info for display
            shift_registration = request.env['dang_ky_ca_lam_theo_ngay'].sudo().search([
                ('nhan_vien_id', '=', nhan_vien_id),
                ('ngay_lam', '=', today),
            ], limit=1)
            shift_name = shift_registration.ca_lam if shift_registration and shift_registration.ca_lam else 'Không xác định'
            
            # Convert timezone helper
            import pytz
            user_tz = pytz.timezone('Asia/Ho_Chi_Minh')
            
            # CASE 1: No record yet → CHECK-IN
            if not existing:
                try:
                    bang_cc = request.env['bang_cham_cong'].sudo().create({
                        'nhan_vien_id': nhan_vien_id,
                        'ngay_cham_cong': today,
                        'gio_vao': datetime.now(),
                    })
                    
                    gio_vao_local = pytz.UTC.localize(bang_cc.gio_vao).astimezone(user_tz)
                    
                    _logger.info(
                        f"[AUTO] Check-in: {nhan_vien_name} - "
                        f"{shift_name} (confidence: {confidence}%)"
                    )
                    
                    return {
                        'success': True,
                        'action': 'checkin',
                        'message': f"✅ Chào {nhan_vien_name}!\nCa: {shift_name}\nCheck-in: {gio_vao_local.strftime('%H:%M:%S')}",
                        'data': {
                            'record_id': bang_cc.id,
                            'time': gio_vao_local.strftime('%H:%M:%S'),
                            'shift': shift_name,
                            'confidence': confidence,
                            'nhan_vien_name': nhan_vien_name
                        }
                    }
                except ValidationError as e:
                    # Shift not registered
                    error_msg = str(e)
                    _logger.warning(f"[AUTO] Check-in failed - no shift: {nhan_vien_name}")
                    return {
                        'success': False,
                        'action': 'no_shift',
                        'message': f"⚠️ {nhan_vien_name}\n\n{error_msg}\n\n📋 Vui lòng đăng ký ca làm trước khi chấm công."
                    }
            
            # CASE 2: Has check-in, no check-out → CHECK-OUT
            elif existing.gio_vao and not existing.gio_ra:
                existing.sudo().write({'gio_ra': datetime.now()})
                
                gio_ra_local = pytz.UTC.localize(existing.gio_ra).astimezone(user_tz)
                
                _logger.info(
                    f"[AUTO] Check-out: {nhan_vien_name} - "
                    f"{shift_name} (confidence: {confidence}%)"
                )
                
                return {
                    'success': True,
                    'action': 'checkout',
                    'message': f"👋 Tạm biệt {nhan_vien_name}!\nCa: {shift_name}\nCheck-out: {gio_ra_local.strftime('%H:%M:%S')}",
                    'data': {
                        'record_id': existing.id,
                        'time': gio_ra_local.strftime('%H:%M:%S'),
                        'shift': shift_name,
                        'confidence': confidence,
                        'nhan_vien_name': nhan_vien_name
                    }
                }
            
            # CASE 3: Already complete → ERROR
            else:
                gio_vao_local = pytz.UTC.localize(existing.gio_vao).astimezone(user_tz)
                gio_ra_local = pytz.UTC.localize(existing.gio_ra).astimezone(user_tz)
                
                _logger.info(f"[AUTO] Already complete: {nhan_vien_name}")
                
                return {
                    'success': False,
                    'action': 'already_complete',
                    'message': (
                        f"✓ {nhan_vien_name}\n\n"
                        f"Bạn đã hoàn thành chấm công hôm nay!\n\n"
                        f"📥 Vào: {gio_vao_local.strftime('%H:%M')}\n"
                        f"📤 Ra: {gio_ra_local.strftime('%H:%M')}"
                    )
                }
                
        except Exception as e:
            _logger.error(f"Error in auto_checkin API: {str(e)}")
            return {
                'success': False,
                'action': 'error',
                'message': f'❌ Lỗi hệ thống: {str(e)}'
            }

