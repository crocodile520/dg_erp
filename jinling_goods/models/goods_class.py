from odoo import fields,api,models



class GoodsClass(models.Model):
    _name = 'goods.class'
    _description = '商品分类'
    _sql_constraints = [('name_unique', 'unique(name)', '名称不可以重复')]


    name = fields.Char('名称',index=True, ondelete='cascade',help='分类名称')
    note = fields.Char('备注',help='备注情况')