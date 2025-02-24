{
    'name': '金凌电子 仓库模块',
    'author': 'Tuna团队',
    'category': 'jinling_erp',
    'description':'用于金凌电子仓库管理',
    'version': '16.0',
    'license': 'LGPL-3',
    'depends': ['mail'],
    'data': [
        'security/jinling_warehouse_group.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/warehouse_view.xml',
        'views/jl_move_in_view.xml',
        'views/jl_move_out_view.xml',
        'report/jl_warehouse_balance_report_view.xml',
        'menu/menu.xml',

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
