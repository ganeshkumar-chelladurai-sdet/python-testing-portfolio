import pytest
import requests

@pytest.mark.api
def test_missing_token_returns_401(app_base_url):
    response = requests.get(f"{app_base_url}/api/customers")
    assert response.status_code == 401
    assert response.json()["error"] == "missing token"

@pytest.mark.api
def test_invalid_token_returns_401(app_base_url):
    response = requests.get(f"{app_base_url}/api/customers", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
    assert response.json()["error"] == "invalid token"

@pytest.mark.api
def test_expired_token_returns_401(app_base_url):
    login_response = requests.post(f"{app_base_url}/api/login", json={"username": "testuser", "password": "Password123"})
    token = login_response.json()["token"]

    expire_response = requests.post(f"{app_base_url}/api/test/expire-token", json={"token": token})
    assert expire_response.status_code == 200

    response = requests.get(f"{app_base_url}/api/customers", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"] == "token expired"