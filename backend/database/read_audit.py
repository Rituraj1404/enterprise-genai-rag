import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "audit.db"

def fetch_audit_logs(limit=50):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT username, role, question, decision, timestamp
        FROM audit_logs
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()
    return rows
