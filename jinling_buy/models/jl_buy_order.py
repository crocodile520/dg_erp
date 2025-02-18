from odoo import fields,api,models
from odoo.exceptions import UserError

TYPE = [
    ('buy','购货'),
    ('return','退货'),
]
ORDER_STATE = [
    ('not_stock','未入库'),
    ('done_stock','全部入库'),
    ('part_stock','部分入库'),
]

STATE = [
    ('draft','草稿'),
    ('done','完成'),
    ('cancel','作废'),
]
class JlBuyOrder(models.Model):
    _name = 'jl.buy.order'
    _description = '采购订单'
    _inherit = ['mail.thread']


    def get_move_line(self, line,move_id):
        '''返回采购入库行'''
        self.ensure_one()
        #防止小数点超长影响
        if round(line.qty,0) - round(line.buy_qty,0) < 0:
            raise UserError('商品%s入库数量超过采购订单数量%s' % (line.goods_id.name,line.qty - line.buy_qty))
        else:
            qty = line.qty - line.buy_qty
        return {
            'goods_id': line.goods_id.id,
            'order_line_id': line.id,
            'move_id': move_id.id,
            'goods_qty': qty,
            'warehouse_id': line.warehouse_id.id,
            'price': line.price,
            'tax_price': line.tax_price,
            'tax_rate': line.tax_rate,
            'type': 'in',
            'date': fields.Date.context_today(self),
            'cost_time': fields.Datetime.now(self),
        }

    def create_warehousing(self):
        '''产生采购入库订单'''
        warehousing_line = []
        move_id = self.env['jl.move'].create({
            'order_id': self.id,
            'origin': self._name,
            'supplier_id': self.supplier_id.id,
        })

        for line in self.line_ids:
            if line.qty - line.buy_qty > 0 :
                warehousing_line.append(self.get_move_line(line,move_id))
            else:
                continue
        if len(warehousing_line):
            warehousing_id = self.env['jl.buy.warehousing'].create({
                'order_id': self.id,
                'buy_move_id': move_id.id,
                'supplier_id': self.supplier_id.id,
            })
            warehousing_id.write({
                'line_ids': [(0, 0,line) for line in warehousing_line]
            })

    def button_done(self):
        self.ensure_one()
        if self.state == 'done':
            raise UserError('单据已经确认，请勿重复确认')
        if not self.line_ids:
            raise UserError('请填写采购申请明细行')
        self.create_warehousing()
        self.write({
            'state':'done'
        })


    def button_draft(self):
        self = self.sudo()
        self.ensure_one()
        if self.state == 'draft':
            raise UserError('请不要重复撤销')
        ids = self.env['jl.buy.warehousing'].search([('order_id', '=', self.id)])
        if any(ids):
            for id in ids:
                if id.state != 'draft':
                    raise UserError('不可以删除已经确定的采购入库订单')
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

    def action_buy_warehousing_view(self):
        self.ensure_one()
        action = {
            'name': '采购入库订单',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'jl.buy.warehousing',
            'view_id': False,
            'target': 'current',
        }

        form_view = self.env.ref('jinling_buy.jl_buy_warehousing_view_form').id
        tree_view = self.env.ref('jinling_buy.jl_buy_warehousing_view_tree').id

        if self.buy_warehousing_count > 1:
            action['domain'] = "[('order_id','=',%s),('is_return','=',False)]" % self.id
            action['view_mode'] = 'tree,form'
            action['views'] = [(tree_view, 'tree'),(form_view, 'form')]
        elif self.buy_warehousing_count == 1:
            warehousing_id = self.env['jl.buy.warehousing'].search([('order_id', '=', self.id),('is_return','=',False)])
            action['views'] = [(form_view, 'form')]
            action['res_id'] = warehousing_id and warehousing_id.id or False
        return action

    def _compute_buy_warehousing_count(selfs):
        for self in selfs:
            self.buy_warehousing_count = self.env['jl.buy.warehousing'].search_count([('order_id','=',self.id),('is_return','=',False)])


    name = fields.Char('单据编号',
                       index=True,
                       copy=False,
                       default=lambda self: self.env['ir.sequence'].next_by_code('jl.buy.order'),
                       help="采购订单的唯一编号，当创建时它会自动生成下一个编号。")
    date = fields.Date('单据日期', default=lambda self: fields.Date.context_today(self), required=True)
    user_id = fields.Many2one('hr.employee', '采购员', default=lambda self: self.env.user.employee_id.id, ondelete='cascade', requierd=True,
                              )
    apply_user_id = fields.Many2one('hr.employee', '采购申请人', default=lambda self: self.env.user.employee_id.id, ondelete='cascade', requierd=True,
                              )
    apply_id = fields.Many2one('jl.buy.apply','采购申请单',index=True, readonly=True, help='关联采购申请单ID')
    delivery_date = fields.Date('要求交货日期', default=lambda self: fields.Date.context_today(self), required=True)
    supplier_id = fields.Many2one('supplier', '供应商', help='供应商')
    main_mobile = fields.Char('联系人',related='supplier_id.main_mobile',ondelete='cascade')
    main_contact = fields.Char('联系人电话',related='supplier_id.main_contact',ondelete='cascade')
    address = fields.Char('联系人地址',related='supplier_id.address',ondelete='cascade')
    type = fields.Selection(TYPE,'类型',default='buy',help='采购订单可以购货或者退货')
    order_state = fields.Selection(ORDER_STATE,'入库状态',default='not_stock',help='货物入库状态')
    line_ids = fields.One2many('jl.buy.order.line','order_id','采购订单明细行',ondelete='cascade',help='关联采购订单明细行')
    state = fields.Selection(STATE, '确认状态', help='单据状态', default='draft',track_visibility='always')
    note = fields.Char('备注')
    buy_warehousing_count = fields.Integer('采购入库订单数量', compute='_compute_buy_warehousing_count')


class JlBuyOrderLine(models.Model):
    _name = 'jl.buy.order.line'
    _description = '采购订单明细'

    @api.depends('qty', 'price', 'tax_price', 'tax_rate')
    def _compute_all_amount(selfs):
        for self in selfs:
            self.tax_price = self.price * (1 + (self.tax_rate / 100))
            self.amount = self.price * self.qty
            self.subtotal = self.qty * (1 + (self.tax_rate / 100)) * self.price
            self.tax_amount = self.subtotal - self.amount

    order_id = fields.Many2one('jl.buy.order','采购订单',index=True, ondelete='cascade')
    delivery_date = fields.Date('要求交货日期', related='order_id.delivery_date', required=True)
    warehouse_id = fields.Many2one('warehouse', '仓库', help='关联仓库，购票物品存储某个仓库')
    goods_id = fields.Many2one('goods', '商品', ondelete='cascade', help='购货商品')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    uom_id = fields.Many2one('uom', related='goods_id.uom_id', ondelete='cascade')
    qty = fields.Float('数量', digits='Quantity', )
    buy_qty = fields.Float('已入库数量', digits='Quantity', )
    price = fields.Float('单价', digits='Price', )
    tax_price = fields.Float('含税单价', digits='Price', compute='_compute_all_amount')
    tax_rate = fields.Float('税率(%)', digits='Amount', )
    tax_amount = fields.Float('税额', digits='Amount', compute='_compute_all_amount')
    amount = fields.Float('金额', digits='Amount', compute='_compute_all_amount')
    subtotal = fields.Float('价税合计', digits='Amount', compute='_compute_all_amount')
    note = fields.Char('备注')
    state = fields.Selection(STATE, '确认状态', related='order_id.state')

