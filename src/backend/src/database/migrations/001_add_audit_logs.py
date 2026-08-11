"""Migration: Add audit_logs table."""

import sqlite3


def migrate(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id VARCHAR(36) NOT NULL,
            user_id VARCHAR(36),
            action_type VARCHAR(50) NOT NULL,
            ip_address VARCHAR(45),
            success DATETIME,
            details_json JSON,
            timestamp DATETIME,
            PRIMARY KEY (id)
        )
    """)

    conn.commit()
    conn.close()
    print("Migration 001 completed: audit_logs table created")


if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "./ollp.db"
    migrate(db_path)
