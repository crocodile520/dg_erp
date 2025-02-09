from odoo import api,fields,models


READONLY_STATES = {
    'done': [('readonly', True)],
    'onchange': [('readonly', True)],
    'stop': [('readonly', True)],
    'cancel': [('readonly', True)],
}

STATE = [
    ('draft','草稿'),
    ('done','完成'),
    ('cancel','作废'),
]

class GoodsBom(models.Model):
    _name = 'goods.bom'
    _description = '产品BOM'
    _inherit = ['mail.thread']



    def button_done(self):
        self.ensure_one()
        self.write({
            'state': 'done',
            'approve_uid': self.env.uid,
            'approve_date': fields.Datetime.now(self),
        })

    def button_draft(self):
        self.ensure_one()
        self.write({
            'state': 'draft'
        })

    def button_cancel(self):
        self.ensure_one()
        self.write({
            'state':'cancel'
        })

    bom_name = fields.Char('名称',track_visibility='always')
    goods_id = fields.Many2one('goods','商品',required=True,ondelete='cascade',help='产品名称')
    describe = fields.Char('描述',related='goods_id.describe', help='用户商品描述')
    specs = fields.Char('规格型号',related='goods_id.specs')
    surface = fields.Char('颜色',related='goods_id.surface')
    goods_class_id = fields.Many2one('goods.class', '商品分类',related='goods_id.goods_class_id', ondelete='cascade', help='分类名称')
    uom_id = fields.Many2one('uom', '单位',related='goods_id.uom_id')
    active = fields.Boolean('启用', default=True)
    note = fields.Char('备注')
    code = fields.Char('代号',ondelete='cascade',help='产品代号')
    line_ids = fields.One2many('goods.bom.line', 'bom_id', ondelete='cascade',
                               help='产品BOM工艺')
    user_id = fields.Many2one(
        'hr.employee',
        '制单人',
        ondelete='restrict',
        states=READONLY_STATES,
        readonly=False,
        default=lambda self: self.env.user.employee_id.id,
        help='制单人',
    )
    date = fields.Date('单据日期', default=lambda self: fields.Date.context_today(self), required=True)
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)
    approve_uid = fields.Many2one('res.users',
                                  '确认人',
                                  copy=False,
                                  ondelete='restrict',
                                  help='确认单据的人')
    approve_date = fields.Datetime('确认日期', copy=False)
    state = fields.Selection(STATE, '确认状态', help='单据状态', default='draft', track_visibility='always')



class GoodsBomLine(models.Model):
    _name = 'goods.bom.line'
    _description = '产品BOM工艺'



    bom_id = fields.Many2one('goods.bom','产品BOM',ondelete='cascade')
    goods_id = fields.Many2one('goods','材料', required=True, ondelete='cascade', help='产品名称')
    describe = fields.Char('描述', related='goods_id.describe', help='用户商品描述')
    specs = fields.Char('规格型号', related='goods_id.specs')
    surface = fields.Char('颜色', related='goods_id.surface')
    qty = fields.Float('数量',ondelete='cascade',help='产品数量')
    goods_class_id = fields.Many2one('goods.class', '商品分类', related='goods_id.goods_class_id', ondelete='cascade',
                                     help='分类名称')
    uom_id = fields.Many2one('uom', '单位', related='goods_id.uom_id')
    note = fields.Char('备注')
    state = fields.Selection(STATE, '确认状态', related='bom_id.state')