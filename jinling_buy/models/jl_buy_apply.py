from odoo import fields, api, models
from odoo.exceptions import UserError

STATE = [
    ('draft', '草稿'),
    ('done', '完成'),
    ('cancel', '作废'),
]


class JlBuyApply(models.Model):
    _name = 'jl.buy.apply'
    _description = '采购申请单'
    _inherit = ['mail.thread']

    def button_done(self):
        '''确认后产生采购订单'''
        self.ensure_one()
        if self.state == 'done':
            raise UserError('单据已经确认，请勿重复确认')
        if not self.line_ids:
            raise UserError('请填写采购申请明细行')
        for line in self.line_ids:
            if not line.warehouse_id:
                raise UserError("%s 商品仓库不能为空" % line.goods_id.name)
        order_id = self.env['jl.buy.order'].create({
            'apply_user_id': self.env.user.employee_id.id,
            'apply_id': self.id,
            'supplier_id': self.supplier_id.id,
            'is_tax': self.is_tax,
        })
        order_id.write({
            'line_ids': [(0, 0, {
                'goods_id': line.goods_id.id,
                'warehouse_id': line.warehouse_id.id,
                'qty': line.qty,
                'price': line.price,
                'tax_price': line.tax_price,
                'tax_rate': line.tax_rate,
            }) for line in self.line_ids]
        })
        self.write({
            'state': 'done'
        })

    def button_draft(self):
        self = self.sudo()
        self.ensure_one()
        if self.state == 'draft':
            raise UserError('请不要重复撤销')
        ids = self.env['jl.buy.order'].search([('apply_id', '=', self.id)])
        if any(ids):
            for id in ids:
                if id.state != 'draft':
                    raise UserError('不可以删除已经确定的采购订单')
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

    def action_buy_order_view(self):
        self.ensure_one()
        action = {
            'name': '采购订单',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'jl.buy.order',
            'view_id': False,
            'target': 'current',
        }

        form_view = self.env.ref('jinling_buy.jl_buy_order_view_form').id
        tree_view = self.env.ref('jinling_buy.jl_buy_order_view_tree').id

        if self.buy_apply_count > 1:
            action['domain'] = "[('apply_id','=',%s)]" % self.id
            action['view_mode'] = 'tree,form'
            action['views'] = [(tree_view, 'tree'), (form_view, 'form')]
        elif self.buy_apply_count == 1:
            order_id = self.env['jl.buy.order'].search([('apply_id', '=', self.id)])
            action['views'] = [(form_view, 'form')]
            action['res_id'] = order_id and order_id.id or False
        return action

    def _compute_buy_apply_count(selfs):
        for self in selfs:
            self.buy_apply_count = self.env['jl.buy.order'].search_count([('apply_id', '=', self.id)])

    name = fields.Char('单据编号',
                       index=True,
                       copy=False,
                       default=lambda self: self.env['ir.sequence'].next_by_code('jl.buy.apply'),
                       help="采购申请订单的唯一编号，当创建时它会自动生成下一个编号。")
    date = fields.Date('单据日期', default=lambda self: fields.Date.context_today(self), required=True)
    user_id = fields.Many2one('hr.employee', '申请人', default=lambda self: self.env.user.employee_id.id,
                              ondelete='cascade', requierd=True, track_visibility='onchange')
    supplier_id = fields.Many2one('supplier', '供应商', help='购货申请需要采购的供应商')
    buy_apply_count = fields.Integer('采购订单数量', compute='_compute_buy_apply_count')
    line_ids = fields.One2many('jl.buy.apply.line', 'buy_apply_id', ondelete='cascade',
                               help='采购申请单明细行')
    state = fields.Selection(STATE, '确认状态', help='单据状态', default='draft', track_visibility='always')
    is_tax = fields.Boolean('是否含税')
    note = fields.Char('备注')


class JlBuyApplyLine(models.Model):
    _name = 'jl.buy.apply.line'
    _description = '采购申请单明细'

    @api.depends('qty', 'price', 'tax_price', 'tax_rate')
    def _compute_all_amount(selfs):
        for self in selfs:
            self.tax_price = round(self.price * (1 + (self.tax_rate / 100)),4)
            self.amount = self.price * self.qty
            self.subtotal = self.qty * self.tax_price
            self.tax_amount = self.subtotal - self.amount

    @api.depends('goods_id')
    def _compute_goods_price(self):
        cr = self._cr
        ids = self.goods_id.ids
        stock = {}
        if any(ids):
            cr.execute("""
                        select
                              goods_id,
                              price,
                              tax_rate
                            from
                              jl_buy_price_strategy
                            where
                            active = TRUE
                              and state = 'done' and goods_id in ({ids})

                    """.format(**{'ids': ','.join([str(id) for id in ids])}))
            for line in cr.dictfetchall():
                stock.update({
                    line['goods_id']: [line['price'],line['tax_rate']]})
        for _d in self:
            _d.price = 0
            _d.tax_rate = 0
            if _d.goods_id.id:
                if _d.goods_id.id in stock.keys():
                    _d.price = stock[_d.goods_id.id][0]
                    _d.tax_rate = stock[_d.goods_id.id][1]

    buy_apply_id = fields.Many2one('jl.buy.apply', '采购申请单', index=True, ondelete='cascade')
    goods_id = fields.Many2one('goods', '商品', ondelete='cascade', help='购货商品')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    uom_id = fields.Many2one('uom', related='goods_id.uom_id', ondelete='cascade')
    goods_class_id = fields.Many2one('goods.class', '商品分类', related='goods_id.goods_class_id', ondelete='cascade',
                                     help='分类名称')
    warehouse_id = fields.Many2one('warehouse', '仓库', help='关联仓库，购票物品存储某个仓库')
    qty = fields.Float('数量', digits='Quantity', )
    price = fields.Float('单价', digits='quantity', compute='_compute_goods_price')
    tax_price = fields.Float('含税单价', digits='Price', compute='_compute_all_amount')
    tax_rate = fields.Float('税率(%)', digits='Amount', )
    tax_amount = fields.Float('税额', digits='Amount', compute='_compute_all_amount')
    amount = fields.Float('金额', digits='Amount', compute='_compute_all_amount')
    subtotal = fields.Float('价税合计', digits='Amount', compute='_compute_all_amount')
    note = fields.Char('备注', related='goods_id.remark')
    state = fields.Selection(STATE, '确认状态', related='buy_apply_id.state')
