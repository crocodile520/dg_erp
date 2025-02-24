{
    'name': '金凌电子 物流中心模块',
    'author': 'Tuna团队',
    'category': 'jinling_erp',
    'description':'用于金凌物流管理',
    'license': 'LGPL-3',
    'version': '16.0',
    'depends': ['mail','jinling_partner','jinling_sell'],
    'data': [
        'security/jinling_logistics_group.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/jl_logistics_view.xml',
        'menu/menu.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
