"""Database migration runner."""

import os
import sys
import importlib.util
from pathlib import Path


def run_migrations(db_path: str):
    """Run all pending migrations."""
    migrations_dir = Path(__file__).parent / "migrations"

    if not db_path.endswith('.db'):
        # Extract path from SQLite URL
        db_path = db_path.replace('sqlite:///', '').replace('sqlite://', '')

    print(f"Running migrations for: {db_path}")

    # Get all migration files
    migration_files = sorted([
        f for f in migrations_dir.glob("*.py")
        if f.name != "__init__.py"
    ])

    for migration_file in migration_files:
        spec = importlib.util.spec_from_file_location(
            migration_file.stem, migration_file
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(db_path)

    print("All migrations completed!")


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "./ollp.db"
    run_migrations(db_path)
