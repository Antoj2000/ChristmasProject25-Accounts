import pytest
# if pytest is not working
# change directory : cd "C:\Users\johns\OneDrive - Atlantic TU\CICD3\Labs\Lab2\Y4_Lab2"
# run python -m pytest


def user_payload(user_id=1, student_id="S1869912", name= "Anthony", email= "user@example.com", age= 19):
    return {
        "user_id": user_id,
        "student_id": student_id,
        "name": name,
        "email": email,
        "age": age
    }

def test_create_user(client):
    r = client.post("/api/users", json=user_payload())
    assert r.status_code == 201
    data = r.json()
    assert data["user_id"] == 1
    assert data["student_id"] == "S1869912"
    assert data["name"] == "Anthony"
    assert data["email"] == "user@example.com"
    assert data["age"] == 19

def test_create_user_id_conflict(client):
    r = client.post("/api/users", json=user_payload()) # try to create same user again
    assert r.status_code == 409
    assert r.json()["detail"] == "user_id already exists"

# will repeat test with different bad student ids
@pytest.mark.parametrize("bad_sid", ["S123", "1234567", "s1234567", "S12345678", "S1234A67"])
def test_bad_student_id(client, bad_sid):
    r = client.post("/api/users", json=user_payload(user_id=3, student_id=bad_sid)) # missing S
    assert r.status_code == 422

def test_delete_then_404(client):
    r = client.post("/api/users", json=user_payload(user_id=4)) # create user 
    r = client.delete("/api/users/delete/4") # delete user
    assert r.status_code == 204
    r = client.get("/api/users/4") # try to get deleted user
    assert r.status_code == 404


def test_update_user(client):
    r = client.post("/api/users", json=user_payload(user_id=5)) # create user 
    r = client.put("/api/users/update/5", json=user_payload(user_id=5, name="Conor")) # update user name
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Conor"
    r = client.get("/api/users/5") # get updated user
    data = r.json()
    assert data["name"] == "Conor"

def test_update_user_404(client):
    r = client.put("/api/users/update/999", json=user_payload(user_id=999)) # update non-existent user
    assert r.status_code == 404
    assert r.json()["detail"] == "user not found"