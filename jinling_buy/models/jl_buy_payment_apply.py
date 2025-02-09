from odoo import fields,api,models


STATE = [
    ('draft','草稿'),
    ('done','完成'),
    ('cancel','作废'),
]

class JlBuyPaymentApply(models.Model):
    _name = 'jl.buy.payment.apply'
    _description = '付款申请单'
    _inherit = ['mail.thread']



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

    name = fields.Char('单据编号',
                       index=True,
                       copy=False,
                       default=lambda self: self.env['ir.sequence'].next_by_code('jl.buy.payment.apply'),
                       help="采购付款申请单的唯一编号，当创建时它会自动生成下一个编号。")
    date = fields.Date('日期', default=lambda self: fields.Date.context_today(self), required=True)
    user_id = fields.Many2one('hr.employee', '经办人', default=lambda self: self.env.user.employee_id.id, ondelete='cascade', requierd=True,
                              track_visibility='onchange')
    order_id = fields.Many2one('jl.buy.order', '采购订单', ondelete='cascade', requierd=True, help='绑定采购订单')
    warehousing_id = fields.Many2one('jl.buy.warehousing', '采购入库单', ondelete='cascade', requierd=True, help='绑定采购入库单')
    supplier_id = fields.Many2one('supplier', '供应商', related='order_id.supplier_id', ondelete='cascade',
                                  requierd=True, help='供应商')
    line_ids = fields.One2many('jl.buy.payment.apply.line', 'apply_id', '付款申请单明细', ondelete='cascade', help='关联付款申请单')
    state = fields.Selection(STATE, '确认状态', help='单据状态', default='draft',track_visibility='always')
    note = fields.Char('备注')




class JlBuyPaymentApplyLine(models.Model):
    _name = 'jl.buy.payment.apply.line'
    _description = '付款申请单明细'

    apply_id = fields.Many2one('jl.buy.payment.apply', '付款申请单', index=True, ondelete='cascade')
    goods_id = fields.Many2one('goods', '商品', ondelete='cascade', help='购货商品')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    uom_id = fields.Many2one('uom', related='goods_id.uom_id', ondelete='cascade')
    qty = fields.Float('数量', digits='Quantity', )
    price = fields.Float('单价', digits='Price', )
    tax_price = fields.Float('含税单价', digits='Price',ondelete='cascade')
    tax_rate = fields.Float('税率(%)', digits='Amount',ondelete='cascade' )
    tax_amount = fields.Float('税额', digits='Amount',ondelete='cascade')
    amount = fields.Float('金额', digits='Amount',ondelete='cascade')
    subtotal = fields.Float('价税合计', digits='Amount',ondelete='cascade')
    note = fields.Char('备注')
    state = fields.Selection(STATE, '确认状态', related='apply_id.state')