#tests/conftest.py

#Sets up a test client for FastAPI using pytest
from fastapi.testclient import TestClient
from app.main import app
import pytest

@pytest.fixture 
def client():
    return TestClient(app)  #Simulates HTTP requests to FastAPI app without live server