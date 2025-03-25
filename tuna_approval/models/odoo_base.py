# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/3/12
Description: odoo_base
"""

import logging
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

Model = models.Model

#修改函数
write_origin = models.BaseModel.write


def write(self, vals):
    # 允许通过上下文跳过审批状态检查
    context = dict(self.env.context) or {}
    if context.get('action_reject'):
        return write_origin(self, vals)
    if context.get('action_approve'):
        return write_origin(self, vals)
    if context.get('action_synchronous'):
        return write_origin(self, vals)
    if not context:
        odoo_approval_write(self, vals)
        return write_origin(self, vals)
    if not context.get('params'):
        odoo_approval_write(self, vals)
        return write_origin(self, vals)
    if context.get('params').get('model') == 'approval.record':
        return write_origin(self, vals)

    # 正常限制修改
    odoo_approval_write(self, vals)
    return write_origin(self, vals)


def odoo_approval_write(self, vals):
    """不允许单据修改"""
    res_state_obj = self.env.get('approval.process')
    if res_state_obj is None:
        return
    for res in self:
        model_id = self.env['ir.model'].sudo().search([('model', '=', res._name)]).id
        flows = res_state_obj.sudo().search([('model_id', '=', model_id),('state','=','confirmed'),('active', '=', True)])
        if not flows:
            continue
        if not flows[0].ing_write and res.x_approval_state == 'approval':
            # 审批中
            raise ValidationError('目前单据属于审批状态不允许进行修改')
        if not flows[0].end_write and res.x_approval_state == 'approved':
            #审批通过
            raise ValidationError('目前单据属于审批通过后不允许进行修改')
    return True


models.BaseModel.write = write


unlink_origin = models.BaseModel.unlink


def unlink(self):
    odoo_approval_unlink(self)
    return unlink_origin(self)


def odoo_approval_unlink(self):
    """不允许删除审批后的单据"""
    res_state_obj = self.env.get('approval.process')
    if res_state_obj is None:
        return
    for res in self:
        model_id = self.env['ir.model'].sudo().search([('model', '=', res._name)]).id
        flows = res_state_obj.sudo().search([('model_id', '=', model_id),('state','=','confirmed'),('active', '=', True)])
        if not flows:
            continue
        if res.x_approval_state != 'draft':
            raise ValidationError('不允许您删除odoo审批后的单据！')
    return True


models.BaseModel.unlink = unlink