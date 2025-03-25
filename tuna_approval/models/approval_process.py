from odoo import api, fields, models, http, _
from odoo.exceptions import UserError
from lxml import etree
import logging
from odoo.addons.web.controllers.main import DataSet
from odoo.http import request
_logger = logging.getLogger(__name__)


class ApprovalProcess(models.Model):
    _name = 'approval.process'
    _description = '审批流程'
    _inherit = ['mail.thread']
    _order = 'id desc'  # 添加排序规则

    name = fields.Char('流程名称', required=True)
    model_id = fields.Many2one('ir.model', '关联模型', required=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.model', string='模型名称', store=True)
    active = fields.Boolean('是否激活', default=True)
    node_ids = fields.One2many('approval.process.node', 'process_id', '审批节点')
    line_ids = fields.One2many(comodel_name='approval.control.line', inverse_name='process_id',string=u'字段详情')
    type = fields.Selection([
        ('sequence', '顺序审批'),
        ('parallel', '并行审批')
    ], string='审批方式', default='sequence', required=True)
    state = fields.Selection([
        ('draft', '草稿'),
        ('confirmed', '已确认')
    ], string='状态', default='draft', tracking=True)


    python_done = fields.Char('审批通过执行方法',help='审批通过之后执行的方法，如果多个方法请用逗号隔开')
    python_rejected = fields.Char('审批拒绝之后执行的方法',help='审批拒绝之后执行的方法，如果多个方法请用逗号隔开')
    python_pending = fields.Char('提交审批执行的方法',help='审批中执行的方法，如果多个方法请用逗号隔开')
    python_restart = fields.Char('重新提交执行的方法',help='审批中执行的方法，如果多个方法请用逗号隔开')
    approval_field = fields.Many2one('ir.model.fields',
                                     domain="[('model_id', '=', model_id)]",
                                     help='选择用于跟踪审批状态的字段')
    ing_write = fields.Boolean(string="审批中允许编辑？", default=False)
    end_write = fields.Boolean(string="审批结束允许编辑？", default=False)
    start_button_ids = fields.Many2many('approval.model.button',
                                              'approval_control_model_start_rel',
                                              string='在审批前不能用的功能', domain="[('model_id', '=', model_id)]")
    button_ids = fields.Many2many('approval.model.button', string='在审批中不能用的功能',
                                        domain="[('model_id', '=', model_id)]")
    pass_button_ids = fields.Many2many('approval.model.button',
                                             'approval_control_model_pass_rel',
                                             string='在审批通过后不能用的功能', domain="[('model_id', '=', model_id)]")
    end_button_ids = fields.Many2many('approval.model.button', 'approval_control_model_end_rel',
                                            string='在审批拒绝后不能用的功能', domain="[('model_id', '=', model_id)]")
    remarks = fields.Text(string=u'备注')

    def init(self):
        """初始化方法，用于修复可能的数据问题"""
        # 确保所有记录都有状态值
        self.env.cr.execute("""
            UPDATE approval_process 
            SET state = 'draft' 
            WHERE state IS NULL
        """)
        # 确保所有记录都有激活状态
        self.env.cr.execute("""
            UPDATE approval_process 
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

    def action_cancel(self):
        self.ensure_one()
        self.state = 'draft'

    @api.onchange('model_id')
    def onchange_button_model_id(self):
        """
        选择的模型获取模型动作按钮
        """
        for rec in self:
            if rec.model_id:
                model_id = rec.model_id
                result = self.env[model_id.model].fields_view_get()
                root = etree.fromstring(result['arch'])
                for reocrd in root.xpath("//header/button"):
                    domain = [('model_id', '=', model_id.id), ('function', '=', reocrd.get('name'))]
                    model_buts = self.env['approval.model.button'].search(domain)
                    if not model_buts:
                        self.env['approval.model.button'].create({
                            'model_id': model_id.id,
                            'name': reocrd.get('string'),
                            'function': reocrd.get('name'),
                        })


class ApprovalProcessNode(models.Model):
    _name = 'approval.process.node'
    _description = '审批节点'
    _order = 'sequence'

    name = fields.Char('节点名称', required=True)
    process_id = fields.Many2one('approval.process', '审批流程', required=True, ondelete='cascade')
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
    node_fields = fields.One2many(comodel_name='approval.process.node.field', inverse_name='node_id',
                                  string='字段设定',
                                  copy=True, store=True)

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



class ApprovalControlLine(models.Model):
    _description = "审批配置字段信息"
    _name = 'approval.control.line'
    _rec_name = 'process_id'

    sequence = fields.Integer(string=u'序号')
    process_id = fields.Many2one(comodel_name='approval.process', string='审批流程', ondelete='set null')
    model_id = fields.Many2one(comodel_name='ir.model', string='模型', related="process_id.model_id")
    field_id = fields.Many2one(comodel_name='ir.model.fields', string='字段', required=True,ondelete='cascade',
                               domain="[('model_id', '=', model_id), ('ttype', 'not in', ['binary', 'boolean'])]")
    ttype = fields.Selection(selection='_get_field_types', string='类型')
    list_ids = fields.One2many(comodel_name='approval.control.list', inverse_name='line_id',string=u'一对多列表字段')


    @api.onchange('field_id')
    def _onchange_fisld_id(self):
        for res in self:
            res.ttype = res.field_id.ttype

    @api.model
    def _get_field_types(self):
        return sorted((key, key) for key in fields.MetaField.by_type)


class ApprovalControlList(models.Model):
    _description = '一对多列表字段'
    _name = 'approval.control.list'
    _rec_name = 'line_id'

    sequence = fields.Integer(string='序号')
    line_id = fields.Many2one(comodel_name='approval.control.line', string='审批配置字段', ondelete='set null')
    line_field_id = fields.Many2one(comodel_name='ir.model.fields', string='字段列表字段')
    field_id = fields.Many2one(comodel_name='ir.model.fields', string='字段',ondelete='cascade', required=True)


    @api.onchange('line_field_id')
    def onchange_line_field_id(self):
        for rec in self:
            model = self.env['ir.model'].sudo().search([('model', '=', rec.line_field_id.relation)], limit=1)
            domain = [('model_id', '=', model.id), ('ttype', 'not in', ['one2many', 'binary', 'boolean'])]
            return {'domain': {'field_id': domain}}


class ApprovalProcessNodeField(models.Model):
    _name = 'approval.process.node.field'
    _description = '字段控制'
    _rec_name = 'node_id'

    node_id = fields.Many2one(comodel_name='approval.process.node', string='审批节点', ondelete='cascade')
    model_id = fields.Many2one(comodel_name="ir.model", string="关联模型", store=True, related='node_id.process_id.model_id')
    field_id = fields.Many2one(comodel_name='ir.model.fields', string='字段', ondelete='cascade')
    readonly = fields.Boolean(string='只读', default=True)
    required = fields.Boolean(string='必填', default=False)
    invisible = fields.Boolean(string='隐藏', default=False)



class ApprovalButton(models.Model):
    _name = 'approval.model.button'
    _description = '审批模型按钮'
    _rec_name = 'name'

    model_id = fields.Many2one('ir.model', string='模型', index=True)
    model_model = fields.Char(string='模型名称', related='model_id.model', store=True, index=True)
    name = fields.Char(string="按钮方法名称", index=True)
    function = fields.Char(string='执行按钮方法', index=True)

    def name_get(self):
        return [(rec.id, "%s:%s" % (rec.model_id.name, rec.name)) for rec in self]


class OdooDataSet(http.Controller):

    @http.route('/web/dataset/call_button', type='json', auth="user")
    def call_button(self, model, method, args, kwargs):
        context = dict(request.env.context)
        context.update(kwargs.get('context', {}))
        kwargs['context'] = context
        ir_model = request.env['ir.model'].sudo().search([('model', '=', model)], limit=1)
        approval = request.env['approval.process'].sudo().search([('model_id', '=', ir_model.id),('state','=','confirmed'),('active', '=', True)], limit=1)
        if approval:
            # 获取当前单据的id
            if args[0]:
                res_id = args[0][0]
            else:
                params = args[1].get('params')
                res_id = params.get('id')
            # 获取当前单据
            now_model = request.env[model].sudo().search([('id', '=', res_id)])
            if now_model and now_model.x_approval_state == 'draft':
                start_but_functions = []
                for button in approval.start_button_ids:
                    start_but_functions.append(button.function)
                if method in start_but_functions:
                    raise UserError("单据当前没有提交审批,不能进行使用")
            elif now_model and now_model.x_approval_state == 'approval':
                but_functions = []
                for button in approval.button_ids:
                    but_functions.append(button.function)
                if method in but_functions:
                    raise UserError("单据当前还是处于审批中状态。不能进行使用！")
            elif now_model and now_model.x_approval_state == 'approved':
                pass_but_functions = []
                for button in approval.pass_button_ids:
                    pass_but_functions.append(button.function)
                if method in pass_but_functions:
                    raise UserError("单据当前设置了审批通过后不能进行使用。")
            elif now_model and now_model.x_approval_state == 'rejected':
                end_but_functions = []
                for button in approval.end_button_ids:
                    end_but_functions.append(button.function)
                if method in end_but_functions:
                    raise UserError("单据当前设置了审批拒绝后不能进行使用。")
        dataset = DataSet()
        return dataset.call_button(model, method, args, kwargs)