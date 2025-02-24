from odoo import fields,models,api



class Partner(models.Model):
    _name = 'partner'
    _description = '客户'
    _inherit = ['mail.thread']
    _sql_constraints = [('name_unique', 'unique(name)', '名称不可以重复'),
                        ('name_unique', 'unique(code)', '编号不可以重复')]

    name = fields.Char('名称')
    code = fields.Char('编号')
    main_mobile = fields.Char('联系人')
    main_contact = fields.Char('联系人电话')
    address = fields.Char('送货地址')
    user_id = fields.Many2one(
        'hr.employee',
        '销售员',
        ondelete='restrict',
        readonly=False,
        default=lambda self: self.env.user.employee_id.id,
        help='销售员',
    )