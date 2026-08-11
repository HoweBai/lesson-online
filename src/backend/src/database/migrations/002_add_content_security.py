"""Migration: Add content security related fields."""

import sqlite3


def migrate(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get existing columns from tutorials
    cursor.execute("PRAGMA table_info(tutorials)")
    existing_columns = {row[1]: row[2] for row in cursor.fetchall()}

    # Define target schema with all known columns
    target_schema = {
        "id": "VARCHAR(36) NOT NULL",
        "owner_id": "VARCHAR(36) NOT NULL",
        "title": "VARCHAR(200) NOT NULL",
        "description": "TEXT",
        "is_public": "BOOLEAN",
        "status": "VARCHAR(9)",
        "outline": "JSON",
        "total_chapters": "INTEGER",
        "current_chapter": "INTEGER",
        "created_at": "DATETIME",
        "updated_at": "DATETIME",
    }

    # Check if all required columns already exist (migration already run)
    missing_columns = [col for col in target_schema if col not in existing_columns]
    if not missing_columns:
        print("Migration 002 skipped: content security fields already present")
        conn.commit()
        conn.close()
        return

    # Build column list for INSERT/SELECT
    all_columns = list(target_schema.keys())
    col_defs = ", ".join(f"{col} {target_schema[col]}" for col in all_columns)

    # Backup existing data
    cursor.execute("CREATE TABLE IF NOT EXISTS tutorials_backup AS SELECT * FROM tutorials")

    # Drop and recreate with new schema
    cursor.execute("DROP TABLE tutorials")
    cursor.execute(f"""
        CREATE TABLE tutorials (
            {col_defs},
            PRIMARY KEY (id),
            FOREIGN KEY(owner_id) REFERENCES users (id)
        )
    """)

    # Determine which columns exist in both tables for data preservation
    existing_cols = list(existing_columns.keys())
    common_cols = [col for col in all_columns if col in existing_cols]

    if common_cols:
        insert_cols = ", ".join(common_cols)
        select_cols = ", ".join(f"COALESCE({col}, NULL)" if col not in existing_columns else col for col in common_cols)
        cursor.execute(f"INSERT INTO tutorials ({insert_cols}) SELECT {select_cols} FROM tutorials_backup")

    # Drop backup
    cursor.execute("DROP TABLE tutorials_backup")

    conn.commit()
    conn.close()
    print(f"Migration 002 completed: content security fields added ({', '.join(missing_columns)})")


if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "./ollp.db"
    migrate(db_path)
