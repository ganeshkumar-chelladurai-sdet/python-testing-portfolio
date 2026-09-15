import pytest

@pytest.mark.ui
def test_valid_login_redirects_to_dashboard(login_page):
    login_page.login("testuser", "Password123")
    login_page.expect_redirected_to_dashboard()

@pytest.mark.ui
def test_wrong_password_shows_error(login_page):
    login_page.login("testuser", "wrongpassword")
    login_page.expect_error("Invalid username or password")

@pytest.mark.ui
def test_unknown_user_shows_error(login_page):
    login_page.login("nosuchuser", "whatever")
    login_page.expect_error("Invalid username or password")

@pytest.mark.ui
def test_empty_fields_shows_error(login_page):
    login_page.login("", "")
    login_page.expect_error("Invalid username or password")

@pytest.mark.ui
def test_error_message_appears_without_fixed_sleep(login_page):
    """Dynamic-wait test: relies on Playwright's auto-retrying expect() to catch the error message as soon as it renders, insead of a hardcoded time.sleep() that either wastes time or risks flakiness."""
    login_page.login("testuser", "wrongpassword")
    login_page.expect_error("Invalid username or password", timeout=3000)

@pytest.mark.ui
def test_dashboard_redirect_waits_for_navigation(login_page):
    """Dynamic-wait test: only asserts on the dashboard once Playwright confirms the URL and content actually changed, rather than assuming a fixed delay was long enough for the server redirect to land."""
    login_page.login("testuser", "Password123")
    login_page.expect_redirected_to_dashboard(timeout=3000)