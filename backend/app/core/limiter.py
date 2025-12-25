from slowapi import Limiter
from slowapi.util import get_remote_address

# Inisialisasi Limiter di sini
limiter = Limiter(key_func=get_remote_address)