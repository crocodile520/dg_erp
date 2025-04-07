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
class SellOrderOut(models.Model):
    _name = 'sell.order.out'
    _description = '销售发货单'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'




    def button_done(self):
        self.ensure_one()
        '''回写发货数量到订单中'''
        if not self.line_ids:
            raise UserError('发货明细不允许为空')
        for line in self.line_ids:
            if float(line.qty) + float(line.line_id.out_qty) > line.line_id.qty:
                raise UserError("发货数量超过销售订单数量")
            line.line_id.write({
                "out_qty":float(line.qty) + float(line.line_id.out_qty)
            })
            if not line.warehouse_id.id:
                raise UserError('%s商品 仓库不允许为空' % line.goods_id.name)
            if line.warehouse_id.id == 1:
                if line.qty > line.ms1_qty:
                    raise UserError('%s商品发货库存数量不足' % line.goods_id.name)
            elif line.warehouse_id.id == 2:
                if line.qty > line.ms2_qty:
                    raise UserError('%s商品发货库存数量不足' % line.goods_id.name)
            elif line.warehouse_id.id == 3:
                if line.qty > line.ms3_qty:
                    raise UserError('%s商品发货库存数量不足' % line.goods_id.name)
            # if not line.weight:
            #     raise UserError('%s商品请填写重量' % line.goods_id.name)
        move_id = self.env['jl.move'].create({
            'sell_order_id': self.order_id.id,
            'order_out_id': self.id,
            'origin': self._name,
            'state': 'done',
            'line_in_ids': [(0, 0, {
                'warehouse_id': line.warehouse_id.id,
                'goods_id': line.goods_id.id,
                'goods_qty': line.qty,
                'type': 'out',
                'date': fields.Date.context_today(self),
                'cost_time': fields.Datetime.now(self),
                'state': 'done',
                'order_out_id': self.id,
            }) for line in self.line_ids]
        })
        self.order_id.button_out()
        for line in self.line_ids:
            if line.line_id.out_qty != line.line_id.qty:
                line.line_id.order_id.write({
                    'out_state':'part'
                })
            else:
                line.line_id.order_id.write({
                    'out_state': 'done'
                })
        self.create_reconciliation()
        self.write({
            'state':'done'
        })

    def button_draft(self):
        self.ensure_one()
        data_zero = [] #记录完全没有返回单line
        data_no = [] # 记录已经发货单了，但是又没有完全发完
        for line in self.line_ids:
            line.line_id.write({
                "out_qty":float(line.line_id.out_qty) - float(line.qty)
            })
        move_ids = self.env['jl.move'].search(
            [('sell_order_id', '=', self.order_id.id), ('order_out_id', '=', self.id), ('state', '=', 'done')])
        for move_id in move_ids:
            move_id.unlink()
        for line in self.line_ids:
            if line.line_id.out_qty == 0:
                data_zero.append(line)
            elif line.line_id.out_qty != line.line_id.qty:
                data_no.append(line)
            else:
                pass
        if len(self.line_ids) == len(data_zero):
            self.order_id.write({
                'out_state': 'draft'
            })
        elif len(self.line_ids) == len(data_no):
            self.order_id.write({
                'out_state': 'part'
            })
        else:
            self.order_id.write({
                'out_state': 'done'
            })
        # 撤销情况下如果有草稿单，并且删除草稿单
        ids = self.env['sell.order.out'].search([('order_id','=',self.order_id.id),('state','=','draft')])
        for id in ids:
            id.unlink()
        rec_ids = self.env['jl.reconciliation'].search([('out_id','=',self.id)])
        for rec_id in rec_ids:
            if rec_id.state == 'done':
                raise UserError('不允许删除已确认对账单')
            else:
                rec_id.unlink()
        self.write({
            'state': 'draft'
        })

    def button_cancel(self):
        self.ensure_one()
        self.write({
            'state': 'cancel'
        })


    def create_reconciliation(self):
        '''产生对账单'''
        rec_id = self.env['jl.reconciliation'].create({
            'order_id':self.order_id.id,
            'out_id':self.id,
            'ref':self.ref,
            'partner_id':self.partner_id.id,
            'delivery_number':self.delivery_number
        })
        rec_id.write({
            'line_ids':[(0,0,{
                'goods_id':line.goods_id.id,
                'weight':line.weight,
                'qty':line.qty,
                'amount':line.amount
            }) for line in self.line_ids]
        })

    def action_rec_view(self):
        self.ensure_one()
        action = {
            'name': '对账单',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'jl.reconciliation',
            'view_id': False,
            'target': 'current',
        }

        form_view = self.env.ref('jinling_finance.jl_reconciliation_view_form').id
        tree_view = self.env.ref('jinling_finance.jl_reconciliation_view_tree').id

        if self.rec_count > 1:
            action['domain'] = "[('out_id','=',%s)]" % self.id
            action['view_mode'] = 'tree,form'
            action['views'] = [(tree_view, 'tree'),(form_view, 'form')]
        elif self.rec_count == 1:
            rec_id = self.env['jl.reconciliation'].search([('out_id', '=', self.id)])
            action['views'] = [(form_view, 'form')]
            action['res_id'] = rec_id and rec_id.id or False
        return action

    def _compute_rec_count(selfs):
        for self in selfs:
            self.rec_count = self.env['jl.reconciliation'].search_count([('out_id','=',self.id)])

    @api.depends('line_ids.amount')
    def _compute_total_amount(self):
        amount_total = 0
        self.amount_total = 0
        for line in self.line_ids:
            amount_total += line.amount
        self.amount_total = amount_total

    def rmb_upper(self, value):
        """
        人民币大写
        :param value: 数字金额
        :return: 中文大写金额
        """
        map = ["零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖"]
        unit = ["元", "拾", "佰", "仟", "万", "拾", "佰", "仟", "亿"]

        # 处理小数，将数字分割成整数和小数部分
        str_value = "%.2f" % value
        int_value, decimal_value = str_value.split('.')

        # 处理整数部分
        int_str = ''
        int_len = len(int_value)
        for i, n in enumerate(int_value):
            n = int(n)
            if n != 0:
                int_str += map[n] + unit[int_len - i - 1]
            else:
                if int_str and not int_str.endswith('零'):
                    int_str += '零'

        # 处理小数部分
        decimal_str = ''
        if decimal_value:
            jiao = int(decimal_value[0])
            fen = int(decimal_value[1])
            if jiao:
                decimal_str += map[jiao] + '角'
            if fen:
                decimal_str += map[fen] + '分'

        # 组合结果
        if not int_str:
            int_str = '零元'
        if not decimal_str:
            if int_str == '零元':
                return '零元整'
            return int_str + '整'
        return int_str + decimal_str

    @api.depends('amount_total')
    def _compute_amount_total_words(self):
        """
        计算金额大写
        """
        for record in self:
            if record.amount_total:
                try:
                    record.amount_total_words = self.rmb_upper(record.amount_total)
                except Exception:
                    record.amount_total_words = '零元整'
            else:
                record.amount_total_words = '零元整'

    def action_get_attachment_view(self):
        """附件上传动作视图"""
        self.ensure_one()
        res = self.env.ref("base.action_attachment").sudo().read()[0]
        res["domain"] = [("res_model", "=", self._name), ("res_id", "in", self.ids)]
        res["context"] = {"default_res_model": self._name, "default_res_id": self.id}
        return res

    def _compute_attachment_number(self):
        """附件上传"""
        attachment_data = self.env["ir.attachment"].read_group(
            [("res_model", "=", self._name), ("res_id", "in", self.ids)],
            ["res_id"],
            ["res_id"],
        )
        attachment = dict(
            (data["res_id"], data["res_id_count"]) for data in attachment_data
        )
        for expense in self:
            expense.attachment_number = attachment.get(expense.id, 0)

    name = fields.Char('单据编号',
                       index=True,
                       copy=False,
                       default=lambda self: self.env['ir.sequence'].next_by_code('sell.order.out'),
                       help="销售发货单的唯一编号，当创建时它会自动生成下一个编号。")
    user_id = fields.Many2one(
        'hr.employee',
        '销售员',
        ondelete='restrict',
        states=READONLY_STATES,
        readonly=False,
        default=lambda self: self.env.user.employee_id.id,
        help='销售员',
    )
    ref = fields.Char('客户订单号', track_visibility='always')
    delivery_number = fields.Char('送货单号', track_visibility='always')
    partner_id = fields.Many2one('partner', '客户')
    order_id = fields.Many2one('sell.order', '销售订单', ondelete='cascade', help='销售订单')
    partner_code = fields.Char('客户编码', related='partner_id.code')
    main_mobile = fields.Char('联系人', related='partner_id.main_mobile')
    main_contact = fields.Char('联系人电话', related='partner_id.main_contact')
    address = fields.Char('送货地址', related='partner_id.address')
    date = fields.Date('单据日期', default=lambda self: fields.Date.context_today(self), required=True)
    delivery_date = fields.Date('交货日期',default=lambda self: fields.Date.context_today(self), required=True)
    line_ids = fields.One2many('sell.order.out.line', 'out_id', ondelete='cascade',
                               help='销售发货单明细行')
    note = fields.Char('备注')
    state = fields.Selection(STATE, '确认状态', help='单据状态', default='draft', track_visibility='always')
    rec_count = fields.Integer('对账单数量',compute='_compute_rec_count')
    amount_total = fields.Float('总金额', digits='Amount', compute='_compute_total_amount')
    carriage = fields.Float('运费', digits='Amount')
    amount_total_words = fields.Char('大写金额',compute='_compute_amount_total_words')
    shop_id = fields.Many2one('sell.shop', '店铺', ondelete='cascade', help='销售店铺')
    attachment_number = fields.Integer(
        compute="_compute_attachment_number", string="附件上传"
    )


class SellOrderOutLine(models.Model):
    _name = 'sell.order.out.line'
    _description = '销售发货明细'

    @api.depends('goods_id')
    def _compute_warehouse_balance(selfs):
        cr = selfs._cr
        goods_ids = selfs.goods_id.ids
        balance_qty = {}
        if any(goods_ids):
            cr.execute("""
                            select * from jl_warehouse_balance_report
                            where goods_id in ({goods_id})
                            """.format(**{'goods_id': ','.join([str(id) for id in goods_ids])}))

            for line in cr.dictfetchall():
                balance_qty.update({
                    line['goods_id']: {'ms1_qty': line['ms1_qty'], 'ms2_qty': line['ms2_qty'],'ms3_qty': line['ms3_qty']}
                })
        for self in selfs:
            key = self.goods_id.id
            qty_dict = balance_qty[key] if key in balance_qty.keys() else 0
            self.ms1_qty = qty_dict['ms1_qty']
            self.ms2_qty = qty_dict['ms2_qty']
            self.ms3_qty = qty_dict['ms3_qty']

    @api.depends('qty', 'price', 'tax_price', 'tax_rate')
    def _compute_all_amount(selfs):
        for self in selfs:
            self.tax_price = self.price * (1 + self.tax_rate / 100)
            self.amount = self.price * self.qty
            self.tax_amount = self.qty * self.tax_price * self.tax_rate / 100
            self.subtotal = (self.price * self.qty) + self.tax_amount



    line_id = fields.Many2one('sell.order.line',
                              '销售订单明细行',
                              states=READONLY_STATES,
                              copy=True,
                              help='销售订单明细行')
    out_id = fields.Many2one('sell.order.out', '销售发货单', ondelete='cascade')
    ref = fields.Char('客户订单号', related='out_id.ref')
    goods_id = fields.Many2one('goods', '产品名称', ondelete='cascade')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    warehouse_id = fields.Many2one('warehouse', '仓库', help='关联仓库，购票物品存储某个仓库')
    delivery_date = fields.Date('交货日期',related='out_id.delivery_date', required=True)
    uom_id = fields.Many2one('uom', related='goods_id.uom_id', ondelete='cascade')
    price = fields.Float('单价', digits='Price', default=0)
    tax_price = fields.Float('含税单价', digits='Price', compute='_compute_all_amount')
    tax_rate = fields.Float('税率(%)', digits='Amount', default=0)
    tax_amount = fields.Float('税额', digits='Amount', compute='_compute_all_amount')
    amount = fields.Float('金额', digits='Amount', compute='_compute_all_amount')
    subtotal = fields.Float('价税合计', digits='Amount', compute='_compute_all_amount')
    weight = fields.Float('重量(KG)', digits='Quantity', )
    qty = fields.Float('发货数量', digits='Quantity', )
    ms1_qty = fields.Float('成品仓库存数量', digits='Quantity', track_visibility='always',
                           compute='_compute_warehouse_balance')
    ms2_qty = fields.Float('PCB板仓库存数量', digits='Quantity', track_visibility='always',
                           compute='_compute_warehouse_balance')
    ms3_qty = fields.Float('原材料仓库存数量', digits='Quantity', track_visibility='always',
                           compute='_compute_warehouse_balance')
    note = fields.Char('备注', help='如果特殊情况请备注')
    state = fields.Selection(STATE, '确认状态', related='out_id.state')

class JlMoveLine(models.Model):
    _inherit = 'jl.move.line'

    order_out_id = fields.Many2one('sell.order.out','销售发货单',ondelete='cascade',help='绑定销售发货单')
