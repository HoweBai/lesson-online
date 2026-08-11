"""Backup API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import logging
import os

from ..database import get_db
from ..services.auth_service import get_current_user
from ..models.user import User
from ..services.backup_service import (
    DatabaseBackup,
    PostgreSQLBackup,
    create_db_backup,
    restore_db_backup,
    list_backups
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def get_db_backup_service() -> DatabaseBackup:
    """Get database backup service instance."""
    db_path = os.getenv("DATABASE_URL", "sqlite:///./ollp.db").replace("sqlite:///", "")
    backup_dir = os.getenv("BACKUP_DIR", "./backups")
    return DatabaseBackup(db_path, backup_dir)


@router.get("/backups", response_model=List[Dict[str, Any]])
async def list_database_backups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """List all database backups."""
    try:
        backup_service = get_db_backup_service()
        backups = backup_service.list_backups()
        return backups
    except Exception as e:
        logger.error(f"Failed to list backups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backups/create", response_model=Dict[str, Any])
async def create_database_backup(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a new database backup."""
    try:
        backup_service = get_db_backup_service()
        backup_path = backup_service.create_backup()
        return {
            "message": "Backup created successfully",
            "backup_path": backup_path,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backups/restore/{backup_name}", response_model=Dict[str, Any])
async def restore_database_backup(
    backup_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Restore database from backup."""
    try:
        backup_dir = os.getenv("BACKUP_DIR", "./backups")
        backup_path = os.path.join(backup_dir, f"{backup_name}.db")

        if not os.path.exists(backup_path):
            raise HTTPException(status_code=404, detail=f"Backup not found: {backup_name}")

        restore_db_backup(backup_path)
        return {
            "message": f"Database restored from {backup_name}",
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Failed to restore backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/backups/{backup_name}", response_model=Dict[str, Any])
async def delete_database_backup(
    backup_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Delete a database backup."""
    try:
        backup_dir = os.getenv("BACKUP_DIR", "./backups")
        backup_path = os.path.join(backup_dir, f"{backup_name}.db")

        if not os.path.exists(backup_path):
            raise HTTPException(status_code=404, detail=f"Backup not found: {backup_name}")

        os.remove(backup_path)
        meta_path = backup_path.replace('.db', '.meta')
        if os.path.exists(meta_path):
            os.remove(meta_path)

        return {
            "message": f"Backup {backup_name} deleted",
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Failed to delete backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))
