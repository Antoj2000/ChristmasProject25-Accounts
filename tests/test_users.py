import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app, get_db
from app.models import Base

# if pytest is not working
# change directory : cd "C:\Users\johns\OneDrive - Atlantic TU\CICD3\Labs\Lab2\Y4_Lab2"
# run python -m pytest

TEST_DB_URL = "sqlite+pysqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False,)
Base.metadata.create_all(bind=engine)

@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        # hand the client to the test
        yield c
        # --- teardown happens when the 'with' block exits ---

def user_payload(account_no="A12345", name= "Anthony", email= "user@example.com", password="Password1"):
    return {
        "account_no": account_no,
        "name": name,
        "email": email,
        "password": password
    }

def test_create_user(client):
    r = client.post("/api/accounts", json=user_payload())
    assert r.status_code == 201

def test_create_account_no_conflict(client):
    r = client.post("/api/accounts", json=user_payload()) # try to create same user again
    assert r.json()["detail"] == "Account already exists"

# will repeat test with bad Account Numbers
@pytest.mark.parametrize("bad_sid", ["A1234", "A123456", "B12345", "12345", "A12B45"])
def test_bad_account_no(client, bad_sid):
    r = client.post("/api/accounts", json=user_payload(email="aj@gmail.com", account_no=bad_sid)) 
    assert r.status_code == 422

# will repeat test with bad passwords
@pytest.mark.parametrize("bad_pwd", ["password", "PASSWORD1", "Passw1", "Password!", "Password123456789012345"])
def test_bad_password(client, bad_pwd):
    r = client.post("/api/accounts", json=user_payload(email="aj@gmail.com", password=bad_pwd)) # missing uppercase letter or digit or too short/long
    assert r.status_code == 422

def test_delete_then_404(client):
    r = client.post("/api/accounts", json=user_payload(account_no="A66666", email="deleteme@yahoo.com")) # create user 
    r = client.delete("/api/accounts/delete/A66666") # delete user
    assert r.status_code == 204
    r = client.get("/api/accounts/A66666") # try to get deleted user
    assert r.status_code == 404


def test_update_account(client):
    r = client.post("/api/accounts", json=user_payload(account_no="A11111", email="update@bing.com")) # create user 
    r = client.put("/api/accounts/update/A11111", json=user_payload(account_no="A11111",email="update@bing.com", name="Conor")) # update user name
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Conor"
    r = client.get("/api/accounts/A11111") # get updated user
    data = r.json()
    assert data["name"] == "Conor"

def test_update_account_404(client):
    r = client.put("/api/accounts/update/A40404", json=user_payload(account_no="A40409")) # update non-existent user
    assert r.status_code == 404
    assert r.json()["detail"] == "Account not found"