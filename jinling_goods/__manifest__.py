{
    'name': '金凌电子 产品模块',
    'author': 'Tuna团队',
    'category': 'jinling_erp',
    'description':'用于金凌电子产品管理',
    'version': '16.0',
    'license': 'LGPL-3',
    'depends': ['mail'],
    'data': [
        'security/jinling_goods_group.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/goods_view.xml',
        'views/uom_view.xml',
        'views/goods_class_view.xml',
        'views/goods_bom_view.xml',
        'views/goods_bom_file_view.xml',
        'menu/menu.xml'
    ],
    'assets': {
            'web.assets_backend': [
                # 'jinling_goods/static/src/js/goods_class_list.js',
                # 'jinling_goods/static/src/scss/goods_class.scss',
            ],
        },
    'installable': True,
    'application': True,
    'auto_install': False,
}