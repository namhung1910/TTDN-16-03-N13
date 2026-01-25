# -*- coding: utf-8 -*-
{
    'name': "nhan_su",

    'summary': """
        Quản lý hồ sơ nhân sự và văn bản liên quan
    """,

    'description': """
        Module quản lý nhân sự:
        - Hồ sơ nhân viên
        - Quá trình công tác
        - Chấm công
        - Văn bản đến cần xử lý
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    'category': 'Human Resources',
    'version': '0.1',

    'depends': ['base'],

    'data': [
        'security/ir.model.access.csv',
        'views/nhan_vien.xml',
        'views/phong_ban.xml',
        'views/chung_chi.xml',
        # 'views/cham_cong.xml',  # Đã chuyển sang module riêng
        'views/lich_su_cong_tac.xml',
        'views/menu.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
}