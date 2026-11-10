import sqlite3

DATABASE = "hospital.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_table():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            token INTEGER NOT NULL,
            status TEXT DEFAULT 'Waiting'
        )
    """)

    # Add status column to an existing database if necessary
    columns = [
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(appointments)"
        ).fetchall()
    ]

    if "status" not in columns:
        conn.execute("""
            ALTER TABLE appointments
            ADD COLUMN status TEXT DEFAULT 'Waiting'
        """)

    conn.commit()
    conn.close()


def save_appointment(name, department):
    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute("SELECT MAX(token) FROM appointments")
    result = cursor.fetchone()

    token = (result[0] or 100) + 1

    cursor.execute("""
        INSERT INTO appointments
        (name, department, token, status)
        VALUES (?, ?, ?, 'Waiting')
    """, (name, department, token))

    conn.commit()
    conn.close()

    return token
