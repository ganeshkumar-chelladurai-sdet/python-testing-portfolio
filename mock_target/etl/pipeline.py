"""
ETL test target.

Mirrors the dedupe + threshold-validation logic from real ETL work:
  - two upstream extracts with overlapping/duplicate customer records
    (case differences, re-submitted rows, conflicting values)
  - dedupe by email, keeping the most recently updated record
  - flag records whose credit_score falls outside a valid range

Each function is deliberately small and pure (pandas in, pandas out)
so it can be unit-tested directly with pytest + pandas, without needing
the CSV files at all.
"""
import pandas as pd

from mock_target.app import get_db, DB_PATH


def load_data(path):
    return pd.read_csv(path)


def merge_sources(df_a, df_b):
    """Combine two source extracts into a single frame before dedupe."""
    return pd.concat([df_a, df_b], ignore_index=True)


def dedupe_customers(df):
    """Dedupe by email (case-insensitive), keeping the most recently updated record."""
    df = df.copy()
    df["email_normalized"] = df["email"].str.strip().str.lower()
    df["updated_at"] = pd.to_datetime(df["updated_at"])
    df = df.sort_values("updated_at", ascending=False)
    df = df.drop_duplicates(subset="email_normalized", keep="first")
    return df.drop(columns=["email_normalized"]).reset_index(drop=True)


def validate_threshold(df, column, min_value, max_value):
    """Split a frame into (valid, invalid) based on whether column is within [min_value, max_value]."""
    mask = df[column].between(min_value, max_value)
    return df[mask].reset_index(drop=True), df[~mask].reset_index(drop=True)


def validate_referential_integrity(reports_df, customer_ids):
    """
    Split reports into (valid, orphaned) based on whether each row's
    customer_id is present in customer_ids. A report is orphaned if it
    references a customer_id that doesn't actually exist.
    """
    mask = reports_df["customer_id"].isin(customer_ids)
    return reports_df[mask].reset_index(drop=True), reports_df[~mask].reset_index(drop=True)


def load_into_db(valid_df, invalid_df, db_path=None):
    """
    Upsert every row from valid_df and invalid_df into the customers table,
    matching existing rows by email (case-insensitive). Rows from valid_df
    get flagged=0, rows from invalid_df get flagged=1. A new email gets
    inserted; an existing email gets its name/credit_score/updated_at/flagged
    updated, keeping its existing database id. Returns
    {"inserted": <int>, "updated": <int>}.
    """
    # db_path is accepted for interface compatibility but ignored: this always
    # writes through the app's own get_db()/DB_PATH rather than a separate connection.
    conn = get_db()
    try:
        inserted = 0
        updated = 0
        for df, flagged in ((valid_df, 0), (invalid_df, 1)):
            for _, row in df.iterrows():
                name = row["name"]
                email = row["email"]

                credit_score = row["credit_score"]
                credit_score = None if pd.isna(credit_score) else int(credit_score)

                updated_at = row["updated_at"]
                if pd.isna(updated_at):
                    updated_at = None
                elif isinstance(updated_at, pd.Timestamp):
                    updated_at = updated_at.isoformat()
                else:
                    updated_at = str(updated_at)

                existing = conn.execute(
                    "SELECT id FROM customers WHERE LOWER(email) = LOWER(?)", (email,)
                ).fetchone()

                if existing:
                    conn.execute(
                        "UPDATE customers SET name = ?, credit_score = ?, updated_at = ?, "
                        "flagged = ? WHERE id = ?",
                        (name, credit_score, updated_at, flagged, existing["id"]),
                    )
                    updated += 1
                else:
                    conn.execute(
                        "INSERT INTO customers (name, email, credit_score, updated_at, flagged) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (name, email, credit_score, updated_at, flagged),
                    )
                    inserted += 1

        conn.commit()
        return {"inserted": inserted, "updated": updated}
    finally:
        conn.close()


def run_pipeline(path_a, path_b, output_path, credit_score_range=(300, 850)):
    df_a = load_data(path_a)
    df_b = load_data(path_b)
    combined = merge_sources(df_a, df_b)
    deduped = dedupe_customers(combined)
    valid, invalid = validate_threshold(deduped, "credit_score", *credit_score_range)
    valid.to_csv(output_path, index=False)
    return valid, invalid


if __name__ == "__main__":
    from pathlib import Path

    DATA_DIR = Path(__file__).resolve().parent.parent / "data"
    valid, invalid = run_pipeline(
        DATA_DIR / "customers_source_a.csv",
        DATA_DIR / "customers_source_b.csv",
        DATA_DIR / "cleaned_customers.csv",
    )
    print(f"Valid records: {len(valid)}")
    print(f"Flagged records: {len(invalid)}")
    print(invalid[["email", "credit_score"]].to_string(index=False))
    result = load_into_db(valid, invalid)
    print(f"Loaded into database at {DB_PATH}: {result}")
