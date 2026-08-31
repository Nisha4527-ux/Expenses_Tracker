from datetime import datetime
import sqlite3

connection = sqlite3.connect("database/expenses.db")
cursor = connection.cursor()

while True:
    try:
        amount = float(input("Enter amount: "))

        if amount <= 0:
            print("Amount must be greater than 0.")
            continue

        break

    except ValueError:
        print("Please enter a valid number.")
print("\nCategories:")
print("1. Food")
print("2. Transport")
print("3. Shopping")
print("4. Bills")
print("5. Entertainment")
print("6. Other")

choice = input("Choose category (1-6): ")

categories = {
    "1": "Food",
    "2": "Transport",
    "3": "Shopping",
    "4": "Bills",
    "5": "Entertainment",
    "6": "Other"
}

category = categories.get(choice)

if category is None:
    print("Invalid category.")
    connection.close()
    exit()
description = input("Enter description: ")
while True:
    date = input("Enter date (YYYY-MM-DD): ")

    try:
        datetime.strptime(date, "%Y-%m-%d")
        break
    except ValueError:
        print("Invalid date. Please use YYYY-MM-DD.")

cursor.execute("""
INSERT INTO expenses (amount, category, description, date)
VALUES (?, ?, ?, ?)
""", (amount, category, description, date))

connection.commit()
connection.close()

print("Expense added successfully!")