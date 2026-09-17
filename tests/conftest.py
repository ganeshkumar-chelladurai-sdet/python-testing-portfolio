import pytest

from mock_target.app import init_db

APP_URL = "http://localhost:5000"

@pytest.fixture
def app_base_url():
    return APP_URL

@pytest.fixture(autouse=True)
def reset_db():
    init_db(reset=True)