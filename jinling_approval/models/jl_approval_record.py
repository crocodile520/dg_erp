from odoo import api, fields, models
from odoo.exceptions import UserError

class JlApprovalRecord(models.Model):
    _name = 'jl.approval.record'
    _description = '审批记录'
    _inherit = ['mail.thread']
    
    name = fields.Char('审批编号', default=lambda self: self.env['ir.sequence'].next_by_code('jl.approval.record'))
    process_id = fields.Many2one('jl.approval.process', '审批流程', required=True, ondelete='cascade')
    model_id = fields.Many2one('ir.model', related='process_id.model_id', store=True)
    res_id = fields.Integer('关联记录ID')
    res_name = fields.Char('关联记录')
    current_node_id = fields.Many2one('jl.approval.process.node', '当前节点')
    state = fields.Selection([
        ('pending', '审批中'),
        ('approved', '已批准'),
        ('rejected', '已拒绝')
    ], string='状态', default='pending', tracking=True)
    line_ids = fields.One2many('jl.approval.record.line', 'record_id', '审批明细')
    
    @api.model
    def create(self, vals):
        """创建时设置第一个审批节点"""
        res = super(JlApprovalRecord, self).create(vals)
        if res.process_id.node_ids:
            res.current_node_id = res.process_id.node_ids[0]
        return res
    
    def action_approve(self):
        """审批通过"""
        self.ensure_one()
        if not self.current_node_id:
            raise UserError('没有需要审批的节点!')
            
        # 检查当前用户是否有权限审批
        if not self._check_approve_permission():
            raise UserError('您没有权限审批此节点!')
            
        # 创建审批记录行
        self.env['jl.approval.record.line'].create({
            'record_id': self.id,
            'node_id': self.current_node_id.id,
            'user_id': self.env.user.id,
            'result': 'approved'
        })
        
        # 获取下一个节点
        next_node = self._get_next_node()
        if next_node:
            self.current_node_id = next_node
        else:
            # 最后一个节点审批通过
            self.state = 'approved'
            # 更新原始记录状态
            if self.res_id:
                record = self.env[self.process_id.model_name].browse(self.res_id)
                record._approval_done()
                
    def action_reject(self):
        """拒绝审批"""
        self.ensure_one()
        if not self._check_approve_permission():
            raise UserError('您没有权限审批此节点!')
            
        self.env['jl.approval.record.line'].create({
            'record_id': self.id,
            'node_id': self.current_node_id.id,
            'user_id': self.env.user.id,
            'result': 'rejected'
        })
        self.state = 'rejected'
        # 更新原始记录状态
        if self.res_id:
            record = self.env[self.process_id.model_name].browse(self.res_id)
            record._approval_reject()
            
    def _check_approve_permission(self):
        """检查当前用户是否有权限审批"""
        self.ensure_one()
        if not self.current_node_id:
            return False
            
        node = self.current_node_id
        user = self.env.user
        
        if node.approve_type == 'user':
            return user.id in node.user_ids.ids
        elif node.approve_type == 'department':
            return user.employee_id.department_id == node.department_id
        elif node.approve_type == 'position':
            return user.employee_id.job_id == node.position_id
        return False
        
    def _get_next_node(self):
        """获取下一个审批节点"""
        self.ensure_one()
        if self.process_id.type == 'parallel':
            # 并行审批时,所有节点同时审批
            return False
            
        # 顺序审批时,按sequence获取下一个节点
        nodes = self.process_id.node_ids.sorted('sequence')
        current_index = nodes.ids.index(self.current_node_id.id)
        if current_index < len(nodes) - 1:
            return nodes[current_index + 1]
        return False 