# -*- coding: utf-8 -*-
from odoo import models, fields


class NhanVienLuong(models.Model):
    """
    Extend nhan_vien model to add salary-related fields
    """
    _inherit = 'nhan_vien'

    # ===== SALARY INFORMATION =====
    luong_hop_dong = fields.Float(
        string="Lương hợp đồng",
        default=15000000,
        help="Mức lương cơ bản theo hợp đồng lao động"
    )
    luong_dong_bao_hiem = fields.Float(
        string="Lương đóng bảo hiểm",
        default=15000000,
        help="Mức lương làm cơ sở để tính bảo hiểm"
    )
    phu_cap_an_trua = fields.Float(
        string="Phụ cấp ăn trưa",
        default=730000,
        help="Phụ cấp ăn trưa mỗi tháng (miễn thuế tối đa 730,000 VNĐ)"
    )
    phu_cap_khac = fields.Float(
        string="Phụ cấp khác",
        default=0,
        help="Các khoản phụ cấp khác (chịu thuế)"
    )

    # ===== TAX INFORMATION =====
    giam_tru_gia_canh = fields.Float(
        string="Giảm trừ gia cảnh",
        default=11000000,
        help="Mức giảm trừ gia cảnh cá nhân (11,000,000 VNĐ)"
    )
    thue_suat_tncn = fields.Float(
        string="Thuế suất TNCN (%)",
        default=5.0,
        help="Thuế suất thuế thu nhập cá nhân áp dụng (%)"
    )

    # ===== RELATIONSHIP =====
    chi_tiet_luong_ids = fields.One2many(
        'chi_tiet_luong',
        'nhan_vien_id',
        string="Lịch sử lương",
        help="Lịch sử bảng lương của nhân viên"
    )
