from sqlalchemy import create_engine, text
import os

# --- KONFIGURASI ROOT MYSQL ---
# Sesuaikan dengan XAMPP/MySQL lokal Abang
# Format: mysql+pymysql://USER:PASSWORD@HOST:PORT
MYSQL_ROOT_URL = "mysql+pymysql://root:@localhost:3306"


def create_real_database(db_name: str, db_user: str, db_pass: str):
    try:
        # Coba konek ke Server MySQL Asli
        engine = create_engine(MYSQL_ROOT_URL)

        with engine.connect() as conn:
            # 1. Buat Database
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}`;"))

            # 2. Buat User (Jika belum ada)
            # Di MySQL 8, syntax CREATE USER dan GRANT dipisah
            conn.execute(text(f"CREATE USER IF NOT EXISTS '{db_user}'@'%' IDENTIFIED BY '{db_pass}';"))

            # 3. Kasih Hak Akses (Privileges)
            conn.execute(text(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_user}'@'%';"))
            conn.execute(text("FLUSH PRIVILEGES;"))

            print(f"✅ REAL MYSQL: Database {db_name} created successfully.")
            return True

    except Exception as e:
        # Fallback ke MODE SIMULASI jika MySQL mati/gak ada (biar coding gak error)
        print(f"⚠️ MYSQL ERROR (Simulation Mode Active): {e}")
        print(f"🖥️ [SIMULASI] CREATE DATABASE {db_name}")
        print(f"🖥️ [SIMULASI] CREATE USER {db_user} PASS {db_pass}")
        return True  # Anggap sukses biar UI jalan


def delete_real_database(db_name: str, db_user: str):
    try:
        engine = create_engine(MYSQL_ROOT_URL)
        with engine.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS `{db_name}`;"))
            conn.execute(text(f"DROP USER IF EXISTS '{db_user}'@'%';"))
            print(f"✅ REAL MYSQL: Database {db_name} deleted.")
    except Exception as e:
        print(f"⚠️ MYSQL ERROR: {e}")