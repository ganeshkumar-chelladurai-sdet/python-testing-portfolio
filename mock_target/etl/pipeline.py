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


def run_pipeline(path_a, path_b, output_path, credit_score_range=(300, 850)):
    df_a = load_data(path_a)
    df_b = load_data(path_b)
    combined = merge_sources(df_a, df_b)
    deduped = dedupe_customers(combined)
    valid, invalid = validate_threshold(deduped, "credit_score", *credit_score_range)
    valid.to_csv(output_path, index=False)
    return valid, invalid


if __name__ == "__main__":
    valid, invalid = run_pipeline(
        "../data/customers_source_a.csv",
        "../data/customers_source_b.csv",
        "../data/cleaned_customers.csv",
    )
    print(f"Valid records: {len(valid)}")
    print(f"Flagged records: {len(invalid)}")
    print(invalid[["email", "credit_score"]].to_string(index=False))
