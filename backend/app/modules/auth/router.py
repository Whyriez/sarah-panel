from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.users import models
from app.core.security import verify_password, create_access_token

router = APIRouter(tags=["Authentication"])


@router.post("/auth/token")
@limiter.limit("5/minute")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # 1. Cari user di database berdasarkan username
    user = db.query(models.User).filter(models.User.username == form_data.username).first()

    # 2. Validasi: User ada? Password cocok?
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Kalau lolos, buatkan Access Token
    access_token = create_access_token(data={"sub": user.username, "role": user.role})

    return {"access_token": access_token, "token_type": "bearer"}