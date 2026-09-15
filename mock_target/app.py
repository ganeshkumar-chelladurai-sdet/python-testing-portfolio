"""
Self-contained system under test for the portfolio.

Serves two things:
  1. A login page (UI test target for pytest-playwright)
  2. A /api/customers CRUD API (API test target for pytest + requests)

Run with: python app.py  (serves on http://localhost:5000)
"""
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


# --- API target: customers CRUD ---
CUSTOMERS = {
    1: {"id": 1, "name": "Jane Doe", "email": "jane.doe@example.com"},
    2: {"id": 2, "name": "Mark Smith", "email": "mark.smith@example.com"},
}
_next_id = 3


@app.route("/api/customers", methods=["GET"])
def list_customers():
    return jsonify(list(CUSTOMERS.values()))


@app.route("/api/customers/<int:customer_id>", methods=["GET"])
def get_customer(customer_id):
    customer = CUSTOMERS.get(customer_id)
    if not customer:
        return jsonify({"error": "not found"}), 404
    return jsonify(customer)


@app.route("/api/customers", methods=["POST"])
def create_customer():
    global _next_id
    body = request.get_json(force=True, silent=True) or {}
    if "name" not in body or "email" not in body:
        return jsonify({"error": "name and email are required"}), 400
    customer = {"id": _next_id, "name": body["name"], "email": body["email"]}
    CUSTOMERS[_next_id] = customer
    _next_id += 1
    return jsonify(customer), 201


@app.route("/api/customers/<int:customer_id>", methods=["PUT"])
def update_customer(customer_id):
    if customer_id not in CUSTOMERS:
        return jsonify({"error": "not found"}), 404
    body = request.get_json(force=True, silent=True) or {}
    CUSTOMERS[customer_id].update({k: v for k, v in body.items() if k in ("name", "email")})
    return jsonify(CUSTOMERS[customer_id])


@app.route("/api/customers/<int:customer_id>", methods=["DELETE"])
def delete_customer(customer_id):
    if customer_id not in CUSTOMERS:
        return jsonify({"error": "not found"}), 404
    del CUSTOMERS[customer_id]
    return "", 204


if __name__ == "__main__":
    app.run(debug=True, port=5000)
