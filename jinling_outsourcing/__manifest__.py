{
    'name': '金凌电子 委外生产模块',
    'author': 'Tuna团队',
    'category': 'jinling_erp',
    'description':'用于金凌电子业务管理',
    'version': '16.0',
    'license': 'LGPL-3',
    'depends': ['base','mail','jinling_partner','jinling_goods'],
    'data': [
        'security/jinling_outsourcing_group.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/jl_mes_ous_view.xml',
        'views/jl_mes_ous_in_view.xml',
        'views/jl_mes_ous_picking_view.xml',
        'views/jl_mes_ous_refund_view.xml',
        'views/jl_ous_quality_view.xml',
        'menu/menu.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
