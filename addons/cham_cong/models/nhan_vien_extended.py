# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class NhanVienFaceRecognition(models.Model):
    _inherit = 'nhan_vien'
    
    # Fields
    face_image = fields.Binary(
        string="Ảnh Khuôn Mặt",
        attachment=True,
        help="Ảnh dùng để đăng ký nhận diện"
    )
    
    face_encoding = fields.Text(
        string="Face Encoding",
        help="Vector encoding của khuôn mặt (JSON)"
    )
    
    face_registered = fields.Boolean(
        string="Đã Đăng Ký",
        compute='_compute_face_registered',
        store=True
    )
    
    face_registered_date = fields.Datetime(
        string="Ngày Đăng Ký",
        readonly=True
    )
    
    # Computed field
    @api.depends('face_encoding')
    def _compute_face_registered(self):
        for record in self:
            record.face_registered = bool(record.face_encoding)
    
    # Constraints
    @api.constrains('face_image')
    def _check_face_image_size(self):
        for record in self:
            if record.face_image and len(record.face_image) > 5 * 1024 * 1024:
                raise ValidationError("Ảnh quá lớn! Vui lòng chọn ảnh < 5MB")
