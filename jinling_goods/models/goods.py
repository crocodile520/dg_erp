from odoo import fields ,api,models


STATE = [
    ('draft','草稿'),
    ('done','完成'),
    ('cancel','作废'),
]
class Goods(models.Model):
    _name = 'goods'
    _description = '商品'
    _inherit = ['mail.thread']
    _sql_constraints = [('name_unique','unique(name)','商品编号不可以重复')]


    name = fields.Char('编号',required=True,help='商品名称')
    describe = fields.Char('描述',help='用户商品描述')
    specs = fields.Char('规格型号')
    surface = fields.Char('颜色')
    goods_class_id = fields.Many2one('goods.class','商品分类',ondelete='cascade',help='分类名称')
    is_search = fields.Boolean('默认筛选',related='goods_class_id.is_search')
    uom_id = fields.Many2one('uom','单位')
    active = fields.Boolean('启用', default=True)
    remark = fields.Char('备注',)
    state = fields.Selection(STATE,'确认状态',help='单据状态',default='draft',track_visibility='always')


    def button_done(self):
        self.ensure_one()
        self.write({
            'state':'done'
        })


    def button_draft(self):
        self.ensure_one()
        self.write({
            'state': 'draft'
        })


    def button_cancel(self):
        self.ensure_one()
        self.write({
            'state': 'cancel'
        })