from odoo import tools
from odoo import api, fields, models

class JlApprovalReport(models.Model):
    _name = 'jl.approval.report'
    _description = '审批统计报表'
    _auto = False

    process_id = fields.Many2one('jl.approval.process', '审批流程')
    record_id = fields.Many2one('jl.approval.record', '审批记录')
    user_id = fields.Many2one('res.users', '审批人')
    state = fields.Selection([
        ('pending', '审批中'),
        ('approved', '已批准'),
        ('rejected', '已拒绝')
    ], string='状态')
    create_date = fields.Datetime('创建时间')
    approve_date = fields.Datetime('审批时间')
    duration = fields.Float('审批耗时(小时)', group_operator="avg")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE or REPLACE VIEW %s as (
                SELECT
                    row_number() OVER () as id,
                    r.process_id,
                    l.record_id,
                    l.user_id,
                    r.state,
                    r.create_date,
                    l.approve_date,
                    EXTRACT(EPOCH FROM (l.approve_date - r.create_date))/3600 as duration
                FROM jl_approval_record r
                LEFT JOIN jl_approval_record_line l ON (r.id = l.record_id)
            )
        """ % (self._table,)) 