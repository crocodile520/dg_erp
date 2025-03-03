from odoo import fields, models

class JlApprovalModelField(models.Model):
    _name = 'jl.approval.model.field'
    _description = '审批模型字段'
    
    model_id = fields.Many2one('jl.approval.model', '审批模型', required=True, ondelete='cascade')
    field_name = fields.Char('字段名称', required=True)
    field_type = fields.Selection([
        ('char', '字符'),
        ('integer', '整数'),
        ('float', '浮点数'),
        ('boolean', '布尔值'),
        ('date', '日期'),
        ('datetime', '日期时间'),
        ('selection', '选择项'),
        ('many2one', '多对一'),
        ('one2many', '一对多'),
        ('many2many', '多对多')
    ], string='字段类型', required=True)
    field_label = fields.Char('字段标签', required=True)
    is_required = fields.Boolean('是否必填')
    selection_options = fields.Text('选择项选项', 
        help='格式: [("key1","值1"),("key2","值2")]')
    relation_model = fields.Char('关联模型',
        help='关系字段的关联模型名称') 