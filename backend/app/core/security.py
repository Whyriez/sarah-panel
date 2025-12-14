import bcrypt
from datetime import datetime, timedelta
from jose import jwt

# KUNCI RAHASIA (Nanti di production taruh di .env, jangan hardcode!)
SECRET_KEY = "rahasia_negara_ini_harus_panjang_dan_acak_banget_lho_bang"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Convert string ke bytes karena bcrypt butuh bytes
    password_byte_enc = plain_password.encode('utf-8')
    hashed_password_byte_enc = hashed_password.encode('utf-8')

    # Cek password
    return bcrypt.checkpw(password_byte_enc, hashed_password_byte_enc)


def get_password_hash(password: str) -> str:
    # Convert ke bytes
    pwd_bytes = password.encode('utf-8')

    # Generate salt dan hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)

    # Kembalikan sebagai string agar bisa disimpan di Database
    return hashed.decode('utf-8')


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Masukkan waktu expired ke dalam token
    to_encode.update({"exp": expire})

    # Bikin Token JWT
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt