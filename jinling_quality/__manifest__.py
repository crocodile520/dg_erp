{
    'name': '金凌电子 品质中心模块',
    'author': 'Tuna团队',
    'category': 'jinling_erp',
    'description':'用于金凌电子质量管理',
    'version': '16.0',
    'license': 'LGPL-3',
    'depends': ['mail','jinling_manufacture'],
    'data': [
        'security/jinling_quality_group.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/jl_quality_view.xml',
        'menu/menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
