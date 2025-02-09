from odoo import fields,models,api



class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    partner_id = fields.Many2one('res.partner')
    @api.model
    def create(self, vals):
        fandx_stock_instance = super(HrEmployee,self).create(vals)
        for instance in fandx_stock_instance:
            if not instance.partner_id:
                instance.partner_id = instance.work_contact_id.id
        return fandx_stock_instance