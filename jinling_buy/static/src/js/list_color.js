odoo.define('jinling_buy.list_view_color', function (require) {
    "use strict";

    var ListRenderer = require('web.ListRenderer');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');

    console.log('Custom List Renderer JS Loaded'); // 确保 JS 文件被加载

    var CustomListRenderer = ListRenderer.extend({
        _renderBodyCell: function (record, node, colIndex, options) {
            var td = this._super.apply(this, arguments);
            if (!td) {
                console.error('Error: td is undefined for column:', node.attrs.name);
                td = document.createElement('td'); // 备用 td，防止报错
            }

            // 兼容 jQuery 对象
            td = $(td).get(0);
            if (!td) {
                console.error('Error: td remains undefined after jQuery check for column:', node.attrs.name);
                return document.createElement('td');
            }

            var fieldValue = record.data[node.attrs.name] || '';
            console.log(`Field: ${node.attrs.name}, Value:`, fieldValue);

            if (node.attrs.name === 'order_state' && fieldValue) {
                console.log('Found order_state field:', fieldValue);
                switch (fieldValue) {
                    case 'not_stock':
                        td.style.color = 'red';
                        td.style.backgroundColor = 'lightpink';
                        break;
                    case 'done_stock':
                        td.style.color = 'green';
                        td.style.backgroundColor = 'lightgreen';
                        break;
                    case 'part_stock':
                        td.style.color = 'orange';
                        td.style.backgroundColor = 'lightyellow';
                        break;
                    default:
                        console.warn('Unknown order_state:', fieldValue);
                }
            }

            return td;
        },
    });


    var CustomListView = ListView.extend({
        config: Object.assign({}, ListView.prototype.config, {
            Renderer: CustomListRenderer,  // 绑定自定义 ListRenderer
        }),
    });

    // 在 viewRegistry 中注册自定义 ListView
    viewRegistry.add('jl_buy_order_list_view', CustomListView);

    return CustomListView;
});