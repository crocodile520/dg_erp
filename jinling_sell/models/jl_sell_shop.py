# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/2/27
Description: jl_sell_shop
"""

from odoo import api,models,fields
from odoo.exceptions import UserError

class SellShop(models.Model):
    _name = 'sell.shop'
    _description = '销售店铺'
    _inherit = ['mail.thread']

    name = fields.Char('店铺名称')
    user_id = fields.Many2one(
        'hr.employee',
        '销售员',
        ondelete='restrict',
        readonly=False,
        default=lambda self: self.env.user.employee_id.id,
        help='销售员',
    )