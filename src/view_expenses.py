import sqlite3

connection = sqlite3.connect("database/expenses.db")
cursor = connection.cursor()

cursor.execute("SELECT * FROM expenses")

expenses = cursor.fetchall()

for expense in expenses:
    print(expense)

connection.close()