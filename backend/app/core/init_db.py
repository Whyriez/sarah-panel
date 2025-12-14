import os
from sqlalchemy.orm import Session
from app.modules.users import models
from app.core.security import get_password_hash
from dotenv import load_dotenv

# Load env variables
load_dotenv()


def init_db(db: Session):
    """
    Fungsi ini akan dipanggil setiap kali server start.
    Tugasnya mengecek apakah Admin sudah ada.
    """

    # Ambil data dari .env
    # Kalau gak ada di .env, kita pakai default "admin" / "password" (biar gak error)
    username = os.getenv("FIRST_SUPERUSER", "admin")
    password = os.getenv("FIRST_SUPERUSER_PASSWORD", "password")
    email = os.getenv("FIRST_SUPERUSER_EMAIL", "admin@example.com")

    # 1. Cek apakah user admin sudah ada di database?
    user = db.query(models.User).filter(models.User.username == username).first()

    if not user:
        print(f"⚡ [INIT] Admin user not found. Creating default superuser: {username}")

        # 2. Buat Admin Baru
        user_in = models.User(
            username=username,
            hashed_password=get_password_hash(password),
            email=email,
            role="admin",  # <--- PENTING: Role langsung Admin
            is_active=True,
        )

        db.add(user_in)
        db.commit()
        db.refresh(user_in)
        print("✅ [INIT] Superuser created successfully!")

    else:
        # Kalau sudah ada, diam saja
        print(f"✅ [INIT] Superuser '{username}' already exists. Skipping creation.")