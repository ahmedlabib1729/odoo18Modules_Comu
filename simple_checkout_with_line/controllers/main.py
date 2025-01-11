from odoo import http
from odoo.http import request
import json


class SimpleCheckout(http.Controller):

    @http.route('/shop/simple_checkout_line', type='http', auth="public", website=True, csrf=False)
    def simple_checkout_form(self, **kwargs):
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>طلب المنتجات</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css" rel="stylesheet" />
            <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js"></script>
            <script>
                let lineCounter = 0;

                function addProductLine() {{
                    lineCounter++;
                    const newRow = `
                        <tr id="line_${{lineCounter}}">
                            <td>
                                <select class="form-control category-select" id="category_${{lineCounter}}" name="category_${{lineCounter}}" style="width: 100%;" onchange="updateProductList(${{lineCounter}})"></select>
                            </td>
                            <td>
                                <select class="form-control product-select" id="product_${{lineCounter}}" name="product_${{lineCounter}}" style="width: 100%;"></select>
                            </td>
                            <td>
                                <input type="number" class="form-control" id="quantity_${{lineCounter}}" name="quantity_${{lineCounter}}" min="1" value="1">
                            </td>
                            <td>
                                <button type="button" class="btn btn-danger" onclick="removeProductLine(${{lineCounter}})">حذف</button>
                            </td>
                        </tr>
                    `;
                    document.getElementById("product-lines").insertAdjacentHTML('beforeend', newRow);
                    setupCategorySelect(`#category_${{lineCounter}}`);
                    setupProductSelect(`#product_${{lineCounter}}`, null);  // ابدأ بدون تصفية
                }}

                function removeProductLine(lineId) {{
                    document.getElementById(`line_${{lineId}}`).remove();
                }}

                function setupCategorySelect(selector) {{
                    $(selector).select2({{
                        ajax: {{
                            url: '/shop/simple_checkout_line/live_search_category',
                            type: 'GET',
                            dataType: 'json',
                            delay: 250,
                            data: function (params) {{
                                return {{
                                    term: params.term || '',  // المصطلح الذي يتم البحث عنه
                                }};
                            }},
                            processResults: function (data) {{
                                return {{
                                    results: data.map(function (item) {{
                                        return {{
                                            id: item.id,
                                            text: item.name
                                        }};
                                    }})
                                }};
                            }},
                            cache: true
                        }},
                        placeholder: 'ابحث عن الفئة أو اختر من القائمة',
                        minimumInputLength: 0,
                        allowClear: true
                    }});
                }}

                function setupProductSelect(selector, categoryId) {{
                    $(selector).select2({{
                        ajax: {{
                            url: '/shop/simple_checkout_line/live_search_product',
                            type: 'GET',
                            dataType: 'json',
                            delay: 250,
                            data: function (params) {{
                                return {{
                                    term: params.term || '',  // المصطلح الذي يتم البحث عنه
                                    category_id: categoryId  // إضافة الفئة لتصفية المنتجات
                                }};
                            }},
                            processResults: function (data) {{
                                return {{
                                    results: data.map(function (item) {{
                                        return {{
                                            id: item.id,
                                            text: item.name
                                        }};
                                    }})
                                }};
                            }},
                            cache: true
                        }},
                        placeholder: 'ابحث عن المنتج أو اختر من القائمة',
                        minimumInputLength: 0,
                        allowClear: true
                    }});
                }}

                function updateProductList(lineId) {{
                    const categoryId = $(`#category_${{lineId}}`).val();
                    setupProductSelect(`#product_${{lineId}}`, categoryId);  // تحديث المنتجات بناءً على الفئة
                }}

                $(document).ready(function () {{
                    addProductLine();  // Start with one line by default
                }});
            </script>
        </head>
        <body class="bg-light">
            <div class="container mt-5">
                <div class="card shadow">
                    <div class="card-header bg-primary text-white text-center">
                        <h2>طلب المنتجات</h2>
                    </div>
                    <div class="card-body">
                        <form action="/shop/simple_checkout_line/submit" method="post">
                            <div class="mb-3">
                                <label for="name" class="form-label">الاسم:</label>
                                <input type="text" id="name" name="name" class="form-control" placeholder="ادخل اسمك" required>
                            </div>
                            <div class="mb-3">
                                <label for="phone" class="form-label">رقم الهاتف:</label>
                                <input type="text" id="phone" name="phone" class="form-control" placeholder="ادخل رقم الهاتف" required>
                            </div>
                            <table class="table table-bordered">
                                <thead>
                                    <tr>
                                        <th>فئة المنتج</th>
                                        <th>اسم المنتج</th>
                                        <th>الكمية</th>
                                        <th>حذف</th>
                                    </tr>
                                </thead>
                                <tbody id="product-lines"></tbody>
                            </table>
                            <button type="button" class="btn btn-secondary mb-3" onclick="addProductLine()">إضافة منتج</button>
                            <button type="submit" class="btn btn-success w-100">إرسال الطلب</button>
                        </form>
                    </div>
                </div>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        '''
        return html

    @http.route('/shop/simple_checkout_line/live_search_category', type='http', auth="public", website=True)
    def live_search_category(self, **kwargs):
        search_term = request.params.get('term', '')
        domain = []
        if search_term:
            domain.append(('name', 'ilike', search_term))

        categories = request.env['product.public.category'].sudo().search(domain, limit=10)
        results = [{'id': category.id, 'name': category.name} for category in categories]

        return request.make_response(json.dumps(results), headers={'Content-Type': 'application/json'})

    @http.route('/shop/simple_checkout_line/live_search_product', type='http', auth="public", website=True)
    def live_search_product(self, **kwargs):
        search_term = request.params.get('term', '')
        category_id = request.params.get('category_id', None)
        domain = []
        if search_term:
            domain.append(('name', 'ilike', search_term))
        if category_id:
            domain.append(('public_categ_ids', 'child_of', int(category_id)))

        products = request.env['product.product'].sudo().search(domain, limit=10)
        results = [{'id': product.id, 'name': product.name} for product in products]

        return request.make_response(json.dumps(results), headers={'Content-Type': 'application/json'})

    @http.route('/shop/simple_checkout_line/submit', type='http', auth="public", website=True, csrf=False)
    def simple_checkout_submit(self, **kwargs):
            name = kwargs.get('name', '')
            phone = kwargs.get('phone', '')

            if not name or not phone:
                return "Error: Name and Phone are required."

            selected_products = []
            for key, value in kwargs.items():
                if key.startswith('product_') and value:
                    product = request.env['product.product'].sudo().browse(int(value))
                    if product.exists():
                        quantity = int(kwargs.get(f'quantity_{key.split("_")[-1]}', 1))
                        selected_products.append((product.id, quantity))

            if not selected_products:
                return "Error: No products selected."

            partner = request.env['res.partner'].sudo().create({
                'name': name,
                'phone': phone,
            })

            order_lines = [(0, 0, {'product_id': pid, 'product_uom_qty': qty}) for pid, qty in selected_products]

            sale_order = request.env['sale.order'].sudo().create({'partner_id': partner.id, 'order_line': order_lines})

            html = f'''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>تم إرسال الطلب</title>
                    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
                </head>
                <body class="bg-light">
                    <div class="container mt-5">
                        <div class="card shadow">
                            <div class="card-header bg-success text-white text-center">
                                <h2>تم إرسال طلبك بنجاح</h2>
                            </div>
                            <div class="card-body">
                                <p class="text-center">تم إنشاء طلبك رقم <strong>{sale_order.name}</strong>.</p>
                                <h4>المنتجات المطلوبة:</h4>
                                <table class="table table-bordered">
                                    <thead class="table-primary">
                                        <tr>
                                            <th>اسم المنتج</th>
                                            <th>الكمية</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                '''
            for product_id, quantity in selected_products:
                product = request.env['product.product'].sudo().browse(product_id)
                html += f'''
                                        <tr>
                                            <td>{product.name}</td>
                                            <td>{quantity}</td>
                                        </tr>
                    '''
            html += '''
                                    </tbody>
                                </table>
                                <a href="/shop/simple_checkout_line" class="btn btn-primary w-100 mt-3">رجوع إلى صفحة الطلب</a>
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                '''
            return html