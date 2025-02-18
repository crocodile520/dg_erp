{
    'name': '金凌电子 业务中心模块',
    'author': 'Tuna团队',
    'category': 'jinling_erp',
    'description':'用于金凌电子业务管理',
    'version': '16.0',
    'depends': ['base','mail','jinling_partner','jinling_goods',],
    'data': [
        'security/jinling_sell_group.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/data.xml',
        'views/jl_sell_order_view.xml',
        'views/jl_sell_apply_view.xml',
        'views/jl_sell_order_out_view.xml',
        'views/jl_sell_order_review_view.xml',
        'views/jl_sell_price_strategy_view.xml',
        'report/paperformat.xml',
        'report/report_sell_out_template.xml',
        'menu/menu.xml',

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
