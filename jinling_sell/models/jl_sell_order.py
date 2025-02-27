from odoo import api,fields,models
from odoo.exceptions import UserError

# 字段只读状态
READONLY_STATES = {
    'done': [('readonly', True)],
    'onchange': [('readonly', True)],
    'stop': [('readonly', True)],
    'cancel': [('readonly', True)],
}

ORDER_TYPE = [
    ('PCBA','PCBA'),
    ('materials','材料'),
    ('CP','成品'),
    ('BCP','半成品'),
]

PARTNER_AREA = [
    ('abroad','国外'),
    ('home','国内'),
]

STATE = [
    ('draft','草稿'),
    ('review','评审中'),
    ('done','完成'),
    ('cancel','作废'),
]

OUT_STATE = [
    ('draft','未发货'),
    ('done','全部发货'),
    ('part','部分发货'),
]


class SellOrder(models.Model):
    _name = 'sell.order'
    _description = '销售订单'
    _inherit = ['mail.thread']



    def button_done(self):
        self.ensure_one()
        if self.state == 'review':
            ids = self.env['sell.order.review'].search([('order_id', '=', self.id),('state','=','draft')])
            if len(ids):
                raise UserError('销售评审单未确认，当前无法确认单据')
            # self.create_mes_plm()#销售订单产生生产工单暂时取消
            self.write({
                'state': 'done',
                'approve_uid': self.env.uid,
                'approve_date': fields.Datetime.now(self),
            })
        else:
            if self.goods_state == 'new':
                ids = self.env['sell.order.review'].search([('order_id', '=', self.id), ('state', 'in', ('draft','done'))])
                if not len(ids):
                    raise UserError('当前款式为新款，需要产生销售评审单，当前无法确认单据')
            # self.create_mes_plm()
            self.write({
                'state': 'done',
                'approve_uid': self.env.uid,
                'approve_date': fields.Datetime.now(self),
            })


    def button_draft(self):
        self.ensure_one()
        out_ids = self.env['sell.order.out'].search([('order_id','=',self.id)])
        review_ids = self.env['sell.order.review'].search([('order_id', '=', self.id)])
        plm_ids = self.env['jl.mes.plm'].search([('order_id','=',self.id)])
        eng_ids = self.env['jl.engineering'].search([('order_id','=',self.id)])
        pro_ids = self.env['jl.mes.plm.programme'].search([('order_id','=',self.id)])
        for pro_id in pro_ids:
            pro_id.unlink()
        if len(eng_ids.filtered(lambda _l: _l.state == 'done').ids) > 0:
            raise UserError('工程工单已经确认了无法撤销')
        else:
            for eng_id in eng_ids:
                eng_id.unlink()
        if len(out_ids.filtered(lambda _l: _l.state == 'done').ids) > 0:
            raise UserError('发货单已经确认了无法撤销')
        else:
            for out_id in out_ids:
                out_id.unlink()
        if len(review_ids.filtered(lambda _l: _l.state == 'done').ids) > 0:
            raise UserError('评审单已经确认了无法撤销')
        else:
            for review_id in review_ids:
                review_id.unlink()
        if len(plm_ids.filtered(lambda _l: _l.state == 'done').ids) > 0:
            raise UserError('工单已经确认了无法撤销')
        else:
            for plm_id in plm_ids:
                plm_id.unlink()
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

    def button_out(self):
        '''产生销售发货单'''
        self.ensure_one()
        data = []
        if not len(self.line_ids):
            raise UserError('发货明细行不可以为空')
        for line in self.line_ids:
            if round(line.qty,2) - round(line.out_qty,2) > 0 :
                data.append(self.get_order_line(line))
        if data:
            order_out_id = self.env['sell.order.out'].create({
                'user_id':self.user_id.id,
                'ref':self.ref,
                'partner_id':self.partner_id.id,
                'order_id':self.id,
            })
            order_out_id.write({
                "line_ids":[(0,0,record) for record in data]
            })

    def get_order_line(self,line):
        self.ensure_one()
        if round(line.qty,2) - round(line.out_qty) < 0:
            raise UserError('发货数量大于销售订单数量')
        else:
            qty = round(line.qty,2) - round(line.out_qty,2)
        return {
            'goods_id': line.goods_id.id,
            'qty': qty,
            'price':line.price,
            'tax_rate':line.tax_rate,
            'warehouse_id': line.warehouse_id.id,
            'delivery_date': line.delivery_date,
            'line_id': line.id,
        }

    def action_sell_order_out_view(self):
        self.ensure_one()
        action = {
            'name': '销售发货单',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sell.order.out',
            'view_id': False,
            'target': 'current',
        }

        form_view = self.env.ref('jinling_sell.sell_order_out_view_form').id
        tree_view = self.env.ref('jinling_sell.sell_order_out_view_tree').id

        if self.order_out_count > 1:
            action['domain'] = "[('order_id','=',%s)]" % self.id
            action['view_mode'] = 'tree,form'
            action['views'] = [(tree_view, 'tree'),(form_view, 'form')]
        elif self.order_out_count == 1:
            order_id = self.env['sell.order.out'].search([('order_id', '=', self.id)])
            action['views'] = [(form_view, 'form')]
            action['res_id'] = order_id and order_id.id or False
        return action


    def _compute_order_out_count(selfs):
        for self in selfs:
            self.order_out_count = self.env['sell.order.out'].search_count([('order_id','=',self.id)])


    def create_order_review(self):
        '''创建评审单'''
        self.ensure_one()
        for line in self.line_ids:
            self.env['sell.order.review'].create({
                'user_id':self.user_id.id,
                'company_id':self.company_id.id,
                'currency_id':self.currency_id.id,
                'warehouse_id': line.warehouse_id.id,
                'order_id': self.id,
                'ref':self.ref,
                'partner_id':self.partner_id.id,
                'delivery_date':self.delivery_date,
                'line_ids':[(0,0,{
                    'goods_id':line.goods_id.id,
                    'qty':line.qty
                })]
            })

        self.write({
            'state': 'review'
        })

    def action_sell_order_review_view(self):
        self.ensure_one()
        action = {
            'name': '销售评审单',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sell.order.review',
            'view_id': False,
            'target': 'current',
        }

        form_view = self.env.ref('jinling_sell.sell_order_review_view_form').id
        tree_view = self.env.ref('jinling_sell.sell_order_review_view_tree').id

        if self.order_review_count > 1:
            action['domain'] = "[('order_id','=',%s)]" % self.id
            action['view_mode'] = 'tree,form'
            action['views'] = [(tree_view, 'tree'),(form_view, 'form')]
        elif self.order_review_count == 1:
            order_id = self.env['sell.order.review'].search([('order_id', '=', self.id)])
            action['views'] = [(form_view, 'form')]
            action['res_id'] = order_id and order_id.id or False
        return action


    def create_mes_plm(self):
        '''通过销售订单/销售评审单确认后产生工单/工程工单'''
        for line in self.line_ids:
            plm_id = self.env['jl.mes.plm'].create({
                'order_id':self.id,
                'goods_id':line.goods_id.id,
                'warehouse_id': line.warehouse_id.id,
                'qty':line.qty,
                'delivery_date':line.delivery_date,
            })
            bom_id = self.env['goods.bom'].search([('goods_id','=',line.goods_id.id)],limit=1)
            plm_id.write({
                'line_ids': [(0, 0, {
                    'goods_id':bom_line.goods_id.id,
                    'qty':bom_line.qty * line.qty
                }) for bom_line in bom_id.line_ids]
            })
            plm_id.line_ids.get_neck_qty()
            eng_id = self.env['jl.engineering'].create({
                'plm_id': plm_id.id,
                'order_id': self.id,
                'goods_id': line.goods_id.id,
                'qty': line.qty,
                'delivery_date': line.delivery_date,
            })
            plm_id.write({
                'eng_id':eng_id.id
            })
            '''创建生产计划单'''
            self.env['jl.mes.plm.programme'].create({
                'plm_id': plm_id.id,
                'order_id': self.id
            })



    def _compute_order_review_count(selfs):
        for self in selfs:
            self.order_review_count = self.env['sell.order.review'].search_count([('order_id','=',self.id)])

    name = fields.Char('单据编号',
                       index=True,
                       copy=False,
                       default=lambda self:self.env['ir.sequence'].next_by_code('sell.order'),
                       help="销售订单的唯一编号，当创建时它会自动生成下一个编号。")
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
    partner_id = fields.Many2one('partner','客户')
    apply_id = fields.Many2one('sell.apply','销售申请单',ondelete='cascade',help='销售申请单')
    partner_code = fields.Char('客户编码', related='partner_id.code')
    main_mobile = fields.Char('联系人', related='partner_id.main_mobile')
    main_contact = fields.Char('联系人电话', related='partner_id.main_contact')
    address = fields.Char('送货地址', related='partner_id.address')
    date = fields.Date('单据日期', default=lambda self: fields.Date.context_today(self), required=True)
    delivery_date = fields.Date('交货日期', default=lambda self: fields.Date.context_today(self), required=True)
    order_type = fields.Selection(ORDER_TYPE,'订单类型',default='CP', help='购货订单的类型')
    partner_area = fields.Selection(PARTNER_AREA,'客户区域',default='home',help='客户订购的区域')
    line_ids = fields.One2many('sell.order.line','order_id',ondelete='cascade',
                               help='销售订单明细行')
    note = fields.Char('备注')
    goods_state = fields.Selection(string=u'产品状态', selection=[('old', '老款'), ('new', '新款')], related='apply_id.goods_state',
                                   copy=False)
    state = fields.Selection(STATE, '确认状态', help='单据状态', default='draft',track_visibility='always')
    out_state = fields.Selection(OUT_STATE, '发货状态', help='发货状态', default='draft',track_visibility='always')
    order_out_count = fields.Integer('发货单数量',compute='_compute_order_out_count')
    order_review_count = fields.Integer('评审单数量',compute='_compute_order_review_count')
    approve_uid = fields.Many2one('res.users',
                                  '确认人',
                                  copy=False,
                                  ondelete='restrict',
                                  help='确认单据的人')
    approve_date = fields.Datetime('确认日期', copy=False)




class SellOrderLine(models.Model):
    _name = 'sell.order.line'
    _description = '销售订单明细行'


    @api.depends('qty','price','tax_price','tax_rate')
    def _compute_all_amount(selfs):
        for self in selfs:
            self.tax_price = self.price * (1 + (self.tax_rate / 100))
            self.amount = self.price * self.qty
            self.subtotal = self.qty * self.tax_price
            self.tax_amount = self.subtotal - self.amount

    @api.onchange('goods_id')
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
                                  jl_sell_price_strategy
                                where
                                active = TRUE
                                  and state = 'done' and goods_id in ({ids})

                        """.format(**{'ids': ','.join([str(id) for id in ids])}))
            for line in cr.dictfetchall():
                stock.update({
                    line['goods_id']: [line['price'], line['tax_rate']]})
        for _d in self:
            _d.price = 0
            _d.tax_rate = 0
            if _d.goods_id.id:
                if _d.goods_id.id in stock.keys():
                    _d.price = stock[_d.goods_id.id][0]
                    _d.tax_rate = stock[_d.goods_id.id][1]

    order_id = fields.Many2one('sell.order','销售订单',ondelete='cascade')
    ref = fields.Char('客户订单号',related='order_id.ref')
    warehouse_id = fields.Many2one('warehouse', '仓库', help='关联仓库，购票物品存储某个仓库')
    goods_id = fields.Many2one('goods','产品名称',ondelete='cascade')
    describe = fields.Char('产品名称',related='goods_id.describe',ondelete='cascade')
    specs = fields.Char('规格型号',related='goods_id.specs',ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    delivery_date = fields.Date('交货日期', related='order_id.delivery_date', required=True)
    uom_id = fields.Many2one('uom',related='goods_id.uom_id',ondelete='cascade')
    qty = fields.Float('数量',digits='Quantity',)
    out_qty = fields.Float('已发货数量',digits='Quantity',default=0)
    price = fields.Float('单价',digits='Price')
    tax_price = fields.Float('含税单价',digits='Price',compute='_compute_all_amount')
    tax_rate = fields.Float('税率(%)',digits='Amount',default=0)
    tax_amount = fields.Float('税额',digits='Amount',compute='_compute_all_amount')
    amount = fields.Float('金额',digits='Amount',compute='_compute_all_amount')
    subtotal = fields.Float('价税合计',digits='Amount',compute='_compute_all_amount')
    note = fields.Char('备注',help='如果特殊情况请备注')
    state = fields.Selection(STATE, '确认状态', related='order_id.state')
