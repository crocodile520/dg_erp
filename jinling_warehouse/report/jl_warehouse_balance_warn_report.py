# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/2/26
Description: jl_warehouse_balance_warn_report
"""
from odoo import api,fields,models,tools


class JlWarehouseBalanceWarnReport(models.Model):
    _name = 'jl.warehouse.balance.warn.report'
    _description = '库存余额告警表'
    _auto = False

    goods_id = fields.Many2one('goods', '商品', ondelete='cascade', help='购货商品')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    uom_id = fields.Many2one('uom', related='goods_id.uom_id', ondelete='cascade')
    goods_class_id = fields.Many2one('goods.class', related='goods_id.goods_class_id', ondelete='cascade')
    ms1_qty = fields.Float('成品仓库存数量', digits='Quantity', track_visibility='always', default=0)
    ms2_qty = fields.Float('PCB板仓数量', digits='Quantity', track_visibility='always', default=0)
    ms3_qty = fields.Float('原材料仓库存数量', digits='Quantity', track_visibility='always', default=0)

    def init(self):
        cr = self._cr
        tools.drop_view_if_exists(cr, 'jl_warehouse_balance_warn_report')
        cr.execute('''
                    CREATE OR REPLACE VIEW jl_warehouse_balance_warn_report as(
                    select row_number() over(order by jwbr.id) id,jwbr.goods_id as goods_id,jwbr.ms1_qty,jwbr.ms2_qty,jwbr.ms3_qty 
                    from jl_warehouse_balance_report jwbr
                    where jwbr.ms1_qty < 1000 or jwbr.ms2_qty < 1000 or jwbr.ms2_qty < 1000
                    )''')