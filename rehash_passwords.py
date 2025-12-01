# rehash_passwords.py

import sqlite3
from werkzeug.security import generate_password_hash

def rehash_all_passwords():
    conn = sqlite3.connect("instance/trips.db")
    cursor = conn.cursor()

    users = cursor.execute("SELECT id, password FROM users").fetchall()

    for user_id, password in users:
        # Skip if password is already hashed (starts with 'pbkdf2:')
        if not password.startswith("pbkdf2:"):
            new_hash = generate_password_hash(password)
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", (new_hash, user_id))

    conn.commit()
    conn.close()
    print("✅ Passwords rehashed successfully.")

if __name__ == "__main__":
    rehash_all_passwords()
