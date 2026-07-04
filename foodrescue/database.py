"""
Run this once to (re)create the schema:  python database.py

If you already have an old LoginData.db from before this rewrite, delete it
first — the schema below changes primary keys and column names
(password -> password_hash) and old data won't migrate automatically.
"""

import sqlite3

DB_FILE = "LoginData.db"

connection = sqlite3.connect(DB_FILE)
cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS USERS (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name    VARCHAR(50) NOT NULL,
    last_name     VARCHAR(50) NOT NULL,
    email         VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    door_no       VARCHAR(20) NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS INVENTORY (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    foodname VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL,
    expiry   DATE NOT NULL,
    door_no  VARCHAR(20) NOT NULL
)
""")

# NOTE: email is a plain column here, not a primary key, so one person can
# make more than one donation (the old schema blocked this).
cursor.execute("""
CREATE TABLE IF NOT EXISTS DONATION (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name     VARCHAR(50) NOT NULL,
    last_name      VARCHAR(50) NOT NULL,
    email          VARCHAR(120) NOT NULL,
    foodname       VARCHAR(50) NOT NULL,
    quantity       INTEGER NOT NULL,
    donation_date  DATE NOT NULL,
    service        VARCHAR(15) NOT NULL
)
""")

connection.commit()
connection.close()

print(f"Schema ready in {DB_FILE}.")
