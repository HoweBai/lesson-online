"""Migration: Add tutorial_comments table."""
import sqlite3


def migrate(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tutorial_comments'")
    if cursor.fetchone():
        print("Migration 004 skipped: tutorial_comments table already exists")
        conn.commit()
        conn.close()
        return

    cursor.execute("""
        CREATE TABLE tutorial_comments (
            id VARCHAR(36) NOT NULL,
            tutorial_id VARCHAR(36) NOT NULL,
            user_id VARCHAR(36) NOT NULL,
            content TEXT NOT NULL,
            parent_id VARCHAR(36),
            like_count INTEGER DEFAULT 0,
            created_at DATETIME,
            PRIMARY KEY (id),
            FOREIGN KEY(tutorial_id) REFERENCES tutorials(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(parent_id) REFERENCES tutorial_comments(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()
    print("Migration 004 completed: tutorial_comments table created")
