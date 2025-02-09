from odoo import api,models,fields
from odoo.exceptions import UserError



# 字段只读状态
READONLY_STATES = {
    'done': [('readonly', True)],
    'onchange': [('readonly', True)],
    'stop': [('readonly', True)],
    'cancel': [('readonly', True)],
}


PARTNER_AREA = [
    ('abroad','国外'),
    ('home','国内'),
]

STATE = [
    ('draft','草稿'),
    ('done','完成'),
    ('cancel','作废'),
]

class SellApply(models.Model):
    _name = 'sell.apply'
    _description = '销售申请单'
    _inherit = ['mail.thread']


    def button_done(self):
        '''确认后产生销售订单'''
        self.ensure_one()
        if self.state == 'done':
            raise UserError('单据已经确认，请勿重复确认')
        if not self.line_ids:
            raise UserError('请填写销售申请明细行')
        for line in self.line_ids:
            if not line.warehouse_id:
                raise UserError('仓库不可以为空')
        order_id = self.env['sell.order'].create({
            'user_id': self.user_id.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'ref': self.ref,
            'partner_id': self.partner_id.id,
            'delivery_date': self.delivery_date,
            'apply_id': self.id,
        })
        order_id.write({
            'line_ids': [(0, 0, {
                'goods_id': line.goods_id.id,
                'qty': line.qty,
                'warehouse_id': line.warehouse_id.id,
                'price': line.price,
                'tax_rate': line.tax_rate,
            }) for line in self.line_ids]
        })
        if order_id.goods_state != 'old':
            order_id.create_order_review()
        self.write({
            'state':'done',
            'approve_uid': self.env.uid,
            'approve_date': fields.Datetime.now(self),
        })

    def button_draft(self):
        self.ensure_one()
        if self.state == 'draft':
            raise UserError('请不要重复撤销')
        ids = self.env['sell.order'].search([('apply_id','=',self.id)])
        if any(ids):
            for id in ids:
                if id.state != 'draft':
                    raise UserError('不可以删除已经确定的销售订单')
                else:
                    id.unlink()
        self.write({
            'state': 'draft'
        })


    def button_cancel(self):
        self.ensure_one()
        self.write({
            'state': 'cancel'
        })


    def action_sell_order_view(self):
        self.ensure_one()
        action = {
            'name': '销售订单',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sell.order',
            'view_id': False,
            'target': 'current',
        }

        form_view = self.env.ref('jinling_sell.sell_order_view_form').id
        tree_view = self.env.ref('jinling_sell.sell_order_view_tree').id

        if self.sell_order_count > 1:
            action['domain'] = "[('apply_id','=',%s)]" % self.id
            action['view_mode'] = 'tree,form'
            action['views'] = [(tree_view, 'tree'),(form_view, 'form')]
        elif self.sell_order_count == 1:
            order_id = self.env['sell.order'].search([('apply_id', '=', self.id)])
            action['views'] = [(form_view, 'form')]
            action['res_id'] = order_id and order_id.id or False
        return action

    def _compute_sell_order_count(selfs):
        for self in selfs:
            self.sell_order_count = self.env['sell.order'].search_count([('apply_id','=',self.id)])

    name = fields.Char('单据编号',
                       index=True,
                       copy=False,
                       default=lambda self: self.env['ir.sequence'].next_by_code('sell.apply'),
                       help="销售申请单的唯一编号，当创建时它会自动生成下一个编号。")
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
    partner_id = fields.Many2one('partner', '客户')
    partner_code = fields.Char('客户编码', related='partner_id.code')
    main_mobile = fields.Char('联系人', related='partner_id.main_mobile')
    main_contact = fields.Char('联系人电话', related='partner_id.main_contact')
    date = fields.Date('单据日期', default=lambda self: fields.Date.context_today(self), required=True)
    delivery_date = fields.Date('要求交货日期', default=lambda self: fields.Date.context_today(self), required=True)
    partner_area = fields.Selection(PARTNER_AREA, '客户区域', default='home', help='客户订购的区域')
    line_ids = fields.One2many('sell.apply.line', 'apply_id', ondelete='cascade',
                               help='销售申请单明细行')
    note = fields.Char('备注')
    goods_state = fields.Selection(string=u'产品状态', selection=[('old', '老款'), ('new', '新款')], default='old', copy=False)
    state = fields.Selection(STATE, '确认状态', help='单据状态', default='draft', track_visibility='always')
    approve_uid = fields.Many2one('res.users',
                                  '确认人',
                                  copy=False,
                                  ondelete='restrict',
                                  help='确认单据的人')
    approve_date = fields.Datetime('确认日期', copy=False)
    sell_order_count = fields.Integer('销售订单数量', compute='_compute_sell_order_count')



class SellApplyLine(models.Model):
    _name = 'sell.apply.line'
    _description = '销售申请单明细行'

    @api.depends('qty', 'price', 'tax_price', 'tax_rate')
    def _compute_all_amount(selfs):
        for self in selfs:
            self.tax_price = self.price * (1 + self.tax_rate / 100)
            self.amount = self.price * self.qty
            self.tax_amount = self.qty * self.tax_price * self.tax_rate / 100
            self.subtotal = (self.price * self.qty) + self.tax_amount

    apply_id = fields.Many2one('sell.apply', '销售申请订单', ondelete='cascade')
    ref = fields.Char('客户订单号', related='apply_id.ref')
    warehouse_id = fields.Many2one('warehouse', '仓库', help='关联仓库，购票物品存储某个仓库')
    goods_id = fields.Many2one('goods', '产品名称', ondelete='cascade')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    uom_id = fields.Many2one('uom', related='goods_id.uom_id', ondelete='cascade')
    qty = fields.Float('数量', digits='Quantity', )
    price = fields.Float('单价', digits='Price', )
    tax_price = fields.Float('含税单价', digits='Price', compute='_compute_all_amount')
    tax_rate = fields.Float('税率(%)', digits='Amount', )
    tax_amount = fields.Float('税额', digits='Amount', compute='_compute_all_amount')
    amount = fields.Float('金额', digits='Amount', compute='_compute_all_amount')
    subtotal = fields.Float('价税合计', digits='Amount', compute='_compute_all_amount')
    note = fields.Char('备注')
    state = fields.Selection(STATE, '确认状态', related='apply_id.state')