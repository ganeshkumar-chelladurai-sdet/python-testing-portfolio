import pytest
import pandas as pd

from mock_target.etl.pipeline import merge_sources, dedupe_customers, validate_threshold, load_into_db
from mock_target.app import get_db

@pytest.fixture
def raw_customer_data():
    """Two overlapping 'source extracts' built directly as DataFrames, not loaded from CSV -- lets us control exactly which messy patterns are present, instead of hoping the sample data happens to cover them."""
    source_a = pd.DataFrame([
        {"email": "jane.doe@example.com", "name": "Jane Doe", "credit_score": 720, "updated_at": "2026-01-05"},
        {"email": "mark.smith@example.com", "name": "Mark Smith", "credit_score": 150, "updated_at": "2026-01-10"}
    ])
    source_b = pd.DataFrame([
            {"email": "Jane.Doe@example.com", "name": "Jane Doe", "credit_score": 735, "updated_at": "2026-03-15"},
            {"email": "alan.turing@example.com", "name": "Alan Turing", "credit_score": 900, "updated_at": "2026-01-20"}
        ])
    return source_a, source_b

@pytest.mark.etl
def test_merge_and_dedup(raw_customer_data):
    source_a, source_b = raw_customer_data

    merged = merge_sources(source_a, source_b)
    assert len(merged) == 4

    deduped = dedupe_customers(merged)
    assert len(deduped) == 3

    jane_row = deduped[deduped["email"].str.lower() == "jane.doe@example.com"]
    assert jane_row.iloc[0]['credit_score'] == 735

@pytest.mark.etl
@pytest.mark.parametrize("credit_score, expected_valid", [
    (300, True),    # exactly the minimum - should be valid (inclusive)
    (850, True),    # exactly the maximum - should be valid (inclusive)
    (299, False),   # just below minimum
    (851, False),   # just above maximum
    (575, True),    # comfortably in range
])
def test_validate_threshold_boundaries(credit_score, expected_valid):
    row = pd.DataFrame([{"email": "test@example.com", "credit_score": credit_score}])
    valid, invalid = validate_threshold(row, "credit_score", 300, 850)
    if expected_valid:
        assert len(valid) == 1 and len(invalid) == 0
    else:
        assert len(valid) == 0 and len(invalid) == 1

@pytest.mark.etl
def test_load_into_db_inserts_and_updates():
    valid = pd.DataFrame([
        {"name": "Jane Doe", "email": "jane.doe@example.com", "credit_score": 750, "updated_at": "2026-04-01"},
        {"name": "New Person", "email": "new.person@example.com", "credit_score": 700, "updated_at": "2026-04-01"},
    ])
    invald = pd.DataFrame([
        {"name": "Bad Score Person", "email": "bad.score@example.com", "credit_score": 999, "updated_at": "2026-04-01"},
    ])

    result = load_into_db(valid, invald)
    assert result == {"inserted": 2, "updated": 1}

    conn = get_db()
    jane = conn.execute("SELECT * FROM customers WHERE email = ?", ("jane.doe@example.com",)).fetchone()
    assert jane["id"] == 1
    assert jane["credit_score"] == 750
    assert jane["flagged"] == 0

    new_person = conn.execute("SELECT * FROM customers WHERE email = ?", ("new.person@example.com",)).fetchone()
    assert new_person["flagged"] == 0

    bad = conn.execute("SELECT * FROM customers WHERE email = ?", ("bad.score@example.com",)).fetchone()
    assert bad["flagged"] == 1
    conn.close()