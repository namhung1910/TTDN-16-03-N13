# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import calendar
from datetime import date


class ChiTietLuong(models.Model):
    _name = 'chi_tiet_luong'
    _description = "Chi tiết lương nhân viên"
    _order = 'bang_luong_id desc, nhan_vien_id'
    _rec_name = 'name'

    # ===== BASIC INFO =====
    name = fields.Char(string="Tên", compute='_compute_name', store=True)
    bang_luong_id = fields.Many2one('bang_luong', string="Bảng lương", required=True, ondelete='cascade')
    nhan_vien_id = fields.Many2one('nhan_vien', string="Nhân viên", required=True, ondelete='cascade')

    # Related fields for easy access
    thang = fields.Selection(related='bang_luong_id.thang', store=True, string="Tháng")
    nam = fields.Integer(related='bang_luong_id.nam', store=True, string="Năm")

    # Cấu hình lương
    cau_hinh_id = fields.Many2one(
        'cau_hinh_luong',
        string="Cấu hình",
        compute='_compute_cau_hinh',
        store=True,
        help="Cấu hình lương áp dụng cho tháng này"
    )

    @api.depends('thang', 'nam')
    def _compute_cau_hinh(self):
        """Tự động chọn cấu hình cho tháng/năm của bảng lương"""
        for record in self:
            if record.thang and record.nam:
                config = self.env['cau_hinh_luong'].get_config(
                    int(record.thang), record.nam
                )
                record.cau_hinh_id = config.id if config else False
            else:
                record.cau_hinh_id = False

    @api.depends('nhan_vien_id', 'bang_luong_id')
    def _compute_name(self):
        """Tạo tên: Lương [Tên NV] - T[X]/[Y]"""
        for record in self:
            if record.nhan_vien_id and record.bang_luong_id:
                record.name = f"Lương {record.nhan_vien_id.name} - T{record.thang}/{record.nam}"
            else:
                record.name = "Chi tiết lương mới"

    # ===== A. THÔNG TIN CƠ BẢN =====
    luong_hop_dong = fields.Float(
        string="Lương hợp đồng",
        related='nhan_vien_id.luong',
        store=True,
        readonly=False,
        help="Lương cơ bản theo hợp đồng - Tự động lấy từ hồ sơ nhân viên"
    )
    
    
    phu_cap_an_trua = fields.Float(
        string="Phụ cấp ăn trưa",
        default=730000,
        help="Miễn thuế tối đa 730,000 VNĐ"
    )
    phu_cap_khac = fields.Float(
        string="Phụ cấp khác",
        default=0,
        help="Các khoản phụ cấp khác (chịu thuế)"
    )

    # ===== B. NGÀY CÔNG =====
    so_ngay_lam_viec = fields.Float(
        string="Số ngày làm việc",
        compute='_compute_so_ngay_cong',
        store=True,
        help="Số ngày làm việc thực tế từ bảng chấm công"
    )
    so_ngay_nghi_phep = fields.Float(
        string="Ngày nghỉ phép",
        default=0,
        help="Ngày nghỉ phép có lương"
    )
    so_ngay_nghi_khong_phep = fields.Float(
        string="Ngày nghỉ không phép",
        compute='_compute_so_ngay_cong',
        store=True,
        help="Ngày vắng mặt không lý do"
    )
    tong_ngay_cong = fields.Float(
        string="Tổng ngày công",
        compute='_compute_tong_ngay_cong',
        store=True,
        help="Làm việc + nghỉ phép"
    )

    @api.depends('bang_luong_id.thang', 'bang_luong_id.nam', 'nhan_vien_id')
    def _compute_so_ngay_cong(self):
        """Tính số ngày làm việc và vắng mặt từ bảng chấm công"""
        for record in self:
            if not (record.bang_luong_id and record.nhan_vien_id):
                record.so_ngay_lam_viec = 0
                record.so_ngay_nghi_khong_phep = 0
                continue

            # Lấy ngày đầu và cuối tháng
            thang = int(record.thang)
            nam = record.nam
            start_date = date(nam, thang, 1)
            last_day = calendar.monthrange(nam, thang)[1]
            end_date = date(nam, thang, last_day)

            # Tìm tất cả bảng chấm công trong tháng
            BangChamCong = self.env['bang_cham_cong']
            
            # Ngày làm việc (đi làm)
            lam_viec = BangChamCong.search_count([
                ('nhan_vien_id', '=', record.nhan_vien_id.id),
                ('ngay_cham_cong', '>=', start_date),
                ('ngay_cham_cong', '<=', end_date),
                ('trang_thai', 'in', ['di_lam', 'di_muon', 've_som', 'di_muon_ve_som'])
            ])

            # Ngày vắng mặt (không phép)
            vang_mat = BangChamCong.search_count([
                ('nhan_vien_id', '=', record.nhan_vien_id.id),
                ('ngay_cham_cong', '>=', start_date),
                ('ngay_cham_cong', '<=', end_date),
                ('trang_thai', '=', 'vang_mat')
            ])

            record.so_ngay_lam_viec = float(lam_viec)
            record.so_ngay_nghi_khong_phep = float(vang_mat)

    @api.depends('so_ngay_lam_viec', 'so_ngay_nghi_phep')
    def _compute_tong_ngay_cong(self):
        """Tổng ngày công = làm việc + nghỉ phép"""
        for record in self:
            record.tong_ngay_cong = record.so_ngay_lam_viec + record.so_ngay_nghi_phep

    # ===== C. LƯƠNG GROSS =====
    luong_chinh = fields.Float(
        string="Lương chính",
        compute='_compute_luong_gross',
        store=True,
        help="Lương hợp đồng / 26 × tổng ngày công"
    )
    tong_thu_nhap = fields.Float(
        string="Tổng thu nhập (Gross)",
        compute='_compute_luong_gross',
        store=True,
        help="Lương chính + phụ cấp ăn trưa + phụ cấp khác"
    )

    @api.depends('luong_hop_dong', 'tong_ngay_cong', 'phu_cap_an_trua', 'phu_cap_khac', 'cau_hinh_id.so_ngay_cong_chuan')
    def _compute_luong_gross(self):
        """Tính lương gross"""
        for record in self:
            # Lấy số ngày công chuẩn từ cấu hình
            so_ngay_chuan = record.cau_hinh_id.so_ngay_cong_chuan if record.cau_hinh_id else 26
            # Lương chính theo ngày công
            record.luong_chinh = (record.luong_hop_dong / so_ngay_chuan) * record.tong_ngay_cong
            # Tổng thu nhập
            record.tong_thu_nhap = record.luong_chinh + record.phu_cap_an_trua + record.phu_cap_khac

    # ===== D. BẢO HIỂM =====
    luong_dong_bao_hiem = fields.Float(
        string="Lương đóng bảo hiểm",
        related='nhan_vien_id.luong',
        store=True,
        readonly=False,
        help="Mức lương cơ sở để tính bảo hiểm - Tự động lấy từ hồ sơ nhân viên"
    )
    bhxh = fields.Float(
        string="BHXH (8%)",
        compute='_compute_bao_hiem',
        store=True
    )
    bhyt = fields.Float(
        string="BHYT (1.5%)",
        compute='_compute_bao_hiem',
        store=True
    )
    bhtn = fields.Float(
        string="BHTN (1%)",
        compute='_compute_bao_hiem',
        store=True
    )
    tong_bao_hiem = fields.Float(
        string="Tổng bảo hiểm",
        compute='_compute_bao_hiem',
        store=True,
        help="BHXH + BHYT + BHTN = 10.5%"
    )

    @api.depends('luong_dong_bao_hiem', 'cau_hinh_id.ty_le_bhxh', 'cau_hinh_id.ty_le_bhyt', 'cau_hinh_id.ty_le_bhtn')
    def _compute_bao_hiem(self):
        """Tính bảo hiểm từ cấu hình"""
        for record in self:
            if record.cau_hinh_id:
                record.bhxh = record.luong_dong_bao_hiem * (record.cau_hinh_id.ty_le_bhxh / 100.0)
                record.bhyt = record.luong_dong_bao_hiem * (record.cau_hinh_id.ty_le_bhyt / 100.0)
                record.bhtn = record.luong_dong_bao_hiem * (record.cau_hinh_id.ty_le_bhtn / 100.0)
            else:
                # Fallback nếu không có config
                record.bhxh = record.luong_dong_bao_hiem * 0.08
                record.bhyt = record.luong_dong_bao_hiem * 0.015
                record.bhtn = record.luong_dong_bao_hiem * 0.01
            record.tong_bao_hiem = record.bhxh + record.bhyt + record.bhtn

    # ===== E. THUẾ TNCN =====
    thu_nhap_chiu_thue = fields.Float(
        string="Thu nhập chịu thuế",
        compute='_compute_thue_tncn',
        store=True,
        help="Tổng thu nhập - phụ cấp ăn trưa (miễn thuế)"
    )
    giam_tru_gia_canh = fields.Float(
        string="Giảm trừ gia cảnh",
        compute='_compute_giam_tru_from_config',
        store=True,
        help="Mức giảm trừ cá nhân từ cấu hình"
    )
    thu_nhap_tinh_thue = fields.Float(
        string="Thu nhập tính thuế",
        compute='_compute_thue_tncn',
        store=True,
        help="Thu nhập chịu thuế - bảo hiểm - giảm trừ gia cảnh"
    )

    @api.depends('cau_hinh_id.giam_tru_gia_canh')
    def _compute_giam_tru_from_config(self):
        """Lấy giảm trừ gia cảnh từ cấu hình"""
        for record in self:
            record.giam_tru_gia_canh = record.cau_hinh_id.giam_tru_gia_canh if record.cau_hinh_id else 15500000
    
    thue_tncn = fields.Float(
        string="Thuế TNCN",
        compute='_compute_thue_tncn',
        store=True,
        help="Thuế TNCN theo biểu thuế lũy tiến"
    )

    def _tinh_thue_luy_tien(self, thu_nhap_tinh_thue):
        """
        Tính thuế TNCN theo biểu thuế lũy tiến 5 bậc (Luật 2026)
        
        Công thức tính nhanh:
        - Bậc 1 (≤ 10tr):        Thuế = x × 5%
        - Bậc 2 (10tr - 30tr):   Thuế = x × 10% - 500,000
        - Bậc 3 (30tr - 60tr):   Thuế = x × 20% - 3,500,000
        - Bậc 4 (60tr - 100tr):  Thuế = x × 30% - 9,500,000
        - Bậc 5 (> 100tr):       Thuế = x × 35% - 14,500,000
        """
        if thu_nhap_tinh_thue <= 0:
            return 0
        elif thu_nhap_tinh_thue <= 10000000:
            return thu_nhap_tinh_thue * 0.05
        elif thu_nhap_tinh_thue <= 30000000:
            return thu_nhap_tinh_thue * 0.10 - 500000
        elif thu_nhap_tinh_thue <= 60000000:
            return thu_nhap_tinh_thue * 0.20 - 3500000
        elif thu_nhap_tinh_thue <= 100000000:
            return thu_nhap_tinh_thue * 0.30 - 9500000
        else:
            return thu_nhap_tinh_thue * 0.35 - 14500000

    @api.depends('tong_thu_nhap', 'phu_cap_an_trua', 'tong_bao_hiem', 'giam_tru_gia_canh', 'cau_hinh_id.phu_cap_an_trua_mien_thue')
    def _compute_thue_tncn(self):
        """Tính thuế TNCN theo biểu lũy tiến"""
        for record in self:
            # Lấy mức phụ cấp miễn thuế từ config
            mien_thue = record.cau_hinh_id.phu_cap_an_trua_mien_thue if record.cau_hinh_id else 730000
            phu_cap_mien_thue = min(record.phu_cap_an_trua, mien_thue)
            
            # Thu nhập chịu thuế (trừ phụ cấp ăn trưa miễn thuế)
            record.thu_nhap_chiu_thue = record.tong_thu_nhap - phu_cap_mien_thue

            # Thu nhập tính thuế
            thu_nhap_tinh_thue = (
                record.thu_nhap_chiu_thue
                - record.tong_bao_hiem
                - record.giam_tru_gia_canh
            )
            # Không được âm
            record.thu_nhap_tinh_thue = max(0, thu_nhap_tinh_thue)

            # Thuế TNCN theo biểu lũy tiến
            record.thue_tncn = record._tinh_thue_luy_tien(record.thu_nhap_tinh_thue)

    # ===== F. LƯƠNG NET =====
    luong_thuc_nhan = fields.Float(
        string="Lương thực nhận (Net)",
        compute='_compute_luong_net',
        store=True,
        help="Tổng thu nhập - bảo hiểm - thuế TNCN"
    )

    @api.depends('tong_thu_nhap', 'tong_bao_hiem', 'thue_tncn')
    def _compute_luong_net(self):
        """Tính lương net"""
        for record in self:
            record.luong_thuc_nhan = (
                record.tong_thu_nhap
                - record.tong_bao_hiem
                - record.thue_tncn
            )

    # ===== NOTES =====
    ghi_chu = fields.Text(string="Ghi chú")

    # ===== CONSTRAINTS =====
    _sql_constraints = [
        ('unique_bang_luong_nhan_vien',
         'unique(bang_luong_id, nhan_vien_id)',
         'Nhân viên đã có chi tiết lương trong bảng lương này!')
    ]

    @api.model
    def create(self, vals):
        """Khi tạo mới, lấy thông tin lương từ nhân viên"""
        if 'nhan_vien_id' in vals:
            nhan_vien = self.env['nhan_vien'].browse(vals['nhan_vien_id'])
            # Lấy lương hợp đồng từ nhân viên (nếu có)
            if hasattr(nhan_vien, 'luong_hop_dong') and nhan_vien.luong_hop_dong:
                vals['luong_hop_dong'] = nhan_vien.luong_hop_dong
            if hasattr(nhan_vien, 'luong_dong_bao_hiem') and nhan_vien.luong_dong_bao_hiem:
                vals['luong_dong_bao_hiem'] = nhan_vien.luong_dong_bao_hiem
        return super(ChiTietLuong, self).create(vals)
