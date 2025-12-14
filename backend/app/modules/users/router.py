from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.users import models, schemas
from app.core.security import get_password_hash
from app.modules.auth.deps import get_current_admin  # Kita kunci pakai ini

router = APIRouter(prefix="/users", tags=["User Management"])

# Schema request (bikin di file schemas.py kalau mau rapi, ditaruh sini jg gpp buat simpel)
from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str
    email: str = None
    role: str = "user"  # user / admin


class UserUpdate(BaseModel):
    password: str = None
    role: str = None


# 1. LIST ALL USERS (Admin Only)
@router.get("/")
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
               current_admin: models.User = Depends(get_current_admin)):
    users = db.query(models.User).offset(skip).limit(limit).all()
    # Hapus password hash dari response biar aman
    for u in users:
        u.hashed_password = "***"
    return users


# 2. CREATE USER (Admin Only)
@router.post("/")
def create_user(user: UserCreate, db: Session = Depends(get_db),
                current_admin: models.User = Depends(get_current_admin)):
    # Cek username kembar
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = get_password_hash(user.password)
    new_user = models.User(
        username=user.username,
        hashed_password=hashed_password,
        email=user.email,
        role=user.role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# 3. DELETE USER (Admin Only)
@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_admin: models.User = Depends(get_current_admin)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself!")

    db.delete(user)
    db.commit()
    return {"message": "User deleted"}