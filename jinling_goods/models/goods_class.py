from odoo import fields,api,models
from odoo.exceptions import ValidationError, UserError



class GoodsClass(models.Model):
    _name = 'goods.class'
    _description = '商品分类'
    _sql_constraints = [('name_unique', 'unique(name)', '名称不可以重复')]

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValidationError(u'错误 ! 您不能创建循环分类')



    @api.depends('child_id', 'goods_ids')
    def _compute_all_goods(self):
        for record in self:
            # 获取所有子分类ID
            category_ids = self.search([('parent_path', 'like', record.parent_path + '%')]).ids
            record.all_goods_ids = self.env['goods'].search([('category_id', 'in', category_ids)])

    name = fields.Char('名称',index=True, ondelete='cascade',help='分类名称')
    note = fields.Char('备注',help='备注情况')
    parent_id = fields.Many2one('goods.class', string=u'上级分类', index=True)
    child_id = fields.One2many('goods.class', 'parent_id', string=u'子分类')
    parent_path = fields.Char(index=True)
    sequence = fields.Integer(u'顺序')
    type = fields.Selection([('view', u'节点'),
                             ('normal', u'常规')],
                            u'类型',
                            required=True,
                            default='normal',
                            help=u'货品分类的类型，分为节点和常规，只有节点的分类才可以建下级货品分类，常规分类不可作为上级货品分类')

    # 添加计算字段获取所有子分类
    child_all_ids = fields.Many2many(
        'goods.class',
        compute='_compute_child_all_categories',
        string='所有子分类'
    )

    @api.depends('child_id', 'child_id.child_id')
    def _compute_child_all_categories(self):
        for record in self:
            child_categories = self.env['goods.class']
            if record.parent_path:
                child_categories = self.search([
                    ('parent_path', 'like', record.parent_path + '%'),
                    ('id', '!=', record.id)
                ])
            record.child_all_ids = child_categories
