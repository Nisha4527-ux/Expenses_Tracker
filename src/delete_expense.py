import sqlite3

connection = sqlite3.connect("database/expenses.db")
cursor = connection.cursor()

expense_id = int(input("Enter expense ID to delete: "))

cursor.execute(
    "DELETE FROM expenses WHERE id = ?",
    (expense_id,)
)

connection.commit()

if cursor.rowcount > 0:
    print("Expense deleted successfully!")
else:
    print("Expense ID not found.")

connection.close()