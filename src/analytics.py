"""
Expense analytics.

Every function returns plain Python data (numbers, dicts, lists) so it can be
used by the Flask/FastAPI backend (jsonify / return directly) or printed by the
CLI report at the bottom of this file.

Dates must be stored as YYYY-MM-DD. `month` arguments use the format YYYY-MM.
"""
from datetime import date

from database import get_connection

DEFAULT_MONTHLY_BUDGET = 5000


# ---------- helpers ----------

def current_month():
    return date.today().strftime("%Y-%m")


def _month_filter(month):
    """Return (WHERE clause, params) for an optional YYYY-MM filter."""
    if month:
        return "WHERE strftime('%Y-%m', date) = ?", (month,)
    return "", ()


def _rows_to_dicts(rows):
    return [dict(row) for row in rows]


# ---------- core analytics ----------

def get_total_spent(month=None):
    where, params = _month_filter(month)
    with get_connection() as conn:
        row = conn.execute(f"SELECT COALESCE(SUM(amount), 0) AS total FROM expenses {where}", params).fetchone()
    return round(row["total"], 2)


def get_average_expense(month=None):
    where, params = _month_filter(month)
    with get_connection() as conn:
        row = conn.execute(f"SELECT COALESCE(AVG(amount), 0) AS avg FROM expenses {where}", params).fetchone()
    return round(row["avg"], 2)


def get_expense_count(month=None):
    where, params = _month_filter(month)
    with get_connection() as conn:
        row = conn.execute(f"SELECT COUNT(*) AS n FROM expenses {where}", params).fetchone()
    return row["n"]


def get_category_breakdown(month=None):
    """[{category, total, percentage}] sorted from highest to lowest spend."""
    where, params = _month_filter(month)
    with get_connection() as conn:
        rows = conn.execute(f"""
            SELECT category, SUM(amount) AS total
            FROM expenses {where}
            GROUP BY category
            ORDER BY total DESC
        """, params).fetchall()

    grand_total = sum(r["total"] for r in rows)
    return [
        {
            "category": r["category"],
            "total": round(r["total"], 2),
            "percentage": round(r["total"] / grand_total * 100, 2) if grand_total else 0,
        }
        for r in rows
    ]


def get_top_category(month=None):
    breakdown = get_category_breakdown(month)
    return breakdown[0] if breakdown else None


def get_daily_spending(month=None):
    """[{date, total}] in date order."""
    where, params = _month_filter(month)
    with get_connection() as conn:
        rows = conn.execute(f"""
            SELECT date, SUM(amount) AS total
            FROM expenses {where}
            GROUP BY date
            ORDER BY date
        """, params).fetchall()
    return [{"date": r["date"], "total": round(r["total"], 2)} for r in rows]


def get_highest_spending_day(month=None):
    days = get_daily_spending(month)
    return max(days, key=lambda d: d["total"]) if days else None


def get_monthly_summary():
    """[{month, total, count}] for every month that has data."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT strftime('%Y-%m', date) AS month,
                   SUM(amount) AS total,
                   COUNT(*) AS count
            FROM expenses
            GROUP BY month
            ORDER BY month
        """).fetchall()
    return [{"month": r["month"], "total": round(r["total"], 2), "count": r["count"]} for r in rows]


def get_top_expenses(limit=5, month=None):
    where, params = _month_filter(month)
    with get_connection() as conn:
        rows = conn.execute(f"""
            SELECT id, amount, category, description, date
            FROM expenses {where}
            ORDER BY amount DESC
            LIMIT ?
        """, params + (limit,)).fetchall()
    return _rows_to_dicts(rows)


# ---------- budget ----------

def get_budget_status(budget=DEFAULT_MONTHLY_BUDGET, month=None):
    """Budget check for one month (defaults to the current month)."""
    month = month or current_month()
    spent = get_total_spent(month)
    percent_used = round(spent / budget * 100, 2) if budget else 0

    if percent_used < 50:
        level = "Low"
    elif percent_used <= 80:
        level = "Moderate"
    else:
        level = "High"

    if percent_used >= 100:
        status, message = "exceeded", "You have exceeded your budget!"
    elif percent_used >= 90:
        status, message = "critical", "You are close to your budget limit!"
    elif percent_used >= 80:
        status, message = "warning", "You have used more than 80% of your budget."
    else:
        status, message = "ok", "Your spending is under control."

    return {
        "month": month,
        "budget": budget,
        "spent": spent,
        "remaining": round(budget - spent, 2),
        "percent_used": percent_used,
        "level": level,
        "status": status,
        "message": message,
    }


# ---------- one call for the dashboard ----------

def get_dashboard_summary(month=None, budget=DEFAULT_MONTHLY_BUDGET):
    """Everything the dashboard needs in a single JSON-friendly dict."""
    return {
        "month": month or "all",
        "total_spent": get_total_spent(month),
        "average_expense": get_average_expense(month),
        "expense_count": get_expense_count(month),
        "top_category": get_top_category(month),
        "highest_spending_day": get_highest_spending_day(month),
        "category_breakdown": get_category_breakdown(month),
        "daily_spending": get_daily_spending(month),
        "monthly_summary": get_monthly_summary(),
        "top_expenses": get_top_expenses(5, month),
        "budget": get_budget_status(budget, month),
    }


# ---------- CLI report (python src/analytics.py) ----------

def print_report(month=None, budget=DEFAULT_MONTHLY_BUDGET):
    s = get_dashboard_summary(month, budget)

    if s["expense_count"] == 0:
        print("No expenses found.")
        return

    print(f"===== EXPENSE SUMMARY ({s['month']}) =====")
    print("Total Expense:", s["total_spent"])
    print("Average Expense:", s["average_expense"])
    print("Number of Expenses:", s["expense_count"])
    top = s["top_category"]
    print("Top Category:", top["category"], "-", top["total"])
    day = s["highest_spending_day"]
    print("Highest Spending Day:", day["date"], "-", day["total"])

    print("\n===== CATEGORY BREAKDOWN =====")
    for c in s["category_breakdown"]:
        print(f"{c['category']}: {c['total']} ({c['percentage']}%)")

    print("\n===== DAILY SPENDING =====")
    for d in s["daily_spending"]:
        print(d["date"], ":", d["total"])

    print("\n===== MONTHLY SUMMARY =====")
    for m in s["monthly_summary"]:
        print(m["month"], ":", m["total"], f"({m['count']} expenses)")

    b = s["budget"]
    print(f"\n===== BUDGET STATUS ({b['month']}) =====")
    print("Budget:", b["budget"])
    print("Spent:", b["spent"])
    print("Remaining:", b["remaining"])
    print(f"Budget Used: {b['percent_used']}% (Level: {b['level']})")
    print(f"[{b['status'].upper()}] {b['message']}")


if __name__ == "__main__":
    print_report()