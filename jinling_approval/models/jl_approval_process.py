from odoo import api, fields, models
from odoo.exceptions import UserError

class JlApprovalProcess(models.Model):
    _name = 'jl.approval.process'
    _description = '审批流程'
    _inherit = ['mail.thread']
    _order = 'id desc'  # 添加排序规则
    
    name = fields.Char('流程名称', required=True)
    model_id = fields.Many2one('ir.model', '关联模型', required=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.model', string='模型名称', store=True)
    active = fields.Boolean('是否激活', default=False)
    node_ids = fields.One2many('jl.approval.process.node', 'process_id', '审批节点')
    type = fields.Selection([
        ('sequence', '顺序审批'),
        ('parallel', '并行审批')
    ], string='审批方式', default='sequence', required=True)
    state = fields.Selection([
        ('draft', '草稿'),
        ('confirmed', '已确认')
    ], string='状态', default='draft', tracking=True)

    def init(self):
        """初始化方法，用于修复可能的数据问题"""
        # 确保所有记录都有状态值
        self.env.cr.execute("""
            UPDATE jl_approval_process 
            SET state = 'draft' 
            WHERE state IS NULL
        """)
        # 确保所有记录都有激活状态
        self.env.cr.execute("""
            UPDATE jl_approval_process 
            SET active = true 
            WHERE active IS NULL
        """)

    def action_save(self):
        """保存审批流程"""
        self.ensure_one()
        if not self.node_ids:
            raise UserError('请至少添加一个审批节点！')
        self.write({'state': 'confirmed'})
        return True
    
    def write(self, vals):
        """激活时自动添加审批字段"""
        if 'active' in vals and vals['active']:
            self._check_approval_fields()
        return super(JlApprovalProcess, self).write(vals)
        
    def _check_approval_fields(self):
        """检查并添加审批字段"""
        self.ensure_one()
        if not self.model_id:
            return
            
        model = self.env[self.model_name]
        
        # 检查是否已继承审批混入类
        if 'approval.mixin' not in model._inherit:
            model._inherit = list(model._inherit) + ['approval.mixin']
            
        # 添加审批相关字段
        if 'approval_state' not in model._fields:
            field = fields.Selection([
                ('draft', '草稿'),
                ('pending', '审批中'),
                ('approved', '已批准'), 
                ('rejected', '已拒绝')
            ], string='审批状态', default='draft', tracking=True)
            model._add_field('approval_state', field)
            
        if 'approval_record_id' not in model._fields:
            field = fields.Many2one('jl.approval.record', '审批记录')
            model._add_field('approval_record_id', field) 