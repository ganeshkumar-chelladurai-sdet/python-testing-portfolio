import pytest
import requests
import jsonschema

@pytest.mark.api
def test_get_customers_list(app_base_url, auth_headers):
    response = requests.get(f"{app_base_url}/api/customers", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) >= 1

@pytest.mark.api
def test_customer_crud_lifecycle(app_base_url, auth_headers):
    # Create
    new_customer = {"name": "Alice Wonderland", "email": "alice@example.com"}
    create_response = requests.post(f"{app_base_url}/api/customers", headers=auth_headers, json=new_customer)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Alice Wonderland"
    customer_id = created["id"]

    # Read
    get_response = requests.get(f"{app_base_url}/api/customers/{customer_id}", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Alice Wonderland"

    # Update
    updated_response = requests.put(f"{app_base_url}/api/customers/{customer_id}", headers=auth_headers, json={"name": "Alice Liddell"},)
    assert updated_response.status_code == 200
    assert updated_response.json()["name"] == "Alice Liddell"

    # Delete
    delete_response = requests.delete(f"{app_base_url}/api/customers/{customer_id}", headers=auth_headers)
    assert delete_response.status_code == 204

    # Confirm it's actually gone
    confirm_response = requests.get(f"{app_base_url}/api/customers/{customer_id}", headers=auth_headers)
    assert confirm_response.status_code == 404

CUSTOMER_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "email": {"type": "string"},
    },
    "required": ["id", "name", "email"],
}

@pytest.mark.api
def test_customer_response_matches_schema(app_base_url, auth_headers):
    response = requests.get(f"{app_base_url}/api/customers", headers=auth_headers)
    assert response.status_code == 200
    customers = response.json()
    for customer in customers:
        jsonschema.validate(instance=customer, schema= CUSTOMER_SCHEMA)

@pytest.mark.api
def test_create_customer_missing_fields_returns_400(app_base_url, auth_headers):
    response = requests.post(f"{app_base_url}/api/customers", headers=auth_headers, json={"name": "No Email Person"})
    assert response.status_code == 400
    assert "error" in response.json()

@pytest.mark.api
def test_get_nonexistent_customer_returns_404(app_base_url, auth_headers):
    response = requests.get(f"{app_base_url}/api/customers/9999", headers=auth_headers)
    assert response.status_code == 404

@pytest.mark.api
def test_update_nonexistent_customer_returns_404(app_base_url, auth_headers):
    response = requests.put(f"{app_base_url}/api/customers/9999", headers=auth_headers, json={"name": "Ghost"})
    assert response.status_code == 404

@pytest.mark.api
def test_delete_nonexistent_customer_returns_404(app_base_url, auth_headers):
    response = requests.delete(f"{app_base_url}/api/customers/9999", headers=auth_headers)
    assert response.status_code == 404

@pytest.mark.api
def test_update_ignores_unexpected_protected_fields(app_base_url, auth_headers):
    response = requests.put(
        f"{app_base_url}/api/customers/1", headers=auth_headers,
        json={"id": 999, "credit_score": 700, "flagged": 1, "name": "Jane Updated"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Jane Updated"
    assert body["id"] == 1
    assert body["credit_score"] != 700
    assert body["flagged"] != 1