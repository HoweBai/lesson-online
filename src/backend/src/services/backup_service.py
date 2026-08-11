"""Backup and restore utilities for the Online Learning Platform."""

import os
import sqlite3
import subprocess
import logging
from datetime import datetime
from typing import Optional
import shutil

logger = logging.getLogger(__name__)


class DatabaseBackup:
    """Handles database backup and restore operations."""

    def __init__(self, db_path: str, backup_dir: str = "./backups"):
        self.db_path = db_path
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)

    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """Create a database backup."""
        if not backup_name:
            backup_name = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        backup_path = os.path.join(self.backup_dir, f"{backup_name}.db")

        try:
            # Copy the database file
            shutil.copy2(self.db_path, backup_path)

            # Create a metadata file
            metadata_path = os.path.join(self.backup_dir, f"{backup_name}.meta")
            with open(metadata_path, 'w') as f:
                f.write(f"Backup created: {datetime.utcnow().isoformat()}\n")
                f.write(f"Source: {self.db_path}\n")
                f.write(f"Size: {os.path.getsize(backup_path)} bytes\n")

            logger.info(f"Database backup created: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise

    def restore_backup(self, backup_path: str) -> bool:
        """Restore database from backup."""
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        try:
            # Backup current database before restore
            if os.path.exists(self.db_path):
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                current_backup = os.path.join(self.backup_dir, f"pre_restore_{timestamp}.db")
                shutil.copy2(self.db_path, current_backup)
                logger.info(f"Current database backed up before restore: {current_backup}")

            # Restore from backup
            shutil.copy2(backup_path, self.db_path)
            logger.info(f"Database restored from: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore database: {e}")
            raise

    def list_backups(self) -> list:
        """List all available backups."""
        backups = []
        for file in os.listdir(self.backup_dir):
            if file.endswith('.db') and not file.startswith('pre_restore_'):
                meta_file = os.path.join(self.backup_dir, f"{file.replace('.db', '.meta')}")
                metadata = {}
                if os.path.exists(meta_file):
                    with open(meta_file, 'r') as f:
                        for line in f:
                            if ':' in line:
                                key, value = line.strip().split(':', 1)
                                metadata[key.strip()] = value.strip()

                backups.append({
                    "filename": file,
                    "path": os.path.join(self.backup_dir, file),
                    "size": os.path.getsize(os.path.join(self.backup_dir, file)),
                    "metadata": metadata
                })

        return sorted(backups, key=lambda x: x["metadata"].get("Backup created", ""), reverse=True)

    def delete_backup(self, backup_path: str) -> bool:
        """Delete a backup file."""
        try:
            os.remove(backup_path)
            meta_path = backup_path.replace('.db', '.meta')
            if os.path.exists(meta_path):
                os.remove(meta_path)
            logger.info(f"Backup deleted: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete backup: {e}")
            return False


class PostgreSQLBackup:
    """Handles PostgreSQL database backup and restore."""

    def __init__(
        self,
        database: str,
        user: str,
        host: str = "localhost",
        port: int = 5432,
        backup_dir: str = "./backups"
    ):
        self.database = database
        self.user = user
        self.host = host
        self.port = port
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)

    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """Create a PostgreSQL database backup."""
        if not backup_name:
            backup_name = f"pg_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        backup_path = os.path.join(self.backup_dir, f"{backup_name}.sql")

        try:
            cmd = [
                "pg_dump",
                "-h", self.host,
                "-p", str(self.port),
                "-U", self.user,
                "-d", self.database,
                "-F", "custom",
                "-f", backup_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")

            logger.info(f"PostgreSQL backup created: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"Failed to create PostgreSQL backup: {e}")
            raise

    def restore_backup(self, backup_path: str) -> bool:
        """Restore PostgreSQL database from backup."""
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        try:
            cmd = [
                "pg_restore",
                "-h", self.host,
                "-p", str(self.port),
                "-U", self.user,
                "-d", self.database,
                "--clean",
                "--if-exists",
                backup_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"pg_restore failed: {result.stderr}")

            logger.info(f"PostgreSQL database restored from: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore PostgreSQL database: {e}")
            raise

    def list_backups(self) -> list:
        """List all PostgreSQL backups."""
        backups = []
        for file in os.listdir(self.backup_dir):
            if file.endswith('.sql') or file.endswith('.custom'):
                backups.append({
                    "filename": file,
                    "path": os.path.join(self.backup_dir, file),
                    "size": os.path.getsize(os.path.join(self.backup_dir, file)),
                    "created": datetime.fromtimestamp(
                        os.path.getctime(os.path.join(self.backup_dir, file))
                    ).isoformat()
                })
        return sorted(backups, key=lambda x: x["created"], reverse=True)


# Convenience functions
def create_db_backup(db_path: str = "./ollp.db", backup_dir: str = "./backups") -> str:
    """Create a backup of the SQLite database."""
    backup = DatabaseBackup(db_path, backup_dir)
    return backup.create_backup()


def restore_db_backup(backup_path: str, db_path: str = "./ollp.db") -> bool:
    """Restore a database backup."""
    backup = DatabaseBackup(db_path)
    return backup.restore_backup(backup_path)


def list_backups(backup_dir: str = "./backups") -> list:
    """List all available backups."""
    backup = DatabaseBackup("./ollp.db", backup_dir)
    return backup.list_backups()
