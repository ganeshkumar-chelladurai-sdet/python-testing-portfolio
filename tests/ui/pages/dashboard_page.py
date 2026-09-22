from playwright.sync_api import Page, expect

class DashboardPage:
    def __init__(self, page: Page):
        self.page = page
        self.customer_list = page.locator("#customer-list")
        self.empty_state = page.locator("#empty-state")

    def customer_row(self, customer_id: int):
        return self.page.locator(f"#customer-row-{customer_id}")

    def expect_customer_visible(self, customer_id: int, name: str, email: str) -> None:
        row = self.customer_row(customer_id)
        expect(row).to_be_visible()
        expect(row.locator(".customer-name")).to_have_text(name)
        expect(row.locator(".customer-email")).to_have_text(email)

    def expect_row_count(self, count: int) -> None:
        expect(self.page.locator(".customer-row")).to_have_count(count)