import os
import sys
import sqlite3
import uuid

# 1. Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.core.management import call_command
from django.conf import settings

def main():
    old_db_path = 'beta_db.sqlite3'
    if not os.path.exists(old_db_path):
        print(f"Xato: '{old_db_path}' fayli topilmadi!")
        print("Iltimos, beta versiyadagi eski db.sqlite3 faylini shu papkaga tashlang va nomini 'beta_db.sqlite3' qilib o'zgartiring.")
        sys.exit(1)

    new_db_path = settings.DATABASES['default']['NAME']
    
    # 2. Eski bazani o'chirib yuboramiz (toza boshlash uchun)
    if os.path.exists(new_db_path):
        print(f"Eski ma'lumotlar bazasi tozalanmoqda: {new_db_path}")
        os.remove(new_db_path)

    # 3. Yangi baza strukturasini yaratamiz
    print("Yangi ma'lumotlar bazasi strukturasi yaratilmoqda (migrate)...")
    call_command('migrate', interactive=False)

    # 4. Ma'lumotlarni ko'chiramiz
    print("Ma'lumotlarni ko'chirish boshlandi...")
    old_conn = sqlite3.connect(old_db_path)
    old_conn.row_factory = sqlite3.Row
    new_conn = sqlite3.connect(new_db_path)
    new_conn.row_factory = sqlite3.Row

    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()

    # Create a default Store
    default_store_id = str(uuid.uuid4()).replace('-', '')
    new_cursor.execute(
        "INSERT INTO common_store (id, created_at, updated_at, name, is_active) VALUES (?, datetime('now'), datetime('now'), ?, ?)",
        (default_store_id, 'Beta Store', True)
    )

    id_maps = {
        'user': {}, 'product': {}, 'sizescale': {}, 'size': {}, 'variant': {}, 'client': {}, 'sale': {}
    }

    # Migrate Users
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

    # Migrate Products
    try:
        products = old_cursor.execute("SELECT * FROM product_products").fetchall()
        for p in products:
            new_id = str(uuid.uuid4()).replace('-', '')
            id_maps['product'][p['id']] = new_id
            
            # Use old ID as barcode if barcode is missing, or just always use it to keep it short
            old_barcode = p['barcode'] if p['barcode'] else str(p['id'])
            
            new_cursor.execute(
                "INSERT INTO product_products (id, created_at, updated_at, name, img, barcode, store_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (new_id, p['created_at'], p['updated_at'], p['name'], p['img'], old_barcode, default_store_id)
            )
    except Exception as e: print(f"Products xatosi: {e}")

    # Migrate SizeScales
    try:
        sizescales = old_cursor.execute("SELECT * FROM product_sizescale").fetchall()
        for s in sizescales:
            new_id = str(uuid.uuid4()).replace('-', '')
            id_maps['sizescale'][s['id']] = new_id
            new_cursor.execute(
                "INSERT INTO product_sizescale (id, created_at, updated_at, name, store_id) VALUES (?, ?, ?, ?, ?)",
                (new_id, s['created_at'], s['updated_at'], s['name'], default_store_id)
            )
    except Exception as e: print(f"SizeScale xatosi: {e}")

    # Migrate Sizes
    try:
        sizes = old_cursor.execute("SELECT * FROM product_size").fetchall()
        for s in sizes:
            new_id = str(uuid.uuid4()).replace('-', '')
            id_maps['size'][s['id']] = new_id
            new_cursor.execute(
                "INSERT INTO product_size (id, created_at, updated_at, name, size_scale_id, store_id) VALUES (?, ?, ?, ?, ?, ?)",
                (new_id, s['created_at'], s['updated_at'], s['name'], id_maps['sizescale'].get(s['size_scale_id']), default_store_id)
            )
    except Exception as e: print(f"Size xatosi: {e}")

    # Migrate Variants
    try:
        variants = old_cursor.execute("SELECT * FROM product_variant").fetchall()
        for v in variants:
            new_id = str(uuid.uuid4()).replace('-', '')
            id_maps['variant'][v['id']] = new_id
            
            # Use old ID as sku if sku is missing, to keep it short
            old_sku = v['sku'] if v['sku'] else str(v['id'])
            
            new_cursor.execute(
                "INSERT INTO product_variant (id, created_at, updated_at, sku, cost_price, sticker_price, quantity, product_id, size_scale_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (new_id, v['created_at'], v['updated_at'], old_sku, v['cost_price'], v['sticker_price'], v['quantity'], id_maps['product'].get(v['product_id']), id_maps['sizescale'].get(v['size_scale_id']))
            )
        
        variant_sizes = old_cursor.execute("SELECT * FROM product_variant_size").fetchall()
        for vs in variant_sizes:
            new_cursor.execute(
                "INSERT INTO product_variant_size (variant_id, size_id) VALUES (?, ?)",
                (id_maps['variant'].get(vs['variant_id']), id_maps['size'].get(vs['size_id']))
            )
    except Exception as e: print(f"Variant xatosi: {e}")

    # Migrate Clients
    try:
        clients = old_cursor.execute("SELECT * FROM sale_client").fetchall()
        for c in clients:
            new_id = str(uuid.uuid4()).replace('-', '')
            id_maps['client'][c['id']] = new_id
            new_cursor.execute(
                "INSERT INTO sale_client (id, created_at, updated_at, name, phone, store_id) VALUES (?, ?, ?, ?, ?, ?)",
                (new_id, c['created_at'], c['updated_at'], c['name'], c['phone'], default_store_id)
            )
    except Exception as e: print(f"Client xatosi: {e}")

    # Migrate PaymentMethods
    try:
        pms = old_cursor.execute("SELECT * FROM sale_paymentmenthod").fetchall()
        for pm in pms:
            new_cursor.execute(
                "INSERT INTO sale_paymentmenthod (id, name) VALUES (?, ?)",
                (pm['id'], pm['name'])
            )
    except Exception as e: print(f"PaymentMethod xatosi: {e}")

    # Migrate Sales
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
    except Exception as e: print(f"Sale xatosi: {e}")

    # Migrate SaleItems
    try:
        items = old_cursor.execute("SELECT * FROM sale_saleitem").fetchall()
        for i in items:
            new_id = str(uuid.uuid4()).replace('-', '')
            new_cursor.execute(
                "INSERT INTO sale_saleitem (id, created_at, updated_at, quantity, price, applied_tax_amount, sale_id, variant_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (new_id, i['created_at'], i['updated_at'], i['quantity'], i['price'], i['applied_tax_amount'], id_maps['sale'].get(i['sale_id']), id_maps['variant'].get(i['variant_id']))
            )
    except Exception as e: print(f"SaleItem xatosi: {e}")

    # Migrate Cash
    try:
        cashes = old_cursor.execute("SELECT * FROM sale_cash").fetchall()
        for c in cashes:
            new_id = str(uuid.uuid4()).replace('-', '')
            new_cursor.execute(
                "INSERT INTO sale_cash (id, created_at, updated_at, is_cash_in, amount, reason, store_id, user_id, client_id, sale_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (new_id, c['created_at'], c['updated_at'], c['is_cash_in'], c['amount'], c['reason'], default_store_id, id_maps['user'].get(c['user_id']), id_maps['client'].get(c['client_id']), id_maps['sale'].get(c['sale_id']))
            )
    except Exception as e: print(f"Cash xatosi: {e}")

    new_conn.commit()
    new_conn.close()
    old_conn.close()

    print("=====================================")
    print("MUVAFFAQIYATLI YAKUNLANDI!")
    print("=====================================")
    print(f"Yangi baza saqlangan joy: {new_db_path}")
    print("Endi dasturni odatdagidek ishga tushirishingiz mumkin!")

if __name__ == '__main__':
    main()
