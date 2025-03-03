from odoo import fields, models, api
from odoo.exceptions import UserError

class JlApprovalProcessNode(models.Model):
    _name = 'jl.approval.process.node'
    _description = '审批节点'
    _order = 'sequence'
    
    name = fields.Char('节点名称', required=True)
    process_id = fields.Many2one('jl.approval.process', '审批流程', required=True, ondelete='cascade')
    sequence = fields.Integer('序号', default=10)
    user_ids = fields.Many2many('res.users', string='审批人')
    department_id = fields.Many2one('hr.department', '审批部门')
    position_id = fields.Many2one('hr.job', '审批岗位')
    multi_user_type = fields.Selection([
        ('any', '任意一人'),
        ('all', '所有人')
    ], string='多人审批类型', default='any')
    approve_type = fields.Selection([
        ('user', '指定用户'),
        ('department', '指定部门'),
        ('position', '指定岗位')
    ], string='审批类型', default='user', required=True)
    
    @api.onchange('approve_type')
    def _onchange_approve_type(self):
        """审批类型变更时清空其他字段"""
        if self.approve_type == 'user':
            self.department_id = False
            self.position_id = False
        elif self.approve_type == 'department':
            self.user_ids = False
            self.position_id = False
        else:
            self.user_ids = False
            self.department_id = False 