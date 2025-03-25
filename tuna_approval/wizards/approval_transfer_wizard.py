# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/3/12
Description: approval.transfer.wizard
"""


from odoo import api, fields, models, tools
from odoo.exceptions import UserError
import logging

class ApprovalTransferWizard(models.TransientModel):
    _name = 'approval.transfer.wizard'
    _description = '转让审批'

    record_id = fields.Many2one('approval.record', string='记录', required=True)
    user_ids = fields.Many2many('res.users', string='新审批人')

    def action_confirm_transfer(self):
        if self.record_id:
            self.record_id.user_ids = self.user_ids  # 添加用户到 user_ids