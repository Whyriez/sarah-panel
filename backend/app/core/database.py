from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Siapkan connect_args kosong sebagai default
connect_args = {}

# Cek apakah URL database menggunakan SQLite
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    # connect_args={"check_same_thread": False} itu wajib khusus buat SQLite
    connect_args = {"check_same_thread": False}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args  # Gunakan variabel connect_args yang sudah disesuaikan
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency: Fungsi ini dipanggil setiap kali ada request ke API yang butuh DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()