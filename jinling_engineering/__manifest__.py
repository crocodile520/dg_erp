{
    'name': '金凌电子 工程业务模块',
    'author': 'Tuna团队',
    'category': 'jinling_erp',
    'description':'用于金凌工程管理',
    'version': '16.0',
    'depends': ['mail','jinling_goods','jinling_manufacture'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/jl_engineering_view.xml',
        'views/jl_tool_view.xml',
        'menu/menu.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
