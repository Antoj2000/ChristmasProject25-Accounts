# app/security.py
from pwdlib import PasswordHash

pwd = PasswordHash.recommended()

def hash_password(plain: str) -> str:
    return pwd.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd.verify(plain, hashed)
