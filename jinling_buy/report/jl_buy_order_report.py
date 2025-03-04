# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/3/4
Description: jl_buy_order_report
"""
from odoo import api,fields,models,tools


class JlBuyOrderReport(models.Model):
    _name = 'jl.buy.order.report'
    _description = '采购购货统计表'
    _auto = False

    goods_id = fields.Many2one('goods', '商品', ondelete='cascade', help='购货商品')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    uom_id = fields.Many2one('uom', related='goods_id.uom_id', ondelete='cascade')
    goods_class_id = fields.Many2one('goods.class', related='goods_id.goods_class_id', ondelete='cascade')
    qty = fields.Float('购买数量', digits='Quantity', track_visibility='always', default=0)
    buy_qty = fields.Float('已入库数量', digits='Quantity', track_visibility='always', default=0)
    amount = fields.Float('总金额', digits='Quantity', track_visibility='always', default=0)
    subtotal = fields.Float('总价税合计', digits='Quantity', track_visibility='always', default=0)

    def init(self):
        cr = self._cr
        tools.drop_view_if_exists(cr, 'jl_buy_order_report')
        cr.execute(f'''
                    CREATE OR REPLACE VIEW jl_buy_order_report as(
                    select row_number() over(order by b.id) id,b.id as goods_id,sum(coalesce(b.qty,0)) as qty,sum(coalesce(b.buy_qty,0)) as buy_qty,sum(coalesce(b.amount,0)) as amount,sum(coalesce(b.subtotal,0)) as subtotal
                    from 
                    (select g.id ,jbol.qty,jbol.buy_qty,jbol.qty * jbol.price as amount,(jbol.qty * (jbol.price * (1 + (jbol.tax_rate / 100)))) as subtotal
                        from jl_buy_order jbo 
                        left join jl_buy_order_line jbol on jbol.order_id = jbo.id
                        left join goods g on g.id = jbol.goods_id
                         where  jbo.state = 'done') as b
                    group by b.id
                    )''')


