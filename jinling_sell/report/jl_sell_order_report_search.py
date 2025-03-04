# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/3/4
Description: jl_sell_order_report_search
"""
# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/3/4
Description: jl_sell_report
"""
# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/3/4
Description: jl_buy_order_report
"""
from odoo import api, fields, models, tools


class JlSellOrderReportSearch(models.Model):
    _name = 'jl.sell.order.report.search'
    _description = '销售员统计表'
    _auto = False

    goods_id = fields.Many2one('goods', '商品', ondelete='cascade', help='购货商品')
    user_id = fields.Many2one('hr.employee', '销售员', ondelete='cascade', help='销售员')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    uom_id = fields.Many2one('uom', related='goods_id.uom_id', ondelete='cascade')
    goods_class_id = fields.Many2one('goods.class', related='goods_id.goods_class_id', ondelete='cascade')
    qty = fields.Float('下单数量', digits='Quantity', track_visibility='always', default=0)
    out_qty = fields.Float('已发货数量', digits='Quantity', track_visibility='always', default=0)
    amount = fields.Float('总金额', digits='Quantity', track_visibility='always', default=0)
    subtotal = fields.Float('总价税合计', digits='Quantity', track_visibility='always', default=0)

    def init(self):
        cr = self._cr
        tools.drop_view_if_exists(cr, 'jl_sell_order_report_search')
        cr.execute(f'''
                    CREATE OR REPLACE VIEW jl_sell_order_report_search as(
                    select row_number() over(order by b.id) id,b.id as goods_id,b.user_id,sum(coalesce(b.qty,0)) as qty,sum(coalesce(b.out_qty,0)) as out_qty,sum(coalesce(b.amount,0)) as amount,sum(coalesce(b.subtotal,0)) as subtotal
                    from 
                    (select g.id,jso.user_id,jsol.qty,jsol.out_qty,jsol.qty * jsol.price as amount,(jsol.qty * (jsol.price * (1 + (jsol.tax_rate / 100)))) as subtotal
                        from sell_order jso 
                        left join sell_order_line jsol on jsol.order_id = jso.id
                        left join goods g on g.id = jsol.goods_id
                         where  jso.state = 'done') as b
                    group by b.id,b.user_id
                    )''')

    def update_report_view(self, start_date, end_date):
        cr = self._cr
        start_date = start_date or '2025-01-31'
        end_date = end_date or '2025-02-20'
        tools.drop_view_if_exists(cr, 'jl_buy_order_report_search')
        cr.execute(f'''
                    CREATE OR REPLACE VIEW jl_sell_order_report_search as(
                    select row_number() over(order by b.id) id,b.id as goods_id,b.user_id,sum(coalesce(b.qty,0)) as qty,sum(coalesce(b.out_qty,0)) as out_qty,sum(coalesce(b.amount,0)) as amount,sum(coalesce(b.subtotal,0)) as subtotal
                    from 
                    (select g.id,jso.user_id,jsol.qty,jsol.out_qty,jsol.qty * jsol.price as amount,(jsol.qty * (jsol.price * (1 + (jsol.tax_rate / 100)))) as subtotal
                        from sell_order jso 
                        left join sell_order_line jsol on jsol.order_id = jso.id
                        left join goods g on g.id = jsol.goods_id
                         where  jso.state = 'done' AND jso.date >= '{start_date}' AND jso.date <= '{end_date}' ) as b
                    group by b.id,b.user_id
                    )''')
