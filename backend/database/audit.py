import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "audit.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        role TEXT,
        question TEXT,
        decision TEXT,
        sources TEXT,
        timestamp TEXT
    )
    """)

    conn.commit()
    conn.close()

def log_event(username, role, question, decision, sources):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO audit_logs
    (username, role, question, decision, sources, timestamp)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        username,
        role,
        question,
        decision,
        ",".join(sources),
        datetime.utcnow().isoformat()
    ))

    conn.commit()
    conn.close()
