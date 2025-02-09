{
    'name': '金凌电子 生产计划模块',
    'author': 'Tuna团队',
    'category': 'jinling_erp',
    'description':'用于金凌电子生产计划管理',
    'version': '16.0',
    'depends': ['mail','jinling_manufacture'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/jl_mes_plm_programme_view.xml',
        'wizard/jl_mes_plm_programme_key_wizard_view.xml',
        'menu/menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
