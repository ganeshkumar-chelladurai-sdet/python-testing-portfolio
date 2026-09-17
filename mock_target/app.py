"""
Self-contained system under test for the portfolio.

Serves two things:
  1. A login page (UI test target for pytest-playwright)
  2. A /api/customers CRUD API (API test target for pytest + requests)

Run with: python app.py  (serves on http://localhost:5000)
"""
import os
import sqlite3

from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

# --- UI target: login page ---
USERS = {"testuser": "Password123"}


@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if USERS.get(username) == password:
            return redirect(url_for("dashboard"))
        error = "Invalid username or password"
    return render_template("login.html", error=error)


@app.route("/dashboard")
def dashboard():
    return "<h1>Welcome</h1><p id='dashboard-msg'>Login successful.</p>"


# --- API target: customers CRUD, backed by SQLite ---
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "app.db")

SCHEMA = """
CREATE TABLE customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    credit_score INTEGER,
    updated_at TEXT,
    flagged INTEGER NOT NULL DEFAULT 0
)
"""

SEED_CUSTOMERS = [
    ("Jane Doe", "jane.doe@example.com"),
    ("Mark Smith", "mark.smith@example.com"),
]

CREDIT_REPORTS_SCHEMA = """
CREATE TABLE credit_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    score INTEGER NOT NULL,
    report_date TEXT NOT NULL,
    source TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
)
"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(reset=False):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    try:
        if reset:
            conn.execute("DROP TABLE IF EXISTS credit_reports")
            conn.execute("DROP TABLE IF EXISTS customers")
            conn.commit()

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='customers'"
        )
        table_exists = cursor.fetchone() is not None

        if not table_exists:
            conn.execute(SCHEMA)
            conn.executemany(
                "INSERT INTO customers (name, email) VALUES (?, ?)", SEED_CUSTOMERS
            )
            conn.commit()

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='credit_reports'"
        )
        reports_table_exists = cursor.fetchone() is not None

        if not reports_table_exists:
            conn.execute(CREDIT_REPORTS_SCHEMA)
            conn.commit()
    finally:
        conn.close()


def row_to_customer(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "credit_score": row["credit_score"],
        "updated_at": row["updated_at"],
        "flagged": row["flagged"],
    }


@app.route("/api/customers", methods=["GET"])
def list_customers():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM customers").fetchall()
        return jsonify([row_to_customer(row) for row in rows])
    finally:
        conn.close()


@app.route("/api/customers/<int:customer_id>", methods=["GET"])
def get_customer(customer_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
        if not row:
            return jsonify({"error": "not found"}), 404
        return jsonify(row_to_customer(row))
    finally:
        conn.close()


@app.route("/api/customers", methods=["POST"])
def create_customer():
    body = request.get_json(force=True, silent=True) or {}
    if "name" not in body or "email" not in body:
        return jsonify({"error": "name and email are required"}), 400

    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO customers (name, email) VALUES (?, ?)",
            (body["name"], body["email"]),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM customers WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return jsonify(row_to_customer(row)), 201
    finally:
        conn.close()


@app.route("/api/customers/<int:customer_id>", methods=["PUT"])
def update_customer(customer_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
        if not row:
            return jsonify({"error": "not found"}), 404

        body = request.get_json(force=True, silent=True) or {}
        updates = {k: v for k, v in body.items() if k in ("name", "email")}
        if updates:
            set_clause = ", ".join(f"{field} = ?" for field in updates)
            conn.execute(
                f"UPDATE customers SET {set_clause} WHERE id = ?",
                (*updates.values(), customer_id),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM customers WHERE id = ?", (customer_id,)
            ).fetchone()

        return jsonify(row_to_customer(row))
    finally:
        conn.close()


@app.route("/api/customers/<int:customer_id>", methods=["DELETE"])
def delete_customer(customer_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
        if not row:
            return jsonify({"error": "not found"}), 404
        conn.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
        conn.commit()
        return "", 204
    finally:
        conn.close()


def row_to_report(row):
    return {
        "id": row["id"],
        "customer_id": row["customer_id"],
        "score": row["score"],
        "report_date": row["report_date"],
        "source": row["source"],
    }


@app.route("/api/customers/<int:customer_id>/credit-reports", methods=["GET"])
def list_credit_reports(customer_id):
    conn = get_db()
    try:
        customer = conn.execute(
            "SELECT id FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
        if not customer:
            return jsonify({"error": "not found"}), 404

        rows = conn.execute(
            "SELECT * FROM credit_reports WHERE customer_id = ?", (customer_id,)
        ).fetchall()
        return jsonify([row_to_report(row) for row in rows])
    finally:
        conn.close()


@app.route("/api/customers/<int:customer_id>/credit-reports", methods=["POST"])
def create_credit_report(customer_id):
    conn = get_db()
    try:
        customer = conn.execute(
            "SELECT id FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
        if not customer:
            return jsonify({"error": "not found"}), 404

        body = request.get_json(force=True, silent=True) or {}
        if "score" not in body or "report_date" not in body:
            return jsonify({"error": "score and report_date are required"}), 400

        cursor = conn.execute(
            "INSERT INTO credit_reports (customer_id, score, report_date, source) "
            "VALUES (?, ?, ?, ?)",
            (customer_id, body["score"], body["report_date"], body.get("source")),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM credit_reports WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return jsonify(row_to_report(row)), 201
    finally:
        conn.close()


@app.route("/api/credit-reports/<int:report_id>", methods=["GET"])
def get_credit_report(report_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM credit_reports WHERE id = ?", (report_id,)
        ).fetchone()
        if not row:
            return jsonify({"error": "not found"}), 404
        return jsonify(row_to_report(row))
    finally:
        conn.close()


@app.route("/api/credit-reports/<int:report_id>", methods=["DELETE"])
def delete_credit_report(report_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM credit_reports WHERE id = ?", (report_id,)
        ).fetchone()
        if not row:
            return jsonify({"error": "not found"}), 404
        conn.execute("DELETE FROM credit_reports WHERE id = ?", (report_id,))
        conn.commit()
        return "", 204
    finally:
        conn.close()


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
