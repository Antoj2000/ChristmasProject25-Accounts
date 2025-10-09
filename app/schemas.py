# app/schemas.py
from pydantic import BaseModel, EmailStr, constr, conint, field_validator


class User(BaseModel):
    user_id: int
    account_no: constr(pattern=r'^A\d{5}$') # used pattern instead of regex as python v2 no longer uses regex
    name: constr(min_length=2, max_length=50)
    email: EmailStr
    password: constr(min_length=8) 

    @field_validator('password')
    def password_must_have_upper_and_digit(cls, passWord):
        if not any(c.islower() for c in passWord):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isupper() for c in passWord):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.isdigit() for c in passWord):
            raise ValueError('Password must contain at least one digit')
        if len(passWord) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if len(passWord) > 20:
            raise ValueError('Password must be at most 20 characters long')
        return passWord
