"""Migration: Add ondelete CASCADE/SET NULL to user foreign keys.

Fixes: User deletion fails due to missing ON DELETE CASCADE constraints.
"""


def migrate(db_url: str):
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import StaticPool

    engine = create_engine(db_url)
    with engine.connect() as conn:
        # tutorials.owner_id -> CASCADE
        try:
            conn.execute(text(
                "ALTER TABLE tutorials DROP CONSTRAINT IF EXISTS tutorials_owner_id_fkey;"
            ))
            conn.execute(text(
                "ALTER TABLE tutorials ADD CONSTRAINT tutorials_owner_id_fkey "
                "FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE;"
            ))
            print("  tutorials.owner_id: added CASCADE")
        except Exception as e:
            print(f"  tutorials.owner_id: {e}")

        # public_catalog.published_by -> CASCADE
        try:
            conn.execute(text(
                "ALTER TABLE public_catalog DROP CONSTRAINT IF EXISTS public_catalog_published_by_fkey;"
            ))
            conn.execute(text(
                "ALTER TABLE public_catalog ADD CONSTRAINT public_catalog_published_by_fkey "
                "FOREIGN KEY (published_by) REFERENCES users(id) ON DELETE CASCADE;"
            ))
            print("  public_catalog.published_by: added CASCADE")
        except Exception as e:
            print(f"  public_catalog.published_by: {e}")

        # public_catalog.approved_by -> SET NULL
        try:
            conn.execute(text(
                "ALTER TABLE public_catalog DROP CONSTRAINT IF EXISTS public_catalog_approved_by_fkey;"
            ))
            conn.execute(text(
                "ALTER TABLE public_catalog ADD CONSTRAINT public_catalog_approved_by_fkey "
                "FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL;"
            ))
            print("  public_catalog.approved_by: added SET NULL")
        except Exception as e:
            print(f"  public_catalog.approved_by: {e}")

        # task_logs.user_id -> CASCADE
        try:
            conn.execute(text(
                "ALTER TABLE task_logs DROP CONSTRAINT IF EXISTS task_logs_user_id_fkey;"
            ))
            conn.execute(text(
                "ALTER TABLE task_logs ADD CONSTRAINT task_logs_user_id_fkey "
                "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;"
            ))
            print("  task_logs.user_id: added CASCADE")
        except Exception as e:
            print(f"  task_logs.user_id: {e}")

        conn.commit()
    engine.dispose()
    print("Migration complete!")


if __name__ == "__main__":
    import os
    db_url = os.getenv("DATABASE_URL", "postgresql://ollp_user:ollp_dev_2026_secure@localhost:5432/ollp_db")
    print(f"Running migration for: {db_url}")
    migrate(db_url)
