from odoo import api,fields,models


class Supplier(models.Model):
    _name = 'supplier'
    _description = '供应商'
    _inherit = ['mail.thread']
    _sql_constraints = [('name_unique', 'unique(name)', '供应商名称不可以重复'),('name_unique', 'unique(code)', '编号不可以重复')]

    name = fields.Char('名称')
    code = fields.Char('编号')
    main_mobile = fields.Char('联系人')
    main_contact = fields.Char('联系人电话')
    address = fields.Char('联系人地址')
    account = fields.Char('账户')
    duty_number = fields.Char('税号')
    bank_address = fields.Char('银行地址')
