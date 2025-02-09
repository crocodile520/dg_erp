from odoo import api,fields,models
from odoo.exceptions import UserError


READONLY_STATES = {
    'done': [('readonly', True)],
    'onchange': [('readonly', True)],
    'stop': [('readonly', True)],
    'cancel': [('readonly', True)],
}
STATE = [
    ('draft','草稿'),
    ('done','完成'),
    ('cancel','作废'),
]

TYPE = [
    ('air_transport','空运'),
    ('sea_transport','海运'),
    ('road_transport','路运'),
    ('express_delivery','快递'),
]

class JlLogistics(models.Model):
    _name = 'logistics'
    _description = '物流'
    _inherit = ['mail.thread']



    def button_done(self):
        self.ensure_one()
        self.write({
            'state':'done',
            'approve_uid': self.env.uid,
            'approve_date': fields.Datetime.now(self),
        })

    def button_draft(self):
        self.ensure_one()
        self.write({
            'state': 'draft',
            'approve_uid': False,
            'approve_date': False,
        })
    def button_cancel(self):
        self.ensure_one()
        self.write({
            'state': 'cancel',
            'approve_uid': self.env.uid,
            'approve_date': fields.Datetime.now(self),
        })


    name = fields.Char('单据编号',
                       index=True,
                       copy=False,
                       default=lambda self: self.env['ir.sequence'].next_by_code('logistics'),
                       help="物流单的唯一编号，当创建时它会自动生成下一个编号。")
    user_id = fields.Many2one(
        'hr.employee',
        '制单人',
        ondelete='restrict',
        states=READONLY_STATES,
        readonly=False,
        default=lambda self: self.env.user.employee_id.id,
        help='制单人',
    )
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)

    order_out_ids = fields.Many2many('sell.order.out','sell_order_out_rel', 'order_out_id', 'user_id', string='销售发货单')
    type = fields.Selection(TYPE,'运输方式',default='road_transport')
    partner_id = fields.Many2one('partner', '客户')
    partner_code = fields.Char('客户编码', related='partner_id.code')
    main_mobile = fields.Char('收货联系人', related='partner_id.main_mobile')
    main_contact = fields.Char('收货联系人电话', related='partner_id.main_contact')
    address = fields.Char('收货地址', related='partner_id.address')
    date = fields.Date('单据日期', default=lambda self: fields.Date.context_today(self), required=True)
    weight = fields.Float('重量KG',digits='Quantity',default=0)
    state = fields.Selection(STATE, '确认状态', help='单据状态', default='draft', track_visibility='always')
    approve_uid = fields.Many2one('res.users',
                                  '确认人',
                                  copy=False,
                                  ondelete='restrict',
                                  help='确认单据的人')
    approve_date = fields.Datetime('确认日期', copy=False)
    note = fields.Char('备注')