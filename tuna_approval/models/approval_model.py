# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/3/7
Description: approval_model
"""
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
import logging
import re
from lxml import etree
import types

_logger = logging.getLogger(__name__)


class ApprovalModel(models.Model):
    _name = 'approval.model'
    _description = '审批模型配置'
    _inherit = ['mail.thread']

    name = fields.Char('名称', required=True)
    model_name = fields.Char(related='model_id.model', string='模型名称', store=True)
    active = fields.Boolean('启用', default=True)
    state = fields.Selection([
        ('draft', '草稿'),
        ('done', '已启用'),
        ('disabled', '已禁用')
    ], string='状态', default='draft',track_visibility='always')

    process_id = fields.Many2one('approval.process', string='审批流程')
    model_id = fields.Many2one('ir.model', '模型',related='process_id.model_id' ,
                               ondelete='cascade',
                               domain=[('transient', '=', False)])

    approval_field = fields.Many2one('ir.model.fields', '审批状态字段',
                                     domain="[('model_id', '=', model_id), ('ttype', '=', 'selection')]",
                                     help='选择用于跟踪审批状态的字段')

    _sql_constraints = [
        ('model_uniq', 'unique(model_id)', '每个模型只能配置一次审批流程!')
    ]

    def action_enable(self):
        """启用审批"""
        self.ensure_one()

        created_fields = []
        try:
            model_name = self.model_name

            # 1. 添加审批相关字段
            field_data = [
                {
                    'name': 'x_approval_state',
                    'field_description': '审批状态',
                    'ttype': 'selection',
                    'selection_ids': [
                        (0, 0, {'value': 'draft', 'name': '草稿'}),
                        (0, 0, {'value': 'approval', 'name': '审批中'}),
                        (0, 0, {'value': 'approved', 'name': '已审批'}),
                        (0, 0, {'value': 'rejected', 'name': '已拒绝'})
                    ],
                    'model': model_name,
                    'model_id': self.model_id.id,
                    'state': 'manual',
                    'store': True,
                },
                {
                    'name': 'x_approval_record_ids',
                    'field_description': '审批记录',
                    'ttype': 'one2many',
                    'relation': 'approval.record',
                    'relation_field': 'process_id',
                    'domain': "[('model_id.model', '=', '%s')]" % model_name,
                    'model': model_name,
                    'model_id': self.model_id.id,
                    'state': 'manual',
                    'store': True,
                }
            ]

            # 创建字段

            # ========== 创建字段 ==========
            for field in field_data:
                fields1 = self.env['ir.model.fields'].search([
                    ('model', '=', model_name),
                    ('name', '=', field['name'])
                ])
                if not self.env['ir.model.fields'].search([
                    ('model', '=', model_name),
                    ('name', '=', field['name'])
                ]):
                    field_obj = self.env['ir.model.fields'].create(field)
                    created_fields.append(field_obj)


            # 刷新模型缓存（替代 _clear_cache）
            self.env.clear()
            self.env['ir.default'].set(
                model_name,  # 目标模型
                'x_approval_state',  # 字段名
                'draft'  # 默认值
            )

            view = self.env['ir.ui.view'].search([
                ('model', '=', model_name),
                ('type', '=', 'tree')
            ], limit=1)

            if view:
                arch_base = view.arch_base

                # 解析 XML 结构
                arch_tree = etree.fromstring(arch_base.encode('utf-8'))
                # 设置颜色区分
                arch_tree.set('decoration-info', "x_approval_state == 'draft'")
                arch_tree.set('decoration-warning', "x_approval_state == 'approval'")
                arch_tree.set('decoration-success', "x_approval_state == 'approved'")
                arch_tree.set('decoration-danger', "x_approval_state == 'rejected'")

                # 插入"审批状态"字段
                if not arch_tree.xpath("//field[@name='x_approval_state']"):
                    new_field = etree.Element('field', name='x_approval_state')
                    arch_tree.append(new_field)


                # 将 XML 结构转换为字符串
                new_arch = etree.tostring(arch_tree, pretty_print=True, encoding='unicode')

                # 更新视图
                view.write({'arch': new_arch})

                # 刷新视图缓存
                self.env['ir.ui.view'].clear_caches()

            # 3. 更新form视图
            form_view = self.env['ir.ui.view'].search([
                ('model', '=', model_name),
                ('type', '=', 'form')
            ], limit=1)

            if form_view:
                arch_form = etree.fromstring(form_view.arch_base)
                header = arch_form.find('.//header')

                if header is None:
                    # 如果没有header，创建一个
                    header = etree.Element('header')
                    sheet = arch_form.find('.//sheet')
                    if sheet is not None:
                        sheet.insert(len(header.xpath('button')), header)

                # 添加审批按钮和状态
                if not header.xpath(".//field[@name='x_approval_state']"):
                    buttons = """
                        <group>
                            <button name="submit_approval"
                                    string="提交审批"
                                    type="object"
                                    class="btn btn-primary"
                                    attrs="{'invisible': [('x_approval_state', '!=', 'draft')]}"/>
                            <button name="action_approve"
                                    string="同意"
                                    type="object"
                                    class="btn btn-success"
                                    attrs="{'invisible': [('x_approval_state', '!=', 'approval')]}"/>
                            <button name="action_reject"
                                    string="拒绝"
                                    type="object"
                                    class="oe_highlight"
                                    attrs="{'invisible': [('x_approval_state', '!=', 'approval')]}"/>
                            <button name="action_synchronous"
                                string="同步数据"
                                type="object"
                                class="btn-light" 
                                />
                            <field name="x_approval_state" widget="statusbar"
                                   statusbar_visible="draft,approval,approved,rejected"/>
                        </group>
                    """

                    # 将其解析为单个根节点
                    header_extension = etree.fromstring(buttons)

                    # 添加到 header
                    header.extend(header_extension)

                # # 添加审批记录
                # sheet = arch_form.find('.//sheet')
                # if sheet is not None and not sheet.xpath(".//field[@name='x_approval_record_ids']"):
                #     approval_records = """
                #         <notebook>
                #             <page string="审批记录" name="approval_records">
                #                 <field name="approval_record_ids" readonly="1">
                #                     <tree>
                #                         <field name="create_date"/>
                #                         <field name="name"/>
                #                         <field name="state"/>
                #                         <field name="approver_ids" widget="many2many_tags"/>
                #                         <field name="approval_user_id"/>
                #                         <field name="approval_date"/>
                #                     </tree>
                #                 </field>
                #             </page>
                #         </notebook>
                #     """
                #     sheet.append(etree.fromstring(approval_records))

                # 更新视图
                form_view.write({
                    'arch': etree.tostring(arch_form, encoding='unicode')
                })


            # 5. 更新状态
            self.state = 'done'
            self.process_id.active = True

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '成功',
                    'message':'审批功能启用成功',
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            # 如果失败，删除已创建的字段
            if created_fields:
                for field in created_fields:
                    # 查找引用该字段的视图
                    views = self.env['ir.ui.view'].search([
                        ('arch_db', 'like', field.name)
                    ])
                    for view in views:
                        try:
                            # 从视图中移除字段引用
                            arch_tree = etree.fromstring(view.arch_base)
                            for node in arch_tree.xpath(f"//field[@name='{field.name}']"):
                                node.getparent().remove(node)
                            view.write({'arch': etree.tostring(arch_tree, encoding='unicode')})
                        except Exception as view_error:
                            _logger.error('Failed to update view %s: %s', view.id, str(view_error))

                    # 删除字段
                    field.unlink()

            _logger.error('Enable approval failed: %s', str(e))
            raise UserError(_('启用失败：%s') % str(e))

    def action_disable(self):
        """禁用审批"""
        self.ensure_one()

        try:
            model_name = self.model_name

            # 1. 删除 tree 视图中的 decoration 属性
            tree_views = self.env['ir.ui.view'].search([
                ('model', '=', model_name),
                ('type', '=', 'tree')
            ])
            if tree_views:
                for tree_view in tree_views:
                    arch_base = tree_view.arch_base

                    # 清除 decoration 属性（解决字段不存在报错）
                    arch_base = re.sub(r'decoration-info=".*?"', '', arch_base)
                    arch_base = re.sub(r'decoration-warning=".*?"', '', arch_base)
                    arch_base = re.sub(r'decoration-success=".*?"', '', arch_base)
                    arch_base = re.sub(r'decoration-danger=".*?"', '', arch_base)

                    #  删除字段引用
                    arch_base = arch_base.replace('<field name="x_approval_state"/>', '')
                    arch_base = arch_base.replace('<field name="x_approval_record_ids"/>', '')

                    #  更新 tree 视图
                    tree_view.write({'arch_base': arch_base})

            form_views = self.env['ir.ui.view'].search([
                ('model', '=', model_name),
                ('type', '=', 'form')
            ])
            views = self.env['ir.ui.view'].search([
                ('model', '=', model_name),
                ('type', '=', 'tree')
            ])
            if views:
                for view in views:
                    arch_base = view.arch_base

                    # 删除 x_approval_state 引用
                    if '<field name="x_approval_state"/>' in arch_base:
                        arch_base = arch_base.replace('<field name="x_approval_state"/>', '')

                    # 删除 x_approval_record_ids 引用
                    if '<field name="x_approval_record_ids"/>' in arch_base:
                        arch_base = arch_base.replace('<field name="x_approval_record_ids"/>', '')

                    # 更新视图
                    view.write({'arch_base': arch_base})

            for form_view in form_views:
                arch_form = etree.fromstring(form_view.arch_base)

                # Remove the 'x_approval_state' field (status bar)
                for field in arch_form.xpath("//field[@name='x_approval_state']"):
                    field.getparent().remove(field)

                # Remove approval buttons from the header
                header = arch_form.find('.//header')
                if header:
                    for button in header.xpath(".//button[@name='submit_approval']"):
                        button.getparent().remove(button)
                    for button in header.xpath(".//button[@name='action_approve']"):
                        button.getparent().remove(button)
                    for button in header.xpath(".//button[@name='action_reject']"):
                        button.getparent().remove(button)
                    for button in header.xpath(".//button[@name='action_synchronous']"):
                        button.getparent().remove(button)

                # After removing fields and buttons, update the form view
                form_view.write({'arch_base': etree.tostring(arch_form, encoding='unicode')})

            # 2. Remove dynamic fields from the model
            field_names = ['x_approval_state', 'x_approval_record_ids']
            fields = self.env['ir.model.fields'].search([
                ('model', '=', model_name),
                ('name', 'in', field_names)
            ])
            if fields:
                for field in fields:
                    field.unlink()

            # 3. Update the state
            self.state = 'disabled'
            self.process_id.active = False
            self.process_id.state = 'draft'

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '成功',
                    'message': '审批功能已禁用',
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            _logger.error('Disable approval failed: %s', str(e))
            raise UserError(_('禁用失败：%s') % str(e))

    def action_cancel(self):
        """撤回"""
        self.ensure_one()
        self.state = 'draft'



