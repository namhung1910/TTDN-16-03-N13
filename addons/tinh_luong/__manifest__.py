# -*- coding: utf-8 -*-
{
    'name': "tinh_luong",

    'summary': """
        Quản lý tính lương và bảo hiểm
    """,

    'description': """
        Module tính lương:
        - Tính lương tháng theo ngày công
        - Tính bảo hiểm (BHXH, BHYT, BHTN)
        - Tính thuế TNCN
        - Quản lý bảng lương và chi tiết lương
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    'category': 'Human Resources',
    'version': '1.0',

    # Dependencies - requires both nhan_su and cham_cong
    'depends': [
        'base',
        'nhan_su',
        'cham_cong'
    ],

    # Data files
    'data': [
        'security/ir.model.access.csv',
        'data/default_config.xml',
        'views/bang_luong_view.xml',
        'views/chi_tiet_luong_view.xml',
        'views/cau_hinh_luong_view.xml',
        'views/menu.xml',
    ],
    
    'demo': [],
    'installable': True,
    'application': True,  # Show as root menu in sidebar
    'auto_install': False,
}
