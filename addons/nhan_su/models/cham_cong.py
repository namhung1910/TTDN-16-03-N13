from odoo import models, fields


class ChamCong(models.Model):
    _name = 'cham_cong'
    _description = 'Chấm công'
    _order = 'ngay desc'

    nhan_vien_id = fields.Many2one(
        'nhan_vien',
        string="Nhân viên",
        required=True,
        ondelete='cascade',
        index=True
    )

    ngay = fields.Date(string="Ngày", required=True)
    gio_vao = fields.Datetime(string="Giờ vào")
    gio_ra = fields.Datetime(string="Giờ ra")

    trang_thai = fields.Selection(
        [
            ('present', 'Có mặt'),
            ('late', 'Đi muộn'),
            ('leave', 'Nghỉ phép'),
            ('absent', 'Vắng'),
        ],
        string="Trạng thái",
        default='present'
    )

    ghi_chu = fields.Text(string="Ghi chú")