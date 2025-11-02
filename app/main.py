# app/main.py

from fastapi import FastAPI, HTTPException, status, Depends, Response
from .database import SessionLocal, engine
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from .schemas import(
    UserCreate, UserRead
)
from .models import AccountsDB, Base

app = FastAPI()

# Uncomment this line to reset DB
# Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

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
def create_account(account: UserCreate, db: Session = Depends(get_db)):
    #Check if user already exists 
    db_account = AccountsDB(**account.model_dump())
    db.add(db_account)
    commit_or_rollback(db, "Account already exists")
    db.refresh(db_account)
    return db_account
    
#Update existing account
@app.put("/api/accounts/update/{account_no}", response_model=UserRead)
def edit_account(account_no: str, payload: UserCreate, db: Session = Depends(get_db)):
    stmt = select(AccountsDB).where(AccountsDB.account_no==account_no)
    acc = db.execute(stmt).scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    for key, value in payload.model_dump().items():
        setattr(acc, key, value)
    try:
        db.commit()
        db.refresh(acc)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email or Account No already exists")
    return acc
    

#Delete existing account
@app.delete("/api/accounts/delete/{account_no}", status_code=status.HTTP_204_NO_CONTENT) #if endpoint succeeds return status code 
def delete_account(account_no: str, db: Session = Depends(get_db)):
    stmt = select(AccountsDB).where(AccountsDB.account_no==account_no)
    acc = db.execute(stmt).scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    db.delete(acc)
    db.commit()
    