import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app, get_db
from app.models import Base
from app.security import get_current_account_claims

TEST_DB_URL = "sqlite+pysqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False,)
Base.metadata.create_all(bind=engine)

@pytest.fixture
def client(monkeypatch):
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_account_claims] = lambda: {"account_no": "A12345"}

    import app.main as main

    monkeypatch.setattr(main, "assign_number_range", lambda db: (1000, 1999))

    async def fake_publish_created(event: dict):
        return None

    async def fake_publish_deleted(event: dict):
        return None

    monkeypatch.setattr(main, "publish_accounts_created", fake_publish_created)
    monkeypatch.setattr(main, "publish_accounts_deleted", fake_publish_deleted)

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def user_payload(
    account_no="A12345",
    name="Anthony",
    email="user@example.com",
    password="Password1",
):
    
    return {
        "account_no": account_no,
        "name": name,
        "email": email,
        "password": password,
    }


# Tests
def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_user_201(client):
    r = client.post("/api/accounts", json=user_payload())
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["account_no"] == "A12345"
    assert data["email"] == "user@example.com"
    assert data["range_start"] == 1000
    assert data["range_end"] == 1999
    assert data["current_con_num"] == 1000


def test_create_account_conflict_400(client):
    payload = user_payload(account_no="A55555", email="conflict@example.com")
    r1 = client.post("/api/accounts", json=payload)
    assert r1.status_code == 201, r1.text

    r2 = client.post("/api/accounts", json=payload)
    assert r2.status_code == 400
    assert r2.json()["detail"] == "Account already exists"



@pytest.mark.parametrize("bad_acc", ["A1234", "A123456", "B12345", "12345", "A12B45"])
def test_bad_account_no_422(client, bad_acc):
    r = client.post("/api/accounts", json=user_payload(account_no=bad_acc, email="new@example.com"))
    assert r.status_code == 422


@pytest.mark.parametrize("bad_pwd", ["password", "PASSWORD1", "Passw1", "Password!", "Password123456789012345"])
def test_bad_password_422(client, bad_pwd):
    r = client.post("/api/accounts", json=user_payload(account_no="A54321", email="new2@example.com", password=bad_pwd))
    assert r.status_code == 422


def test_get_account_by_number_200(client):
    client.post("/api/accounts", json=user_payload())
    r = client.get("/api/accounts/A12345")
    assert r.status_code == 200
    data = r.json()
    assert data["account_no"] == "A12345"
    assert data["name"] == "Anthony"
    assert data["email"] == "user@example.com"


def test_get_account_not_found_404(client):
    r = client.get("/api/accounts/A99999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Account not found"


def test_update_account_200(client):
    client.post("/api/accounts", json=user_payload(account_no="A11111", email="update@bing.com", name="Anto"))

    app.dependency_overrides[get_current_account_claims] = lambda: {"account_no": "A11111"}

    payload = {"name": "Conor", "email": "update@bing.com"}
    r = client.put("/api/accounts/update/A11111", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Conor"

    r2 = client.get("/api/accounts/A11111")
    assert r2.status_code == 200
    assert r2.json()["name"] == "Conor"


def test_update_account_forbidden_403(client):
    client.post("/api/accounts", json=user_payload(account_no="A22222", email="x@x.com"))

    app.dependency_overrides[get_current_account_claims] = lambda: {"account_no": "A99999"}

    payload = {"name": "NewName", "email": "x@x.com"}
    r = client.put("/api/accounts/update/A22222", json=payload)
    assert r.status_code == 403
    assert r.json()["detail"] == "Token not valid for this account"


def test_update_account_404(client):
    app.dependency_overrides[get_current_account_claims] = lambda: {"account_no": "A40404"}
    payload = {"name": "Someone", "email": "someone@example.com"}
    r = client.put("/api/accounts/update/A40404", json=payload)
    assert r.status_code == 404
    assert r.json()["detail"] == "Account not found"


def test_delete_then_404(client):
    client.post("/api/accounts", json=user_payload(account_no="A66666", email="deleteme@yahoo.com"))

    app.dependency_overrides[get_current_account_claims] = lambda: {"account_no": "A66666"}

    r = client.delete("/api/accounts/delete/A66666")
    assert r.status_code == 204

    r2 = client.get("/api/accounts/A66666")
    assert r2.status_code == 404


def test_delete_forbidden_403(client):
    client.post("/api/accounts", json=user_payload(account_no="A77777", email="deleteme2@yahoo.com"))

    app.dependency_overrides[get_current_account_claims] = lambda: {"account_no": "A99999"}

    r = client.delete("/api/accounts/delete/A77777")
    assert r.status_code == 403
    assert r.json()["detail"] == "Token not valid for this account"


def test_delete_not_found_404(client):
    app.dependency_overrides[get_current_account_claims] = lambda: {"account_no": "A88888"}
    r = client.delete("/api/accounts/delete/A88888")
    assert r.status_code == 404
    assert r.json()["detail"] == "Account not found"


def test_current_con_num_and_increment(client):
    client.post("/api/accounts", json=user_payload(account_no="A33333", email="c@c.com"))

    r1 = client.get("/api/accounts/A33333/currentConNum")
    assert r1.status_code == 200
    assert r1.json()["account_no"] == "A33333"
    assert r1.json()["current_con_num"] == 1000

    r2 = client.patch("/api/accounts/A33333/incrementConNum")
    assert r2.status_code == 200
    assert r2.json()["current_con_num"] == 1001

    r3 = client.get("/api/accounts/A33333/currentConNum")
    assert r3.status_code == 200
    assert r3.json()["current_con_num"] == 1001