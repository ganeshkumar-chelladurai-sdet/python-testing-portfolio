"""
Shared fixtures for the UI test suite.

Assumes mock_target/app.py is already running on http://localhost:5000 before pytest starts. See README.md for how to start it in a seperate terminal.
"""
import pytest

from tests.ui.pages.login_page import LoginPage

@pytest.fixture
def login_page(page, app_base_url):
    """A LoginPage already navigated to the login screen, ready to use."""
    return LoginPage(page, base_url=app_base_url).open()