{
    'name': '金凌电子 制造中心模块',
    'author': 'Tuna团队',
    'category': 'jinling_erp',
    'description':'用于金凌电子业务管理',
    'version': '16.0',
    'depends': ['base','mail','jinling_partner','jinling_goods','jinling_sell'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/jl_mes_plm_view.xml',
        'views/jl_mes_plm_in_view.xml',
        # 'views/jl_mes_plm_picking_view.xml',
        'views/jl_mes_plm_refund_view.xml',
        'menu/menu.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
