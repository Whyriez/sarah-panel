import secrets
import string
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.databases import models, schemas
from app.modules.auth.deps import get_current_user
from app.modules.users.models import User
from app.system.mysql_manager import create_real_database, delete_real_database

router = APIRouter(prefix="/databases", tags=["Databases"])


# Generate Password Random Kuat
def generate_password(length=16):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))


@router.get("/", response_model=list[schemas.DatabaseResponse])
def read_dbs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(models.Database).filter(models.Database.user_id == current_user.id).all()


@router.post("/", response_model=schemas.DatabaseResponse)
def create_db(payload: schemas.DatabaseCreate, db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    # 1. ATURAN PREFIX: user_alim_namadb
    # Gunakan system_username kalau ada, kalau gak pakai username panel
    prefix = current_user.system_username if current_user.system_username else current_user.username

    real_db_name = f"{prefix}_{payload.name}"
    real_db_user = f"{prefix}"  # Username DB disamakan dengan user panel biar simpel (atau bisa dibikin unik per DB)

    # Cek duplikat di panel DB
    if db.query(models.Database).filter(models.Database.name == real_db_name).first():
        raise HTTPException(status_code=400, detail="Database name already exists")

    # 2. Generate Password
    db_pass = generate_password()

    # 3. Panggil System Manager (MySQL Asli)
    create_real_database(real_db_name, real_db_user, db_pass)

    # 4. Simpan ke Database Panel
    new_db = models.Database(
        name=real_db_name,
        db_user=real_db_user,
        db_password=db_pass,
        user_id=current_user.id
    )

    db.add(new_db)
    db.commit()
    db.refresh(new_db)

    return new_db


@router.delete("/{db_id}")
def delete_db(db_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    database = db.query(models.Database).filter(models.Database.id == db_id,
                                                models.Database.user_id == current_user.id).first()
    if not database:
        raise HTTPException(status_code=404, detail="Database not found")

    # Hapus dari MySQL Asli
    delete_real_database(database.name, database.db_user)

    # Hapus dari DB Panel
    db.delete(database)
    db.commit()

    return {"message": "Database deleted"}