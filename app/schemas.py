# app/schemas.py
from pydantic import BaseModel, EmailStr, constr, conint


class User(BaseModel):
    user_id: int
    student_id: constr(pattern=r'^S\d{7}$') # used pattern instead of regex as python v2 no longer uses regex
    name: constr(min_length=2, max_length=50)
    email: EmailStr
    age: conint(gt=18)
