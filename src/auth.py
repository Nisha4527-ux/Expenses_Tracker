"""
User accounts. Passwords are never stored in plain text — only a salted hash
(werkzeug's generate_password_hash, the same helper Flask itself ships with).
"""
import re

from werkzeug.security import check_password_hash, generate_password_hash

from database import get_connection

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
MIN_PASSWORD_LENGTH = 6


def register_user(username, password):
    """Create an account. Returns (user_dict, None) or (None, error_message)."""
    username = (username or "").strip()

    if not USERNAME_RE.match(username):
        return None, "Username must be 3-20 characters: letters, numbers, or underscore only"
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        return None, f"Password must be at least {MIN_PASSWORD_LENGTH} characters"

    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            return None, "That username is already taken"

        is_first_account = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"] == 0

        cursor = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        user_id = cursor.lastrowid

        if is_first_account:
            # Expenses added before any account existed have no owner.
            # The first person to sign up gets to keep that earlier data.
            conn.execute("UPDATE expenses SET user_id = ? WHERE user_id IS NULL", (user_id,))

    return {"id": user_id, "username": username}, None


def authenticate_user(username, password):
    """Check a login. Returns the user dict if valid, else None."""
    username = (username or "").strip()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    if row and check_password_hash(row["password_hash"], password):
        return {"id": row["id"], "username": row["username"]}
    return None