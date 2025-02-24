// static/src/js/goods_class_list.js
odoo.define('jinling_goods.list_view', function (require) {
    "use strict";

    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');
    var TreeView = require('web.TreeView');

    var GoodsClassListController = ListController.extend({
        init: function () {
            this._super.apply(this, arguments);
            this.leftTreeView = null;
        },

        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                // 创建左侧树形视图容器
                var $leftTree = $('<div>').addClass('o_goods_class_left');
                var $rightList = $('<div>').addClass('o_goods_class_right');

                // 将当前列表视图移动到右侧容器
                self.$el.addClass('o_goods_class_split');
                self.$el.find('.o_list_view').appendTo($rightList);

                // 添加左右容器
                self.$el.prepend($leftTree);
                self.$el.append($rightList);

                // 加载左侧树形视图
                return self._loadLeftTreeView($leftTree);
            });
        },

        _loadLeftTreeView: function ($container) {
            var self = this;
            return this._rpc({
                model: 'goods.class',
                method: 'search_read',
                domain: [['parent_id', '=', false]],
                fields: ['name', 'type', 'child_id'],
            }).then(function (result) {
                var $tree = $('<div>').addClass('o_tree');
                result.forEach(function (record) {
                    self._renderTreeNode($tree, record);
                });
                $container.append($tree);
            });
        },

        _renderTreeNode: function ($parent, record) {
            var $node = $('<div>')
                .addClass('o_tree_node')
                .attr('data-id', record.id);

            var $header = $('<div>')
                .addClass('o_tree_header')
                .text(record.name)
                .click(this._onNodeClick.bind(this));

            $node.append($header);
            $parent.append($node);

            if (record.child_id && record.child_id.length) {
                var $children = $('<div>').addClass('o_tree_children');
                $node.append($children);
                this._loadChildren(record.id, $children);
            }
        },

        _loadChildren: function (parentId, $container) {
            var self = this;
            return this._rpc({
                model: 'goods.class',
                method: 'search_read',
                domain: [['parent_id', '=', parentId]],
                fields: ['name', 'type', 'child_id'],
            }).then(function (result) {
                result.forEach(function (record) {
                    self._renderTreeNode($container, record);
                });
            });
        },

        _onNodeClick: function (ev) {
            var $node = $(ev.currentTarget).closest('.o_tree_node');
            var categoryId = $node.data('id');

            // 更新右侧列表视图的域
            this.update({
                domain: [['parent_id', 'child_of', categoryId]],
            });
        },
    });

    var GoodsClassListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: GoodsClassListController,
        }),
    });

    viewRegistry.add('goods_class_split_list', GoodsClassListView);
});