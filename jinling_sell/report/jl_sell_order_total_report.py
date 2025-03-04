# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/3/4
Description: jl_sell_order_total_report
"""
from odoo import api,fields,models,tools


class JlSellOrderTotalReport(models.Model):
    _name = 'jl.sell.order.total.report'
    _description = '销售员总业绩统计表'
    _auto = False

    user_id = fields.Many2one('hr.employee', '销售员', ondelete='cascade', help='销售员')
    qty = fields.Float('下单数量', digits='Quantity', track_visibility='always', default=0)
    out_qty = fields.Float('已发货数量', digits='Quantity', track_visibility='always', default=0)
    amount = fields.Float('总金额', digits='Quantity', track_visibility='always', default=0)
    subtotal = fields.Float('总价税合计', digits='Quantity', track_visibility='always', default=0)

    def init(self):
        cr = self._cr
        tools.drop_view_if_exists(cr, 'jl_sell_order_total_report')
        cr.execute(f'''
                    CREATE OR REPLACE VIEW jl_sell_order_total_report as(
                    select row_number() over(order by b.user_id) id,b.user_id,sum(coalesce(b.qty,0)) as qty,sum(coalesce(b.out_qty,0)) as out_qty,sum(coalesce(b.amount,0)) as amount,sum(coalesce(b.subtotal,0)) as subtotal
                    from 
                    (select jso.user_id,jsol.qty,jsol.out_qty,jsol.qty * jsol.price as amount,(jsol.qty * (jsol.price * (1 + (jsol.tax_rate / 100)))) as subtotal
                        from sell_order jso 
                        left join sell_order_line jsol on jsol.order_id = jso.id
                        left join goods g on g.id = jsol.goods_id
                         where  jso.state = 'done') as b
                    group by b.user_id
                    )''')