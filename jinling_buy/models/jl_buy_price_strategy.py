# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/2/18
Description: jl_buy_price_strateg
"""

from odoo import fields,api,models
from odoo.exceptions import UserError
import datetime

STATES = [
    ('draft', '草稿'),
    ('done', '已确认'),
    ('onchange', '变更中'),
    ('review', '待复核'),
    ('lost', '失效')]




class JlBuyPriceStrategy(models.Model):
    _name = 'jl.buy.price.strategy'
    _description = '采购价格策略'
    _inherit = ['mail.thread']


    def _compute_attachment_number(self):
        """附件上传"""
        attachment_data = self.env['ir.attachment'].read_group(
            [('res_model', '=', self._name), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for expense in self:
            expense.attachment_number = attachment.get(expense.id, 0)

    def button_done(self):
        self.ensure_one()
        if self.state == 'done':
            raise UserError('单据已经确认，请勿重复确认')
        strategy_id = self.env['jl.buy.price.strategy'].search([('supplier_id','=',self.supplier_id.id),('goods_id','=',self.goods_id.id),('state','=','done'),('active','=','True')],limit=1)
        if strategy_id:
            raise UserError("价格策略供应商%s\商品%s已经存在，无需再创建" %(self.supplier_id.name,self.goods_id.name))
        self.state = 'done'

    def button_draft(self):
        self.ensure_one()
        if self.state == 'draft':
            raise UserError('单据已经撤销，请勿重复撤销')
        self.state = 'draft'

    @api.depends('price', 'tax_rate')
    def _compute_tax_price(selfs):
        for self in selfs:
            self.tax_price = round(self.price * (1 + (self.tax_rate / 100)),4)


    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)
    supplier_id = fields.Many2one('supplier', '供应商')
    currency_id = fields.Many2one('res.currency', '外币币别')
    goods_id = fields.Many2one('goods', '商品', required=True)
    goods_class_id = fields.Many2one('goods.class', string='商品分类', help="商品分类信息",
                                     related='goods_id.goods_class_id')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    uom_id = fields.Many2one('uom', string='单位', related='goods_id.uom_id', ondelete='restrict',
                             help='商品的计量单位')
    qty_start = fields.Float('最小起订量', default=0)
    qty_end = fields.Float('最大起订量', default=0)
    price = fields.Float('单价', digits='Price')
    tax_price = fields.Float('含税单价', digits='Price',compute='_compute_tax_price')
    # discount_rate = fields.Float('折扣率%', help='折扣率')
    tax_rate = fields.Float('税率(%)', digits='Amount', )
    start_date = fields.Date('开始日期', required=True,
                             default=lambda self: datetime.datetime.now())
    end_date = fields.Date('结束日期')
    # ref = fields.Reference(string='来源记录', selection='_select_objects')
    is_lock = fields.Boolean('价格锁定', default=False, track_visibility='always')
    state = fields.Selection(STATES, '确认状态',
                             help="价格策略的确认状态", index=True,
                             copy=False, default='draft',
                             track_visibility='always')
    active = fields.Boolean('启用', default=True)
    attachment_number = fields.Integer(compute='_compute_attachment_number', string='附件上传')