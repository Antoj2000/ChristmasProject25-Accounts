# app/schemas.py
from pydantic import BaseModel, EmailStr, constr, conint, field_validator, StringConstraints, Field
from typing import Annotated, Optional, List


# ---------- Reusable Type aliases -----------

AccountStr = Annotated[str, constr(pattern=r'^A\d{5}$')]
NameStr = Annotated[str, StringConstraints(min_length=2, max_length=50)]
PasswordStr = Annotated[str, StringConstraints(min_length=8, max_length=20)]

class UserCreate(BaseModel):

    account_no: AccountStr 
    name: NameStr
    email: EmailStr
    password: PasswordStr 

    @field_validator('password')
    def password_must_have_upper_and_digit(cls, password):
        if not any(c.islower() for c in password):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isupper() for c in password):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.isdigit() for c in password):
            raise ValueError('Password must contain at least one digit')
        return password


class UserRead(BaseModel):
    id : int
    account_no: AccountStr
    name: NameStr
    email: EmailStr
    password: PasswordStr


