"""Migration: Add user_bookmarks table."""
import sqlite3


def migrate(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_bookmarks'")
    if cursor.fetchone():
        print("Migration 003 skipped: user_bookmarks table already exists")
        conn.commit()
        conn.close()
        return

    cursor.execute("""
        CREATE TABLE user_bookmarks (
            id VARCHAR(36) NOT NULL,
            user_id VARCHAR(36) NOT NULL,
            tutorial_id VARCHAR(36) NOT NULL,
            created_at DATETIME,
            PRIMARY KEY (id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(tutorial_id) REFERENCES tutorials(id) ON DELETE CASCADE,
            UNIQUE(user_id, tutorial_id)
        )
    """)

    conn.commit()
    conn.close()
    print("Migration 003 completed: user_bookmarks table created")
