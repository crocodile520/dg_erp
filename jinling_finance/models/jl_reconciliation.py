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

class JlReconciliation(models.Model):
    _name = 'jl.reconciliation'
    _description = '对账单'
    _inherit = ['mail.thread']


    def button_done(self):
        self.ensure_one()
        self.write({
            'state':'done',
            'approve_uid': self.env.uid,
            'approve_date': fields.Datetime.now(self),
        })


    def button_draft(self):
        self.ensure_one()
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
                       default=lambda self: self.env['ir.sequence'].next_by_code('jl.reconciliation'),
                       help="销售发货单的唯一编号，当创建时它会自动生成下一个编号。")
    user_id = fields.Many2one(
        'hr.employee',
        '制单人',
        ondelete='restrict',
        states=READONLY_STATES,
        readonly=False,
        default=lambda self: self.env.user.employee_id.id,
        help='制单人',
    )
    order_id = fields.Many2one('sell.order', '销售订单', ondelete='cascade', help='销售订单')
    out_id = fields.Many2one('sell.order.out', '销售发货单', ondelete='cascade', help='销售订单')
    ref = fields.Char('客户订单号', track_visibility='always')
    delivery_number = fields.Char('送货单号', track_visibility='always')
    partner_id = fields.Many2one('partner', '客户')
    user_order_id = fields.Many2one(
        'hr.employee',
        '销售员',
        ondelete='restrict',
        states=READONLY_STATES,
        readonly=False,
        related='order_id.user_id',
        help='销售员',
    )
    partner_code = fields.Char('客户编码', related='partner_id.code')
    main_mobile = fields.Char('联系人', related='partner_id.main_mobile')
    main_contact = fields.Char('联系人电话', related='partner_id.main_contact')
    address = fields.Char('联系人地址', related='partner_id.address')
    date = fields.Date('单据日期', default=lambda self: fields.Date.context_today(self), required=True)
    line_ids = fields.One2many('jl.reconciliation.line', 'rec_id', ondelete='cascade',
                               help='对账单明细')
    note = fields.Char('备注')
    state = fields.Selection(STATE, '确认状态', help='单据状态', default='draft', track_visibility='always')


class JlReconciliationLine(models.Model):
    _name = 'jl.reconciliation.line'
    _description = '对账单明细'

    rec_id = fields.Many2one('jl.reconciliation', '对账单', ondelete='cascade')
    ref = fields.Char('客户订单号', related='rec_id.ref')
    goods_id = fields.Many2one('goods', '产品名称', ondelete='cascade')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    uom_id = fields.Many2one('uom', related='goods_id.uom_id', ondelete='cascade')
    weight = fields.Float('重量(KG)', digits='Quantity', )
    qty = fields.Float('发货数量', digits='Quantity')
    amount = fields.Float('金额',digits='Amount')
    note = fields.Char('备注', help='如果特殊情况请备注')
    state = fields.Selection(STATE, '确认状态', related='rec_id.state')