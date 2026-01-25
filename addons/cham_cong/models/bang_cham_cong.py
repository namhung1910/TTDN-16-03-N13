from odoo import models, fields, api
from datetime import datetime, time, timedelta
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import pytz

class BangChamCong(models.Model):
    _name = 'bang_cham_cong'
    _description = "Bảng chấm công"
    _rec_name = 'Id_BCC'
    _order = 'ngay_cham_cong asc, gio_vao_ca asc, id asc'

    # Basic fields
    nhan_vien_id = fields.Many2one('nhan_vien', string="Nhân viên", required=True)
    ngay_cham_cong = fields.Date("Ngày chấm công", required=True)

    Id_BCC = fields.Char(string="ID BCC", compute="_compute_Id_BCC", store=True)

    @api.depends('nhan_vien_id', 'ngay_cham_cong')
    def _compute_Id_BCC(self):
        for record in self:
            if record.nhan_vien_id and record.ngay_cham_cong:
                record.Id_BCC = f"{record.nhan_vien_id.name}_{record.ngay_cham_cong.strftime('%Y-%m-%d')}"
            else:
                record.Id_BCC = ""
    
    # Đăng ký ca làm
    dang_ky_ca_lam_id = fields.Many2one('dang_ky_ca_lam_theo_ngay', string="Đăng ký ca làm")
    ca_lam = fields.Selection(related='dang_ky_ca_lam_id.ca_lam', store=True, string="Ca làm")

    @api.onchange('nhan_vien_id', 'ngay_cham_cong')
    def _onchange_dang_ky_ca_lam(self):
        for record in self:
            if record.nhan_vien_id and record.ngay_cham_cong:
                dk_ca_lam = self.env['dang_ky_ca_lam_theo_ngay'].search([
                    ('nhan_vien_id', '=', record.nhan_vien_id.id),
                    ('ngay_lam', '=', record.ngay_cham_cong)
                ], limit=1)
                record.dang_ky_ca_lam_id = dk_ca_lam.id if dk_ca_lam else False
            else:
                record.dang_ky_ca_lam_id = False

    @api.model
    def create(self, vals):
        # Xử lý dang_ky_ca_lam_id
        if vals.get('nhan_vien_id') and vals.get('ngay_cham_cong'):
            # Tìm đăng ký ca làm
            dk_ca_lam = self.env['dang_ky_ca_lam_theo_ngay'].search([
                ('nhan_vien_id', '=', vals['nhan_vien_id']),
                ('ngay_lam', '=', vals['ngay_cham_cong'])
            ], limit=1)
            if dk_ca_lam:
                vals['dang_ky_ca_lam_id'] = dk_ca_lam.id
            
            # Tìm đơn từ
            don_tu = self.env['don_tu'].search([
                ('nhan_vien_id', '=', vals['nhan_vien_id']),
                ('ngay_ap_dung', '=', vals['ngay_cham_cong']),
                ('trang_thai_duyet', '=', 'da_duyet')
            ], limit=1)
            if don_tu:
                vals['don_tu_id'] = don_tu.id
            
        return super(BangChamCong, self).create(vals)

    def write(self, vals):
        for record in self:
            # Lấy giá trị mới hoặc giữ giá trị cũ
            nhan_vien_id = vals.get('nhan_vien_id', record.nhan_vien_id.id)
            ngay_cham_cong = vals.get('ngay_cham_cong', record.ngay_cham_cong)
            
            if nhan_vien_id and ngay_cham_cong:
                # Tìm đăng ký ca làm
                dk_ca_lam = self.env['dang_ky_ca_lam_theo_ngay'].search([
                    ('nhan_vien_id', '=', nhan_vien_id),
                    ('ngay_lam', '=', ngay_cham_cong)
                ], limit=1)
                vals['dang_ky_ca_lam_id'] = dk_ca_lam.id if dk_ca_lam else False
            
                # Tìm đơn từ
                don_tu = self.env['don_tu'].search([
                    ('nhan_vien_id', '=', nhan_vien_id),
                    ('ngay_ap_dung', '=', ngay_cham_cong),
                    ('trang_thai_duyet', '=', 'da_duyet')
                ], limit=1)
                vals['don_tu_id'] = don_tu.id if don_tu else False
            
        return super(BangChamCong, self).write(vals)

    # Thời gian làm việc - FIXED times, no timezone conversion
    gio_vao_ca = fields.Char("Giờ vào ca", compute='_compute_gio_ca', store=True)
    gio_ra_ca = fields.Char("Giờ ra ca", compute='_compute_gio_ca', store=True)
    
    @api.depends('ca_lam', 'ngay_cham_cong')
    def _compute_gio_ca(self):
        """
        Compute shift start/end times as FIXED time strings.
        No timezone conversion - these are wall clock times.
        """
        for record in self:
            if not record.ca_lam:
                record.gio_vao_ca = False
                record.gio_ra_ca = False
                continue

            # Define shift times as strings (HH:MM:SS format)
            if record.ca_lam == "Sáng":
                record.gio_vao_ca = "07:30:00"
                record.gio_ra_ca = "11:30:00"
            elif record.ca_lam == "Chiều":
                record.gio_vao_ca = "13:30:00"
                record.gio_ra_ca = "17:30:00"
            elif record.ca_lam == "Cả ngày":
                record.gio_vao_ca = "07:30:00"
                record.gio_ra_ca = "17:30:00"
            else:
                record.gio_vao_ca = False
                record.gio_ra_ca = False

    gio_vao = fields.Datetime("Giờ vào thực tế")
    gio_ra = fields.Datetime("Giờ ra thực tế")

    # Tính toán đi muộn
    phut_di_muon_goc = fields.Float("Số phút đi muộn gốc", compute="_compute_phut_di_muon_goc", store=True)
    phut_di_muon = fields.Float("Số phút đi muộn thực tế", compute="_compute_phut_di_muon", store=True)
    
    @api.depends('gio_vao', 'gio_vao_ca')
    def _compute_phut_di_muon_goc(self):
        for record in self:
            if record.gio_vao and record.gio_vao_ca:
                try:
                    # Parse gio_vao_ca string (HH:MM:SS)
                    h_ca, m_ca, s_ca = map(int, record.gio_vao_ca.split(':'))
                    
                    # Convert gio_vao from UTC to local timezone
                    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
                    gio_vao_utc = pytz.UTC.localize(record.gio_vao)
                    gio_vao_local = gio_vao_utc.astimezone(vn_tz)
                    gio_vao_time = gio_vao_local.time()
                    
                    # Compare time portions
                    ca_seconds = h_ca * 3600 + m_ca * 60 + s_ca
                    vao_seconds = gio_vao_time.hour * 3600 + gio_vao_time.minute * 60 + gio_vao_time.second
                    
                    delta_seconds = vao_seconds - ca_seconds
                    record.phut_di_muon_goc = max(0, delta_seconds / 60)
                except (ValueError, AttributeError):
                    record.phut_di_muon_goc = 0
            else:
                record.phut_di_muon_goc = 0

    @api.depends('phut_di_muon_goc', 'don_tu_id', 'loai_don', 'thoi_gian_xin')
    def _compute_phut_di_muon(self):
        for record in self:
            record.phut_di_muon = record.phut_di_muon_goc
            
            # Nếu có đơn từ được duyệt
            if record.don_tu_id and record.don_tu_id.trang_thai_duyet == 'da_duyet':
                if record.loai_don == 'di_muon':
                    record.phut_di_muon = max(0, record.phut_di_muon_goc - record.thoi_gian_xin)

    # Tính toán về sớm
    phut_ve_som_goc = fields.Float("Số phút về sớm gốc", compute="_compute_phut_ve_som_goc", store=True)
    phut_ve_som = fields.Float("Số phút về sớm thực tế", compute="_compute_phut_ve_som", store=True)
    
    @api.depends('gio_ra', 'gio_ra_ca')
    def _compute_phut_ve_som_goc(self):
        for record in self:
            if record.gio_ra and record.gio_ra_ca:
                try:
                    # Parse gio_ra_ca string (HH:MM:SS)
                    h_ca, m_ca, s_ca = map(int, record.gio_ra_ca.split(':'))
                    
                    # Convert gio_ra from UTC to local timezone  
                    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
                    gio_ra_utc = pytz.UTC.localize(record.gio_ra)
                    gio_ra_local = gio_ra_utc.astimezone(vn_tz)
                    gio_ra_time = gio_ra_local.time()
                    
                    # Compare time portions
                    ca_seconds = h_ca * 3600 + m_ca * 60 + s_ca
                    ra_seconds = gio_ra_time.hour * 3600 + gio_ra_time.minute * 60 + gio_ra_time.second
                    
                    delta_seconds = ca_seconds - ra_seconds
                    record.phut_ve_som_goc = max(0, delta_seconds / 60)
                except (ValueError, AttributeError):
                    record.phut_ve_som_goc = 0
            else:
                record.phut_ve_som_goc = 0

    @api.depends('phut_ve_som_goc', 'don_tu_id', 'loai_don', 'thoi_gian_xin')
    def _compute_phut_ve_som(self):
        for record in self:
            record.phut_ve_som = record.phut_ve_som_goc
            
            # Nếu có đơn từ được duyệt
            if record.don_tu_id and record.don_tu_id.trang_thai_duyet == 'da_duyet':
                if record.loai_don == 've_som':
                    record.phut_ve_som = max(0, record.phut_ve_som_goc - record.thoi_gian_xin)
                

    # Trạng thái chấm công
    trang_thai = fields.Selection([
        ('di_lam', 'Đi làm'),
        ('di_muon', 'Đi muộn'),
        ('di_muon_ve_som', 'Đi muộn và về sớm'),
        ('ve_som', 'Về sớm'),
        ('vang_mat', 'Vắng mặt'),
        ('vang_mat_co_phep', 'Vắng mặt có phép'),
    ], string="Trạng thái", compute="_compute_trang_thai", store=True)
    
    @api.depends('phut_di_muon', 'phut_ve_som', 'gio_vao', 'gio_ra')
    def _compute_trang_thai(self):
        for record in self:
            if not record.gio_vao and not record.gio_ra:
                record.trang_thai = 'vang_mat'
            # ⚠️ FIX: Check cả 2 trước, vì nếu check di_muon trước sẽ không bao giờ đến di_muon_ve_som
            elif record.phut_di_muon > 0 and record.phut_ve_som > 0:
                record.trang_thai = 'di_muon_ve_som'
            elif record.phut_di_muon > 0:
                record.trang_thai = 'di_muon'
            elif record.phut_ve_som > 0:
                record.trang_thai = 've_som'
            else:
                record.trang_thai = 'di_lam'

    # Đơn từ liên quan
    don_tu_id = fields.Many2one('don_tu', string="Đơn từ")
    loai_don = fields.Selection(string='Loại đơn',related='don_tu_id.loai_don')
    thoi_gian_xin = fields.Float(string='Thời gian xin',related='don_tu_id.thoi_gian_xin')
    
    @api.onchange('nhan_vien_id', 'ngay_cham_cong')
    def _onchange_don_tu(self):
        for record in self:
            if record.nhan_vien_id and record.ngay_cham_cong:
                don_tu = self.env['don_tu'].search([
                    ('nhan_vien_id', '=', record.nhan_vien_id.id),
                    ('ngay_ap_dung', '=', record.ngay_cham_cong),
                    ('trang_thai_duyet', '=', 'da_duyet')
                ], limit=1)
                record.don_tu_id = don_tu.id if don_tu else False
            else:
                record.don_tu_id = False
    
    ghi_chu = fields.Text(string="Ghi chú")
    
    @api.constrains('nhan_vien_id', 'ngay_cham_cong')
    def _check_shift_registration(self):
        """
        Validate: Nhân viên phải đăng ký ca làm trước khi chấm công
        Áp dụng cho CẢ chấm công thủ công VÀ Face Recognition
        """
        for record in self:
            if record.nhan_vien_id and record.ngay_cham_cong:
                # Check if employee has registered shift for this date
                shift_registration = self.env['dang_ky_ca_lam_theo_ngay'].search([
                    ('nhan_vien_id', '=', record.nhan_vien_id.id),
                    ('ngay_lam', '=', record.ngay_cham_cong),
                ], limit=1)
                
                if not shift_registration:
                    raise ValidationError(
                        f'⚠️ Nhân viên {record.nhan_vien_id.name} chưa đăng ký ca làm '
                        f'cho ngày {record.ngay_cham_cong.strftime("%d/%m/%Y")}!\n\n'
                        f'📋 Vui lòng đăng ký ca làm trước khi chấm công.'
                    )
    
    @api.model
    def auto_mark_absent_for_missed_shifts(self):
        """
        Scheduled job: Auto-create absent records for registered shifts
        without check-in after shift end time.
        
        Run daily at 23:00 VN time.
        """
        import logging
        _logger = logging.getLogger(__name__)
        
        from datetime import date, datetime, time
        import pytz
        
        today = date.today()
        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        now_local = datetime.now(vn_tz)
        
        # Get all shift registrations for today
        registrations = self.env['dang_ky_ca_lam_theo_ngay'].search([
            ('ngay_lam', '=', today),
            ('ca_lam', '!=', '')  # Only registered shifts
        ])
        
        _logger.info(f"[AUTO-ABSENT] Checking {len(registrations)} shift registrations for {today}")
        
        created_count = 0
        
        for reg in registrations:
            # Get shift end time
            shift_end_time = self._get_shift_end_time(reg.ca_lam)
            if not shift_end_time:
                continue
            
            # Create shift end datetime in VN timezone
            shift_end_datetime = vn_tz.localize(
                datetime.combine(today, shift_end_time)
            )
            
            # Skip if shift hasn't ended yet
            if now_local < shift_end_datetime:
                _logger.debug(
                    f"[AUTO-ABSENT] Skipping {reg.nhan_vien_id.name} - "
                    f"{reg.ca_lam}: shift not ended yet (ends at {shift_end_time})"
                )
                continue
            
            # Check if attendance record already exists for this shift
            existing = self.search([
                ('nhan_vien_id', '=', reg.nhan_vien_id.id),
                ('ngay_cham_cong', '=', today),
                ('ca_lam', '=', reg.ca_lam)
            ], limit=1)
            
            if existing:
                _logger.debug(
                    f"[AUTO-ABSENT] Skipping {reg.nhan_vien_id.name} - "
                    f"{reg.ca_lam}: attendance record exists"
                )
                continue
            
            # Create absent record
            try:
                self.create({
                    'nhan_vien_id': reg.nhan_vien_id.id,
                    'ngay_cham_cong': today,
                    'dang_ky_ca_lam_id': reg.id,
                    # ca_lam will be auto-filled from dang_ky_ca_lam_id
                    'gio_vao': False,
                    'gio_ra': False,
                    # trang_thai will auto-compute to 'vang_mat'
                })
                
                created_count += 1
                _logger.info(
                    f"[AUTO-ABSENT] ✓ Marked absent: {reg.nhan_vien_id.name} - "
                    f"Ca {reg.ca_lam} on {today}"
                )
            except Exception as e:
                _logger.error(
                    f"[AUTO-ABSENT] ✗ Error marking absent for {reg.nhan_vien_id.name}: {str(e)}"
                )
        
        _logger.info(f"[AUTO-ABSENT] Completed: Auto-marked {created_count} employees as absent")
        return created_count
    
    def _get_shift_end_time(self, ca_lam):
        """
        Get shift end time based on shift name
        
        Returns:
            datetime.time: End time of shift
        """
        shift_times = {
            'Sáng': time(11, 30),
            'Chiều': time(17, 30),
            'Cả ngày': time(17, 30)
        }
        return shift_times.get(ca_lam)