from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import convert_file
from lxml import etree
import logging

_logger = logging.getLogger(__name__)

# 保存原始的setup_base方法
Model = models.Model
original_setup_base = Model._setup_base

@api.model
def _setup_base(self):
    """扩展setup_base方法，添加审批字段"""
    original_setup_base(self)
    setup_approval_fields(self)

def setup_approval_fields(self):
    """添加审批相关字段"""
    def add_field(name, field):
        if name not in self._fields:
            self._add_field(name, field)
    
    # 检查模型是否需要审批功能
    self._cr.execute("""
        SELECT COUNT(*) FROM jl_approval_process ap 
        JOIN ir_model im ON ap.model_id = im.id 
        WHERE im.model = %s AND ap.active = true
    """, (self._name,))
    
    if self._cr.fetchone()[0] > 0:
        # 添加审批字段
        add_field('approval_state', fields.Selection([
            ('draft', '草稿'),
            ('pending', '审批中'),
            ('approved', '已批准'),
            ('rejected', '已拒绝')
        ], string='审批状态', default='draft', tracking=True, copy=False))
        
        add_field('approval_record_id', fields.Many2one(
            'jl.approval.record', '审批记录', copy=False))
            
        add_field('approve_uid', fields.Many2one(
            'res.users', '确认人', copy=False))
            
        add_field('approve_date', fields.Datetime(
            '确认日期', copy=False))

@api.model
def _create_approval_view(self):
    """为模型创建审批相关视图"""
    model_name = self._name
    
    # 查找模型的表单视图
    form_view = self.env['ir.ui.view'].search([
        ('model', '=', model_name),
        ('type', '=', 'form')
    ], limit=1)
    
    if not form_view:
        return
            
    # 创建继承视图
    inherit_view_xml = f"""<?xml version="1.0"?>
        <odoo>
            <record id="view_{model_name.replace('.','_')}_form_approval_inherit" model="ir.ui.view">
                <field name="name">{model_name}.form.approval.inherit</field>
                <field name="model">{model_name}</field>
                <field name="inherit_id" ref="{form_view.xml_id}"/>
                <field name="arch" type="xml">
                    <xpath expr="//header" position="inside">
                        <button name="action_submit_approval" 
                                string="提交审批" 
                                type="object"
                                class="oe_highlight"
                                attrs="{{'invisible': [('approval_state', '!=', 'draft')]}}"/>
                        <field name="approval_state" widget="statusbar"/>
                    </xpath>
                    <xpath expr="//sheet" position="inside">
                        <div class="oe_button_box" name="button_box">
                            <button name="action_view_approval_record"
                                    type="object"
                                    class="oe_stat_button"
                                    icon="fa-tasks"
                                    attrs="{{'invisible': [('approval_record_id', '=', False)]}}">
                                <field name="approval_record_id" string="审批记录" widget="statinfo"/>
                            </button>
                        </div>
                    </xpath>
                    <xpath expr="//sheet" position="after">
                        <div class="oe_chatter">
                            <field name="message_follower_ids"/>
                            <field name="message_ids"/>
                        </div>
                    </xpath>
                </field>
            </record>
        </odoo>
    """
    
    # 创建或更新视图
    try:
        tools.convert_file(
            self.env.cr, 'jinling_approval',
            'approval_view.xml',
            inherit_view_xml.encode(),
            {}, 'init', noupdate=True,
            kind='model'
        )
    except Exception as e:
        _logger.error('Failed to create approval view: %s', e)

@api.model
def action_submit_approval(self):
    """提交审批"""
    if self.approval_state != 'draft':
        raise ValidationError(_('只有草稿状态可以提交审批！'))
        
    # 查找审批流程
    process = self.env['jl.approval.process'].search([
        ('model_name', '=', self._name),
        ('active', '=', True)
    ], limit=1)
    
    if not process:
        raise ValidationError(_('未找到有效的审批流程！'))
        
    # 创建审批记录
    record = self.env['jl.approval.record'].create({
        'process_id': process.id,
        'res_id': self.id,
        'res_name': self.display_name,
    })
    
    # 更新状态
    self.write({
        'approval_state': 'pending',
        'approval_record_id': record.id
    })
    
    return True

@api.model
def action_view_approval_record(self):
    """查看审批记录"""
    if not self.approval_record_id:
        return
            
    return {
        'name': _('审批记录'),
        'type': 'ir.actions.act_window',
        'res_model': 'jl.approval.record',
        'res_id': self.approval_record_id.id,
        'view_mode': 'form',
        'target': 'current',
    }

# 替换原始的setup_base方法
Model._setup_base = _setup_base
Model._create_approval_view = _create_approval_view
Model.action_submit_approval = action_submit_approval
Model.action_view_approval_record = action_view_approval_record

# 保存原始的write方法
write_origin = models.BaseModel.write

def write(self, vals):
    """扩展write方法，添加审批限制"""
    check_approval_write(self, vals)
    return write_origin(self, vals)

def check_approval_write(self, vals):
    """检查审批状态下的写入权限"""
    # 忽略关注者更新
    if len(vals) == 1 and list(vals.keys())[0] == 'message_follower_ids':
        return
        
    # 检查是否有审批流程
    self._cr.execute("""
        SELECT ap.id FROM jl_approval_process ap 
        JOIN ir_model im ON ap.model_id = im.id 
        WHERE im.model = %s AND ap.active = true
    """, (self._name,))
    
    if not self._cr.fetchone():
        return
        
    for record in self:
        if record.approval_state == 'pending':
            raise ValidationError('当前单据正在审批中，不允许修改！')
        elif record.approval_state in ['approved', 'rejected']:
            raise ValidationError('当前单据审批已结束，不允许修改！')

# 替换原始的write方法
models.BaseModel.write = write

# 保存原始的unlink方法
unlink_origin = models.BaseModel.unlink

def unlink(self):
    """扩展unlink方法，添加审批限制"""
    check_approval_unlink(self)
    return unlink_origin(self)

def check_approval_unlink(self):
    """检查审批状态下的删除权限"""
    # 检查是否有审批流程
    self._cr.execute("""
        SELECT ap.id FROM jl_approval_process ap 
        JOIN ir_model im ON ap.model_id = im.id 
        WHERE im.model = %s AND ap.active = true
    """, (self._name,))
    
    if not self._cr.fetchone():
        return
        
    for record in self:
        if record.approval_state != 'draft':
            raise ValidationError('只有草稿状态的单据才能删除！')

# 替换原始的unlink方法
models.BaseModel.unlink = unlink

class ApprovalMixin(models.AbstractModel):
    _name = 'approval.mixin'
    _description = '审批混入类'
    _inherit = ['mail.thread']

    approval_state = fields.Selection([
        ('draft', '草稿'),
        ('pending', '审批中'),
        ('approved', '已批准'),
        ('rejected', '已拒绝')
    ], string='审批状态', default='draft', tracking=True, copy=False)
    
    approval_record_id = fields.Many2one('jl.approval.record', '审批记录', copy=False)
    approve_uid = fields.Many2one('res.users', '确认人', copy=False)
    approve_date = fields.Datetime('确认日期', copy=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """扩展视图获取方法，添加审批相关元素"""
        result = super(ApprovalMixin, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu
        )
        
        # 检查是否需要添加审批功能
        self._cr.execute("""
            SELECT COUNT(*) FROM jl_approval_process ap 
            JOIN ir_model im ON ap.model_id = im.id 
            WHERE im.model = %s AND ap.active = true
        """, (self._name,))
        
        if self._cr.fetchone()[0] > 0:
            if view_type == 'form':
                modify_form_view(self, result)
            elif view_type == 'tree':
                modify_tree_view(self, result)
                
        return result

    def modify_form_view(self, result):
        """修改表单视图，添加审批按钮和状态"""
        try:
            root = etree.fromstring(result['arch'])
            
            # 添加审批字段到fields
            fields_info = self.fields_get(['approval_state', 'approval_record_id', 'approve_uid', 'approve_date'])
            result['fields'].update(fields_info)
            
            # 处理header
            headers = root.xpath('//header')
            if not headers:
                header = etree.Element('header')
                root.insert(0, header)
            else:
                header = headers[0]
                
            # 添加提交审批按钮
            submit_button = etree.Element('button')
            submit_button.set('name', 'action_submit_approval')
            submit_button.set('string', '提交审批')
            submit_button.set('type', 'object')
            submit_button.set('class', 'oe_highlight')
            submit_button.set('attrs', "{'invisible': [('approval_state', '!=', 'draft')]}")
            header.insert(0, submit_button)
            
            # 添加状态栏
            state_field = etree.Element('field')
            state_field.set('name', 'approval_state')
            state_field.set('widget', 'statusbar')
            state_field.set('statusbar_visible', 'draft,pending,approved,rejected')
            header.append(state_field)
            
            # 处理button_box
            sheets = root.xpath('//sheet')
            if sheets:
                sheet = sheets[0]
                button_boxs = sheet.xpath('//div[@class="oe_button_box"]')
                if not button_boxs:
                    button_box = etree.Element('div')
                    button_box.set('class', 'oe_button_box')
                    button_box.set('name', 'button_box')
                    sheet.insert(0, button_box)
                else:
                    button_box = button_boxs[0]
                    
                # 添加审批记录按钮
                record_button = etree.Element('button')
                record_button.set('name', 'action_view_approval_record')
                record_button.set('type', 'object')
                record_button.set('class', 'oe_stat_button')
                record_button.set('icon', 'fa-tasks')
                record_button.set('attrs', "{'invisible': [('approval_record_id', '=', False)]}")
                
                record_field = etree.Element('field')
                record_field.set('name', 'approval_record_id')
                record_field.set('string', '审批记录')
                record_field.set('widget', 'statinfo')
                
                record_button.append(record_field)
                button_box.append(record_button)
            
            # 添加消息区域
            form = root.xpath('//form')[0]
            chatters = form.xpath('//div[@class="oe_chatter"]')
            if not chatters:
                chatter = etree.Element('div')
                chatter.set('class', 'oe_chatter')
                
                followers = etree.Element('field')
                followers.set('name', 'message_follower_ids')
                followers.set('widget', 'mail_followers')
                chatter.append(followers)
                
                thread = etree.Element('field')
                thread.set('name', 'message_ids')
                thread.set('widget', 'mail_thread')
                chatter.append(thread)
                
                form.append(chatter)
            
            result['arch'] = etree.tostring(root)
            
        except Exception as e:
            _logger.error('Failed to modify form view: %s', str(e))

    def modify_tree_view(self, result):
        """修改列表视图，添加审批状态列"""
        try:
            root = etree.fromstring(result['arch'])
            
            # 添加审批字段到fields
            fields_info = self.fields_get(['approval_state'])
            result['fields'].update(fields_info)
            
            # 添加审批状态字段
            field = etree.Element('field')
            field.set('name', 'approval_state')
            root.append(field)
            
            # 添加状态颜色
            root.set('decoration-info', "approval_state == 'draft'")
            root.set('decoration-warning', "approval_state == 'pending'")
            root.set('decoration-success', "approval_state == 'approved'")
            root.set('decoration-danger', "approval_state == 'rejected'")
            
            result['arch'] = etree.tostring(root)
            
        except Exception as e:
            _logger.error('Failed to modify tree view: %s', str(e))

    def action_submit_approval(self):
        """提交审批"""
        self.ensure_one()
        if self.approval_state != 'draft':
            raise ValidationError(_('只有草稿状态可以提交审批！'))
            
        # 查找审批流程
        process = self.env['jl.approval.process'].search([
            ('model_name', '=', self._name),
            ('active', '=', True)
        ], limit=1)
        
        if not process:
            raise ValidationError(_('未找到有效的审批流程！'))
            
        # 创建审批记录
        record = self.env['jl.approval.record'].create({
            'process_id': process.id,
            'res_id': self.id,
            'res_name': self.display_name,
        })
        
        # 更新状态
        self.write({
            'approval_state': 'pending',
            'approval_record_id': record.id
        })
        
        return True

    def action_view_approval_record(self):
        """查看审批记录"""
        self.ensure_one()
        if not self.approval_record_id:
            return
            
        return {
            'name': _('审批记录'),
            'type': 'ir.actions.act_window',
            'res_model': 'jl.approval.record',
            'res_id': self.approval_record_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _approval_done(self):
        """审批通过"""
        self.write({
            'approval_state': 'approved',
            'approve_uid': self.env.uid,
            'approve_date': fields.Datetime.now()
        })
        
    def _approval_reject(self):
        """审批拒绝"""
        self.write({
            'approval_state': 'rejected',
            'approve_uid': self.env.uid,
            'approve_date': fields.Datetime.now()
        })