# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/3/3
Description: jl_sample_apply
"""
from odoo import fields, api, models
from odoo.exceptions import UserError

STATE = [
    ('draft', '草稿'),
    ('done', '完成'),
    ('cancel', '作废'),
]


class JlSampleApply(models.Model):
    _name = 'jl.sample.apply'
    _description = '样品申请单'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'



    def button_done(self):
        """样品申请单确认产生样品订单"""
        self.ensure_one()
        if self.state == 'done':
            raise UserError("订单已确认，请勿重复确认")
        if not self.goods_id:
            raise UserError("请填写商品！")
        if not self.warehouse_id:
            raise UserError("请填写仓库！")
        bom_id = self.env['goods.bom'].search([('goods_id', '=', self.goods_id.id)], limit=1)
        # 创建新的明细行
        lines = []
        for bom_line in bom_id.line_ids:
            lines.append((0, 0, {
                'goods_id': bom_line.goods_id.id,
                'qty': bom_line.qty * (self.qty or 0)
            }))
        self.env['jl.sample.order'].create({
            "apply_id":self.id,
            "user_id":self.user_id.id,
            "goods_id":self.goods_id.id,
            "warehouse_id":self.warehouse_id.id,
            "qty":self.qty,
            "line_ids":lines
        })
        self.write({
            'state': 'done',
            'approve_uid': self.env.uid,
            'approve_date': fields.Datetime.now(self),
        })


    def button_draft(self):
        self.ensure_one()
        if self.state == 'draft':
            raise UserError("订单已撤回，请勿重复确认")
        ids = self.env['jl.sample.order'].search([('apply_id', '=', self.id)])
        if any(ids):
            for id in ids:
                if id.state != 'draft':
                    raise UserError('不可以删除已经确定的样品订单')
                else:
                    id.unlink()

        self.write({
            'state': 'draft',
            'approve_uid': None,
            'approve_date': None,
        })

    def button_cancel(self):
        self.ensure_one()
        self.write({
            'state': 'cancel'
        })

    def action_sample_order_view(self):
        self.ensure_one()
        action = {
            'name': '样品订单',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'jl.sample.order',
            'view_id': False,
            'target': 'current',
        }

        form_view = self.env.ref('jinling_sample.jl_sample_order_view_form').id
        tree_view = self.env.ref('jinling_sample.jl_sample_order_view_tree').id

        if self.sample_order_count > 1:
            action['domain'] = "[('apply_id','=',%s)]" % self.id
            action['view_mode'] = 'tree,form'
            action['views'] = [(tree_view, 'tree'), (form_view, 'form')]
        elif self.sample_order_count == 1:
            order_id = self.env['jl.sample.order'].search([('apply_id', '=', self.id)])
            action['views'] = [(form_view, 'form')]
            action['res_id'] = order_id and order_id.id or False
        return action

    def _compute_sample_order_count(selfs):
        for self in selfs:
            self.sample_order_count = self.env['jl.sample.order'].search_count([('apply_id', '=', self.id)])

    name = fields.Char('单据编号',
                       index=True,
                       copy=False,
                       default=lambda self: self.env['ir.sequence'].next_by_code('jl.sample.apply'),
                       help="样品申请订单的唯一编号，当创建时它会自动生成下一个编号。")
    date = fields.Date('单据日期', default=lambda self: fields.Date.context_today(self), required=True)
    user_id = fields.Many2one('hr.employee', '申请人', default=lambda self: self.env.user.employee_id.id,
                              ondelete='cascade', requierd=True, track_visibility='onchange')
    goods_id = fields.Many2one('goods', '产品名称', ondelete='cascade')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    uom_id = fields.Many2one('uom', related='goods_id.uom_id', ondelete='cascade')
    warehouse_id = fields.Many2one('warehouse', '仓库', help='关联仓库，购票物品存储某个仓库')
    sample_order_count = fields.Integer('样品订单数量', compute='_compute_sample_order_count')
    qty = fields.Integer('数量')
    state = fields.Selection(STATE, '确认状态', help='单据状态', default='draft', track_visibility='always')
    note = fields.Char('备注')
    approve_uid = fields.Many2one('res.users',
                                  '确认人',
                                  copy=False,
                                  ondelete='restrict',
                                  help='确认单据的人')
    approve_date = fields.Datetime('确认日期', copy=False)
