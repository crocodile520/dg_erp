{
    'name': '金凌电子 业务客户模块',
    'author': 'Tuna团队',
    'category': 'jinling_erp',
    'description':'用于金凌电子客户管理',
    'version': '16.0',
    'license': 'LGPL-3',
    'depends': ['base','mail',],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/data.xml',
        'views/partner_view.xml',
        'menu/menu.xml',

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
