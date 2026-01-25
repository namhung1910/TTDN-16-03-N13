# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import calendar


class BangLuong(models.Model):
    _name = 'bang_luong'
    _description = "Bảng lương"
    _order = 'nam desc, thang desc'
    _rec_name = 'name'

    # ===== BASIC INFO =====
    name = fields.Char(string="Tên bảng lương", compute='_compute_name', store=True)
    thang = fields.Selection(
        selection=[(str(i), str(i)) for i in range(1, 13)],
        string="Tháng",
        required=True,
        default=lambda self: str(fields.Date.today().month)
    )
    nam = fields.Integer(
        string="Năm",
        required=True,
        default=lambda self: fields.Date.today().year
    )
    ngay_tinh = fields.Date(
        string="Ngày tính lương",
        default=fields.Date.today,
        required=True
    )
    ngay_cham = fields.Date(
        string="Ngày chốt",
        help="Ngày chốt lương (deadline)"
    )

    @api.depends('thang', 'nam')
    def _compute_name(self):
        """Tạo tên bảng lương: Bảng lương tháng X/YYYY"""
        for record in self:
            if record.thang and record.nam:
                record.name = f"Bảng lương tháng {record.thang}/{record.nam}"
            else:
                record.name = "Bảng lương mới"

    # ===== STATUS =====
    trang_thai = fields.Selection([
        ('nhap', 'Nháp'),
        ('da_tinh', 'Đã tính'),
        ('da_duyet', 'Đã duyệt'),
        ('da_thanh_toan', 'Đã thanh toán')
    ], string="Trạng thái", default='nhap', required=True, tracking=True)

    # ===== SALARY DETAILS (One2many) =====
    chi_tiet_luong_ids = fields.One2many(
        'chi_tiet_luong',
        'bang_luong_id',
        string="Chi tiết lương"
    )

    # ===== SUMMARY FIELDS (Computed) =====
    so_nhan_vien = fields.Integer(
        string="Số nhân viên",
        compute='_compute_summary',
        store=True
    )
    tong_luong_gross = fields.Float(
        string="Tổng lương Gross",
        compute='_compute_summary',
        store=True
    )
    tong_bao_hiem = fields.Float(
        string="Tổng bảo hiểm",
        compute='_compute_summary',
        store=True
    )
    tong_thue = fields.Float(
        string="Tổng thuế TNCN",
        compute='_compute_summary',
        store=True
    )
    tong_luong_net = fields.Float(
        string="Tổng lương Net",
        compute='_compute_summary',
        store=True
    )

    @api.depends('chi_tiet_luong_ids.tong_thu_nhap',
                 'chi_tiet_luong_ids.tong_bao_hiem',
                 'chi_tiet_luong_ids.thue_tncn',
                 'chi_tiet_luong_ids.luong_thuc_nhan')
    def _compute_summary(self):
        """Tính tổng các khoản từ chi tiết lương"""
        for record in self:
            record.so_nhan_vien = len(record.chi_tiet_luong_ids)
            record.tong_luong_gross = sum(record.chi_tiet_luong_ids.mapped('tong_thu_nhap'))
            record.tong_bao_hiem = sum(record.chi_tiet_luong_ids.mapped('tong_bao_hiem'))
            record.tong_thue = sum(record.chi_tiet_luong_ids.mapped('thue_tncn'))
            record.tong_luong_net = sum(record.chi_tiet_luong_ids.mapped('luong_thuc_nhan'))

    # ===== NOTES =====
    ghi_chu = fields.Text(string="Ghi chú")

    # ===== CONSTRAINTS =====
    _sql_constraints = [
        ('unique_thang_nam', 'unique(thang, nam)',
         'Đã tồn tại bảng lương cho tháng này!')
    ]

    @api.constrains('thang', 'nam')
    def _check_thang_nam(self):
        """Validate tháng và năm hợp lệ"""
        for record in self:
            if not (1 <= int(record.thang) <= 12):
                raise ValidationError("Tháng phải từ 1 đến 12!")
            if record.nam < 2000 or record.nam > 2100:
                raise ValidationError("Năm không hợp lệ!")

    # ===== ACTIONS =====
    def action_tao_chi_tiet_luong(self):
        """
        Tạo chi tiết lương cho tất cả nhân viên
        - Tìm tất cả nhân viên active
        - Tạo record chi_tiet_luong cho từng nhân viên
        """
        self.ensure_one()
        
        if self.trang_thai != 'nhap':
            raise ValidationError("Chỉ có thể tạo chi tiết lương khi ở trạng thái Nháp!")

        # Xóa chi tiết cũ (nếu có)
        self.chi_tiet_luong_ids.unlink()

        # Tìm tất cả nhân viên
        nhan_vien_ids = self.env['nhan_vien'].search([])
        
        if not nhan_vien_ids:
            raise ValidationError("Không tìm thấy nhân viên nào!")

        # Tạo chi tiết lương cho từng nhân viên
        chi_tiet_vals = []
        for nhan_vien in nhan_vien_ids:
            chi_tiet_vals.append({
                'bang_luong_id': self.id,
                'nhan_vien_id': nhan_vien.id,
            })
        
        self.env['chi_tiet_luong'].create(chi_tiet_vals)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': f'Đã tạo chi tiết lương cho {len(nhan_vien_ids)} nhân viên',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_xac_nhan(self):
        """Chuyển trạng thái: nhap → da_tinh"""
        for record in self:
            if not record.chi_tiet_luong_ids:
                raise ValidationError("Chưa có chi tiết lương! Vui lòng tạo chi tiết lương trước.")
            record.trang_thai = 'da_tinh'

    def action_duyet(self):
        """Chuyển trạng thái: da_tinh → da_duyet"""
        for record in self:
            if record.trang_thai != 'da_tinh':
                raise ValidationError("Chỉ có thể duyệt khi đã tính lương!")
            record.trang_thai = 'da_duyet'

    def action_thanh_toan(self):
        """Chuyển trạng thái: da_duyet → da_thanh_toan"""
        for record in self:
            if record.trang_thai != 'da_duyet':
                raise ValidationError("Chỉ có thể thanh toán khi đã duyệt!")
            record.trang_thai = 'da_thanh_toan'

    def action_quay_lai_nhap(self):
        """Quay lại trạng thái nháp"""
        for record in self:
            record.trang_thai = 'nhap'
