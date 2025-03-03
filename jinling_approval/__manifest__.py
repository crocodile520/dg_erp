{
    'name': '金凌电子 审批管理模块',
    'author': 'Tuna团队',
    'category': 'jinling_erp',
    'description': '用于金凌电子审批流程管理',
    'version': '16.0',
    'license': 'LGPL-3',
    'depends': ['mail', 'base', 'hr'],
    'data': [
        # 安全配置
        'security/jinling_approval_group.xml',
        'security/ir.model.access.csv',
        
        # 数据
        'data/sequence.xml',
        
        # 视图
        'views/jl_approval_model_view.xml',
        'views/jl_approval_process_view.xml',
        'views/jl_approval_record_view.xml',
        'report/jl_approval_report.xml',
        
        # 菜单 - 最后加载
        'menu/menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
} 