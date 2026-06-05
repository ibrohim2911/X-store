import sqlite3
import uuid
import os

old_db_path = 'db_old.sqlite3'
new_db_path = 'C:\\Users\\User\\AppData\\Roaming\\XStore\\db.sqlite3'

if not os.path.exists(old_db_path):
    print("Old DB not found!")
    exit(1)

old_conn = sqlite3.connect(old_db_path)
old_conn.row_factory = sqlite3.Row
new_conn = sqlite3.connect(new_db_path)
new_conn.row_factory = sqlite3.Row

old_cursor = old_conn.cursor()
new_cursor = new_conn.cursor()

# 1. Create a default Store
default_store_id = str(uuid.uuid4()).replace('-', '')
new_cursor.execute(
    "INSERT INTO common_store (id, created_at, updated_at, name, is_active) VALUES (?, datetime('now'), datetime('now'), ?, ?)",
    (default_store_id, 'Default Store', True)
)

id_maps = {
    'user': {},
    'product': {},
    'sizescale': {},
    'size': {},
    'variant': {},
    'client': {},
    'sale': {}
}

# 2. Migrate Users
users = old_cursor.execute("SELECT * FROM user_user").fetchall()
for u in users:
    new_id = str(uuid.uuid4()).replace('-', '')
    id_maps['user'][u['id']] = new_id
    new_cursor.execute(
        """INSERT INTO user_user 
           (id, password, last_login, is_superuser, first_name, last_name, email, is_staff, is_active, date_joined, created_at, updated_at, name, phone_number, store_id) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (new_id, u['password'], u['last_login'], u['is_superuser'], u['first_name'], u['last_name'], u['email'], u['is_staff'], u['is_active'], u['date_joined'], 
         u['created_at'] if 'created_at' in u.keys() else '2023-01-01 00:00:00',
         u['updated_at'] if 'updated_at' in u.keys() else '2023-01-01 00:00:00',
         u['name'], u['phone_number'], default_store_id)
    )

# 3. Migrate Products
products = old_cursor.execute("SELECT * FROM product_products").fetchall()
for p in products:
    new_id = str(uuid.uuid4()).replace('-', '')
    id_maps['product'][p['id']] = new_id
    new_cursor.execute(
        "INSERT INTO product_products (id, created_at, updated_at, name, img, barcode, store_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (new_id, p['created_at'], p['updated_at'], p['name'], p['img'], p['barcode'], default_store_id)
    )

# 4. Migrate SizeScales
sizescales = old_cursor.execute("SELECT * FROM product_sizescale").fetchall()
for s in sizescales:
    new_id = str(uuid.uuid4()).replace('-', '')
    id_maps['sizescale'][s['id']] = new_id
    new_cursor.execute(
        "INSERT INTO product_sizescale (id, created_at, updated_at, name, store_id) VALUES (?, ?, ?, ?, ?)",
        (new_id, s['created_at'], s['updated_at'], s['name'], default_store_id)
    )

# 5. Migrate Sizes
sizes = old_cursor.execute("SELECT * FROM product_size").fetchall()
for s in sizes:
    new_id = str(uuid.uuid4()).replace('-', '')
    id_maps['size'][s['id']] = new_id
    new_cursor.execute(
        "INSERT INTO product_size (id, created_at, updated_at, name, size_scale_id, store_id) VALUES (?, ?, ?, ?, ?, ?)",
        (new_id, s['created_at'], s['updated_at'], s['name'], id_maps['sizescale'].get(s['size_scale_id']), default_store_id)
    )

# 6. Migrate Variants
variants = old_cursor.execute("SELECT * FROM product_variant").fetchall()
for v in variants:
    new_id = str(uuid.uuid4()).replace('-', '')
    id_maps['variant'][v['id']] = new_id
    new_cursor.execute(
        "INSERT INTO product_variant (id, created_at, updated_at, sku, cost_price, sticker_price, quantity, product_id, size_scale_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (new_id, v['created_at'], v['updated_at'], v['sku'], v['cost_price'], v['sticker_price'], v['quantity'], id_maps['product'].get(v['product_id']), id_maps['sizescale'].get(v['size_scale_id']))
    )

try:
    variant_sizes = old_cursor.execute("SELECT * FROM product_variant_size").fetchall()
    for vs in variant_sizes:
        new_cursor.execute(
            "INSERT INTO product_variant_size (variant_id, size_id) VALUES (?, ?)",
            (id_maps['variant'].get(vs['variant_id']), id_maps['size'].get(vs['size_id']))
        )
except:
    pass

# 7. Migrate Clients
try:
    clients = old_cursor.execute("SELECT * FROM sale_client").fetchall()
    for c in clients:
        new_id = str(uuid.uuid4()).replace('-', '')
        id_maps['client'][c['id']] = new_id
        new_cursor.execute(
            "INSERT INTO sale_client (id, created_at, updated_at, name, phone, store_id) VALUES (?, ?, ?, ?, ?, ?)",
            (new_id, c['created_at'], c['updated_at'], c['name'], c['phone'], default_store_id)
        )
except:
    pass

# 8. Migrate PaymentMethods
try:
    pms = old_cursor.execute("SELECT * FROM sale_paymentmenthod").fetchall()
    for pm in pms:
        # these keep integer IDs
        new_cursor.execute(
            "INSERT INTO sale_paymentmenthod (id, name) VALUES (?, ?)",
            (pm['id'], pm['name'])
        )
except:
    pass

# 9. Migrate Sales
try:
    sales = old_cursor.execute("SELECT * FROM sale_sale").fetchall()
    for s in sales:
        new_id = str(uuid.uuid4()).replace('-', '')
        id_maps['sale'][s['id']] = new_id
        new_cursor.execute(
            "INSERT INTO sale_sale (id, created_at, updated_at, total_price, status, debt, payment_method_id, seller_id, store_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id, s['created_at'], s['updated_at'], s['total_price'], s['status'], s['debt'], s['payment_method_id'], id_maps['user'].get(s['seller_id']), default_store_id)
        )
    
    sale_clients = old_cursor.execute("SELECT * FROM sale_sale_client").fetchall()
    for sc in sale_clients:
        new_cursor.execute(
            "INSERT INTO sale_sale_client (sale_id, client_id) VALUES (?, ?)",
            (id_maps['sale'].get(sc['sale_id']), id_maps['client'].get(sc['client_id']))
        )
except:
    pass

# 10. Migrate SaleItems
try:
    items = old_cursor.execute("SELECT * FROM sale_saleitem").fetchall()
    for i in items:
        new_id = str(uuid.uuid4()).replace('-', '')
        new_cursor.execute(
            "INSERT INTO sale_saleitem (id, created_at, updated_at, quantity, price, applied_tax_amount, sale_id, variant_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id, i['created_at'], i['updated_at'], i['quantity'], i['price'], i['applied_tax_amount'], id_maps['sale'].get(i['sale_id']), id_maps['variant'].get(i['variant_id']))
        )
except:
    pass

# 11. Migrate Cash
try:
    cashes = old_cursor.execute("SELECT * FROM sale_cash").fetchall()
    for c in cashes:
        new_id = str(uuid.uuid4()).replace('-', '')
        new_cursor.execute(
            "INSERT INTO sale_cash (id, created_at, updated_at, is_cash_in, amount, reason, store_id, user_id, client_id, sale_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id, c['created_at'], c['updated_at'], c['is_cash_in'], c['amount'], c['reason'], default_store_id, id_maps['user'].get(c['user_id']), id_maps['client'].get(c['client_id']), id_maps['sale'].get(c['sale_id']))
        )
except:
    pass

new_conn.commit()
print("Data migration successful!")
new_conn.close()
old_conn.close()
