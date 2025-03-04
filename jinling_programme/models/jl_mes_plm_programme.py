from odoo import api,fields,models,tools

class JlMesPlmProgrammeReport(models.Model):
    _name = 'jl.mes.plm.programme'
    _description = '生产计划'
    _order = 'date desc, id desc'

    plm_id = fields.Many2one('jl.mes.plm', '生产工单', ondelete='cascade', help='绑定生产工单')
    lock = fields.Boolean('锁定',default=False)
    order_id = fields.Many2one('sell.order', '销售订单', ondelete='cascade', help='绑定销售订单')
    user_id = fields.Many2one(related='order_id.user_id',string='销售员')
    goods_id = fields.Many2one('goods','商品',related='plm_id.goods_id',ondelete='cascade', help='购货商品')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    uom_id = fields.Many2one('uom', related='goods_id.uom_id', ondelete='cascade')
    qty = fields.Float('数量',related='plm_id.qty', digits='Quantity', track_visibility='always')
    date = fields.Date('单据日期',related='plm_id.date')
    delivery_date = fields.Date('要求交货日期',related='plm_id.delivery_date')
    task_type = fields.Selection( '开工状态',related='plm_id.task_type', track_visibility='always')



class JlMesPlmProgrammeKey(models.TransientModel):
    _name = 'jl.mes.plm.programme.key'
    _description = '生产计划锁定'

    def button_done(self):
        for plan in self.env['jl.mes.plm.programme'].search([('id', 'in', self.env.context.get('active_ids'))]):
            if plan.plm_id.state != 'cencal' and not plan.lock:
                plan.lock = True

class JlMesPlmProgrammeunlockKey(models.TransientModel):
    _name = 'jl.mes.plm.programme.unlock.key'
    _description = '生产计划解锁'

    def button_done(self):
        for plan in self.env['jl.mes.plm.programme'].search([('id', 'in', self.env.context.get('active_ids'))]):
            if plan.plm_id.state != 'cencal' and plan.lock:
                plan.lock = False