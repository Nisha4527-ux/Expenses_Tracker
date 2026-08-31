import sqlite3

connection = sqlite3.connect("database/expenses.db")

cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    date TEXT NOT NULL
)
""")

connection.commit()
connection.close()

print("Database and expenses table created successfully!")