# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/2/18
Description: jl_move_out
"""

from odoo import fields,api,models
from odoo.exceptions import UserError


STATE = [
    ('draft','草稿'),
    ('done','出库'),
    ('cancel','作废'),
]

MOVE_LINE_TYPE = [
        ('out', '出库'),
        ('in', '入库'),
        ('rejection', '拒收'),
        ('internal', '内部调拨'),
    ]
class JlMoveIn(models.Model):
    _name = 'jl.move.out'
    _description = '额外出库单'
    _inherit = ['mail.thread']


    def button_done(self):
        self.ensure_one()
        if self.state == 'done':
            raise UserError('单据已经确认，请勿重复确认')
        if not self.line_ids:
            raise UserError('请填写额外入库单明细行')
        for line in self.line_ids:
            if not line.warehouse_id:
                raise UserError("%s 商品仓库不能为空" % line.goods_id.name)
        move_ids = self.env['jl.move'].search(
            [('move_out_id', '=', self.id), ('state', '=', 'done')])
        if move_ids:
            move_ids.state = 'done'
            for move_id in move_ids:
                move_id.line_out_ids.state = 'done'
        else:
            move_id = self.env['jl.move'].create({
                'origin': self._name,
                "move_out_id":self.id,
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
            self.move_id = move_id.id

        self.write({
            "state":"done",
            "approve_uid": self.env.uid,
            "approve_date": fields.Datetime.now(self),
        })


    def button_draft(self):
        self.ensure_one()
        if self.state == 'draft':
            raise UserError('单据已经撤销，请勿重复撤销')
        move_ids = self.env['jl.move'].search(
            [('move_out_id', '=', self.id), ('state', '=', 'done')])
        for move_id in move_ids:
            for line in move_id.line_out_ids:
                line.state = 'draft'
            move_id.state = 'draft'
        self.write({
            "state": "draft",
            "approve_uid": self.env.uid,
            "approve_date": fields.Datetime.now(self),
        })

    def button_cancel(self):
        self.ensure_one()
        move_ids = self.env['jl.move'].search(
            [('move_out_id', '=', self.id), ('state', '=', 'done')])
        if move_ids:
            move_ids.unlink()
        self.write({
            "state": "cancel",
            "approve_uid": self.env.uid,
            "approve_date": fields.Datetime.now(self),
        })


    name = fields.Char('单据编号', copy=False, default=lambda self: self.env['ir.sequence'].next_by_code('jl.move.in'),
                       help='单据编号，创建时会自动生成')
    state = fields.Selection(STATE, '状态', copy=False, default='draft',
                             index=True,
                             help='移库单状态标识，新建时状态为草稿;确认后状态为已确认',
                             track_visibility='onchange')
    date = fields.Date('单据日期', required=True, copy=False, default=fields.Date.context_today,
                       help='单据创建日期，默认为当前天')

    move_id = fields.Many2one('jl.move', string='移库单', ondelete='cascade',
                              help='出库/入库/移库单行对应的移库单')
    user_id = fields.Many2one(
        'hr.employee',
        '经办人',
        ondelete='restrict',
        states={'done': [('readonly', True)]},
        default=lambda self: self.env.user.employee_id.id,
        help='单据经办人',
        track_visibility='onchange'
    )
    note = fields.Char('备注')
    line_ids = fields.One2many('jl.move.out.line', 'move_out_id', '额外出库单明细行', ondelete='cascade', help='关联移库单')
    approve_date = fields.Datetime('确认日期', copy=False)
    approve_uid = fields.Many2one('res.users', '确认人',
                                  copy=False, ondelete='restrict',
                                  help='移库单的确认人')


class JlMoveOutLine(models.Model):
    _name = 'jl.move.out.line'
    _description = '额外出库单明细行'

    move_out_id = fields.Many2one('jl.move.out', '额外出库单', ondelete='cascade')
    goods_id = fields.Many2one('goods', string='商品', required=True,
                               index=True, ondelete='restrict',
                               help='该单据行对应的商品')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    uom_id = fields.Many2one('uom', string='单位',related='goods_id.uom_id', ondelete='restrict',help='商品的计量单位')
    warehouse_id = fields.Many2one('warehouse', '仓库', help='关联仓库，购票物品存储某个仓库')
    type = fields.Selection(MOVE_LINE_TYPE,
                            '类型',
                            required=True,
                            default='out',
                            help='类型：出库、入库 或者 内部调拨')
    qty = fields.Float('数量',
                             digits='Quantity',
                             default=1,
                             required=True,
                             help='商品的数量')
    note = fields.Text('备注',
                       help='可以为该单据添加一些需要的标识信息')


class JlMove(models.Model):
    _inherit = 'jl.move'

    move_out_id = fields.Many2one('jl.move.out', '额外出库单', ondelete='cascade', help='绑定额外入库单')
