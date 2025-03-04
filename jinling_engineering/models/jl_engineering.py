from odoo import api,fields,models
from odoo.exceptions import UserError


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

class JlEngineering(models.Model):
    _name = 'jl.engineering'
    _description = '工程工单'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'



    def button_done(self):
        self.ensure_one()
        if not len(self.line_ids):
            raise UserError('工具明细行不可以为空！')
        self.write({
            'state':'done',
            'approve_uid': self.env.uid,
            'approve_date': fields.Datetime.now(self),
        })


    def button_draft(self):
        self.ensure_one()
        if self.plm_id.state != 'draft':
            raise UserError('当前工单已经开工，无法撤回')
        self.write({
            'state': 'draft',
            'approve_uid': False,
            'approve_date': False,
        })


    def button_cancel(self):
        self.ensure_one()
        self.write({
            'state': 'cancel',
            'approve_uid': self.env.uid,
            'approve_date': fields.Datetime.now(self),
        })

    name = fields.Char('单据编号',
                       index=True,
                       copy=False,
                       default=lambda self: self.env['ir.sequence'].next_by_code('jl.engineering'),
                       help="质量检验单的唯一编号，当创建时它会自动生成下一个编号。")
    user_id = fields.Many2one(
        'hr.employee',
        '制单人',
        ondelete='restrict',
        states=READONLY_STATES,
        readonly=False,
        default=lambda self: self.env.user.employee_id.id,
        help='制单人',
    )
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)
    plm_id = fields.Many2one('jl.mes.plm', '生产工单', ondelete='cascade', help='绑定生产工单')
    order_id = fields.Many2one('sell.order', '销售订单', ondelete='cascade', help='绑定销售订单')
    goods_id = fields.Many2one('goods', '商品', ondelete='cascade', help='购货商品')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    uom_id = fields.Many2one('uom', related='goods_id.uom_id', ondelete='cascade')
    qty = fields.Float('数量', digits='Quantity', track_visibility='always', default=0)
    line_ids = fields.One2many('jl.engineering.line', 'eng_id', '工程工单明细行', ondelete='cascade',
                               help='工程工单明细行')
    date = fields.Date('单据日期', default=lambda self: fields.Date.context_today(self), required=True)
    delivery_date = fields.Date('要求交货日期', related='plm_id.delivery_date', required=True)
    state = fields.Selection(STATE, '确认状态', help='单据状态', default='draft', track_visibility='always')
    approve_uid = fields.Many2one('res.users',
                                  '确认人',
                                  copy=False,
                                  ondelete='restrict',
                                  help='确认单据的人')
    approve_date = fields.Datetime('确认日期', copy=False)
    note = fields.Char('备注')



class JlEngineeringLine(models.Model):
    _name = 'jl.engineering.line'
    _description = '工程工单明细'

    eng_id = fields.Many2one('jl.engineering', '工程工单', ondelete='cascade', help='关联工程工单')
    tool_id = fields.Many2one('tool', '工具', ondelete='cascade', help='关联工具')
    specs = fields.Char('规格型号',related='tool_id.specs')
    uom_id = fields.Many2one('uom', '单位',related='tool_id.uom_id')
    surface = fields.Char('颜色',related='tool_id.surface')
    qty = fields.Float('数量', digits='Quantity', track_visibility='always', default=0)
    note = fields.Char('备注')
    state = fields.Selection(STATE, '确认状态', related='eng_id.state')