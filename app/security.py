# app/security.py
from pwdlib import PasswordHash
import os
import jwt
from jwt import InvalidTokenError, ExpiredSignatureError, InvalidAudienceError, InvalidIssuerError

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

pwd = PasswordHash.recommended()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
JWT_ISS = os.getenv("JWT_ISS", "auth-service")
JWT_AUD = os.getenv("JWT_AUD", "dpd-app")

bearer_scheme = HTTPBearer(auto_error=True)

def decode_access_token(token: str) -> dict:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET is not set for this service")

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALG],
            audience=JWT_AUD,
            issuer=JWT_ISS,
        )
        return payload

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except (InvalidAudienceError, InvalidIssuerError):
        raise HTTPException(status_code=401, detail="Invalid token claims")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    

def get_current_account_claims(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    return decode_access_token(creds.credentials)

def hash_password(plain: str) -> str:
    return pwd.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd.verify(plain, hashed)
