# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/3/3
Description: jl_sample_picking
"""

from odoo import api,models,fields
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

class JlSamplePicking(models.Model):
    _name = 'jl.sample.picking'
    _description = '样品领料'
    _inherit = ['mail.thread']

    def button_done(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError('领料单明细不允许为空')
        for line in self.line_ids:
            if not line.warehouse_id.id:
                raise UserError('%s商品 仓库不允许为空' % line.goods_id.name)
            if line.warehouse_id.id == 1:
                if line.qty > line.ms1_qty:
                    raise UserError('%s商品%s领料库存数量不足' % (line.goods_id.name,line.warehouse_id.name))
            elif line.warehouse_id.id == 2:
                if line.qty > line.ms2_qty:
                    raise UserError('%s商品%s领料库存数量不足' % (line.goods_id.name, line.warehouse_id.name))
            elif line.warehouse_id.id == 3:
                if line.qty > line.ms3_qty:
                    raise UserError('%s商品%s领料库存数量不足' % (line.goods_id.name, line.warehouse_id.name))
        for record in self.line_ids:
            if float(record.qty) + float(record.order_line_id.done_qty) >  float(record.order_line_id.neck_qty):
                raise UserError('领料数量超过了待领数量')
            record.order_line_id.write({
                'neck_qty':float(record.order_line_id.neck_qty) - float(record.qty),
                'done_qty':float(record.order_line_id.done_qty) + float(record.qty)
            })
        move_id = self.env['jl.move'].create({
            'sample_order_id': self.order_id.id,
            'sample_pick_id': self.id,
            'origin': self._name,
            'state': 'done',
            'line_out_ids': [(0, 0, {
                'warehouse_id': line.warehouse_id.id,
                'goods_id': line.goods_id.id,
                'goods_qty': line.qty,
                'type': 'out',
                'date': fields.Date.context_today(self),
                'cost_time': fields.Datetime.now(self),
                'state': 'done',
            }) for line in self.line_ids]
        })
        self.write({
            'state':'done',
            'approve_uid': self.env.uid,
            'approve_date': fields.Datetime.now(self),
        })


    def button_draft(self):
        self.ensure_one()
        for line in self.line_ids:
            line.order_line_id.write({
                'neck_qty': float(line.order_line_id.neck_qty) + float(line.qty),
                'done_qty': float(line.order_line_id.done_qty) - float(line.qty)
            })
        ids = self.env['jl.move'].search([('sample_pick_id','=',self.id),('sample_order_id','=',self.order_id.id),('state','=','done')])
        for id in ids:
            id.unlink()
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
                       default=lambda self: self.env['ir.sequence'].next_by_code('jl.sample.picking'),
                       help="生产领料单的唯一编号，当创建时它会自动生成下一个编号。")
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
    order_id = fields.Many2one('jl.sample.order', '样品订单', ondelete='cascade',help='关联样品订单')
    date = fields.Date('单据日期', default=lambda self: fields.Date.context_today(self), required=True)
    line_ids = fields.One2many('jl.sample.picking.line', 'pick_id', ondelete='cascade',
                               help='样品领料单明细行')
    note = fields.Char('备注')
    approve_uid = fields.Many2one('res.users',
                                  '确认人',
                                  copy=False,
                                  ondelete='restrict',
                                  help='确认单据的人')
    approve_date = fields.Datetime('确认日期', copy=False)
    state = fields.Selection(STATE, '确认状态', help='单据状态', default='draft', track_visibility='always')


class JlSamplePickingLine(models.Model):
    _name = 'jl.sample.picking.line'
    _description = '样品领料单明细行'


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
                    line['goods_id']:{'ms1_qty':line['ms1_qty'],'ms2_qty':line['ms2_qty'],'ms3_qty':line['ms3_qty']}
                })
        for self in selfs:
            key = self.goods_id.id
            qty_dict = balance_qty[key] if key in balance_qty.keys() else 0
            self.ms1_qty = qty_dict['ms1_qty']
            self.ms2_qty = qty_dict['ms2_qty']
            self.ms3_qty = qty_dict['ms3_qty']


    pick_id = fields.Many2one('jl.sample.picking', '样品领料单', ondelete='cascade')
    order_line_id = fields.Many2one('jl.sample.order.line', '样品订单明细', ondelete='cascade')
    warehouse_id = fields.Many2one('warehouse', '仓库', help='关联仓库，购票物品存储某个仓库')
    goods_id = fields.Many2one('goods', '产品名称', ondelete='cascade')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    uom_id = fields.Many2one('uom', related='goods_id.uom_id', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    qty = fields.Float('数量', digits='Quantity')
    ms1_qty = fields.Float('成品仓库存数量', digits='Quantity', track_visibility='always', compute='_compute_warehouse_balance')
    ms2_qty = fields.Float('PCB板仓库存数量', digits='Quantity', track_visibility='always', compute='_compute_warehouse_balance')
    ms3_qty = fields.Float('原材料仓库存数量', digits='Quantity', track_visibility='always', compute='_compute_warehouse_balance')
    note = fields.Char('备注')
    state = fields.Selection(STATE, '确认状态', related='pick_id.state')

class JlMove(models.Model):
    _inherit = 'jl.move'

    sample_pick_id = fields.Many2one('jl.sample.picking', '样品领料单', ondelete='cascade', help='绑定样品领料单')
    sample_order_id = fields.Many2one('jl.sample.order', '样品订单', ondelete='cascade', help='绑定样品订单')

