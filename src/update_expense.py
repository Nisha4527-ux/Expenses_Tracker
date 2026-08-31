import sqlite3

connection = sqlite3.connect("database/expenses.db")
cursor = connection.cursor()

expense_id = int(input("Enter expense ID to update: "))

amount = float(input("Enter new amount: "))
category = input("Enter new category: ")
description = input("Enter new description: ")
date = input("Enter new date (YYYY-MM-DD): ")

cursor.execute("""
UPDATE expenses
SET amount = ?, category = ?, description = ?, date = ?
WHERE id = ?
""", (amount, category, description, date, expense_id))

connection.commit()

if cursor.rowcount > 0:
    print("Expense updated successfully!")
else:
    print("Expense ID not found.")

connection.close()