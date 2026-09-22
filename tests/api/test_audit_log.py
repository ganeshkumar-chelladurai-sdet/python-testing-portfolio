import pytest
import requests

@pytest.mark.api
def test_audit_log_records_customer_creation(app_base_url, auth_headers):
    create_response = requests.post(
        f"{app_base_url}/api/customers",
        json={"name": "Audit Customer", "email": "audit@example.com"},
        headers=auth_headers,
    )
    customer_id = create_response.json()["id"]

    audit_response = requests.get(f"{app_base_url}/api/audit-log/customer/{customer_id}", headers=auth_headers)
    assert audit_response.status_code == 200
    entries = audit_response.json()
    assert len(entries) == 1
    assert entries[0]["action"] == "create"
    assert entries[0]["old_values"] is None

@pytest.mark.api
def test_audit_log_records_customer_update(app_base_url, auth_headers):
    create_response = requests.post(
        f"{app_base_url}/api/customers",
        json={"name": "Audit Customer", "email": "audit@example.com"},
        headers=auth_headers,
    )
    customer_id = create_response.json()["id"]

    requests.put(f"{app_base_url}/api/customers/{customer_id}", json={"name": "Updated Name"}, headers=auth_headers)

    audit_response = requests.get(f"{app_base_url}/api/audit-log/customer/{customer_id}", headers=auth_headers)
    entires = audit_response.json()
    assert len(entires) == 2
    assert entires[1]["action"] == "update"

@pytest.mark.api
def test_audit_log_records_customer_deletion(app_base_url, auth_headers):
    create_response = requests.post(
        f"{app_base_url}/api/customers",
        json={"name": "Audit Customer", "email": "audit@example.com"},
        headers=auth_headers,
    )
    customer_id = create_response.json()["id"]

    requests.delete(f"{app_base_url}/api/customers/{customer_id}", headers=auth_headers)

    audit_response = requests.get(f"{app_base_url}/api/audit-log/customer/{customer_id}", headers=auth_headers)
    entries = audit_response.json()
    assert len(entries) == 2
    assert entries[1]["action"] == "delete"

@pytest.mark.api
def test_audit_log_update_captures_old_and_new_values(app_base_url, auth_headers):
    create_response = requests.post(
        f"{app_base_url}/api/customers",
        json={"name": "Original Name", "email": "orginal@example.com"},
        headers=auth_headers,
    )
    customer_id = create_response.json()["id"]

    requests.put(f"{app_base_url}/api/customers/{customer_id}", json={"name": "Changed Name"}, headers=auth_headers)

    audit_response = requests.get(f"{app_base_url}/api/audit-log/customer/{customer_id}", headers=auth_headers)
    entires = audit_response.json()
    update_entry = entires[1]

    assert update_entry["old_values"] == {"name": "Original Name"}
    assert update_entry["new_values"] == {"name": "Changed Name"}
    assert "email" not in update_entry["old_values"]
    assert "email" not in update_entry["new_values"]