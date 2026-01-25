# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CauHinhLuong(models.Model):
    _name = 'cau_hinh_luong'
    _description = "Cấu hình lương"
    _order = 'nam desc, thang desc'
    _rec_name = 'name'

    # ===== PERIOD =====
    name = fields.Char(
        string="Tên cấu hình",
        compute='_compute_name',
        store=True
    )
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

    @api.depends('thang', 'nam')
    def _compute_name(self):
        """Tạo tên: Cấu hình lương tháng X/YYYY"""
        for record in self:
            if record.thang and record.nam:
                record.name = f"Cấu hình lương T{record.thang}/{record.nam}"
            else:
                record.name = "Cấu hình lương mới"

    # ===== TAX CONFIGURATION - BIỂU THUẾ LŨY TIẾN 5 BẬC (2026) =====
    # Bậc 1
    bac_1_nguong = fields.Float(
        string="Bậc 1 - Ngưỡng tối đa",
        default=10000000,
        help="Thu nhập tính thuế tối đa cho bậc 1 (VNĐ)"
    )
    bac_1_thue_suat = fields.Float(
        string="Bậc 1 - Thuế suất (%)",
        default=5.0,
        help="≤ 10 triệu"
    )
    
    # Bậc 2
    bac_2_nguong = fields.Float(
        string="Bậc 2 - Ngưỡng tối đa",
        default=30000000,
        help="Thu nhập tính thuế tối đa cho bậc 2 (VNĐ)"
    )
    bac_2_thue_suat = fields.Float(
        string="Bậc 2 - Thuế suất (%)",
        default=10.0,
        help="10 triệu - 30 triệu"
    )
    bac_2_tru = fields.Float(
        string="Bậc 2 - Số trừ",
        default=500000,
        help="Công thức nhanh: x × 10% - 500,000"
    )
    
    # Bậc 3
    bac_3_nguong = fields.Float(
        string="Bậc 3 - Ngưỡng tối đa",
        default=60000000,
        help="Thu nhập tính thuế tối đa cho bậc 3 (VNĐ)"
    )
    bac_3_thue_suat = fields.Float(
        string="Bậc 3 - Thuế suất (%)",
        default=20.0,
        help="30 triệu - 60 triệu"
    )
    bac_3_tru = fields.Float(
        string="Bậc 3 - Số trừ",
        default=3500000,
        help="Công thức nhanh: x × 20% - 3,500,000"
    )
    
    # Bậc 4
    bac_4_nguong = fields.Float(
        string="Bậc 4 - Ngưỡng tối đa",
        default=100000000,
        help="Thu nhập tính thuế tối đa cho bậc 4 (VNĐ)"
    )
    bac_4_thue_suat = fields.Float(
        string="Bậc 4 - Thuế suất (%)",
        default=30.0,
        help="60 triệu - 100 triệu"
    )
    bac_4_tru = fields.Float(
        string="Bậc 4 - Số trừ",
        default=9500000,
        help="Công thức nhanh: x × 30% - 9,500,000"
    )
    
    # Bậc 5
    bac_5_thue_suat = fields.Float(
        string="Bậc 5 - Thuế suất (%)",
        default=35.0,
        help="> 100 triệu"
    )
    bac_5_tru = fields.Float(
        string="Bậc 5 - Số trừ",
        default=14500000,
        help="Công thức nhanh: x × 35% - 14,500,000"
    )

    # ===== INSURANCE CONFIGURATION =====
    ty_le_bhxh = fields.Float(
        string="Tỷ lệ BHXH (%)",
        default=8.0,
        help="Bảo hiểm xã hội - Phần người lao động đóng"
    )
    ty_le_bhyt = fields.Float(
        string="Tỷ lệ BHYT (%)",
        default=1.5,
        help="Bảo hiểm y tế - Phần người lao động đóng"
    )
    ty_le_bhtn = fields.Float(
        string="Tỷ lệ BHTN (%)",
        default=1.0,
        help="Bảo hiểm thất nghiệp - Phần người lao động đóng"
    )
    tong_ty_le_bao_hiem = fields.Float(
        string="Tổng tỷ lệ BH (%)",
        compute='_compute_tong_bao_hiem',
        store=True,
        help="Tổng: BHXH + BHYT + BHTN"
    )

    @api.depends('ty_le_bhxh', 'ty_le_bhyt', 'ty_le_bhtn')
    def _compute_tong_bao_hiem(self):
        """Tính tổng tỷ lệ bảo hiểm"""
        for record in self:
            record.tong_ty_le_bao_hiem = (
                record.ty_le_bhxh +
                record.ty_le_bhyt +
                record.ty_le_bhtn
            )

    # ===== DEDUCTIONS =====
    giam_tru_gia_canh = fields.Float(
        string="Giảm trừ gia cảnh",
        default=15500000,
        help="Mức giảm trừ gia cảnh cá nhân (VNĐ) - Luật 2026"
    )
    phu_cap_an_trua_mien_thue = fields.Float(
        string="Phụ cấp ăn trưa miễn thuế",
        default=730000,
        help="Mức phụ cấp ăn trưa miễn thuế tối đa (VNĐ)"
    )

    # ===== WORKING DAYS =====
    so_ngay_cong_chuan = fields.Integer(
        string="Số ngày công chuẩn",
        default=26,
        help="Số ngày làm việc chuẩn trong tháng để tính lương"
    )

    # ===== STATUS =====
    active = fields.Boolean(
        string="Kích hoạt",
        default=True,
        help="Tắt để không sử dụng cấu hình này"
    )

    # ===== NOTES =====
    ghi_chu = fields.Text(string="Ghi chú")

    # ===== CONSTRAINTS =====
    _sql_constraints = [
        ('unique_thang_nam',
         'unique(thang, nam)',
         'Đã tồn tại cấu hình cho tháng này! Vui lòng chỉnh sửa cấu hình hiện có.')
    ]

    @api.constrains('thang', 'nam')
    def _check_thang_nam(self):
        """Validate tháng và năm hợp lệ"""
        for record in self:
            if not (1 <= int(record.thang) <= 12):
                raise ValidationError("Tháng phải từ 1 đến 12!")
            if record.nam < 2000 or record.nam > 2100:
                raise ValidationError("Năm không hợp lệ!")

    @api.constrains('ty_le_bhxh', 'ty_le_bhyt', 'ty_le_bhtn')
    def _check_ty_le(self):
        """Validate tỷ lệ bảo hiểm"""
        for record in self:
            if record.ty_le_bhxh < 0 or record.ty_le_bhxh > 50:
                raise ValidationError("Tỷ lệ BHXH phải từ 0-50%!")
            if record.ty_le_bhyt < 0 or record.ty_le_bhyt > 50:
                raise ValidationError("Tỷ lệ BHYT phải từ 0-50%!")
            if record.ty_le_bhtn < 0 or record.ty_le_bhtn > 50:
                raise ValidationError("Tỷ lệ BHTN phải từ 0-50%!")

    @api.constrains('giam_tru_gia_canh', 'phu_cap_an_trua_mien_thue')
    def _check_giam_tru(self):
        """Validate giá trị giảm trừ"""
        for record in self:
            if record.giam_tru_gia_canh < 0:
                raise ValidationError("Giảm trừ gia cảnh không được âm!")
            if record.phu_cap_an_trua_mien_thue < 0:
                raise ValidationError("Phụ cấp ăn trưa miễn thuế không được âm!")

    @api.constrains('so_ngay_cong_chuan')
    def _check_so_ngay_cong(self):
        """Validate số ngày công"""
        for record in self:
            if record.so_ngay_cong_chuan < 1 or record.so_ngay_cong_chuan > 31:
                raise ValidationError("Số ngày công chuẩn phải từ 1-31!")

    # ===== HELPER METHODS =====
    @api.model
    def get_config(self, thang, nam):
        """
        Lấy cấu hình cho tháng/năm cụ thể.
        Nếu không tìm thấy, tự động tạo cấu hình mới với giá trị mặc định.
        
        Args:
            thang (int): Tháng (1-12)
            nam (int): Năm
            
        Returns:
            recordset: Cấu hình lương cho tháng/năm đó
        """
        # Tìm cấu hình active
        config = self.search([
            ('thang', '=', str(thang)),
            ('nam', '=', nam),
            ('active', '=', True)
        ], limit=1)

        # Nếu không có, tạo mới với giá trị mặc định
        if not config:
            config = self.create({
                'thang': str(thang),
                'nam': nam,
                # Các giá trị khác dùng default
            })

        return config

    def action_duplicate_to_next_month(self):
        """
        Nhân bản cấu hình này sang tháng tiếp theo
        """
        self.ensure_one()
        
        thang = int(self.thang)
        nam = self.nam
        
        # Tính tháng/năm tiếp theo
        if thang == 12:
            next_thang = 1
            next_nam = nam + 1
        else:
            next_thang = thang + 1
            next_nam = nam

        # Kiểm tra đã tồn tại chưa
        exists = self.search([
            ('thang', '=', str(next_thang)),
            ('nam', '=', next_nam)
        ], limit=1)

        if exists:
            raise ValidationError(
                f"Đã tồn tại cấu hình cho tháng {next_thang}/{next_nam}!"
            )

        # Tạo bản sao
        new_config = self.copy({
            'thang': str(next_thang),
            'nam': next_nam,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': f'Đã nhân bản cấu hình sang tháng {next_thang}/{next_nam}',
                'type': 'success',
                'sticky': False,
            }
        }
