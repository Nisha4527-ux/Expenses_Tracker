import sqlite3

connection = sqlite3.connect("database/expenses.db")
cursor = connection.cursor()

# Total expenses
cursor.execute("SELECT SUM(amount) FROM expenses")
total = cursor.fetchone()[0]

print("Total Expenses:", total if total else 0)

# Expenses by category
print("\nExpenses by Category:")

cursor.execute("""
    SELECT category, SUM(amount)
    FROM expenses
    GROUP BY category
""")

data = cursor.fetchall()

for category, amount in data:
    print(category, ":", amount)

    # Highest spending category
cursor.execute("""
    SELECT category, SUM(amount)
    FROM expenses
    GROUP BY category
    ORDER BY SUM(amount) DESC
    LIMIT 1
""")

highest = cursor.fetchone()

if highest:
    print("\nHighest Spending Category:", highest[0])
    print("Amount Spent:", highest[1])
else:
    print("\nNo expenses found.")

    # Average expense
cursor.execute("SELECT AVG(amount) FROM expenses")
average = cursor.fetchone()[0]

print("\nAverage Expense:", round(average, 2))

# Daily expenses
print("\nExpenses by Date:")

cursor.execute("""
    SELECT date, SUM(amount)
    FROM expenses
    GROUP BY date
    ORDER BY date
""")

daily_data = cursor.fetchall()

for date, amount in daily_data:
    print(date, ":", amount)

    # Highest spending day
cursor.execute("""
    SELECT date, SUM(amount)
    FROM expenses
    GROUP BY date
    ORDER BY SUM(amount) DESC
    LIMIT 1
""")

highest_day = cursor.fetchone()

if highest_day:
    print("\nHighest Spending Day:", highest_day[0])
    print("Amount Spent:", highest_day[1])
else:
    print("\nNo expenses found.")

    # Spending percentage by category
print("\nSpending Percentage by Category:")

cursor.execute("SELECT SUM(amount) FROM expenses")
total = cursor.fetchone()[0]

cursor.execute("""
    SELECT category, SUM(amount)
    FROM expenses
    GROUP BY category
""")

category_data = cursor.fetchall()

for category, amount in category_data:
    percentage = (amount / total) * 100
    print(category, ":", round(percentage, 2), "%")

    # Spending summary
print("\n===== EXPENSE SUMMARY =====")
print("Total Expense:", total)
print("Average Expense:", round(average, 2))

if highest:
    print("Top Category:", highest[0])
    print("Top Category Amount:", highest[1])

if highest_day:
    print("Highest Spending Day:", highest_day[0])
    print("Highest Day Amount:", highest_day[1])

    # Budget Analysis
budget = 3000

print("\n===== BUDGET ANALYSIS =====")
print("Monthly Budget:", budget)
print("Total Expense:", total)

if total > budget:
    print("Status: Budget Exceeded")
    print("Amount Exceeded:", total - budget)
else:
    print("Status: Within Budget")
    print("Amount Remaining:", budget - total)

    # Spending Level

percentage_used = (total / budget) * 100

print("\n===== SPENDING LEVEL =====")
print("Budget Used:", round(percentage_used, 2), "%")

if percentage_used < 50:
    print("Spending Level: Low")
elif percentage_used <= 80:
    print("Spending Level: Moderate")
else:
    print("Spending Level: High")

    # Spending Warning

print("\n===== SPENDING WARNING =====")

if percentage_used >= 90:
    print("Warning: You are close to your budget limit!")
elif percentage_used >= 70:
    print("Notice: Your spending is getting high.")
else:
    print("Good: Your spending is under control.")

    # Monthly Analytics

month = "2026-08"

cursor.execute("""
    SELECT SUM(amount)
    FROM expenses
    WHERE date LIKE ?
""", (month + "%",))

monthly_total = cursor.fetchone()[0]

if monthly_total is None:
    monthly_total = 0

print("\n===== MONTHLY ANALYTICS =====")
print("Month:", month)
print("Monthly Total Expense:", monthly_total)

cursor.execute("""
    SELECT COUNT(*)
    FROM expenses
    WHERE date LIKE ?
""", (month + "%",))

monthly_count = cursor.fetchone()[0]

print("Number of Expenses:", monthly_count)

# Monthly Average

if monthly_count > 0:
    monthly_average = monthly_total / monthly_count
else:
    monthly_average = 0

print("Monthly Average Expense:", round(monthly_average, 2))

# Top Category for the Month

cursor.execute("""
    SELECT category, SUM(amount) AS total
    FROM expenses
    WHERE date LIKE ?
    GROUP BY category
    ORDER BY total DESC
    LIMIT 1
""", (month + "%",))

top_month_category = cursor.fetchone()

if top_month_category:
    print("Top Category:", top_month_category[0])
    print("Top Category Amount:", top_month_category[1])
else:
    print("No expenses found for this month.")

    # Daily Spending

cursor.execute("""
    SELECT date, SUM(amount) AS total
    FROM expenses
    WHERE date LIKE ?
    GROUP BY date
    ORDER BY date
""", (month + "%",))

daily_expenses = cursor.fetchall()

print("\n===== DAILY SPENDING =====")

for day, amount in daily_expenses:
    print(day, ":", amount)

connection.close()

