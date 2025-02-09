from odoo import fields,models,api


STATE = [
    ('draft','草稿'),
    ('done','完成'),
    ('cancel','作废'),
]
class Warehouse(models.Model):
    _name = 'warehouse'
    _description = '仓库'
    _inherit = ['mail.thread']


    code = fields.Char('编号')
    name = fields.Char('仓库',required=True,help='货品储存仓库的位置')
    address = fields.Char('地址',help='仓库的具体位置')
    phone = fields.Char('电话')
    contact = fields.Char('联系人')
    user_id = fields.Many2one('hr.employee','仓管',help='负责仓库的人')
    remark = fields.Char('备注', )
    state = fields.Selection(STATE,'确认状态', help='单据状态',default='draft')


    def button_done(self):
        self.ensure_one()
        self.write({
            'state':'done'
        })


    def button_draft(self):
        self.write({
            'state': 'draft'
        })


    def button_cancel(self):
        self.write({
            'state': 'cancel'
        })