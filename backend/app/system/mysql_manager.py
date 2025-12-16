from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Load environment variables dari file .env
load_dotenv()

# Ambil password root dari .env (yang digenerate oleh install.sh tadi)
DB_ROOT_PASS = os.getenv("MYSQL_ROOT_PASSWORD", "")

# --- KONFIGURASI ROOT MYSQL ---
# Format: mysql+pymysql://USER:PASSWORD@HOST:PORT
# Kita gunakan f-string untuk memasukkan password secara dinamis
MYSQL_ROOT_URL = f"mysql+pymysql://root:{DB_ROOT_PASS}@localhost:3306"

def create_real_database(db_name: str, db_user: str, db_pass: str):
    try:
        # Coba konek ke Server MySQL Asli
        engine = create_engine(MYSQL_ROOT_URL)

        with engine.connect() as conn:
            # 1. Buat Database
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}`;"))

            # 2. Buat User (Syntax kompatibel MySQL 8 & MariaDB)
            conn.execute(text(f"CREATE USER IF NOT EXISTS '{db_user}'@'%' IDENTIFIED BY '{db_pass}';"))

            # 3. Kasih Hak Akses (Privileges)
            conn.execute(text(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_user}'@'%';"))
            conn.execute(text("FLUSH PRIVILEGES;"))

            print(f"✅ REAL MYSQL: Database {db_name} created successfully.")
            return True

    except Exception as e:
        print(f"⚠️ MYSQL ERROR: {e}")
        # Jangan fallback ke simulasi jika errornya autentikasi, supaya ketahuan kalau ada salah config
        return False

def delete_real_database(db_name: str, db_user: str):
    try:
        engine = create_engine(MYSQL_ROOT_URL)
        with engine.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS `{db_name}`;"))
            conn.execute(text(f"DROP USER IF EXISTS '{db_user}'@'%';"))
            print(f"✅ REAL MYSQL: Database {db_name} deleted.")
    except Exception as e:
        print(f"⚠️ MYSQL ERROR: {e}")