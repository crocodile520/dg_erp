{
    'name': '金凌电子 产品模块',
    'author': 'Tuna团队',
    'category': 'jinling_erp',
    'description':'用于金凌电子产品管理',
    'version': '16.0',
    'depends': ['mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/goods_view.xml',
        'views/uom_view.xml',
        'views/goods_class_view.xml',
        'views/goods_bom_view.xml',
        'menu/menu.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
