import os
import django
import sqlite3
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

db_path = settings.DATABASES['default']['NAME']
print("DB Path:", db_path)

conn = sqlite3.connect(db_path)
for row in conn.execute("SELECT sql FROM sqlite_master WHERE type='table'"):
    print(row[0])
