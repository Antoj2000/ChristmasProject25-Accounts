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

#Get user by id
#@app.get("/api/users/{user_id}")
#def get_user(user_id: int):
    for u in users:
        if u.user_id == user_id:
            return u
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

#Create user
@app.post("/api/accounts", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_account(account: UserCreate, db: Session = Depends(get_db)):
    #Check if user already exists 
    db_account = AccountsDB(**account.model_dump())
    db.add(db_account)
    commit_or_rollback(db, "Account already exists")
    db.refresh(db_account)
    return db_account
    
#Update existing user
#@app.put("/api/users/update/{user_id}")
#def edit_user(user_id: int, edited_user: User): # user id from URL and user object from payload
    for i, u in enumerate(users): # checks list of users 
        if u.user_id == user_id: # match ids
            users[i] = edited_user # replace the old user with the new one
            return edited_user 
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found") #404 if user doesnt exist 


#Delete existing user
#@app.delete("/api/users/delete/{user_id}", status_code=status.HTTP_204_NO_CONTENT) #if endpoint succeeds return status code 
#def delete_user(user_id: int): # user ID from URL
    for u in users: # checks list 
        if u.user_id == user_id: # match ids 
            users.remove(u) # remove user
            return # exits function - this will then return 204 if successful 
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found") #404 if user doesnt exist 
                

        