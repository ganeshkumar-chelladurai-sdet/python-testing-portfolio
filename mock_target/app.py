"""
Self-contained system under test for the portfolio.

Serves two things:
  1. A login page (UI test target for pytest-playwright)
  2. A /api/customers CRUD API (API test target for pytest + requests)

Run with: python app.py  (serves on http://localhost:5000)
"""
import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, jsonify, session

app = Flask(__name__)
# Hardcoded for a local test target only; a real deployment would pull this from an
# environment variable or a secrets manager, never commit it to source.
app.secret_key = "dev-secret-key-not-for-production"

# --- UI target: login page ---
USERS = {"testuser": "Password123"}


@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if USERS.get(username) == password:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        error = "Invalid username or password"
    return render_template("login.html", error=error)


@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM customers").fetchall()
        customers = [row_to_customer(row) for row in rows]
    finally:
        conn.close()
    return render_template("dashboard.html", customers=customers)


# --- API auth: bearer tokens ---
TOKENS = {}


@app.route("/api/login", methods=["POST"])
def api_login():
    body = request.get_json(force=True, silent=True) or {}
    username = body.get("username")
    password = body.get("password")
    if (
        isinstance(username, str)
        and isinstance(password, str)
        and USERS.get(username) == password
    ):
        token = secrets.token_hex(16)
        TOKENS[token] = {
            "username": username,
            "expires_at": datetime.utcnow() + timedelta(hours=1),
        }
        return jsonify({"token": token}), 200
    return jsonify({"error": "invalid credentials"}), 401


def expire_token(token):
    TOKENS[token]["expires_at"] = datetime.utcnow() - timedelta(seconds=1)


def require_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "missing token"}), 401
        token = header[len("Bearer "):].strip()
        entry = TOKENS.get(token)
        if entry is None:
            return jsonify({"error": "invalid token"}), 401
        if entry["expires_at"] < datetime.utcnow():
            TOKENS.pop(token, None)
            return jsonify({"error": "token expired"}), 401
        return view(*args, **kwargs)

    return wrapper


if os.environ.get("ENABLE_TEST_ENDPOINTS") == "1":

    @app.route("/api/test/expire-token", methods=["POST"])
    def test_expire_token():
        body = request.get_json(force=True, silent=True) or {}
        token = body.get("token")
        if token not in TOKENS:
            return jsonify({"error": "unknown token"}), 404
        expire_token(token)
        return jsonify({"expired": True}), 200


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
@require_auth
def list_customers():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM customers").fetchall()
        return jsonify([row_to_customer(row) for row in rows])
    finally:
        conn.close()


@app.route("/api/customers/<int:customer_id>", methods=["GET"])
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
