import pytest
from tests.ui.pages.login_page import LoginPage
BASE_URL = "http://localhost:5000"

@pytest.fixture
def login_page(page):
    """A LoginPage already navigated to the login screen, ready to use."""
    return LoginPage(page, base_url=BASE_URL).open()