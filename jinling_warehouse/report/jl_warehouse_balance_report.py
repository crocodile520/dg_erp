from odoo import api,fields,models,tools


class JlWarehouseBalanceReport(models.Model):
    _name = 'jl.warehouse.balance.report'
    _description = '库存余额表'
    _auto = False

    goods_id = fields.Many2one('goods', '商品', ondelete='cascade', help='购货商品')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    uom_id = fields.Many2one('uom', related='goods_id.uom_id', ondelete='cascade')
    ms1_qty = fields.Float('成品仓库存数量', digits='Quantity', track_visibility='always', default=0)
    ms2_qty = fields.Float('半成品仓库存数量', digits='Quantity', track_visibility='always', default=0)
    ms3_qty = fields.Float('原材料仓库存数量', digits='Quantity', track_visibility='always', default=0)
    ms4_qty = fields.Float('废品仓库存数量', digits='Quantity', track_visibility='always', default=0)
    gms1_qty = fields.Float('国外成品仓库存数量', digits='Quantity', track_visibility='always', default=0)
    gms2_qty = fields.Float('国外半成品仓库存数量', digits='Quantity', track_visibility='always', default=0)
    gms3_qty = fields.Float('国外原材料仓库存数量', digits='Quantity', track_visibility='always', default=0)
    gms4_qty = fields.Float('国外废品仓库存数量', digits='Quantity', track_visibility='always', default=0)

    def init(self):
        cr = self._cr
        tools.drop_view_if_exists(cr, 'jl_warehouse_balance_report')
        cr.execute('''
                    CREATE OR REPLACE VIEW jl_warehouse_balance_report as(
                    select row_number() over(order by g.id) id,g.id as goods_id,sum(coalesce(ms1_qty,0)) as ms1_qty,sum(coalesce(ms2_qty,0)) as ms2_qty,
                        sum(coalesce(ms3_qty,0)) as ms3_qty,sum(coalesce(ms4_qty,0)) as ms4_qty,sum(coalesce(gms1_qty,0)) as gms1_qty,
                        sum(coalesce(gms2_qty,0)) as gms2_qty,sum(coalesce(gms3_qty,0)) as gms3_qty,sum(coalesce(gms4_qty,0)) as gms4_qty 
                        from goods g
                        left join (
                        select b.goods_id,
                        (case when b.warehouse_id is null then 0
                        when b.warehouse_id = 1 then coalesce(b.balance,0) end) as ms1_qty,
                        (case when b.warehouse_id is null then 0
                        when b.warehouse_id = 2 then coalesce(b.balance,0) end) as ms2_qty,
                        (case when b.warehouse_id is null then 0
                        when b.warehouse_id = 3 then coalesce(b.balance,0) end) as ms3_qty,
                        (case when b.warehouse_id is null then 0
                        when b.warehouse_id = 4 then coalesce(b.balance,0) end) as ms4_qty,
                        (case when b.warehouse_id is null then 0
                        when b.warehouse_id = 5 then coalesce(b.balance,0) end) as gms1_qty,
                        (case when b.warehouse_id is null then 0
                        when b.warehouse_id = 6 then coalesce(b.balance,0) end) as gms2_qty,
                        (case when b.warehouse_id is null then 0
                        when b.warehouse_id = 7 then coalesce(b.balance,0) end) as gms3_qty,
                        (case when b.warehouse_id is null then 0
                        when b.warehouse_id = 8 then coalesce(b.balance,0) end) as gms4_qty
                        from (
                        select a.goods_id,a.warehouse_id,coalesce(sum(a.in_qty) - sum(a.out_qty),0) balance 
                        from (
                        select jml.goods_id,
                        jml.warehouse_id,
                         (case when jml.type is null then 0 
                         when jml.type != 'out' then  coalesce(jml.goods_qty) else 0 end  ) as in_qty,
                        (case when jml.type is null then 0 
                         when jml.type != 'in' then  coalesce(jml.goods_qty) else 0 end  ) as out_qty
                            from jl_move_line jml
                            where jml.state ='done'
                            )a group by a.goods_id,a.warehouse_id
                            )b
                            ) c on c.goods_id = g.id group by g.id,g,goods_id
                    )''')