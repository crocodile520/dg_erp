from odoo import fields,models,api
from odoo.exceptions import UserError

STATE = [
    ('draft','草稿'),
    ('done','完成'),
    ('rejection','拒收'),
    ('cancel','作废'),
]

class JlBuyWarehousing(models.Model):
    _name = 'jl.buy.warehousing'
    _description = '采购入库单'
    _inherits = {'jl.move': 'buy_move_id'}
    _inherit = ['mail.thread']



    def button_payment(self):
        '''创建付款申请单'''
        self.ensure_one()
        # ids = self.env['jl.buy.payment.apply'].search([('warehousing_id','=',self.id)])
        # if any(ids):
        #     raise UserError('付款申请单已存在，无需重复申请')
        apply_id = self.env['jl.buy.payment.apply'].create({
            'order_id':self.order_id.id,
            'warehousing_id':self.id,
            'supplier_id':self.supplier_id.id,
        })
        apply_id.write({
            'line_ids':[(0,0,{
                'goods_id':line.goods_id.id,
                'qty':line.goods_qty,
                'price':line.price,
                'tax_price':line.tax_price,
                'tax_rate':line.tax_rate,
                'tax_amount':line.tax_amount,
                'amount':line.amount,
                'subtotal':line.subtotal,
            })for line in self.line_ids]
        })

    def button_done(self):
        self.ensure_one()
        data = []
        if self.state == 'done':
            raise UserError('单据已经确认，请勿重复确认')
        if not self.line_ids:
            raise UserError('请填写采购入库单明细行')
        '''回写入库数量到采购订单中'''
        for line in self.line_ids:
            if line.goods_qty < 0:
                raise UserError('入库数量不可以为0')
            if line.order_line_id.buy_qty + line.goods_qty > line.order_line_id.qty:
                raise UserError('入库数量不能大于采购订单数量')
            line.order_line_id.write({
                'buy_qty':line.goods_qty +line.order_line_id.buy_qty
            })
        for line in self.line_ids:
            if line.order_line_id.buy_qty != line.order_line_id.qty:
                data.append(line)
        if len(data):
            self.order_id.order_state = 'part_stock'
        else:
            self.order_id.order_state = 'done_stock'
        self.order_id.create_warehousing()
        self.write({
            'state':'done'
        })
        self.buy_move_id.write({
            'state':'done'
        })
        for record in self.line_ids:
            record.write({
                'state':'done'
            })


    def button_draft(self):
        self.ensure_one()
        zero_data = []
        if self.state == 'draft':
           raise UserError('目前状态是草稿状态，请勿重复撤销！')
        '''撤销时回写采购订单入库数量'''
        for line in self.line_ids:
            if line.goods_qty < 0:
                raise UserError('撤销时，入库数量不能为负数')
            line.order_line_id.write({
                'buy_qty':line.order_line_id.buy_qty - line.goods_qty
            })
        for line in self.order_id.line_ids:
            if line.buy_qty == 0:
                zero_data.append(line)
        if len(zero_data) == len(self.order_id.line_ids):
            self.order_id.order_state = 'not_stock'
        else:
            self.order_id.order_state = 'part_stock'
        ids = self.env['jl.buy.payment.apply'].search([('warehousing_id', '=', self.id)])
        if any(ids):
            for id in ids:
                if id.state != 'draft':
                    raise UserError('不可以删除已经确定的付款申请单')
                else:
                    id.unlink()
        move_ids = self.env['jl.move'].search([('order_id', '=', self.order_id.id), ('state', '=', 'done')])
        for move_id in move_ids:
            line_ids = self.env['jl.move.line'].search(
                [('move_id', '=', move_id.id), ('warehousing_id', '=', self.id), ('state', '=', 'done')])
            if len(line_ids):
                for line_id in line_ids:
                    line_id.write({
                        'state':'draft'
                    })
        self.buy_move_id.write({
            "state": 'draft'
        })
        self.write({
            'state': 'draft'
        })

    def button_return(self):
        '''创建退货单'''
        self.ensure_one()
        return_line = []
        ids = self.env['jl.buy.warehousing'].search([('id','=',self.id),('is_return','=',True),('state', '=', 'draft')])
        if any(ids):
            raise UserError('当前采购入库单已经存在草稿退货单')
        move_id = self.env['jl.move'].create({
            'order_id': self.order_id.id,
            'origin': 'jl.buy.warehousing.return',
            'supplier_id': self.supplier_id.id,
        })
        for line in self.line_ids:
            return_line.append(self.get_return_line(line,move_id))
        if len(return_line):
            return_id = self.with_context(is_return=True).create({
                'order_id':self.order_id.id,
                'is_return': True,
                'buy_move_id': move_id.id,
                'origin_id': self.id,
                'supplier_id': self.supplier_id.id,
                'line_ids':[(0, 0,line) for line in return_line]
            })
            # return_id.write({
            #     'line_ids': [(0, 0,line) for line in return_line]
            # })
    def get_return_line(self,line,move_id):
        self.ensure_one()
        return {
            'goods_id': line.goods_id.id,
            'order_line_id': line.order_line_id.id,
            'warehouse_id': line.warehouse_id.id,
            'move_id': move_id.id,
            'goods_qty': line.goods_qty,
            'price': line.price,
            'tax_price': line.tax_price,
            'tax_rate': line.tax_rate,
            'type': 'out',
            'date': fields.Date.context_today(self),
            'cost_time': fields.Datetime.now(self),
        }


    def button_cancel(self):
        self.ensure_one()
        self.write({
            'state': 'cancel'
        })

    def button_rejection(self):
        '''拒收'''
        move_ids = self.env['jl.move'].search([('order_id','=',self.order_id.id),('state','=','draft')])
        for move_id in move_ids:
            line_ids = self.env['jl.move.line'].search([('move_id', '=', move_id.id),('warehousing_id','=',self.id),('state','=','draft')])
            if len(line_ids):
                for line_id in line_ids:
                    line_id.write({
                        'type': 'rejection',
                        'state':'done'
                    })
                self.write({
                    'state': 'rejection'
                })
    def button_out_done(self):
        self.ensure_one()
        for id  in self.buy_move_id.line_out_ids:
            id.write({
                'state':'done'
            })
        self.write({
            'state': 'done'
        })
        self.buy_move_id.write({
            'state': 'done'
        })



    def button_out_draft(self):
        self.ensure_one()
        for id  in self.buy_move_id.line_out_ids:
            id.write({
                'state':'draft'
            })
        self.write({
            'state': 'draft'
        })
        self.buy_move_id.write({
            'state': 'draft'
        })


    def action_buy_payment_view(self):
        self.ensure_one()
        action = {
            'name': '付款申请单',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'jl.buy.payment.apply',
            'view_id': False,
            'target': 'current',
        }

        form_view = self.env.ref('jinling_buy.jl_buy_payment_apply_view_form').id
        tree_view = self.env.ref('jinling_buy.jl_buy_payment_apply_view_tree').id

        if self.buy_payment_count > 1:
            action['domain'] = "[('warehousing_id','=',%s)]" % self.id
            action['view_mode'] = 'tree,form'
            action['views'] = [(tree_view, 'tree'),(form_view, 'form')]
        elif self.buy_payment_count == 1:
            apply_id = self.env['jl.buy.payment.apply'].search([('warehousing_id', '=', self.id)])
            action['views'] = [(form_view, 'form')]
            action['res_id'] = apply_id and apply_id.id or False
        return action

    def _compute_buy_payment_count(selfs):
        for self in selfs:
            self.buy_payment_count = self.env['jl.buy.payment.apply'].search_count([('warehousing_id','=',self.id)])


    def action_buy_out_view(self):
        self.ensure_one()
        action = {
            'name': '退货单',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'jl.buy.warehousing',
            'view_id': False,
            'target': 'current',
        }

        form_view = self.env.ref('jinling_buy.jl_buy_return_view_form').id
        tree_view = self.env.ref('jinling_buy.jl_buy_return_view_tree').id

        if self.buy_out_count > 1:
            action['domain'] = "[('origin_id','=',%s),('is_return','=','true')]" % self.id
            action['view_mode'] = 'tree,form'
            action['views'] = [(tree_view, 'tree'),(form_view, 'form')]
        elif self.buy_out_count == 1:
            warehousing_id = self.env['jl.buy.warehousing'].search([('origin_id', '=', self.id)])
            action['views'] = [(form_view, 'form')]
            action['res_id'] = warehousing_id and warehousing_id.id or False
        return action

    def _compute_buy_out_count(selfs):
        for self in selfs:
            self.buy_out_count = self.env['jl.buy.warehousing'].search_count([('origin_id','=',self.id),('is_return','=','true')])

    @api.model
    def create(self, vals):
        '''创建采购入库单时生成有序编号'''
        if not self.env.context.get('is_return'):
            name = self._name
        else:
            name = 'jl.buy.return'
        if vals.get('name', '') == '':
            vals['name'] = self.env['ir.sequence'].next_by_code(name) or ''

        vals.update({
            'origin': 'jl.buy.warehousing.return',
        })
        return super(JlBuyWarehousing, self).create(vals)

    name = fields.Char('单据编号',
                       index=True,
                       copy=False,
                       default=lambda self: self.env['ir.sequence'].next_by_code('jl.buy.warehousing'),
                       help="采购订单的唯一编号，当创建时它会自动生成下一个编号。")
    date = fields.Date('入库日期', default=lambda self: fields.Date.context_today(self), required=True)
    origin_id = fields.Many2one('jl.buy.warehousing', '来源单据', copy=False)
    user_id = fields.Many2one('hr.employee', '经办人', default=lambda self: self.env.user.employee_id.id, ondelete='cascade', requierd=True,
                              )
    order_id = fields.Many2one('jl.buy.order','采购订单',ondelete='cascade', requierd=True,help='绑定采购订单')
    state = fields.Selection(STATE, '确认状态', help='单据状态', default='draft',track_visibility='always')
    is_return = fields.Boolean('是否退货', default=lambda self: self.env.context.get('is_return'),
                               help='是否为退货类型')
    supplier_id = fields.Many2one('supplier','供应商',related='order_id.supplier_id', ondelete='cascade', requierd=True, help='供应商')
    buy_move_id = fields.Many2one('jl.move', '移库单',
                                   ondelete='cascade',
                                  help='入库单号')
    note = fields.Char('备注')
    line_ids = fields.One2many('jl.move.line','warehousing_id','移库单明细',ondelete='cascade',help='关联移库单')
    buy_payment_count = fields.Integer('付款申请单数量', compute='_compute_buy_payment_count')
    buy_out_count = fields.Integer('退货单据数量', compute='_compute_buy_out_count')



class JlMoveLine(models.Model):
    _inherit = 'jl.move.line'

    warehousing_id = fields.Many2one('jl.buy.warehousing','采购入库单',ondelete='cascade',help='绑定采购入库单')
    order_line_id = fields.Many2one('jl.buy.order.line','采购订单单明细',ondelete='cascade',help='绑定采购订单明细行')
