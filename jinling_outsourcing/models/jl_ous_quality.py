# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/2/26
Description: jl_ous_quality
"""
from odoo import api,fields,models
from odoo.exceptions import UserError




READONLY_STATES = {
    'done': [('readonly', True)],
    'onchange': [('readonly', True)],
    'stop': [('readonly', True)],
    'cancel': [('readonly', True)],
}
STATE = [
    ('draft','草稿'),
    ('done','入库'),
    ('cancel','作废'),
]

class JlOusQuality(models.Model):
    _name = 'jl.ous.quality'
    _description = '委外质量检验单'
    _inherit = ['mail.thread']




    def button_done(self):
        self.ensure_one()
        '''质检合格后产生委外生产入库单'''
        if self.qualified_qty <= 0:
            raise UserError('合格数量不可以小于等于0')
        self.env['jl.mes.ous.in'].create({
            'ous_id':self.ous_id.id,
            'quality_id':self.id,
            'goods_id':self.goods_id.id,
            'qty':self.qualified_qty,
            'warehouse_id':self.warehouse_id.id
        })
        self.write({
            'state':'done',
            'approve_uid': self.env.uid,
            'approve_date': fields.Datetime.now(self),
        })


    def button_draft(self):
        self.ensure_one()
        if self.state == 'draft':
            raise UserError('请不要重复撤销')
        ids = self.env['jl.mes.ous.in'].search([('quality_id','=',self.id)])
        if any(ids):
            for id in ids:
                if id.state != 'draft':
                    raise UserError('不可以删除已经确定的委外生产入库单')
                else:
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


    def action_ous_quality_view(self):
        self.ensure_one()
        action = {
            'name': '委外生产入库单',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'jl.mes.ous.in',
            'view_id': False,
            'target': 'current',
        }

        form_view = self.env.ref('jinling_outsourcing.jl_mes_ous_in_view_form').id
        tree_view = self.env.ref('jinling_outsourcing.jl_mes_ous_in_view_tree').id

        if self.ous_in_count > 1:
            action['domain'] = "[('quality_id','=',%s)]" % self.id
            action['view_mode'] = 'tree,form'
            action['views'] = [(tree_view, 'tree'),(form_view, 'form')]
        elif self.ous_in_count == 1:
            quality_id = self.env['jl.mes.ous.in'].search([('quality_id', '=', self.id)])
            action['views'] = [(form_view, 'form')]
            action['res_id'] = quality_id and quality_id.id or False
        return action

    def _compute_ous_in_count(selfs):
        for self in selfs:
            self.ous_in_count = self.env['jl.mes.ous.in'].search_count([('quality_id','=',self.id)])

    name = fields.Char('单据编号',
                       index=True,
                       copy=False,
                       default=lambda self: self.env['ir.sequence'].next_by_code('jl.ous.quality'),
                       help="委外质量检验单的唯一编号，当创建时它会自动生成下一个编号。")
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
    goods_id = fields.Many2one('goods', '商品', ondelete='cascade', help='购货商品')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    uom_id = fields.Many2one('uom', related='goods_id.uom_id', ondelete='cascade')
    qty = fields.Float('数量', digits='Quantity', track_visibility='always',default=0)
    qualified_qty = fields.Float('合格数量', digits='Quantity', track_visibility='always')
    no_qty = fields.Float('不合格数量', digits='Quantity',default=0 )
    in_qty = fields.Float('入库数量', digits='Quantity',default=0 )
    bool = fields.Boolean('是否返工',ondelete='cascade')
    type = fields.Selection(string=u'出入库方式',selection=[('in', '入库'), ('out', '出库')])
    warehouse_id = fields.Many2one('warehouse', '仓库', help='关联仓库，购票物品存储某个仓库')
    reason = fields.Char('产品不合格原因')
    date = fields.Date('单据日期', default=lambda self: fields.Date.context_today(self), required=True)
    state = fields.Selection(STATE, '确认状态', help='单据状态', default='draft', track_visibility='always')
    approve_uid = fields.Many2one('res.users',
                                  '确认人',
                                  copy=False,
                                  ondelete='restrict',
                                  help='确认单据的人')
    approve_date = fields.Datetime('确认日期', copy=False)
    note = fields.Char('备注')
    ous_in_count = fields.Integer('委外生产入库单数量', compute='_compute_ous_in_count')