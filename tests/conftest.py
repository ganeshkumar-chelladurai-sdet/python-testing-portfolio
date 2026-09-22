import requests
import pytest

from mock_target.app import init_db

APP_URL = "http://localhost:5000"

@pytest.fixture
def app_base_url():
    return APP_URL

@pytest.fixture(autouse=True)
def reset_db():
    init_db(reset=True)

@pytest.fixture(scope="session")
def auth_headers():
    response = requests.post(f"{APP_URL}/api/login", json={"username": "testuser", "password": "Password123"})
    assert response.status_code == 200
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}