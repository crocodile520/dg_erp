from odoo import api,fields,models
from odoo.exceptions import UserError





# 字段只读状态
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
class SellOrderReview(models.Model):
    _name = 'sell.order.review'
    _description = '销售评审单'
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
            'state': 'draft',
            'approve_uid': False,
            'approve_date': False,
        })

    def button_cancel(self):
        self.ensure_one()
        self.write({
            'state':'cancel',
            'approve_uid': self.env.uid,
            'approve_date': fields.Datetime.now(self),
        })

    name = fields.Char('单据编号',
                       index=True,
                       copy=False,
                       default=lambda self: self.env['ir.sequence'].next_by_code('sell.order.review'),
                       help="销售评审单的唯一编号，当创建时它会自动生成下一个编号。")
    user_id = fields.Many2one(
        'hr.employee',
        '销售员',
        ondelete='restrict',
        states=READONLY_STATES,
        readonly=False,
        default=lambda self: self.env.user.employee_id.id,
        help='销售员',
    )
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', '外币')
    ref = fields.Char('客户订单号', track_visibility='always')
    order_id = fields.Many2one('sell.order', '销售订单', ondelete='cascade', help='销售订单')
    partner_id = fields.Many2one('partner', '客户')
    partner_code = fields.Char('客户编码', related='partner_id.code')
    main_mobile = fields.Char('联系人', related='partner_id.main_mobile')
    main_contact = fields.Char('联系人电话', related='partner_id.main_contact')
    address = fields.Char('送货地址', related='partner_id.address')
    date = fields.Date('单据日期', default=lambda self: fields.Date.context_today(self), required=True)
    delivery_date = fields.Date('交货日期', default=lambda self: fields.Date.context_today(self), required=True)
    line_ids = fields.One2many('sell.order.review.line', 'review_id', ondelete='cascade',
                               help='销售评审单明细行')
    note = fields.Char('备注')
    warehouse_id = fields.Many2one('warehouse', '仓库', help='关联仓库，购票物品存储某个仓库')
    state = fields.Selection(STATE, '确认状态', help='单据状态', default='draft', track_visibility='always')
    approve_uid = fields.Many2one('res.users',
                                  '确认人',
                                  copy=False,
                                  ondelete='restrict',
                                  help='确认单据的人')
    approve_date = fields.Datetime('确认日期', copy=False)



class SellOrderReviewLine(models.Model):
    _name = 'sell.order.review.line'
    _description = '销售评审单明细'

    review_id = fields.Many2one('sell.order.review', '销售评审单', ondelete='cascade')
    ref = fields.Char('客户订单号', related='review_id.ref')
    goods_id = fields.Many2one('goods', '产品名称', ondelete='cascade')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    uom_id = fields.Many2one('uom', related='goods_id.uom_id', ondelete='cascade')
    prediction_date = fields.Date('预测完工日期',ondelete='cascade')
    delivery_date = fields.Date('交货日期', related='review_id.delivery_date', required=True,ondelete='cascade')
    qty = fields.Float('下单数量', digits='Quantity', )
    note = fields.Char('备注', help='如果特殊情况请备注')
    state = fields.Selection(STATE, '确认状态', related='review_id.state')