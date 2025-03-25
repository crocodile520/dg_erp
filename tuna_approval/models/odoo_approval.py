# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/3/11
Description: odoo_approval
"""

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
import logging
import datetime

_logger = logging.getLogger(__name__)


def _submit_approval(self):
    """提交审批"""
    self.ensure_one()
    data_dict = {}
    process_id = self.env['approval.process'].search([
        ('model_id', '=', self._name),
        ('active', '=', True)
    ])
    if not process_id:
        raise UserError("当前审批单没有进行设置，请前往设置一下")
    if process_id.line_ids:
        for line in process_id.line_ids:
            name = None
            field_description = None
            relation = None
            ttype = None
            if not line.field_id.relation:
                name = line.field_id.name
                field_description = line.field_id.field_description
                relation = line.field_id.relation
                ttype = line.field_id.ttype
                # 使用 getattr() 动态获取字段值
            else:
                field_description = line.field_id.field_description
                name = line.field_id.name
                relation = line.field_id.relation
                ttype = line.field_id.ttype
            value = getattr(self, name, None)
            if not relation:
                # 处理单值字段
                if isinstance(value, datetime.date):
                    value = value.strftime('%Y-%m-%d')
                elif isinstance(value, datetime.datetime):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                data_dict[field_description] = value
                data_dict[field_description] = value
            elif relation and ttype == 'many2one':
                if value:
                    # 取出记录的 display_name（一般是 name 字段）
                    line_value = value.display_name
                    # 或者取具体字段，如 name、email 等
                    # line_value = value.name
                else:
                    line_value = ''

                data_dict[field_description] = line_value
            elif ttype == 'many2many':
                data_dict[field_description] = []
                if value:
                    for record in value:
                        # 取出 display_name 或其他字段
                        record_data = record.display_name  # 或者 record.name、record.email等
                        data_dict[field_description].append(record_data)
            else:
                name_dict = {}  # 存储多对一的配置字段信息
                data_dict[field_description] = []
                line_list = self.env['approval.control.list'].sudo().search([('line_id', '=',line.id )])

                if line_list:
                    for _line in line_list:
                        line_name = _line.field_id.name
                        line_field_description = _line.field_id.field_description
                        name_dict[line_field_description] = line_name
                    if value:
                        if value._name == relation:  # 确认是关联的 One2many 字段
                            for record in value:
                                record_data = {}
                                for key,value in name_dict.items():
                                # 遍历关联模型的字段，提取数据
                                    for field in record._fields:
                                        if field != 'id' and record._fields[field].type not in ('binary',) and field == value:
                                            line_value = getattr(record, value, None)
                                            if isinstance(line_value, datetime.date):
                                                line_value = line_value.strftime('%Y-%m-%d')
                                            elif isinstance(line_value, datetime.datetime):
                                                line_value = line_value.strftime('%Y-%m-%d %H:%M:%S')
                                            elif isinstance(line_value, models.Model):  # Many2one字段
                                                line_value = line_value.display_name
                                            record_data[key] = line_value
                                data_dict[field_description].append(record_data)
    record_id= self.env['approval.record'].sudo().create({
        "process_id":process_id.id,
        "res_id":self.id,
        "res_name":self._name,
        "order_name":self.name,
        'dynamic_data': data_dict
    })
    record_id._onchange_dynamic_data()
    self.write({'x_approval_state': 'approval'})
    self.message_post(body="提交审批成功，请等待审批人进行审批！", message_type='notification')
    user = []
    name = None
    if record_id.current_node_id.approve_type == 'user':
        user_ids = record_id.current_node_id.user_ids
        user_ids = user_ids
        if user_ids:
            for user_id in user_ids:
                user.append(user_id.name)
        name = ','.join(user)
    elif record_id.current_node_id.approve_type == 'department':
        name = record_id.current_node_id.department_id.name
    elif record_id.current_node_id.approve_type == 'position':
        name = record_id.current_node_id.position_id.name
    record = self.env[process_id.model_name].browse(record_id.res_id)
    record.message_post(body=f"<span style='color: purple;'>等待 {name} 审批</span>", message_type='notification')

Model = models.Model
setattr(Model, 'submit_approval', _submit_approval)


def _action_approve(self):
    """同意审批"""
    self.ensure_one()
    res_id = self.id
    res_name = self._name
    record_id = self.env['approval.record'].search([('res_id','=',res_id),('res_name','=',res_name)],limit=1)
    if record_id:
        with self.env.cr.savepoint():
            record_id.with_context(action_approve=True).action_approve()

    else:
        raise UserError("当前审批单不存在审批单记录中，请联系管理员处理!")


Model = models.Model
setattr(Model, 'action_approve', _action_approve)


def _action_reject(self):
    """拒绝审批"""
    self.ensure_one()
    res_id = self.id
    res_name = self._name
    record_id = self.env['approval.record'].search([('res_id', '=', res_id), ('res_name', '=', res_name)], limit=1)
    if record_id:
        with self.env.cr.savepoint():
            record_id.with_context(action_reject=True).action_reject()
    else:
        raise UserError("当前审批单不存在审批单记录中，请联系管理员处理!")


Model = models.Model
setattr(Model, 'action_reject', _action_reject)

def _action_synchronous(self):
    """同步数据"""
    self.ensure_one()
    res_id = self.id
    res_name = self._name
    record_id = self.env['approval.record'].search([('res_id', '=', res_id), ('res_name', '=', res_name)], limit=1)
    if record_id:
        if self.state == 'approved':
            with self.env.cr.savepoint():
                record_id.with_context(action_synchronous=True).action_synchronous()
    else:
        raise UserError("当前审批单不存在审批单记录中，请联系管理员处理!")


Model = models.Model
setattr(Model, 'action_synchronous', _action_synchronous)