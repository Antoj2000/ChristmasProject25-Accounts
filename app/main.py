# app/main.py

from fastapi import FastAPI, HTTPException, status
from .schemas import User

app = FastAPI()
users: list[User] = []

@app.get("/hello")
def hello():
    return {"message": "Hello, World!"}

#Get all users
@app.get("/api/users")
def get_users():
    return users

#Get user by id
@app.get("/api/users/{user_id}")
def get_user(user_id: int):
    for u in users:
        if u in users: 
            if u.user_id == user_id:
                return u
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

#Create user
@app.post("/api/users", status_code=status.HTTP_201_CREATED)
def add_user(user: User):
    #Check if user already exists 
    if any(u.user_id == user.user_id for u in users):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="user_id already exists")
    users.append(user) #append means to add to list
    return user
    
#Update existing user
@app.put("/api/users/update/{user_id}")
def edit_user(user_id: int, edited_user: User): # user id from URL and user object from payload
    for i, u in enumerate(users): # checks list of users 
        if u.user_id == user_id: # match ids
            users[i] = edited_user # replace the old user with the new one
            return edited_user 
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found") #404 if user doesnt exist 


#Delete existing user
@app.delete("/api/users/delete/{user_id}", status_code=status.HTTP_204_NO_CONTENT) #if endpoint succeeds return status code 
def delete_user(user_id: int): # user ID from URL
    for u in users: # checks list 
        if u.user_id == user_id: # match ids 
            users.remove(u) # remove user
            return # exits function - this will then return 204 if successful 
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found") #404 if user doesnt exist 
                

#Health endpoint
@app.get("/api/health", status_code=status.HTTP_200_OK)
def health():
    return "OK"
    
        