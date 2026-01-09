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
    ConRead
)
from .models import AccountsDB, Base
from .utils import assign_number_range
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

#Get all users
@app.get("/api/accounts", response_model=list[UserRead])
def list_accounts(db: Session = Depends(get_db)):
    stmt = select(AccountsDB).order_by(AccountsDB.id)
    return db.execute(stmt).scalars().all()

#Get account by account number
@app.get("/api/accounts/{account_no}", response_model=UserRead)
def get_account_by_number(account_no: str, db: Session = Depends(get_db)):
    stmt = select(AccountsDB).where(AccountsDB.account_no==account_no)
    acc = db.execute(stmt).scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    return acc

#Create user
@app.post("/api/accounts", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_account(account: UserCreate, db: Session = Depends(get_db)):
    start, end = assign_number_range(db)
    acc = account.model_dump()
    plain = acc.pop("password")            
    acc["password_hash"] = hash_password(plain) 
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
def edit_account(account_no: str, payload: UserCreate, db: Session = Depends(get_db), claims: dict = Depends(get_current_account_claims)):
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