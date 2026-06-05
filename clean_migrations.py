import os
import glob

apps = ['common', 'product', 'sale', 'user']
for app in apps:
    migration_dir = os.path.join(app, 'migrations')
    if os.path.exists(migration_dir):
        files = glob.glob(os.path.join(migration_dir, '*.py'))
        for f in files:
            if not f.endswith('__init__.py'):
                os.remove(f)
                print(f'Deleted {f}')

import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

db_path = settings.DATABASES['default']['NAME']
if os.path.exists(db_path):
    os.remove(db_path)
    print(f'Deleted {db_path}')
else:
    print(f'{db_path} not found')
