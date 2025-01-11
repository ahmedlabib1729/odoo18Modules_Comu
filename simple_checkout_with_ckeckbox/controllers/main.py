from odoo import http
from odoo.http import request


class SimpleCheckout(http.Controller):

    @http.route('/shop/simple_checkout', type='http', auth="public", website=True, csrf=False)
    def simple_checkout_form(self, **kwargs):
        # Fetch search parameters
        search_name = kwargs.get('search_name', '')
        search_category = kwargs.get('search_category', '')

        # Fetch categories
        website_categories = request.env['product.public.category'].sudo().search([])

        # Build domain for products
        domain = []
        if search_name:
            domain.append(('name', 'ilike', search_name))
        if search_category:
            domain.append(('public_categ_ids', 'child_of', int(search_category)))

        # Fetch products based on domain
        products = request.env['product.product'].sudo().search(domain)

        # Generate HTML
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>طلب المنتجات</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
            <script>
                function updateProducts() {{
                    const searchName = document.getElementById("search_name").value;
                    const searchCategory = document.getElementById("search_category").value;

                    // Fetch updated products using AJAX
                    fetch(`/shop/simple_checkout/update_products?search_name=${{searchName}}&search_category=${{searchCategory}}`)
                        .then(response => response.text())
                        .then(html => {{
                            document.getElementById("products_list").innerHTML = html;
                        }})
                        .catch(error => alert('حدث خطأ أثناء تحديث المنتجات. حاول مرة أخرى.'));
                }}
            </script>
            <style>
                .product-item {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 15px;
                    padding: 10px;
                    border-bottom: 1px solid #ddd;
                }}
                .product img {{
                    width: 70px;
                    height: 70px;
                    object-fit: cover;
                    border-radius: 5px;
                }}
                .product-info {{
                    flex-grow: 1;
                    margin-left: 15px;
                }}
            </style>
        </head>
        <body class="bg-light">
            <div class="container mt-5">
                <div class="card shadow">
                    <div class="card-header bg-primary text-white text-center">
                        <h2>طلب المنتجات</h2>
                    </div>
                    <div class="card-body">
                        <!-- Search Form -->
                        <div class="mb-4">
                            <div class="row g-3">
                                <div class="col-md-6">
                                    <input type="text" class="form-control" id="search_name" name="search_name" value="{search_name}" placeholder="ابحث عن المنتج" onkeyup="updateProducts()">
                                </div>
                                <div class="col-md-4">
                                    <select id="search_category" name="search_category" class="form-select" onchange="updateProducts()">
                                        <option value="">-- اختر الفئة --</option>
        '''
        for category in website_categories:
            selected = 'selected' if str(category.id) == search_category else ''
            html += f'<option value="{category.id}" {selected}>{category.name}</option>'
        html += '''
                                    </select>
                                </div>
                            </div>
                        </div>

                        <!-- Customer Info -->
                        <form action="/shop/simple_checkout/submit" method="post">
                            <div class="mb-3">
                                <label for="name" class="form-label">الاسم:</label>
                                <input type="text" class="form-control" id="name" name="name" placeholder="ادخل اسمك" required>
                            </div>
                            <div class="mb-3">
                                <label for="phone" class="form-label">رقم الهاتف:</label>
                                <input type="text" class="form-control" id="phone" name="phone" placeholder="ادخل رقم الهاتف" required>
                            </div>

                            <!-- Product List -->
                            <div id="products_list">
        '''
        for product in products:
            image_url = f"/web/image/product.product/{product.id}/image_128"
            html += f'''
                                <div class="product-item">
                                    <img src="{image_url}" alt="{product.name}">
                                    <div class="product-info">
                                        <div class="product-name">{product.name}</div>
                                        <div>
                                            <input type="checkbox" id="product_{product.id}" name="product_{product.id}">
                                            <label for="product_{product.id}" class="form-label">اختيار</label>
                                            <input type="number" id="quantity_{product.id}" name="quantity_{product.id}" min="1" value="1" class="form-control" style="width: 70px;">
                                        </div>
                                    </div>
                                </div>
            '''
        html += '''
                            </div>
                            <button type="submit" class="btn btn-success w-100 mt-4">إرسال الطلب</button>
                        </form>
                    </div>
                </div>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        '''
        return html

    @http.route('/shop/simple_checkout/update_products', type='http', auth="public", website=True)
    def update_products(self, **kwargs):
        search_name = kwargs.get('search_name', '')
        search_category = kwargs.get('search_category', '')

        # Build domain for products
        domain = []
        if search_name:
            domain.append(('name', 'ilike', search_name))
        if search_category:
            domain.append(('public_categ_ids', 'child_of', int(search_category)))

        # Fetch products based on domain
        products = request.env['product.product'].sudo().search(domain)

        # Render products
        html = ""
        for product in products:
            image_url = f"/web/image/product.product/{product.id}/image_128"
            html += f'''
            <div class="product-item">
                <img src="{image_url}" alt="{product.name}">
                <div class="product-info">
                    <div class="product-name">{product.name}</div>
                    <div>
                        <input type="checkbox" id="product_{product.id}" name="product_{product.id}">
                        <label for="product_{product.id}" class="form-label">اختيار</label>
                        <input type="number" id="quantity_{product.id}" name="quantity_{product.id}" min="1" value="1" class="form-control" style="width: 70px;">
                    </div>
                </div>
            </div>
            '''
        return html

    @http.route('/shop/simple_checkout/submit', type='http', auth="public", website=True, csrf=False)
    def simple_checkout_submit(self, **kwargs):
        # Get customer details
        name = kwargs.get('name', '').strip()
        phone = kwargs.get('phone', '').strip()

        if not name or not phone:
            return "Error: Name and Phone are required."

        # Fetch selected products from the form
        selected_products = []
        for key, value in kwargs.items():
            if key.startswith('product_') and value == 'on':
                product_id = int(key.split('_')[1])
                quantity = int(kwargs.get(f'quantity_{product_id}', 1))
                selected_products.append((product_id, quantity))

        if not selected_products:
            return "Error: No products selected."

        # Create customer record
        partner = request.env['res.partner'].sudo().create({
            'name': name,
            'phone': phone,
        })

        # Create sales order lines
        order_lines = []
        product_details = []
        for product_id, quantity in selected_products:
            product = request.env['product.product'].sudo().browse(product_id)
            order_lines.append((0, 0, {
                'product_id': product.id,
                'product_uom_qty': quantity,
                'price_unit': product.list_price,
            }))
            product_details.append((product.name, quantity))

        # Create sales order
        sale_order = request.env['sale.order'].sudo().create({
            'partner_id': partner.id,
            'order_line': order_lines,
        })

        # Generate confirmation page
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>شكراً لك</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container mt-5">
                <div class="card shadow">
                    <div class="card-header bg-success text-white text-center">
                        <h2>تم إرسال طلبك بنجاح</h2>
                    </div>
                    <div class="card-body">
                        <p class="text-center">تم إنشاء طلبك رقم <strong>{sale_order.name}</strong> بنجاح.</p>
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
        for product_name, quantity in product_details:
            html += f'''
                                <tr>
                                    <td>{product_name}</td>
                                    <td>{quantity}</td>
                                </tr>
            '''
        html += '''
                            </tbody>
                        </table>
                        <a href="/shop/simple_checkout" class="btn btn-primary w-100">رجوع إلى الصفحة الرئيسية</a>
                    </div>
                </div>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        '''
        return html
