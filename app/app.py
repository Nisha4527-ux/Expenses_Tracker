import math
import sys
from datetime import date, datetime
from pathlib import Path

from flask import Flask, jsonify, request

# Make the modules in src/ importable no matter where the app is launched from
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import analytics  # noqa: E402
from database import get_connection, init_db  # noqa: E402

app = Flask(__name__, static_folder="../frontend", static_url_path="")

init_db()  # make sure the table exists on startup


# ---------- helpers ----------

def error(message, status=400):
    return jsonify({"error": message}), status


def valid_month(value):
    try:
        datetime.strptime(value, "%Y-%m")
        return True
    except (TypeError, ValueError):
        return False


def valid_date(value):
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except (TypeError, ValueError):
        return False


def clean_expense(data):
    """Validate and normalise an expense payload -> (clean_dict, error_message)."""
    try:
        amount = float(data.get("amount"))
    except (TypeError, ValueError):
        return None, "amount must be a number"
    if not math.isfinite(amount) or amount <= 0:
        return None, "amount must be greater than 0"

    category = str(data.get("category") or "").strip()
    if not category:
        return None, "category is required"

    expense_date = data.get("date") or str(date.today())
    if not valid_date(expense_date):
        return None, "date must be in YYYY-MM-DD format"

    return {
        "amount": round(amount, 2),
        "category": category.title(),  # "food" and "Food" group together
        "description": str(data.get("description") or "").strip(),
        "date": expense_date,
    }, None


def get_json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


# ---------- pages ----------

@app.route("/")
def home():
    return app.send_static_file("index.html")


# ---------- expenses (CRUD) ----------

@app.route("/api/expenses", methods=["GET"])
def list_expenses():
    month = request.args.get("month")
    category = request.args.get("category")
    limit = request.args.get("limit", type=int)

    if month and not valid_month(month):
        return error("month must be in YYYY-MM format")

    query = "SELECT id, amount, category, description, date FROM expenses"
    conditions, params = [], []
    if month:
        conditions.append("strftime('%Y-%m', date) = ?")
        params.append(month)
    if category:
        conditions.append("LOWER(category) = LOWER(?)")
        params.append(category)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY date DESC, id DESC"
    if limit and limit > 0:
        query += " LIMIT ?"
        params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/expenses", methods=["POST"])
@app.route("/add-expense", methods=["POST"])  # old route, keeps the current frontend working
def add_expense():
    data = get_json_body()
    if data is None:
        return error("request body must be JSON")

    expense, problem = clean_expense(data)
    if problem:
        return error(problem)

    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO expenses (amount, category, description, date) VALUES (?, ?, ?, ?)",
            (expense["amount"], expense["category"], expense["description"], expense["date"]),
        )
        expense["id"] = cursor.lastrowid

    return jsonify({"message": "Expense added successfully!", "expense": expense}), 201


@app.route("/api/expenses/<int:expense_id>", methods=["PUT"])
def update_expense(expense_id):
    data = get_json_body()
    if data is None:
        return error("request body must be JSON")

    with get_connection() as conn:
        existing = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        if existing is None:
            return error("expense not found", 404)

        # fields that are not sent keep their current value
        merged = {**dict(existing), **data}
        expense, problem = clean_expense(merged)
        if problem:
            return error(problem)

        conn.execute(
            "UPDATE expenses SET amount = ?, category = ?, description = ?, date = ? WHERE id = ?",
            (expense["amount"], expense["category"], expense["description"], expense["date"], expense_id),
        )

    expense["id"] = expense_id
    return jsonify({"message": "Expense updated successfully!", "expense": expense})


@app.route("/api/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    if cursor.rowcount == 0:
        return error("expense not found", 404)
    return jsonify({"message": "Expense deleted successfully!"})


@app.route("/api/categories", methods=["GET"])
def list_categories():
    with get_connection() as conn:
        rows = conn.execute("SELECT DISTINCT category FROM expenses ORDER BY category").fetchall()
    return jsonify([r["category"] for r in rows])


# ---------- analytics ----------

@app.route("/api/summary", methods=["GET"])
def summary():
    """Everything the dashboard needs. Optional: ?month=YYYY-MM&budget=5000"""
    month = request.args.get("month")
    budget = request.args.get("budget", default=analytics.DEFAULT_MONTHLY_BUDGET, type=float)

    if month and not valid_month(month):
        return error("month must be in YYYY-MM format")
    if budget is None or budget <= 0:
        return error("budget must be greater than 0")

    return jsonify(analytics.get_dashboard_summary(month, budget))


@app.route("/api/budget", methods=["GET"])
def budget_status():
    month = request.args.get("month")
    budget = request.args.get("budget", default=analytics.DEFAULT_MONTHLY_BUDGET, type=float)

    if month and not valid_month(month):
        return error("month must be in YYYY-MM format")
    if budget is None or budget <= 0:
        return error("budget must be greater than 0")

    return jsonify(analytics.get_budget_status(budget, month))


if __name__ == "__main__":
    app.run(debug=True)