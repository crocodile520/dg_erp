from odoo import api, fields, models
from odoo.exceptions import UserError
import json
import logging
_logger = logging.getLogger(__name__)


class ApprovalRecord(models.Model):
    _name = 'approval.record'
    _description = '审批记录'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char('审批编号', default=lambda self: self.env['ir.sequence'].next_by_code('approval.record'))
    process_id = fields.Many2one('approval.process', '审批流程', required=True, ondelete='cascade')
    model_id = fields.Many2one('ir.model', related='process_id.model_id', store=True)
    date = fields.Date('单据日期', default=lambda self: fields.Date.context_today(self), required=True)
    res_id = fields.Integer('关联记录ID')
    res_name = fields.Char('关联记录')
    order_name = fields.Char('订单号')
    current_node_id = fields.Many2one('approval.process.node', '当前节点',track_visibility='always')
    user_ids = fields.Many2many('res.users', string='用户当前审批人',track_visibility='always')
    department_id = fields.Many2one('hr.department', '部门当前审批人',track_visibility='always')
    position_id = fields.Many2one('hr.job', '岗位当前审批人',track_visibility='always')
    approve_type = fields.Selection([
        ('user', '指定用户'),
        ('department', '指定部门'),
        ('position', '指定岗位')
    ], string='审批类型', related='current_node_id.approve_type')
    state = fields.Selection([
        ('pending', '审批中'),
        ('approved', '已批准'),
        ('rejected', '已拒绝')
    ], string='状态', default='pending', tracking=True)
    line_ids = fields.One2many('approval.record.line', 'record_id', '审批明细')
    dynamic_data = fields.Json(string="动态数据")

    is_admin = fields.Boolean(
        string='是否是管理员',
        compute='_compute_is_admin',
        store=False
    )

    @api.depends()
    def _compute_is_admin(self):
        admin_group = self.env.ref('tuna_approval.approval_root_groups')
        for record in self:
            record.is_admin = self.env.user in admin_group.users

    def action_transfer_approval(self):
        return {
            'name': '选择用户',
            'type': 'ir.actions.act_window',
            'res_model': 'approval.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_record_id': self.id}
        }

    # 计算字段，判断当前用户是否在 user_ids 里
    is_current_user_allowed = fields.Boolean(
        compute='_compute_is_current_user_allowed',
        store=False
    )

    @api.depends('user_ids')
    def _compute_is_current_user_allowed(self):
        for record in self:
            record.is_current_user_allowed = self.env.user in record.user_ids

    # 解析后的动态数据
    dynamic_data_lines = fields.One2many(
        'approval.order.info.line.item',
        'item_id',
        string="动态数据行"
    )
    line_data_lines = fields.One2many(
        'approval.order.info.line',
        'record_id',
        string="订单明细行"
    )

    def _onchange_dynamic_data(self):
        # 清除已有数据
        self.dynamic_data_lines = [(5, 0, 0)]
        if isinstance(self.dynamic_data, dict):
            new_lines = []
            line_data = []
            for key, value in self.dynamic_data.items():
                if type(value) == list and value:
                    for record in value:
                        line_data.append((0,0,{
                            'line_value':record
                        }))
                else:
                    new_lines.append((0, 0, {
                        'field_key': key,
                        'field_value': str(value)
                    }))
            self.dynamic_data_lines = new_lines
            self.line_data_lines = line_data

    @api.model
    def create(self, vals):
        """创建时设置第一个审批节点"""
        res = super(ApprovalRecord, self).create(vals)
        if res.process_id.node_ids:
            res.current_node_id = res.process_id.node_ids[0]
            if res.current_node_id.approve_type == 'user':
                _logger.info(f'{res.current_node_id.user_ids}======')
                res.user_ids = res.current_node_id.user_ids
            elif res.current_node_id.approve_type == 'department':
                _logger.info(f'{res.current_node_id.department_id}======')
                res.department_id = res.current_node_id.department_id.id
            elif res.current_node_id.approve_type == 'position':
                res.position_id = res.current_node_id.position_id.id
        if self.res_id:
            pending_list = self._get_pending_button_method()
            record = self.env[self.process_id.model_name].browse(self.res_id)
            if pending_list:
                for line in pending_list:
                    button_method = line
                    # 用 getattr 获取方法对象，存在则调用
                    if hasattr(record, button_method):
                        getattr(record, button_method)()
        return res

    def action_approve(self):
        """审批通过"""
        self.ensure_one()
        if not self.current_node_id:
            raise UserError('没有需要审批的节点!')

        # 检查当前用户是否有权限审批
        if not self._check_approve_permission():
            raise UserError(f'您没有权限审批此节点')

        # 创建审批记录行
        self.env['approval.record.line'].create({
            'record_id': self.id,
            'node_id': self.current_node_id.id,
            'user_id': self.env.user.id,
            'result': 'approved'
        })

        # 获取下一个节点
        next_node = self._get_next_node()
        if next_node:
            self.current_node_id = next_node
            user = []
            name = None
            if self.current_node_id.approve_type == 'user':
                self.user_ids = self.current_node_id.user_ids
                user_ids = self.user_ids
                if user_ids:
                    for user_id in user_ids:
                        user.append(user_id.name)
                name = ','.join(user)
            elif self.current_node_id.approve_type == 'department':
                self.department_id = self.current_node_id.department_id.id
                name = self.current_node_id.department_id.name
            elif self.current_node_id.approve_type == 'position':
                self.position_id = self.current_node_id.position_id.id
                name = self.current_node_id.position_id.name
            record = self.env[self.process_id.model_name].browse(self.res_id)
            record.message_post(body=f"<span style='color: purple;'>等待 {name} 审批</span>", message_type='notification')
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        else:
            # 最后一个节点审批通过
            self.state = 'approved'
            # 更新原始记录状态
            if self.res_id:
                done_list = self._get_done_button_method()
                record = self.env[self.process_id.model_name].browse(self.res_id)
                if done_list:
                    for line in done_list:
                        button_method = line
                        # 用 getattr 获取方法对象，存在则调用
                        if hasattr(record, button_method):
                            getattr(record, button_method)()
                record.x_approval_state = 'approved'
                record.message_post(body="<span style='color: green;'>审批完成</span>", message_type='notification')

    def action_reject(self):
        """拒绝审批"""
        self.ensure_one()
        if not self._check_approve_permission():
            raise UserError(f'您没有权限审批此节点')

        self.env['approval.record.line'].create({
            'record_id': self.id,
            'node_id': self.current_node_id.id,
            'user_id': self.env.user.id,
            'result': 'rejected'
        })
        # 用带有 context 的方式修改状态，跳过审批状态检查
        self.state = 'rejected'
        # 更新原始记录状态
        if self.res_id:
            reject_list = self._get_reject_button_method()
            record = self.env[self.process_id.model_name].browse(self.res_id)
            if reject_list:
                for line in reject_list:
                    button_method = line
                    # 用 getattr 获取方法对象，存在则调用
                    if hasattr(record, button_method):
                        getattr(record, button_method)()
            record.x_approval_state = 'rejected'
            user = []
            name = None
            if self.current_node_id.approve_type == 'user':
                user_ids = self.user_ids
                if user_ids:
                    for user_id in user_ids:
                        user.append(user_id.name)
                name = ','.join(user)
            elif self.current_node_id.approve_type == 'department':
                name = self.current_node_id.department_id.name
            elif self.current_node_id.approve_type == 'position':
                name = self.current_node_id.position_id.name
            record = self.env[self.process_id.model_name].browse(self.res_id)
            record.message_post(body=f"<span style='color: red;'>{name}拒绝审批</span>", message_type='notification')

    def action_synchronous(self):
        """同步数据"""
        self.ensure_one()
        if self.state == 'approved':
            if self.res_id:
                done_list = self._get_done_button_method()
                record = self.env[self.process_id.model_name].browse(self.res_id)
                if done_list:
                    for line in done_list:
                        button_method = line
                        # 用 getattr 获取方法对象，存在则调用
                        if hasattr(record, button_method):
                            getattr(record, button_method)()
                record.x_approval_state = 'approved'
        elif self.state == 'approval':
            self.action_approve()
        elif self.state == 'rejected':
            if self.res_id:
                reject_list = self._get_reject_button_method()
                record = self.env[self.process_id.model_name].browse(self.res_id)
                if reject_list:
                    for line in reject_list:
                        button_method = line
                        # 用 getattr 获取方法对象，存在则调用
                        if hasattr(record, button_method):
                            getattr(record, button_method)()
                record.x_approval_state = 'rejected'

    def _check_approve_permission(self):
        """检查当前用户是否有权限审批"""
        self.ensure_one()
        if not self.current_node_id:
            return False

        node = self.current_node_id
        user = self.env.user

        if node.approve_type == 'user':
            if not self.is_admin:
                if user.id not in self.user_ids.ids:
                    user = []
                    node = self.current_node_id
                    user_ids = self.user_ids
                    if user_ids:
                        for user_id in user_ids:
                            user.append(user_id.name)
                    name = ','.join(user)
                    raise UserError(f'您没有权限审批此节点!当前审批人{name}')
                else:
                    return user.id in self.user_ids.ids
            return True
        elif node.approve_type == 'department':
            if not self.is_admin:
                if user.employee_id.department_id != node.department_id:
                    raise UserError(f'您没有权限审批此节点!当前部门审批')
                else:
                    return user.employee_id.department_id == node.department_id
            return True
        elif node.approve_type == 'position':
            if not self.is_admin:
                if user.employee_id.job_id != node.position_id:
                    raise UserError(f'您没有权限审批此节点!当前岗位审批')
                else:
                    return user.employee_id.job_id == node.position_id
            return True
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

    def _get_done_button_method(self):
        """获取审批成功之后的方法"""
        self.ensure_one()
        python_done = self.process_id.python_done
        if not python_done:
            return None
        button_list = python_done.split(',')
        return button_list

    def _get_pending_button_method(self):
        """获取审批之中的方法"""
        self.ensure_one()
        pending_done = self.process_id.python_pending
        if not pending_done:
            return None
        pending_list = pending_done.split(',')
        return pending_list

    def _get_reject_button_method(self):
        """获取拒绝审批之后的方法"""
        self.ensure_one()
        reject_done = self.process_id.python_rejected
        if not reject_done:
            return None
        reject_list = reject_done.split(',')
        return reject_list

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(ApprovalRecord, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                          submenu=submenu)

        if view_type == 'form':
            arch_base = res['arch']
            if self.order_info_ids:
                dynamic_fields = """
                        <page string="动态数据">
                            <group>
                    """
                for info in self.order_info_ids:
                    if info.dynamic_data:
                        for key, value in eval(info.dynamic_data).items():
                            dynamic_fields += f"""
                                    <field name="dynamic_data" string="{key}" nolabel="1" />
                                """
                dynamic_fields += """
                            </group>
                        </page>
                    """

                # 将动态视图插入到已存在的 notebook 结构中
                insert_position = arch_base.find('</notebook>')
                if insert_position != -1:
                    arch_base = arch_base[:insert_position] + dynamic_fields + arch_base[insert_position:]

                res['arch'] = arch_base

        return res



class ApprovalRecordLine(models.Model):
    _name = 'approval.record.line'
    _description = '审批记录明细'
    _inherit = ['mail.thread']
    _order = 'approve_date desc'

    record_id = fields.Many2one('approval.record', '审批记录', ondelete='cascade')
    node_id = fields.Many2one('approval.process.node', '审批节点')
    user_id = fields.Many2one('res.users', '审批人')
    result = fields.Selection([
        ('approved', '通过'),
        ('rejected', '拒绝')
    ], string='审批结果')
    approve_date = fields.Datetime('审批时间', default=fields.Datetime.now)
    note = fields.Text('备注',tracking=True)

class ApprovalOrderInfo(models.Model):
    _name = 'approval.order.info'
    _description = '审批信息内容'
    _inherit = ['mail.thread']

    record_id = fields.Many2one('approval.record', string='审批记录', ondelete='cascade')
    name = fields.Char(string="记录名称")



class ApprovalOrderInfoLineItem(models.Model):
    _name = 'approval.order.info.line.item'
    _description = '审批动态数据项'

    item_id = fields.Many2one('approval.record', string="审批信息")
    field_key = fields.Char(string="字段名")
    field_value = fields.Char(string="字段值")

class ApprovalOrderInfoLine(models.Model):
    _name = 'approval.order.info.line'
    _description = '订单明细行'

    record_id = fields.Many2one('approval.record', string="审批信息")
    line_value = fields.Json(string="订单明细",default='{}')

    line_value_parsed = fields.Char(string="Parsed Value", compute='_compute_line_value_parsed')

    def _compute_line_value_parsed(self):
        for record in self:
            try:
                if isinstance(record.line_value, str):  # 如果 line_value 是字符串类型
                    data = json.loads(record.line_value)  # 尝试解析为 JSON
                elif isinstance(record.line_value, dict):  # 如果 line_value 已经是字典
                    data = record.line_value
                else:
                    data = {}

                # 根据需要从 data 中提取字段，假设是一个字典
                record.line_value_parsed = ', '.join(f"{key}: {value}" for key, value in data.items())
            except (json.JSONDecodeError, TypeError):
                record.line_value_parsed = "Invalid JSON"

