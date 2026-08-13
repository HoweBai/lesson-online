"""Admin API endpoints for platform management."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta

from ..database import get_db
from ..services.auth_service import get_current_user
from ..services.admin_service import admin_service, AdminService
from ..models.user import User
from ..models.tutorial import Tutorial
from ..models.public_catalog import PublicCatalog

logger = logging.getLogger(__name__)

admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.post("/login")
async def admin_login(
    body: dict,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Admin login with email and password."""
    try:
        return admin_service.admin_login(db, body.get("email", ""), body.get("password", ""))
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@admin_router.get("/me")
async def get_admin_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_service.require_admin)
) -> Dict[str, Any]:
    """Get current admin user info."""
    return {"user": current_user.to_dict()}


@admin_router.get("/users")
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_service.require_admin),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """List all users with pagination and optional search."""
    query = db.query(User)
    if search:
        query = query.filter(
            User.username.ilike(f"%{search}%") |
            User.email.ilike(f"%{search}%")
        )
    total = query.count()
    offset = (page - 1) * limit
    users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "data": [u.to_dict() for u in users],
        "pagination": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit}
    }


@admin_router.get("/users/{user_id}")
async def get_user_detail(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_service.require_admin)
) -> Dict[str, Any]:
    """Get user detail with tutorial counts."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    tutorials = db.query(Tutorial).filter(Tutorial.owner_id == user_id).all()
    return {
        "user": user.to_dict(),
        "tutorial_count": len(tutorials),
        "tutorials": [t.to_dict() for t in tutorials]
    }


@admin_router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_service.require_admin)
) -> Dict[str, Any]:
    """Toggle user admin status (is_admin field)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot modify your own admin status")
    user.is_admin = body.get("is_admin", False)
    db.commit()
    db.refresh(user)
    return {"message": "User status updated", "user": user.to_dict()}


@admin_router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_service.require_admin)
) -> Dict[str, Any]:
    """Delete a user and all their data."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    # Cascade delete is handled by SQLAlchemy relationships
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}


@admin_router.get("/catalog/pending")
async def list_pending_tutorials(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_service.require_admin),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    """List tutorials pending review (status='reviewing')."""
    query = db.query(Tutorial).filter(Tutorial.status == "reviewing")
    total = query.count()
    offset = (page - 1) * limit
    tutorials = query.order_by(Tutorial.created_at.desc()).offset(offset).limit(limit).all()
    result = []
    for t in tutorials:
        catalog = db.query(PublicCatalog).filter(PublicCatalog.tutorial_id == t.id).first()
        result.append({
            **t.to_dict(),
            "view_count": catalog.view_count if catalog else 0,
            "like_count": catalog.like_count if catalog else 0,
            "reported_count": catalog.reported_count if catalog else 0,
        })
    return {
        "data": result,
        "pagination": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit}
    }


@admin_router.put("/catalog/{tutorial_id}/review")
async def review_tutorial(
    tutorial_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_service.require_admin)
) -> Dict[str, Any]:
    """Approve or reject a tutorial. body: {action: 'approve'|'reject'}."""
    tutorial = db.query(Tutorial).filter(Tutorial.id == tutorial_id).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")
    action = body.get("action", "")
    if action == "approve":
        tutorial.status = "published"
        tutorial.is_public = True
    elif action == "reject":
        tutorial.status = "draft"
        tutorial.is_public = False
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'.")
    db.commit()
    db.refresh(tutorial)
    return {"message": f"Tutorial {action}d", "tutorial": tutorial.to_dict()}


@admin_router.get("/stats/overview")
async def get_stats_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_service.require_admin)
) -> Dict[str, Any]:
    """Get platform overview statistics."""
    total_users = db.query(User).count()
    total_tutorials = db.query(Tutorial).count()
    published_tutorials = db.query(Tutorial).filter(Tutorial.status == "published").count()
    pending_tutorials = db.query(Tutorial).filter(Tutorial.status == "reviewing").count()

    # New users in last 7 days
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users = db.query(User).filter(User.created_at >= week_ago).count()

    # Published this month
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    published_month = db.query(Tutorial).filter(
        Tutorial.status == "published", Tutorial.created_at >= month_start
    ).count()

    return {
        "total_users": total_users,
        "total_tutorials": total_tutorials,
        "published_tutorials": published_tutorials,
        "pending_tutorials": pending_tutorials,
        "new_users_last_7_days": new_users,
        "published_this_month": published_month,
    }


@admin_router.get("/stats/users")
async def get_user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_service.require_admin),
    period: str = Query("30d", description="Period: 7d, 30d, 90d")
) -> Dict[str, Any]:
    """Get user growth statistics for a period."""
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
    start_date = datetime.utcnow() - timedelta(days=days)

    # Group by date
    from sqlalchemy import func
    results = db.query(
        func.date(User.created_at).label("date"),
        func.count(User.id).label("count")
    ).filter(User.created_at >= start_date).group_by("date").order_by("date").all()

    return {
        "period": period,
        "growth": [{"date": str(r.date), "count": r.count} for r in results],
        "total": len(results),
    }


@admin_router.get("/stats/tutorials")
async def get_tutorial_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_service.require_admin),
    period: str = Query("30d")
) -> Dict[str, Any]:
    """Get tutorial creation and status statistics."""
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
    start_date = datetime.utcnow() - timedelta(days=days)

    total = db.query(Tutorial).filter(Tutorial.created_at >= start_date).count()
    by_status = {}
    for status_val in ["draft", "reviewing", "published", "retired"]:
        count = db.query(Tutorial).filter(
            Tutorial.created_at >= start_date, Tutorial.status == status_val
        ).count()
        by_status[status_val] = count

    return {"period": period, "total": total, "by_status": by_status}
