"""Alert API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from ..database import get_db
from ..services.auth_service import get_current_user
from ..models.user import User
from ..services.alert_service import (
    alert_manager,
    send_alert,
    get_recent_alerts,
    get_alert_stats,
    AlertLevel
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/alerts", tags=["alerts"])


@router.get("/", response_model=Dict[str, Any])
async def get_alerts(
    hours: int = 24,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get recent alerts."""
    alerts = get_recent_alerts(hours, limit)
    stats = get_alert_stats()
    return {
        "alerts": alerts,
        "stats": stats,
        "total": len(alerts)
    }


@router.post("/send", response_model=Dict[str, Any])
async def send_test_alert(
    level: str = "info",
    message: str = "Test alert",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Send a test alert."""
    try:
        alert_level = AlertLevel(level.lower())
    except ValueError:
        alert_level = AlertLevel.INFO

    alert = send_alert(alert_level, message, "api_test", {"user_id": str(current_user.id)})
    return {
        "message": "Alert sent",
        "alert": alert.to_dict()
    }


@router.post("/system/critical", response_model=Dict[str, Any])
async def system_critical_alert(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Send a critical system alert."""
    alert = send_alert(
        AlertLevel.CRITICAL,
        "System critical alert triggered",
        "system_monitor",
        {"triggered_by": str(current_user.id)}
    )
    return {"message": "Critical alert sent", "alert": alert.to_dict()}


@router.post("/system/error", response_model=Dict[str, Any])
async def system_error_alert(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Send an error system alert."""
    alert = send_alert(
        AlertLevel.ERROR,
        "System error alert triggered",
        "system_monitor",
        {"triggered_by": str(current_user.id)}
    )
    return {"message": "Error alert sent", "alert": alert.to_dict()}


@router.post("/system/warning", response_model=Dict[str, Any])
async def system_warning_alert(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Send a warning system alert."""
    alert = send_alert(
        AlertLevel.WARNING,
        "System warning alert triggered",
        "system_monitor",
        {"triggered_by": str(current_user.id)}
    )
    return {"message": "Warning alert sent", "alert": alert.to_dict()}
