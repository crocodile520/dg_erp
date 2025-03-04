# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/2/26
Description: jl_mes_ous
"""
from odoo import fields,models,api
from odoo.exceptions import UserError

STATE = [
    ('draft','草稿'),
    ('start','开工中'),
    ('done','完成'),
    ('stop','暂停'),
    ('cancel','作废'),
]
TASK_TYPE = [
    ('not_task','未开工'),
    ('task','开工'),
    ('stop','暂停'),
]

class LxMesOus(models.Model):
    _name = "jl.mes.ous"
    _description = "委外生产工单"
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'



    def button_start(self):
        self.ensure_one()
        if not self.warehouse_id:
            raise UserError('仓库不允许为空！请填写仓库')
        pick_id = self.env['jl.mes.ous.picking'].create({
            'ous_id': self.id
        })
        for line in self.line_ids:
            line.neck_qty = line.qty
            pick_id.write({
                'line_ids': [(0, 0, {
                    'ous_line_id': line.id,
                    'goods_id': line.goods_id.id,
                    'qty': line.qty
                })]
            })
        self.write({
            'state': 'start',
            'task_type':'task'
        })

    def button_stop(self):
        self.ensure_one()
        self.write({
            'state': 'stop',
            'task_type': 'stop'
        })

    def button_continue(self):
        self.ensure_one()
        self.write({
            'state': 'start',
            'task_type': 'task'
        })

    def button_done(self):
        self.ensure_one()
        if self.done_qty <= 0:
            raise UserError('完工数量不可以等于小于0')
        self.create_quality()
        self.write({
            'state': 'done',
            'approve_uid': self.env.uid,
            'approve_date': fields.Datetime.now(self),
        })


    def button_draft(self):
        self = self.sudo()
        self.ensure_one()
        if self.state == 'draft':
            raise UserError('请不要重复撤销')
        ous_quality_ids = self.env['jl.ous.quality'].search([('ous_id','=',self.id)])
        ous_pick_ids = self.env['jl.mes.ous.picking'].search([('ous_id','=',self.id)])
        ous_ref_ids = self.env['jl.mes.ous.refund'].search([('ous_id','=',self.id)])
        if any(ous_quality_ids):
            for ous_quality_id in ous_quality_ids:
                if ous_quality_id.state != 'draft':
                    raise UserError('不可以删除已经确定的质量检验单')
                else:
                    ous_quality_id.unlink()
        if any(ous_pick_ids):
            for ous_pick_id in ous_pick_ids:
                if ous_pick_id.state != 'draft':
                    raise UserError('不可以删除已经确定的领料单')
                else:
                    ous_pick_id.unlink()
        if any(ous_ref_ids):
            for ous_ref_id in ous_ref_ids:
                if ous_ref_id.state != 'draft':
                    raise UserError('不可以删除已经确定的退料单')
                else:
                    ous_ref_id.unlink()
        self.write({
            'state': 'draft'
        })


    def button_cancel(self):
        self.ensure_one()
        self.write({
            'state': 'cancel'
        })

    def create_quality(self):
        '''生产完成产生委外质检单'''
        self.env['jl.ous.quality'].create({
            'ous_id':self.id,
            'goods_id':self.goods_id.id,
            'warehouse_id':self.warehouse_id.id,
            'qty':self.qty,
            'type':'in'
        })

    def action_ous_quality_view(self):
        self.ensure_one()
        action = {
            'name': '委外质量检验单',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'jl.ous.quality',
            'view_id': False,
            'target': 'current',
        }

        form_view = self.env.ref('jinling_outsourcing.jl_ous_quality_view_form').id
        tree_view = self.env.ref('jinling_outsourcing.jl_ous_quality_view_tree').id

        if self.quality_count > 1:
            action['domain'] = "[('ous_id','=',%s)]" % self.id
            action['view_mode'] = 'tree,form'
            action['views'] = [(tree_view, 'tree'),(form_view, 'form')]
        elif self.quality_count == 1:
            quality_id = self.env['jl.ous.quality'].search([('ous_id', '=', self.id)])
            action['views'] = [(form_view, 'form')]
            action['res_id'] = quality_id and quality_id.id or False
        return action


    def action_ous_picking_view(self):
        self.ensure_one()
        action = {
            'name': '委外生产领料单',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'jl.mes.ous.picking',
            'view_id': False,
            'target': 'current',
        }

        form_view = self.env.ref('jinling_outsourcing.jl_mes_ous_picking_view_form').id
        tree_view = self.env.ref('jinling_outsourcing.jl_mes_ous_picking_view_tree').id

        if self.picking_count > 1:
            action['domain'] = "[('ous_id','=',%s)]" % self.id
            action['view_mode'] = 'tree,form'
            action['views'] = [(tree_view, 'tree'),(form_view, 'form')]
        elif self.picking_count == 1:
            picking_id = self.env['jl.mes.ous.picking'].search([('ous_id', '=', self.id)])
            action['views'] = [(form_view, 'form')]
            action['res_id'] = picking_id and picking_id.id or False
        return action

    def action_ous_refund_view(self):
        self.ensure_one()
        action = {
            'name': '委外生产退料单',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'jl.mes.ous.refund',
            'view_id': False,
            'target': 'current',
        }

        form_view = self.env.ref('jinling_outsourcing.jl_mes_ous_refund_view_form').id
        tree_view = self.env.ref('jinling_outsourcing.jl_mes_ous_refund_view_tree').id

        if self.refund_count > 1:
            action['domain'] = "[('ous_id','=',%s)]" % self.id
            action['view_mode'] = 'tree,form'
            action['views'] = [(tree_view, 'tree'),(form_view, 'form')]
        elif self.refund_count == 1:
            refund_id = self.env['jl.mes.ous.refund'].search([('ous_id', '=', self.id)])
            action['views'] = [(form_view, 'form')]
            action['res_id'] = refund_id and refund_id.id or False
        return action

    def button_mes_ous_refund(self):
        '''创建委外退料单'''

        ous_pick_id = self.env['jl.mes.ous.refund'].create({
            'ous_id':self.id
        })
        ous_pick_id.write({
            'line_ids':[(0,0,{
                'ous_line_id':line.id,
                'goods_id':line.goods_id.id,
                'qty':line.qty
            }) for line in self.line_ids]
        })

    def button_mes_ous_picking(self):
        '''创建领料单'''

        ids = self.env['jl.mes.ous.picking'].search([('ous_id', '=', self.id), ('state', '=', 'draft')])
        if ids:
            ids.unlink()
        pick_id = self.env['jl.mes.ous.picking'].create({
            'ous_id': self.id
        })
        for line in self.line_ids:
            if line.neck_qty > 0:
                pick_id.write({
                    'line_ids': [(0, 0, {
                        'ous_line_id': line.id,
                        'goods_id': line.goods_id.id,
                        'qty': line.neck_qty
                    })]
                })

    def _compute_quality_count(selfs):
        for self in selfs:
            self.quality_count = self.env['jl.ous.quality'].search_count([('ous_id','=',self.id)])

    def _compute_picking_count(selfs):
        for self in selfs:
            self.picking_count = self.env['jl.mes.ous.picking'].search_count([('ous_id','=',self.id)])

    def _compute_refund_count(selfs):
        for self in selfs:
            self.refund_count = self.env['jl.mes.ous.refund'].search_count([('ous_id','=',self.id)])

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

    name = fields.Char('单据编号', index=True, copy=False, default=lambda self:self.env['ir.sequence'].next_by_code('jl.mes.ous'),
                       help="创建时它会自动生成下一个编号")
    # order_id = fields.Many2one('sell.order','销售订单',ondelete='cascade',help='绑定销售订单')
    # partner_id = fields.Many2one('partner', '客户',related='order_id.partner_id')
    # partner_code = fields.Char('客户编码', related='order_id.partner_code')
    # ref = fields.Char('客户订单号', related='order_id.ref',track_visibility='always')
    user_id = fields.Many2one('hr.employee', '经办人', default=lambda self: self.env.user.employee_id.id, ondelete='cascade', requierd=True,
                              )
    # eng_id = fields.Many2one('jl.engineering', '工程工单', ondelete='cascade', help='绑定工程工单')
    task_type = fields.Selection(TASK_TYPE,'开工状态',default='not_task', track_visibility='always')
    goods_id = fields.Many2one('goods', '商品', ondelete='cascade', help='购货商品')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    uom_id = fields.Many2one('uom', related='goods_id.uom_id', ondelete='cascade')
    qty = fields.Float('数量', digits='Quantity', track_visibility='always')
    done_qty = fields.Float('完工数量', digits='Quantity', track_visibility='always')
    buy_qty = fields.Float('已入库数量', digits='Quantity', )
    warehouse_id = fields.Many2one('warehouse', '仓库', help='关联仓库，购票物品存储某个仓库')
    date = fields.Date('单据日期', default=lambda self: fields.Date.context_today(self), required=True)
    delivery_date = fields.Date('要求交货日期', default=lambda self: fields.Date.context_today(self), required=True)
    state = fields.Selection(STATE, '确认状态', help='单据状态', default='draft', track_visibility='always')
    line_ids = fields.One2many('jl.mes.ous.line','ous_id','生产工单明细',ondelete='cascade',help='关联生产工单明细行')
    approve_uid = fields.Many2one('res.users',
                                  '确认人',
                                  copy=False,
                                  ondelete='restrict',
                                  help='确认单据的人')
    approve_date = fields.Datetime('确认日期', copy=False)
    quality_count = fields.Integer('委外质量检验单数量', compute='_compute_quality_count')
    picking_count = fields.Integer('委外生产领料单数量', compute='_compute_picking_count')
    refund_count = fields.Integer('委外生产退料单数量', compute='_compute_refund_count')
    note = fields.Char('备注')



class JlMesOusLine(models.Model):
    _name = 'jl.mes.ous.line'
    _description = '委外生产工单明细'


    def get_neck_qty(selfs):
        for self in selfs:
            self.neck_qty = self.qty


    ous_id = fields.Many2one('jl.mes.ous','委外生产工单',ondelete='cascade',help='关联生产工单')
    goods_id = fields.Many2one('goods', '商品', ondelete='cascade', help='购货商品')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    uom_id = fields.Many2one('uom', related='goods_id.uom_id', ondelete='cascade')
    qty = fields.Float('数量', digits='Quantity', )
    neck_qty = fields.Float('待领料数量', digits='Quantity')
    done_qty = fields.Float('已领料数量', digits='Quantity')
    refund_qty = fields.Float('退料数量', digits='Quantity')
    state = fields.Selection(STATE, '确认状态', related='ous_id.state')
    note = fields.Char('备注')


class JlMove(models.Model):
    _inherit = 'jl.move'

    ous_id = fields.Many2one('jl.mes.ous', '委外生产工单', ondelete='cascade', help='绑定委外生产工单')