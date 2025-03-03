# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/3/3
Description: goods_bom_file
"""
from odoo import fields ,api,models


STATE = [
    ('draft','草稿'),
    ('done','完成'),
    ('cancel','作废'),
]
class GoodsBomFile(models.Model):
    _name = 'goods.bom.file'
    _description = '商品'
    _inherit = ['mail.thread']
    _sql_constraints = [('name_unique','unique(name)','bom名称不可以重复')]


    def button_done(self):
        self.ensure_one()
        self.write({
            'state': 'done',
            'approve_uid': self.env.uid,
            'approve_date': fields.Datetime.now(self),
        })

    def button_draft(self):
        self.ensure_one()
        self.write({
            'state': 'draft',
            'approve_uid': None,
            'approve_date': None,
        })

    def button_cancel(self):
        self.ensure_one()
        self.write({
            'state': 'cancel'
        })

    def _compute_attachment_number(self):
        """附件上传"""
        attachment_data = self.env["ir.attachment"].read_group(
            [("res_model", "=", self._name), ("res_id", "in", self.ids)],
            ["res_id"],
            ["res_id"],
        )
        attachment = dict(
            (data["res_id"], data["res_id_count"]) for data in attachment_data
        )
        for expense in self:
            expense.attachment_number = attachment.get(expense.id, 0)

    def action_get_attachment_view(self):
        """附件上传动作视图"""
        self.ensure_one()
        res = self.env.ref("base.action_attachment").sudo().read()[0]
        res["domain"] = [("res_model", "=", self._name), ("res_id", "in", self.ids)]
        res["context"] = {"default_res_model": self._name, "default_res_id": self.id}
        return res

    name = fields.Char('bom名称编号', required=True, help='bom名称编号')
    attachment_ids = fields.One2many('ir.attachment', 'res_id', domain=[('res_model', '=', 'goods.bom.file')],
                                     string="Attachments")

    goods_id = fields.Many2one('goods', '商品', required=True, ondelete='cascade', help='产品名称')
    describe = fields.Char('描述', related='goods_id.describe', help='用户商品描述')
    specs = fields.Char('规格型号', related='goods_id.specs')
    surface = fields.Char('颜色', related='goods_id.surface')
    goods_class_id = fields.Many2one('goods.class', '商品分类', related='goods_id.goods_class_id', ondelete='cascade',
                                     help='分类名称')
    uom_id = fields.Many2one('uom', '单位', related='goods_id.uom_id')
    active = fields.Boolean('启用', default=True)
    state = fields.Selection(STATE, '确认状态', help='单据状态', default='draft', track_visibility='always')
    note = fields.Char('备注')
    approve_uid = fields.Many2one('res.users',
                                  '确认人',
                                  copy=False,
                                  ondelete='restrict',
                                  help='确认单据的人')
    approve_date = fields.Datetime('确认日期', copy=False)

    attachment_number = fields.Integer(
        compute="_compute_attachment_number", string="附件上传"
    )