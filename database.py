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
#
# status tracks the order lifecycle for this donation:
#   'available' -> nobody has requested it yet, shows up in /stackFood
#   'pending'   -> someone requested it, waiting on the donor to approve/decline
#   'approved'  -> donor approved the request
cursor.execute("""
CREATE TABLE IF NOT EXISTS DONATION (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name            VARCHAR(50) NOT NULL,
    last_name             VARCHAR(50) NOT NULL,
    email                 VARCHAR(120) NOT NULL,
    foodname              VARCHAR(50) NOT NULL,
    quantity              INTEGER NOT NULL,
    donation_date         DATE NOT NULL,
    service               VARCHAR(15) NOT NULL,
    status                VARCHAR(15) NOT NULL DEFAULT 'available',
    ordered_by_first_name VARCHAR(50),
    ordered_by_last_name  VARCHAR(50),
    ordered_by_email      VARCHAR(120)
)
""")

# --- Lightweight migration for DBs created before the columns above existed ---
existing_columns = {row[1] for row in cursor.execute("PRAGMA table_info(DONATION)").fetchall()}
migration_columns = {
    "status": "VARCHAR(15) NOT NULL DEFAULT 'available'",
    "ordered_by_first_name": "VARCHAR(50)",
    "ordered_by_last_name": "VARCHAR(50)",
    "ordered_by_email": "VARCHAR(120)",
}
for column, definition in migration_columns.items():
    if column not in existing_columns:
        cursor.execute(f"ALTER TABLE DONATION ADD COLUMN {column} {definition}")
        print(f"Migrated: added DONATION.{column}")

connection.commit()
connection.close()

print(f"Schema ready in {DB_FILE}.")