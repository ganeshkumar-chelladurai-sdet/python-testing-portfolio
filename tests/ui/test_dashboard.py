import pytest
from playwright.sync_api import expect

from tests.ui.pages.dashboard_page import DashboardPage

@pytest.mark.ui
def test_dashboard_lists_customers(login_page):
    login_page.login("testuser", "Password123")
    login_page.expect_redirected_to_dashboard()

    dashboard = DashboardPage(login_page.page)
    dashboard.expect_row_count(2)
    dashboard.expect_customer_visible(1, "Jane Doe", "jane.doe@example.com")
    dashboard.expect_customer_visible(2, "Mark Smith", "mark.smith@example.com")

@pytest.mark.ui
def test_dashboard_redirects_when_not_logged_in(page, app_base_url):
    page.goto(f"{app_base_url}/dashboard")
    expect(page).to_have_url(f"{app_base_url}/")