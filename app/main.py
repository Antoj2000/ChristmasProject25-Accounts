# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from .database import SessionLocal, engine
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from .schemas import(
    UserCreate, UserRead,
    ConRead, UserEdit,
    PhoneNumberCreate,
    PhoneNumberRead,
    EmailCreate,
    EmailRead,
    AddressCreate,
    AddressRead,
)
from .models import AccountsDB, PhoneNumberDB, EmailDB, AddressDB, Base
from .utils import assign_number_range, generate_next_account_no
from .worker import publish_accounts_created, publish_accounts_deleted
from .security import hash_password, get_current_account_claims

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # dev-friendly; tighten in prod
    allow_methods=["*"],
    allow_headers=["*"],
)

# Uncomment this line to reset DB
#Base.metadata.drop_all(bind=engine)
#Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def commit_or_rollback(db: Session, error_msg: str):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

@app.get("/health")
def health():
    return {"status" : "ok"}

# --- Accounts

#Returns all accounts 
@app.get("/api/accounts", response_model=list[UserRead])
def list_accounts(db: Session = Depends(get_db)):
    stmt = (
        select(AccountsDB)
        .options(
            selectinload(AccountsDB.phone_numbers),
            selectinload(AccountsDB.emails),
            selectinload(AccountsDB.addresses),
        )
        .order_by(AccountsDB.id)
    )
    return db.execute(stmt).scalars().all()

#Get account by account number
@app.get("/api/accounts/{account_no}", response_model=UserRead)
def get_account_by_number(account_no: str, db: Session = Depends(get_db)):
    stmt = (
        select(AccountsDB)
        .options(
            selectinload(AccountsDB.phone_numbers),
            selectinload(AccountsDB.emails),
            selectinload(AccountsDB.addresses),
        )
        .where(AccountsDB.account_no == account_no)
    )
    acc = db.execute(stmt).scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    return acc

#Create user
@app.post("/api/accounts", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_account(account: UserCreate, db: Session = Depends(get_db)):
    start, end = assign_number_range(db)
    next_account_no = generate_next_account_no(db)
    acc = account.model_dump()
    plain = acc.pop("password")            
    acc["password_hash"] = hash_password(plain) 
    acc["account_no"] = next_account_no
    acc.update({
        "range_start": start,
        "range_end": end,
        "current_con_num": start
    })
    #Check if user already exists 
    db_account = AccountsDB(**acc)
    db.add(db_account)
    commit_or_rollback(db, "Account already exists")
    db.refresh(db_account)

    event = {
    "account_id": db_account.id,
    "account_no": db_account.account_no,
    "email": db_account.email,
    "password_hash": db_account.password_hash, 
    }

    await publish_accounts_created(event)
    return db_account
    
#Update existing account
@app.put("/api/accounts/update/{account_no}", response_model=UserRead)
def edit_account(account_no: str, payload: UserEdit, db: Session = Depends(get_db), claims: dict = Depends(get_current_account_claims)):
    token_account_no = claims.get("account_no")
    if not token_account_no or token_account_no != account_no:
        raise HTTPException(status_code=403, detail="Token not valid for this account")

    stmt = select(AccountsDB).where(AccountsDB.account_no==account_no)
    acc = db.execute(stmt).scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    
    for key, value in payload.model_dump().items():
        setattr(acc, key, value)
    try:
        db.commit()
        db.refresh(acc)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email or Account No already exists")
    return acc
    

#Delete existing account
@app.delete("/api/accounts/delete/{account_no}", status_code=204) #if endpoint succeeds return status code 
async def delete_account(account_no: str, db: Session = Depends(get_db), claims: dict = Depends(get_current_account_claims)):
    token_account_no = claims.get("account_no")
    if not token_account_no or token_account_no != account_no:
        raise HTTPException(status_code=403, detail="Token not valid for this account")
    
    stmt = select(AccountsDB).where(AccountsDB.account_no==account_no)
    acc = db.execute(stmt).scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(acc)
    db.commit()

    event = {
    "account_id": acc.id,
    "account_no": acc.account_no,
    }
    await publish_accounts_deleted(event)


#Get current consignment number
@app.get("/api/accounts/{account_no}/currentConNum", response_model=ConRead)
def get_current_con_num(account_no: str, db: Session = Depends(get_db)):
    acc = db.query(AccountsDB).filter(AccountsDB.account_no == account_no).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    return acc
    
#Increment current con number
@app.patch("/api/accounts/{account_no}/incrementConNum", response_model=ConRead)
def increment_con_num(account_no: str, db: Session = Depends(get_db)):
    acc = db.query(AccountsDB).with_for_update().filter(AccountsDB.account_no == account_no).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    acc.current_con_num += 1
    db.commit() 
    db.refresh(acc)
    return acc

# --- Phone number endpoints ---

@app.post("/api/accounts/{account_no}/phone-numbers", response_model=PhoneNumberRead)
def add_phone_number(
    account_no: str,
    phone: PhoneNumberCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_account_claims),
):
    """Add a phone number to the authenticated account.

    If the new number is marked as primary or if there are no existing
    numbers, the ``is_primary`` flag will be set and all other numbers
    will be demoted.
    """
    token_account_no = claims.get("account_no")
    if not token_account_no or token_account_no != account_no:
        raise HTTPException(status_code=403, detail="Token not valid for this account")
    stmt = (
        select(AccountsDB)
        .options(selectinload(AccountsDB.phone_numbers))
        .where(AccountsDB.account_no == account_no)
    )
    acc = db.execute(stmt).scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    # Determine whether this should be the primary phone number
    make_primary = bool(phone.is_primary)
    phone_db = PhoneNumberDB(value=phone.value, is_primary=False, account_id=acc.id)
    if len(acc.phone_numbers) == 0:
        # first number becomes primary automatically
        phone_db.is_primary = True
    elif make_primary:
        # demote existing primary numbers
        for pn in acc.phone_numbers:
            pn.is_primary = False
        phone_db.is_primary = True
    db.add(phone_db)
    db.commit()
    db.refresh(phone_db)
    return phone_db


@app.put("/api/accounts/{account_no}/phone-numbers/{phone_id}", response_model=PhoneNumberRead)
def update_phone_number(
    account_no: str,
    phone_id: int,
    phone: PhoneNumberCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_account_claims),
):
    """Update an existing phone number.

    A primary phone number cannot be demoted unless another number is
    promoted in the same request.  To change the primary number, send
    ``is_primary=True`` for the desired number.
    """
    token_account_no = claims.get("account_no")
    if not token_account_no or token_account_no != account_no:
        raise HTTPException(status_code=403, detail="Token not valid for this account")
    stmt = (
        select(PhoneNumberDB)
        .join(AccountsDB)
        .options(selectinload(PhoneNumberDB.account))
        .where(AccountsDB.account_no == account_no, PhoneNumberDB.id == phone_id)
    )
    phone_db = db.execute(stmt).scalar_one_or_none()
    if not phone_db:
        raise HTTPException(status_code=404, detail="Phone number not found")
    # Update the value
    phone_db.value = phone.value
    if phone.is_primary and not phone_db.is_primary:
        # promote this number and demote others
        acc = phone_db.account
        for pn in acc.phone_numbers:
            pn.is_primary = False
        phone_db.is_primary = True
    elif phone.is_primary is False and phone_db.is_primary:
        # Attempting to unset primary directly is not allowed
        raise HTTPException(
            status_code=400,
            detail="Cannot unset the primary phone number directly; set another number as primary instead",
        )
    db.commit()
    db.refresh(phone_db)
    return phone_db


@app.delete("/api/accounts/{account_no}/phone-numbers/{phone_id}", status_code=204)
def delete_phone_number(
    account_no: str,
    phone_id: int,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_account_claims),
):
    """Delete a phone number from the authenticated account.

    If the deleted number is primary and there is another number
    available, the first remaining number will be promoted to primary.
    """
    token_account_no = claims.get("account_no")
    if not token_account_no or token_account_no != account_no:
        raise HTTPException(status_code=403, detail="Token not valid for this account")
    stmt = (
        select(PhoneNumberDB)
        .join(AccountsDB)
        .options(selectinload(PhoneNumberDB.account))
        .where(AccountsDB.account_no == account_no, PhoneNumberDB.id == phone_id)
    )
    phone_db = db.execute(stmt).scalar_one_or_none()
    if not phone_db:
        raise HTTPException(status_code=404, detail="Phone number not found")
    acc = phone_db.account
    if phone_db.is_primary:
        # Find another phone number to promote
        other = next((pn for pn in acc.phone_numbers if pn.id != phone_id), None)
        if other is not None:
            other.is_primary = True
    db.delete(phone_db)
    db.commit()


# --- Email endpoints ---

@app.post("/api/accounts/{account_no}/emails", response_model=EmailRead)
def add_email(
    account_no: str,
    email: EmailCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_account_claims),
):
    """Add an email address to the authenticated account."""
    token_account_no = claims.get("account_no")
    if not token_account_no or token_account_no != account_no:
        raise HTTPException(status_code=403, detail="Token not valid for this account")
    stmt = (
        select(AccountsDB)
        .options(selectinload(AccountsDB.emails))
        .where(AccountsDB.account_no == account_no)
    )
    acc = db.execute(stmt).scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    make_primary = bool(email.is_primary)
    email_db = EmailDB(value=email.value, is_primary=False, account_id=acc.id)
    if len(acc.emails) == 0:
        email_db.is_primary = True
    elif make_primary:
        for e in acc.emails:
            e.is_primary = False
        email_db.is_primary = True
    db.add(email_db)
    db.commit()
    db.refresh(email_db)
    return email_db


@app.put("/api/accounts/{account_no}/emails/{email_id}", response_model=EmailRead)
def update_email(
    account_no: str,
    email_id: int,
    email: EmailCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_account_claims),
):
    """Update an email address on the authenticated account."""
    token_account_no = claims.get("account_no")
    if not token_account_no or token_account_no != account_no:
        raise HTTPException(status_code=403, detail="Token not valid for this account")
    stmt = (
        select(EmailDB)
        .join(AccountsDB)
        .options(selectinload(EmailDB.account))
        .where(AccountsDB.account_no == account_no, EmailDB.id == email_id)
    )
    email_db = db.execute(stmt).scalar_one_or_none()
    if not email_db:
        raise HTTPException(status_code=404, detail="Email address not found")
    email_db.value = email.value
    if email.is_primary and not email_db.is_primary:
        acc = email_db.account
        for e in acc.emails:
            e.is_primary = False
        email_db.is_primary = True
    elif email.is_primary is False and email_db.is_primary:
        raise HTTPException(
            status_code=400,
            detail="Cannot unset the primary email directly; set another email as primary instead",
        )
    db.commit()
    db.refresh(email_db)
    return email_db


@app.delete("/api/accounts/{account_no}/emails/{email_id}", status_code=204)
def delete_email(
    account_no: str,
    email_id: int,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_account_claims),
):
    """Remove an email address from the authenticated account.

    If the deleted email was primary, another email will be promoted if
    available.
    """
    token_account_no = claims.get("account_no")
    if not token_account_no or token_account_no != account_no:
        raise HTTPException(status_code=403, detail="Token not valid for this account")
    stmt = (
        select(EmailDB)
        .join(AccountsDB)
        .options(selectinload(EmailDB.account))
        .where(AccountsDB.account_no == account_no, EmailDB.id == email_id)
    )
    email_db = db.execute(stmt).scalar_one_or_none()
    if not email_db:
        raise HTTPException(status_code=404, detail="Email address not found")
    acc = email_db.account
    if email_db.is_primary:
        other = next((e for e in acc.emails if e.id != email_id), None)
        if other is not None:
            other.is_primary = True
    db.delete(email_db)
    db.commit()


# --- Address endpoints ---

@app.post("/api/accounts/{account_no}/addresses", response_model=AddressRead)
def add_address(
    account_no: str,
    address: AddressCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_account_claims),
):
    """Add a delivery address to the authenticated account."""
    token_account_no = claims.get("account_no")
    if not token_account_no or token_account_no != account_no:
        raise HTTPException(status_code=403, detail="Token not valid for this account")
    stmt = (
        select(AccountsDB)
        .options(selectinload(AccountsDB.addresses))
        .where(AccountsDB.account_no == account_no)
    )
    acc = db.execute(stmt).scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    make_default = bool(address.is_default)
    address_db = AddressDB(
        account_id=acc.id,
        title=address.title,
        line1=address.line1,
        line2=address.line2,
        line3=address.line3,
        line4=address.line4,
        eircode=address.eircode,
        type=address.type,
        is_default=False,
    )
    if len(acc.addresses) == 0:
        address_db.is_default = True
    elif make_default:
        for addr in acc.addresses:
            addr.is_default = False
        address_db.is_default = True
    db.add(address_db)
    db.commit()
    db.refresh(address_db)
    return address_db


@app.put("/api/accounts/{account_no}/addresses/{address_id}", response_model=AddressRead)
def update_address(
    account_no: str,
    address_id: int,
    address: AddressCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_account_claims),
):
    """Update a delivery address on the authenticated account."""
    token_account_no = claims.get("account_no")
    if not token_account_no or token_account_no != account_no:
        raise HTTPException(status_code=403, detail="Token not valid for this account")
    stmt = (
        select(AddressDB)
        .join(AccountsDB)
        .options(selectinload(AddressDB.account))
        .where(AccountsDB.account_no == account_no, AddressDB.id == address_id)
    )
    address_db = db.execute(stmt).scalar_one_or_none()
    if not address_db:
        raise HTTPException(status_code=404, detail="Address not found")
    # Update fields
    address_db.title = address.title
    address_db.line1 = address.line1
    address_db.line2 = address.line2
    address_db.line3 = address.line3
    address_db.line4 = address.line4
    address_db.eircode = address.eircode
    address_db.type = address.type
    if address.is_default and not address_db.is_default:
        acc = address_db.account
        for addr in acc.addresses:
            addr.is_default = False
        address_db.is_default = True
    elif address.is_default is False and address_db.is_default:
        raise HTTPException(
            status_code=400,
            detail="Cannot unset the default address directly; set another address as default instead",
        )
    db.commit()
    db.refresh(address_db)
    return address_db


@app.delete("/api/accounts/{account_no}/addresses/{address_id}", status_code=204)
def delete_address(
    account_no: str,
    address_id: int,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_account_claims),
):
    """Remove an address from the authenticated account.

    If the deleted address was the default and another address exists,
    that address becomes the new default automatically.
    """
    token_account_no = claims.get("account_no")
    if not token_account_no or token_account_no != account_no:
        raise HTTPException(status_code=403, detail="Token not valid for this account")
    stmt = (
        select(AddressDB)
        .join(AccountsDB)
        .options(selectinload(AddressDB.account))
        .where(AccountsDB.account_no == account_no, AddressDB.id == address_id)
    )
    address_db = db.execute(stmt).scalar_one_or_none()
    if not address_db:
        raise HTTPException(status_code=404, detail="Address not found")
    acc = address_db.account
    if address_db.is_default:
        other = next((a for a in acc.addresses if a.id != address_id), None)
        if other is not None:
            other.is_default = True
    db.delete(address_db)
    db.commit()