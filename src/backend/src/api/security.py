"""Security scanning API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging

from ..database import get_db
from ..models.audit_log import AuditLog

logger = logging.getLogger(__name__)

security_router = APIRouter(prefix="/security", tags=["security"])


@security_router.get("/scans", response_model=Dict[str, Any])
async def get_security_scans(
    db: Session = Depends(get_db),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    """Get security scan records."""
    query = db.query(AuditLog).filter(AuditLog.action_type == 'content_scanned')

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action_type:
        query = query.filter(AuditLog.action_type == action_type)

    total = query.count()
    offset = (page - 1) * limit
    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    return {
        "data": [log.to_dict() for log in logs],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


@security_router.get("/stats", response_model=Dict[str, Any])
async def get_security_stats(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get security scan statistics."""
    total_scans = db.query(AuditLog).filter(
        AuditLog.action_type == 'content_scanned'
    ).count()

    flagged_count = db.query(AuditLog).filter(
        AuditLog.action_type == 'content_scanned',
        AuditLog.details_json['reasons'].isnot(None)
    ).count()

    return {
        "total_scans": total_scans,
        "flagged_count": flagged_count,
        "flag_rate": flagged_count / total_scans if total_scans > 0 else 0
    }
