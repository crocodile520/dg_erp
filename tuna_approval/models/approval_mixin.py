# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

class ApprovalMixin(models.AbstractModel):
    _name = 'approval.mixin'
    _description = '审批Mixin'

    approval_state = fields.Selection([
        ('draft', '草稿'),
        ('approval', '审批中'),
        ('approved', '已通过'),
        ('rejected', '已拒绝')
    ], string='审批状态', default='draft', tracking=True)
    
    approval_record_ids = fields.One2many(
        'approval.record', 'res_id',
        domain=lambda self: [('model_id.model', '=', self._name)],
        string='审批记录')

    def _need_approval(self):
        """检查是否需要审批"""
        self.ensure_one()
        rules = self.env['approval.rule'].search([
            ('model_name', '=', self._name),
            ('active', '=', True)
        ])
        
        for rule in rules:
            if rule.domain:
                domain = eval(rule.domain)
                if not self.search([('id', '=', self.id)] + domain):
                    continue
            return rule
        return False

    def submit_approval(self):
        """提交审批"""
        for record in self:
            rule = record._need_approval()
            if not rule:
                continue
                
            approvers = rule._get_approvers(record)
            if not approvers:
                raise UserError('未找到审批人')
                
            self.env['approval.record'].create({
                'name': '%s-%s' % (rule.name, record.display_name),
                'rule_id': rule.id,
                'res_id': record.id,
                'approver_ids': [(6, 0, approvers.ids)]
            })
            
            record.approval_state = 'approval'

    def action_approve(self):
        """审批通过"""
        self.approval_state = 'approved'

    def action_reject(self):
        """审批拒绝"""
        self.approval_state = 'rejected'

    @api.model
    def create(self, vals):
        record = super().create(vals)
        rules = self.env['approval.rule'].search([
            ('model_name', '=', self._name),
            ('active', '=', True),
            ('type', 'in', ['create', 'both'])
        ])
        if rules:
            record.submit_approval()
        if 'x_approval_state' not in vals:
            vals['x_approval_state'] = 'draft'  # Default value
        return record

    def write(self, vals):
        res = super().write(vals)
        rules = self.env['approval.rule'].search([
            ('model_name', '=', self._name),
            ('active', '=', True),
            ('type', 'in', ['write', 'both'])
        ])
        if rules:
            self.submit_approval()
        return res 