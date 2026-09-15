from playwright.sync_api import Page, expect

class LoginPage:
    def __init__(self, page: Page, base_url: str = "http://localhost:5000"):
        self.page = page
        self.base_url = base_url

        self.username_input = page.locator("#username")
        self.password_input = page.locator("#password")
        self.login_button = page.locator("#login-button")
        self.error_message = page.locator("#error-message")
        self.dashboard_message = page.locator("#dashboard-msg")

    def open(self) -> "LoginPage":
        self.page.goto(self.base_url)
        return self

    def login(self, username: str, password: str) -> "LoginPage":
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.login_button.click()
        return self

    def expect_error(self, text: str, timeout: int = 5000) -> None:
        expect(self.error_message).to_be_visible(timeout=timeout)
        expect(self.error_message).to_contain_text(text)

    def expect_redirected_to_dashboard(self, timeout: int = 5000) -> None:
        expect(self.page).to_have_url(f"{self.base_url}/dashboard", timeout=timeout)
        expect(self.dashboard_message).to_be_visible(timeout=timeout)
        expect(self.dashboard_message).to_contain_text("Login successful")