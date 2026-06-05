import os
import django
from django.conf import settings
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

with connection.cursor() as cursor:
    try:
        cursor.execute('ALTER TABLE "sale_auditlog" ADD COLUMN "user_id" char(32) NULL REFERENCES "user_user" ("id") DEFERRABLE INITIALLY DEFERRED;')
        print("Auditlog user_id OK")
    except Exception as e:
        print("Auditlog user_id ERROR:", e)

    try:
        cursor.execute('ALTER TABLE "sale_cash" ADD COLUMN "store_id" char(32) NULL REFERENCES "common_store" ("id") DEFERRABLE INITIALLY DEFERRED;')
        print("Cash store_id OK")
    except Exception as e:
        print("Cash store_id ERROR:", e)
        
    try:
        cursor.execute('ALTER TABLE "sale_cash" ADD COLUMN "user_id" char(32) NULL REFERENCES "user_user" ("id") DEFERRABLE INITIALLY DEFERRED;')
        print("Cash user_id OK")
    except Exception as e:
        print("Cash user_id ERROR:", e)
