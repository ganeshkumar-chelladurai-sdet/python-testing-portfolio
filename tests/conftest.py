import pytest

APP_URL = "http://localhost:5000"

@pytest.fixture
def app_base_url():
    return APP_URL