# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/3/4
Description: jl_buy_order_wizards_view
"""
from odoo import models, fields, api
from datetime import date
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

class JlSellOrderWizard(models.TransientModel):
    _name = 'jl.sell.order.wizard'
    _description = '销售员统计筛选'

    goods_id = fields.Many2one('goods', string="商品")
    user_id = fields.Many2one('hr.employee', string="销售员")
    start_date = fields.Date('开始时间',required=True)
    end_date = fields.Date('结束时间',required=True)

    def button_confirm(self):
        if self.end_date < self.start_date:
            raise UserError('开始日期不能大于结束日期！\n 所选的开始日期:%s 结束日期:%s' %
                            (self.start_date, self.end_date))
        domain = []
        if self.goods_id:
            domain = [('goods_id', '=', self.goods_id.id),
                      ]
        if self.user_id:
            domain.append(('user_id','=',self.user_id.id))

        # 更新视图
        self.env['jl.sell.order.report.search'].update_report_view(self.start_date, self.end_date)
        view = self.env.ref('jinling_sell.jl_sell_order_report_search_tree')


        return {
            'name': '销售员统计筛选',
            'view_mode': 'tree',
            'res_model': 'jl.sell.order.report.search',
            'type': 'ir.actions.act_window',
            'views': [(view.id, 'tree')],
            'context':{'start_date':self.start_date,'end_date':self.end_date},
            'domain': domain,
            'limit': 200,
            'target': 'main',
        }
