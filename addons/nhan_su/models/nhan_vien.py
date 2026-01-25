# -*- coding: utf-8 -*-
from odoo import models, fields, api

class NhanVien(models.Model):
    _name = 'nhan_vien'
    _description = 'Thông tin nhân viên'
    _order = 'ma_dinh_danh'

    # --- Thông tin cơ bản ---
    name = fields.Char(string="Họ và Tên", required=True)
    ma_dinh_danh = fields.Char(string="Mã định danh", required=True)
    ngay_sinh = fields.Date(string="Ngày sinh")
    que_quan = fields.Char(string="Quê quán")
    email = fields.Char(string="Email")
    so_dien_thoai = fields.Char(string="Số điện thoại")
    dia_chi = fields.Char(string="Địa chỉ")
    bao_hiem_xa_hoi = fields.Char(string="Số BHXH")
    luong = fields.Float(string="Mức lương", groups="base.group_system")

    # --- Quan hệ ---
    phong_ban_id = fields.Many2one('phong_ban', string="Phòng ban")

    # --- One2many nội bộ ---
    chung_chi_ids = fields.One2many('chung_chi', 'nhan_vien_id', string="Danh sách chứng chỉ")
    # NOTE: Không thêm bang_cham_cong_ids để tránh circular dependency
    # Truy cập chấm công qua menu: QLNS → Nghiệp vụ → Chấm công
    lich_su_cong_tac_ids = fields.One2many('lich_su_cong_tac', 'nhan_vien_id', string="Lịch sử công tác")

    # ĐÃ XÓA SẠCH CODE LIÊN QUAN ĐẾN VĂN BẢN Ở ĐÂY