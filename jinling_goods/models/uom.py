from odoo import fields,models,api



class Uom(models.Model):
    _name = 'uom'
    _description = '单位'

    name = fields.Char('名称',help='单位名称')
