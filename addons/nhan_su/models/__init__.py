# -*- coding: utf-8 -*-

# Nạp các model ít liên kết trước
from . import phong_ban
from . import nhan_vien  # Nạp sau cùng vì nó chứa các One2many trỏ đến các model trên
from . import chung_chi
# from . import cham_cong  # Đã chuyển sang module riêng 'cham_cong'
from . import lich_su_cong_tac