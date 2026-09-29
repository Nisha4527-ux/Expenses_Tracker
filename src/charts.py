import sqlite3
import matplotlib.pyplot as plt

# Connect to database
connection = sqlite3.connect("database/expenses.db")
cursor = connection.cursor()

# Get category-wise expenses
cursor.execute("""
    SELECT category, SUM(amount)
    FROM expenses
    GROUP BY category
    ORDER BY SUM(amount) DESC
""")

data = cursor.fetchall()

# Close database connection
connection.close()

# Separate categories and amounts
categories = [row[0] for row in data]
amounts = [row[1] for row in data]

# Create bar chart
plt.bar(categories, amounts)

plt.title("Category-wise Expenses")
plt.xlabel("Category")
plt.ylabel("Amount")

plt.xticks(rotation=45)
plt.tight_layout()

plt.show()

# Monthly Spending Chart

import sqlite3
import matplotlib.pyplot as plt

connection = sqlite3.connect("database/expenses.db")
cursor = connection.cursor()

cursor.execute("""
    SELECT strftime('%Y-%m', date), SUM(amount)
    FROM expenses
    GROUP BY strftime('%Y-%m', date)
    ORDER BY strftime('%Y-%m', date)
""")

monthly_data = cursor.fetchall()

connection.close()

months = [row[0] for row in monthly_data]
amounts = [row[1] for row in monthly_data]

plt.bar(months, amounts)

plt.title("Monthly Spending")
plt.xlabel("Month")
plt.ylabel("Amount")

plt.tight_layout()
plt.show()

# Daily Spending Chart

connection = sqlite3.connect("database/expenses.db")
cursor = connection.cursor()

cursor.execute("""
    SELECT date, SUM(amount)
    FROM expenses
    GROUP BY date
    ORDER BY date
""")

daily_data = cursor.fetchall()

connection.close()

dates = [row[0] for row in daily_data]
amounts = [row[1] for row in daily_data]

plt.plot(dates, amounts, marker="o")

plt.title("Daily Spending")
plt.xlabel("Date")
plt.ylabel("Amount")

plt.xticks(rotation=45)
plt.tight_layout()

plt.show()