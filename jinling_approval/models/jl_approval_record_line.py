from odoo import fields, models

class JlApprovalRecordLine(models.Model):
    _name = 'jl.approval.record.line'
    _description = '审批记录明细'
    _order = 'approve_date desc'
    
    record_id = fields.Many2one('jl.approval.record', '审批记录', ondelete='cascade')
    node_id = fields.Many2one('jl.approval.process.node', '审批节点')
    user_id = fields.Many2one('res.users', '审批人')
    result = fields.Selection([
        ('approved', '通过'),
        ('rejected', '拒绝')
    ], string='审批结果')
    approve_date = fields.Datetime('审批时间', default=fields.Datetime.now)
    note = fields.Text('备注') 