from odoo import api,fields,models




class Tool(models.Model):
    _name = 'tool'
    _description = '工具'

    _sql_constraints = [('name_unique', 'unique(name)', '名称不可以重复')]

    name = fields.Char('名称')
    specs= fields.Char('规格型号')
    uom_id = fields.Many2one('uom', '单位')
    surface = fields.Char('颜色')