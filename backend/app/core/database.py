from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Kita pakai SQLite file bernama 'sarahpanel.db'
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# connect_args={"check_same_thread": False} itu wajib khusus buat SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
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