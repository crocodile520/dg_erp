from odoo import fields,api,models
from odoo.exceptions import UserError


STATE = [
    ('draft','草稿'),
    ('done','完成'),
    ('cancel','作废'),
]

MOVE_LINE_TYPE = [
        ('out', '出库'),
        ('in', '入库'),
        ('rejection', '拒收'),
        ('internal', '内部调拨'),
    ]
class JlMove(models.Model):
    _name = 'jl.move'
    _description = '移库单'

    origin = fields.Char('移库类型', required=True,
                         help='移库类型')
    name = fields.Char('单据编号', copy=False, default=lambda self: self.env['ir.sequence'].next_by_code('jl.move'),
                       help='单据编号，创建时会自动生成')
    ref = fields.Char('外部单号')
    state = fields.Selection(STATE, '状态', copy=False, default='draft',
                             index=True,
                             help='移库单状态标识，新建时状态为草稿;确认后状态为已确认',
                             track_visibility='onchange')
    supplier_id = fields.Many2one('supplier', '业务伙伴', ondelete='restrict',
                                 help='该单据对应的业务伙伴')
    date = fields.Date('单据日期', required=True, copy=False, default=fields.Date.context_today,
                       help='单据创建日期，默认为当前天')
    order_id = fields.Many2one('jl.buy.order','采购订单',copy=False, ondelete='restrict',help='绑定采购订单')
    sell_order_id = fields.Many2one('sell.order','销售订单',ondelete='cascade',help='绑定销售订单')
    order_out_id = fields.Many2one('sell.order.out', '销售发货单', ondelete='cascade', help='绑定销售发货单')
    plm_id = fields.Many2one('jl.mes.plm','生产工单',copy=False, ondelete='restrict',help='绑定生产工单')
    plm_in_id = fields.Many2one('jl.mes.plm.in','生产入库单',copy=False, ondelete='restrict',help='绑定生产入库单')
    # pick_id = fields.Many2one('jl.mes.plm.picking', '生产领料单', copy=False, ondelete='restrict', help='绑定生产领料单')
    approve_uid = fields.Many2one('res.users', '确认人',
                                  copy=False, ondelete='restrict',
                                  help='移库单的确认人')
    approve_date = fields.Datetime('确认日期', copy=False)
    line_out_ids = fields.One2many('jl.move.line', 'move_id', '出库明细',
                                   domain=[
                                       ('type', 'in', ['out','rejection'])],
                                   copy=True,
                                   help='出库类型的移库单对应的出库明细')
    line_in_ids = fields.One2many('jl.move.line', 'move_id', '入库明细',
                                  domain=[('type', '=', ['in','rejection'])],
                                  context={'type': 'in'}, copy=True,
                                  help='入库类型的移库单对应的入库明细')
    in_goods_id = fields.Many2one('goods', string='入库商品',
                                  related='line_in_ids.goods_id')
    out_goods_id = fields.Many2one('goods', string='出库商品',
                                   related='line_out_ids.goods_id')

    note = fields.Text('备注',
                       copy=False,
                       help='可以为该单据添加一些需要的标识信息')
    user_id = fields.Many2one(
        'hr.employee',
        '经办人',
        ondelete='restrict',
        states={'done': [('readonly', True)]},
        default=lambda self: self.env.user.employee_id.id,
        help='单据经办人',
        track_visibility='onchange'
    )

class JlMoveLine(models.Model):
    _name = 'jl.move.line'

    @api.depends('goods_qty', 'tax_price', 'discount_amount', 'tax_rate')
    def _compute_all_amount(self):
        '''当订单行的数量、含税单价、折扣额、税率改变时，改变金额、税额、价税合计'''
        for wml in self:
            if wml.tax_rate > 100:
                raise UserError('税率不能输入超过100的数')
            if wml.tax_rate < 0:
                raise UserError('税率不能输入负数')
            wml.subtotal = wml.tax_price * wml.goods_qty - wml.discount_amount  # 价税合计
            wml.tax_amount = wml.subtotal / \
                             (100 + wml.tax_rate) * wml.tax_rate  # 税额
            wml.amount = wml.subtotal - wml.tax_amount  # 金额

    @api.depends('goods_id')
    def _compute_uom_uos(self):
        for wml in self:
            if wml.goods_id:
                wml.uom_id = wml.goods_id.uom_id

    move_id = fields.Many2one('jl.move', string='移库单', ondelete='cascade',
                              help='出库/入库/移库单行对应的移库单')
    supplier_id = fields.Many2one('supplier', string='业务伙伴',related='move_id.supplier_id')
    plan_date = fields.Date('计划日期', default=fields.Date.context_today)
    date = fields.Date('完成日期', copy=False,
                       help='单据完成日期')
    cost_time = fields.Datetime('确认时间', copy=False,
                                help='单据确认时间')
    warehouse_id = fields.Many2one('warehouse', '仓库', help='关联仓库，购票物品存储某个仓库')
    type = fields.Selection(MOVE_LINE_TYPE,
                            '类型',
                            required=True,
                            default=lambda self: self.env.context.get('type'),
                            help='类型：出库、入库 或者 内部调拨')
    state = fields.Selection(STATE, '状态', copy=False, default='draft',
                             index=True,
                             help='状态标识，新建时状态为草稿;确认后状态为已完成')
    goods_id = fields.Many2one('goods', string='商品', required=True,
                               index=True, ondelete='restrict',
                               help='该单据行对应的商品')
    describe = fields.Char('产品名称', related='goods_id.describe', ondelete='cascade')
    specs = fields.Char('规格型号', related='goods_id.specs', ondelete='cascade')
    surface = fields.Char('颜色', related='goods_id.surface', ondelete='cascade')
    lot_id = fields.Many2one('jl.move.line', '批号',
                             help='该单据行对应的商品的批号，一般是出库单行')
    production_date = fields.Date('生产日期', default=fields.Date.context_today,
                                  help='商品的生产日期')
    shelf_life = fields.Integer('保质期(天)',
                                help='商品的保质期(天)')
    uom_id = fields.Many2one('uom', string='单位', ondelete='restrict', compute=_compute_uom_uos,
                             help='商品的计量单位', store=True)
    goods_qty = fields.Float('数量',
                             digits='Quantity',
                             default=1,
                             required=True,
                             help='商品的数量')

    price = fields.Float('单价',
                         store=True,
                         digits='Price',
                         help='商品的单价')
    tax_price = fields.Float('含税单价',
                               digits='Price',
                               help='商品的含税单价')
    discount_rate = fields.Float('折扣率%',
                                 help='单据的折扣率%')
    discount_amount = fields.Float('折扣额',
                                   digits='Amount',
                                   help='单据的折扣额')
    amount = fields.Float('金额', compute=_compute_all_amount, store=True,
                          digits='Amount',
                          help='单据的金额,计算得来')
    tax_rate = fields.Float('税率(%)',
                            help='单据的税率(%)')
    tax_amount = fields.Float('税额', compute=_compute_all_amount, store=True,
                              digits='Amount',
                              help='单据的税额,有单价×数量×税率计算得来')
    subtotal = fields.Float('价税合计', compute=_compute_all_amount, store=True,
                            digits='Amount',
                            help='价税合计,有不含税金额+税额计算得来')
    note = fields.Text('备注',
                       help='可以为该单据添加一些需要的标识信息')
    cost_unit = fields.Float('单位成本', digits='Price',
                             help='入库/出库单位成本')
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)
    scrap = fields.Boolean('报废')
