{
    'name': 'T4Tek Tracking Odoo 18.0',
    'version': '1.0',
    "author": "Đặng Thành Nhân",
    'sequence': 0,
    'description': '',
    'depends': [ "stock", "product", "web", "bus", "base", "rfid_reader"],
    'installable': True,
    'auto_install': True,
    'application': True,
    'data':
        [
        'security/access_user.xml',
        'security/ir.model.access.csv',
        "views/stock_receipt_views.xml",
        "views/stock_receipt_card_view.xml",
        "views/menu_views.xml",
    ],
    'assets': {
         'web.assets_backend': [
            't4tek_device_tracking/static/src/js/share/**/*',
            't4tek_device_tracking/static/src/xml/share/**/*',
            't4tek_device_tracking/static/src/js/backend/**/*',
            't4tek_device_tracking/static/src/css/backend/**/*',
            't4tek_device_tracking/static/src/xml/backend/**/*',
        ],
    },
    'license': 'LGPL-3',
}
