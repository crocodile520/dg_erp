from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class JlApprovalModel(models.Model):
    _name = 'jl.approval.model'
    _description = '审批模型同步表'
    _inherit = ['mail.thread']
    
    name = fields.Char('模型名称', required=True)
    model_id = fields.Many2one('ir.model', '关联模型', required=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.model', string='模型标识', store=True)
    process_id = fields.Many2one('jl.approval.process', '审批流程')
    field_ids = fields.One2many('jl.approval.model.field', 'model_id', '同步字段')
    active = fields.Boolean('是否激活', default=True)
    state = fields.Selection([
        ('draft', '草稿'),
        ('synced', '已同步'),
        ('cancel', '已取消')
    ], string='状态', default='draft', tracking=True)
    
    _sql_constraints = [
        ('model_unique', 'unique(model_id)', '同一个模型不能重复同步!')
    ]
    
    def action_sync(self):
        """同步审批功能到目标模型"""
        self.ensure_one()
        if not self.model_id:
            raise UserError(_('请先选择要同步的模型！'))
            
        try:
            # 动态创建继承模型
            model_name = self.model_name
            inherit_name = f'jl.approval.{model_name.replace(".", "_")}'
            
            # 检查是否已存在继承模型
            if inherit_name in self.env:
                # 如果存在，先删除旧的
                self.env['ir.model'].search([('model', '=', inherit_name)]).unlink()
            
            # 创建新的继承模型
            model_data = {
                'name': f'Approval {self.model_id.name}',
                'model': inherit_name,
                'inherit_model_ids': [(6, 0, [self.model_id.id])],
                'field_id': [
                    (0, 0, {
                        'name': 'approval_state',
                        'field_description': '审批状态',
                        'ttype': 'selection',
                        'selection': "[('draft', '草稿'), ('pending', '审批中'), ('approved', '已批准'), ('rejected', '已拒绝')]",
                        'default': "'draft'",
                    }),
                    (0, 0, {
                        'name': 'approval_record_id',
                        'field_description': '审批记录',
                        'ttype': 'many2one',
                        'relation': 'jl.approval.record',
                    }),
                ],
            }
            
            # 创建继承模型
            self.env['ir.model'].create(model_data)
            
            # 创建继承视图
            view_data = {
                'name': f'{model_name}.form.approval.inherit',
                'type': 'form',
                'model': model_name,
                'mode': 'extension',
                'inherit_id': self.env['ir.ui.view'].search([
                    ('model', '=', model_name),
                    ('type', '=', 'form'),
                    ('mode', '=', 'primary')
                ], limit=1).id,
                'arch': """
                    <data>
                        <header position="inside">
                            <button name="action_submit_approval" 
                                    string="提交审批" 
                                    type="object"
                                    class="oe_highlight"
                                    attrs="{'invisible': [('approval_state', '!=', 'draft')]}"/>
                            <field name="approval_state" widget="statusbar"
                                   statusbar_visible="draft,pending,approved,rejected"/>
                        </header>
                        <sheet position="inside">
                            <div class="oe_button_box" name="button_box">
                                <button name="action_view_approval_record"
                                        type="object"
                                        class="oe_stat_button"
                                        icon="fa-tasks"
                                        attrs="{'invisible': [('approval_record_id', '=', False)]}">
                                    <field name="approval_record_id" string="审批记录" widget="statinfo"/>
                                </button>
                            </div>
                        </sheet>
                    </data>
                """,
            }
            
            self.env['ir.ui.view'].create(view_data)
            
            # 更新状态
            self.write({'state': 'synced'})
            
            # 升级模块
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('成功'),
                    'message': _('审批功能同步成功'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error('Sync approval failed: %s', str(e))
            raise UserError(_('同步失败：%s') % str(e))
            
    def action_cancel(self):
        """取消同步"""
        self.ensure_one()
        try:
            # 删除继承模型
            inherit_name = f'jl.approval.{self.model_name.replace(".", "_")}'
            self.env['ir.model'].search([('model', '=', inherit_name)]).unlink()
            
            # 删除继承视图
            self.env['ir.ui.view'].search([
                ('name', '=', f'{self.model_name}.form.approval.inherit'),
                ('model', '=', self.model_name)
            ]).unlink()
            
            # 更新状态
            self.write({'state': 'cancel'})
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('成功'),
                    'message': _('审批功能已取消同步'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error('Cancel sync failed: %s', str(e))
            raise UserError(_('取消同步失败：%s') % str(e))
        
    def action_draft(self):
        """重置为草稿"""
        self.write({'state': 'draft'})

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