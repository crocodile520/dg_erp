# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/3/3
Description: jl_sample_order
"""

from odoo import fields, api, models
from odoo.exceptions import UserError

STATE = [
    ('draft', '草稿'),
    ('done', '完成'),
    ('cancel', '作废'),
]


class JlSamplOrder(models.Model):
    _name = 'jl.sample.order'
    _description = '样品订单'
    _inherit = ['mail.thread']

    def button_done(self):
        self.ensure_one()
        if self.state == 'done':
            raise UserError("订单已确认，请勿重复确认")
        for line in self.line_ids:
            line.neck_qty = line.qty
        pick_id = self.env['jl.sample.picking'].create({
            'order_id': self.id
        })
        for line in self.line_ids:
            line.neck_qty = line.qty
            pick_id.write({
                'line_ids': [(0, 0, {
                    'order_line_id': line.id,
                    'goods_id': line.goods_id.id,
                    'qty': line.qty
                })]
            })
        self.write({
            'state': 'done',
            'approve_uid': self.env.uid,
            'approve_date': fields.Datetime.now(self),
        })

    def button_draft(self):
        self.ensure_one()
        if self.state == 'draft':
            raise UserError("订单已撤销，请勿重复确认")

        ids = self.env['jl.sample.picking'].search([('order_id', '=', self.id)])
        in_ids = self.env['jl.sample.in'].search([('order_id', '=', self.id)])
        if any(ids):
            for id in ids:
                if id.state != 'draft':
                    raise UserError('不可以删除已经确定的样品领料订单')
                else:
                    id.unlink()

        if any(in_ids):
            for in_id in in_ids:
                if in_id.state != 'draft':
                    raise UserError('不可以删除已经确定的样品领料订单')
                else:
                    in_id.unlink()

        self.write({
            'state': 'done',
            'approve_uid': self.env.uid,
            'approve_date': fields.Datetime.now(self),
        })

    def button_cancel(self):
        self.ensure_one()
        self.write({
            'state': 'cancel'
        })

    def button_sample_in(self):
        """产生样品入库单"""
        self.ensure_one()
        if self.qty <= 0:
            raise UserError('合格数量不可以小于等于0')
        if self.qty > self.in_qty:
            self.env['jl.sample.in'].create({
                'order_id':self.id,
                'goods_id':self.goods_id.id,
                'qty':self.qty - self.in_qty,
                'warehouse_id':self.warehouse_id.id
            })
        # self.write({
        #     'state':'done',
        #     'approve_uid': self.env.uid,
        #     'approve_date': fields.Datetime.now(self),
        # })


    def button_sample_picking(self):
        '''创建领料单'''
        ids = self.env['jl.sample.picking'].search([('order_id','=',self.id),('state','=','draft')])
        if ids:
            ids.unlink()
        pick_id = self.env['jl.sample.picking'].create({
            'order_id':self.id
        })
        for line in self.line_ids:
            if line.neck_qty > 0:
                pick_id.write({
                    'line_ids': [(0, 0, {
                        'order_line_id': line.id,
                        'goods_id': line.goods_id.id,
                        'qty': line.neck_qty
                    })]
                })



    def action_picking_view(self):
        self.ensure_one()
        action = {
            'name': '样品领料单',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'jl.sample.picking',
            'view_id': False,
            'target': 'current',
        }

        form_view = self.env.ref('jinling_sample.jl_sample_picking_view_form').id
        tree_view = self.env.ref('jinling_sample.jl_sample_picking_view_tree').id

        if self.picking_count > 1:
            action['domain'] = "[('order_id','=',%s)]" % self.id
            action['view_mode'] = 'tree,form'
            action['views'] = [(tree_view, 'tree'),(form_view, 'form')]
        elif self.picking_count == 1:
            picking_id = self.env['jl.sample.picking'].search([('order_id', '=', self.id)])
            action['views'] = [(form_view, 'form')]
            action['res_id'] = picking_id and picking_id.id or False
        return action


    def _compute_picking_count(selfs):
        for self in selfs:
            self.picking_count = self.env['jl.sample.picking'].search_count([('order_id','=',self.id)])

    @api.onchange('goods_id', 'qty')
    def onchange_line_id(self):
        """
        当商品或数量变化时，更新生产工单明细行
        """
        if not self.goods_id:
            return
        bom_id = self.env['goods.bom'].search([('goods_id', '=', self.goods_id.id)], limit=1)
        if not bom_id:
            return
        self.line_ids = False

        # 创建新的明细行
        lines = []
        for bom_line in bom_id.line_ids:
            lines.append((0, 0, {
                'goods_id': bom_line.goods_id.id,
                'qty': bom_line.qty * (self.qty or 0)
            }))
        self.line_ids = lines


    def action_sample_in_view(self):
        self.ensure_one()
        action = {
            'name': '样品入库单',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'jl.sample.in',
            'view_id': False,
            'target': 'current',
        }

        form_view = self.env.ref('jinling_sample.jl_sample_in_view_form').id
        tree_view = self.env.ref('jinling_sample.jl_sample_in_view_tree').id

        if self.sample_in_count > 1:
            action['domain'] = "[('order_id','=',%s)]" % self.id
            action['view_mode'] = 'tree,form'
            action['views'] = [(tree_view, 'tree'),(form_view, 'form')]
        elif self.sample_in_count == 1:
            in_id = self.env['jl.sample.in'].search([('order_id', '=', self.id)])
            action['views'] = [(form_view, 'form')]
            action['res_id'] = in_id and in_id.id or False
        return action

    def _compute_sample_in_count(selfs):
        for self in selfs:
            self.sample_in_count = self.env['jl.sample.in'].search_count([('order_id','=',self.id)])


    name = fields.Char('单据编号',
                       index=True,
                       copy=False,
                       default=lambda self: self.env['ir.sequence'].next_by_code('jl.sample.order'),
                       help="样品订单的唯一编号，当创建时它会自动生成下一个编号。")
    apply_id = fields.Many2one('jl.sample.apply', '样品申请单', help='关联')
    date = fields.Date('单据日期', default=lambda self: fields.Date.context_today(self), required=True)
    user_id = fields.Many2one('hr.employee', '申请人', default=lambda self: self.env.user.employee_id.id,
                              ondelete='cascade', requierd=True, track_visibility='onchange')
    goods_id = fields.Many2one('goods', '产品名称', ondelete='cascade')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    uom_id = fields.Many2one('uom', related='goods_id.uom_id', ondelete='cascade')
    warehouse_id = fields.Many2one('warehouse', '仓库', help='关联仓库，购票物品存储某个仓库')
    line_ids = fields.One2many('jl.sample.order.line', 'order_id', ondelete='cascade',
                               help='样品订单明细行')
    qty = fields.Integer('数量')
    in_qty = fields.Float('已入库数量', digits='Quantity', )
    state = fields.Selection(STATE, '确认状态', help='单据状态', default='draft', track_visibility='always')
    note = fields.Char('备注')
    approve_uid = fields.Many2one('res.users',
                                  '确认人',
                                  copy=False,
                                  ondelete='restrict',
                                  help='确认单据的人')
    approve_date = fields.Datetime('确认日期', copy=False)
    picking_count = fields.Integer('样品领料单数量', compute='_compute_picking_count')
    sample_in_count = fields.Integer('样品入库单数量', compute='_compute_sample_in_count')


class JlSampleOrderLine(models.Model):
    _name = 'jl.sample.order.line'
    _description = '样品订单明细'

    def get_neck_qty(selfs):
        for self in selfs:
            self.neck_qty = self.qty


    order_id = fields.Many2one('jl.sample.order','样品订单',ondelete='cascade',help='关联样品订单')
    goods_id = fields.Many2one('goods', '商品', ondelete='cascade', help='购货商品')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    uom_id = fields.Many2one('uom', related='goods_id.uom_id', ondelete='cascade')
    qty = fields.Float('数量', digits='Quantity', )
    neck_qty = fields.Float('待领料数量', digits='Quantity')
    done_qty = fields.Float('已领料数量', digits='Quantity')
    refund_qty = fields.Float('退料数量', digits='Quantity')
    state = fields.Selection(STATE, '确认状态', related='order_id.state')
    note = fields.Char('备注')