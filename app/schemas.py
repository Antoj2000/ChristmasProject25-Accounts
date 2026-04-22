# app/schemas.py
from pydantic import BaseModel, EmailStr, constr, conint, field_validator, StringConstraints, Field
from typing import Annotated, Optional, List

# ---------- Reusable Type aliases -----------
AccountStr = Annotated[str, StringConstraints(pattern=r'^A\d{5}$')]
NameStr = Annotated[str, StringConstraints(min_length=2, max_length=50)]
PasswordStr = Annotated[str, StringConstraints(min_length=8, max_length=20)]
PhoneStr = Annotated[str, StringConstraints(min_length=3, max_length=20)]
AddressTitleStr = Annotated[str, StringConstraints(min_length=1, max_length=50)]
AddressLineStr = Annotated[str, StringConstraints(min_length=1, max_length=100)]
EircodeStr = Annotated[str, StringConstraints(min_length=8, max_length=8)]

# PHONE NUMBER SCHEMAS
class PhoneNumberCreate(BaseModel):
    """Schema for creating a new phone number."""
    value: PhoneStr
    is_primary: Optional[bool] = False


class PhoneNumberRead(BaseModel):
    """Schema returned for a phone number record."""
    id: int
    value: PhoneStr
    is_primary: bool

    class Config:
        from_attributes = True


# EMAIL SCHEMAS
class EmailCreate(BaseModel):
    """Schema for creating a new email address."""
    value: EmailStr
    is_primary: Optional[bool] = False


class EmailRead(BaseModel):
    """Schema returned for an email record."""
    id: int
    value: EmailStr
    is_primary: bool

    class Config:
        from_attributes = True

# ADDRESS SCHEMAS

class AddressCreate(BaseModel):
    """Schema for creating a new address."""
    title: AddressTitleStr
    line1: AddressLineStr
    line2: Optional[AddressLineStr] = None
    line3: AddressLineStr 
    line4: AddressLineStr 
    eircode: EircodeStr
    type: str
    is_default: Optional[bool] = False

class AddressRead(BaseModel):
    """Schema returned for an address record."""
    id: int
    title: AddressTitleStr
    line1: AddressLineStr
    line2: Optional[AddressLineStr] = None
    line3: AddressLineStr 
    line4: AddressLineStr 
    eircode: EircodeStr
    type: str
    is_default: Optional[bool] = False

    class Config:
        from_attributes = True

# USER SCHEMAS
class UserCreate(BaseModel):

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
    range_start: int
    range_end: int
    current_con_num: int
    phone_numbers: List[PhoneNumberRead] = []
    emails: List[EmailRead] = []
    addresses: List[AddressRead] = []

    class Config:
        from_attributes = True

class UserEdit(BaseModel):
    name: NameStr
    email: EmailStr

class ConRead(BaseModel):
    account_no: AccountStr
    current_con_num: int