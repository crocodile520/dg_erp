# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/2/26
Description: jl_mes_ous_in
"""
from odoo import fields,api,models
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
class JlMesPlmIn(models.Model):
    _name = 'jl.mes.ous.in'
    _description = '委外生产入库单'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'


    def button_done(self):
        self.ensure_one()
        if self.state == 'done':
            raise UserError('单据已经确认，请勿重复确认')
        if float(self.qty) + float(self.quality_id.in_qty) > float(self.quality_id.qty):
            raise UserError("入库数量不可以大于生产订单数量")
        if self.qty > self.quality_id.qualified_qty:
            raise UserError("入库数量不可以大于合格数量")
        self.quality_id.write({
            'in_qty':self.quality_id.in_qty + self.qty
        })
        self.ous_id.write({
            'buy_qty':self.ous_id.buy_qty + self.qty
        })
        move_id = self.env['jl.move'].create({
            'ous_id': self.ous_id.id,
            'ous_in_id': self.id,
            'origin': self._name,
            'state':'done',
            'line_in_ids':[(0,0,{
                'warehouse_id':self.warehouse_id.id,
                'goods_id':self.goods_id.id,
                'goods_qty':self.qty,
                'type':'in',
                'date':fields.Date.context_today(self),
                'cost_time':fields.Datetime.now(self),
                'state':'done',
                'ous_in_id': self.id,
            })]
        })

        if self.quality_id.qualified_qty - self.quality_id.in_qty > 0:
            self.env['jl.mes.ous.in'].create({
                'ous_id': self.ous_id.id,
                'quality_id': self.quality_id.id,
                'goods_id': self.goods_id.id,
                'qty': self.quality_id.qty - self.quality_id.in_qty,
                'warehouse_id': self.warehouse_id.id
            })
        self.write({
            'state':'done',
            'approve_uid': self.env.uid,
            'approve_date': fields.Datetime.now(self),
        })


    def button_draft(self):
        self.ensure_one()
        self.quality_id.write({
            'in_qty':float(self.quality_id.in_qty) - float(self.qty)
        })
        self.ous_id.write({
            'buy_qty':float(self.ous_id.buy_qty) - float(self.qty)
        })
        ids = self.env['jl.mes.ous.in'].search([('ous_id','=',self.ous_id.id),('state','=','draft')])
        for id in ids:
            id.unlink()
        move_ids = self.env['jl.move'].search([('ous_id','=',self.ous_id.id),('ous_in_id','=',self.id),('state','=','done')])
        for move_id in move_ids:
            move_id.unlink()
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
                       default=lambda self: self.env['ir.sequence'].next_by_code('jl.mes.ous.in'),
                       help="生产入库单的唯一编号，当创建时它会自动生成下一个编号。")
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
    ous_id = fields.Many2one('jl.mes.ous', '委外生产工单', ondelete='cascade', help='绑定委外生产工单')
    quality_id = fields.Many2one('jl.ous.quality', '委外质检单', ondelete='cascade', help='绑定委外质检单')
    goods_id = fields.Many2one('goods', '商品', ondelete='cascade', help='购货商品')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    uom_id = fields.Many2one('uom', related='goods_id.uom_id', ondelete='cascade')
    qty = fields.Float('入库数量', digits='Quantity', track_visibility='always')
    warehouse_id = fields.Many2one('warehouse', '仓库', help='关联仓库，购票物品存储某个仓库')
    date = fields.Date('单据日期', default=lambda self: fields.Date.context_today(self), required=True)
    date_in = fields.Date('入库日期', default=lambda self: fields.Date.context_today(self), required=True)
    line_ids = fields.One2many('jl.move.line', 'ous_in_id', '移库单明细', ondelete='cascade', help='关联移库单')
    state = fields.Selection(STATE, '确认状态', help='单据状态', default='draft', track_visibility='always')
    approve_uid = fields.Many2one('res.users',
                                  '确认人',
                                  copy=False,
                                  ondelete='restrict',
                                  help='确认单据的人')
    approve_date = fields.Datetime('确认日期', copy=False)
    note = fields.Char('备注')

class JlMoveLine(models.Model):
    _inherit = 'jl.move.line'

    ous_in_id = fields.Many2one('jl.mes.ous.in','委外生产入库单',ondelete='cascade',help='绑定委外生产入库单')

class JlMove(models.Model):
    _inherit = 'jl.move'

    ous_in_id = fields.Many2one('jl.mes.ous.in', '委外生产入库单', ondelete='cascade', help='绑定委外生产入库单')
