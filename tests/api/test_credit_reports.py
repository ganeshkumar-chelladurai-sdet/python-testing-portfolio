import pytest
import requests

@pytest.mark.api
def test_list_reports_empty_for_new_customer(app_base_url, auth_headers):
    response = requests.get(f"{app_base_url}/api/customers/1/credit-reports", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.api
def test_list_reports_for_nonexistent_customer_returns_404(app_base_url, auth_headers):
    response = requests.get(f"{app_base_url}/api/customers/9999/credit-reports", headers=auth_headers)
    assert response.status_code == 404

@pytest.mark.api
def test_create_report_missing_fields_returns_400(app_base_url, auth_headers):
    response = requests.post(f"{app_base_url}/api/customers/1/credit-reports", headers=auth_headers, json={"score": 700})
    assert response.status_code == 400
    assert "error" in response.json()

@pytest.mark.api
def test_create_report_for_nonexistent_customer_returns_404(app_base_url, auth_headers):
    response = requests.post(
        f"{app_base_url}/api/customers/9999/credit-reports",
        headers=auth_headers,
        json={"score": 700, "report_date": "2026-04-01"},
    )
    assert response.status_code == 404

@pytest.mark.api
def test_report_crud_lifecycle(app_base_url, auth_headers):
    create_response = requests.post(
        f"{app_base_url}/api/customers/1/credit-reports",
        headers=auth_headers,
        json={"score": 720, "report_date": "2026-04-01", "source": "ICB"},
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["customer_id"] == 1
    report_id = created["id"]

    get_response = requests.get(f"{app_base_url}/api/credit-reports/{report_id}", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["score"] == 720

    list_response = requests.get(f"{app_base_url}/api/customers/1/credit-reports", headers=auth_headers)
    assert len(list_response.json()) == 1

    delete_response = requests.delete(f"{app_base_url}/api/credit-reports/{report_id}", headers= auth_headers)
    assert delete_response.status_code == 204

    confirm_response = requests.get(f"{app_base_url}/api/credit-reports/{report_id}", headers=auth_headers)
    assert confirm_response.status_code == 404

@pytest.mark.api
def test_put_on_report_is_not_allowed(app_base_url, auth_headers):
    response = requests.put(f"{app_base_url}/api/credit-reports/1", headers=auth_headers, json={"score": 800})
    assert response.status_code == 405