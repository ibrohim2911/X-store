import shutil
import os

db_path = os.path.join("config", "db", "db.sqlite3")
backup_path = os.path.join("config", "db", "db_old.sqlite3")

if os.path.exists(db_path):
    shutil.copy2(db_path, backup_path)
    print(f"Successfully backed up {db_path} to {backup_path}")
else:
    print(f"Database {db_path} not found!")
