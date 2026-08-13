# P2 Admin Panel & Dark Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add admin panel (login, user management, tutorial review, stats dashboard) and dark mode support to the Online Learning Platform.

**Architecture:** Backend admin API with admin-only middleware using `is_admin` flag on User model. Frontend admin pages gated by `AdminGuard` component. Dark mode uses React Context + Tailwind `dark:` class strategy stored in localStorage.

**Tech Stack:** FastAPI + SQLAlchemy + SQLite (backend), React 18 + TypeScript + Tailwind CSS + recharts (frontend)

**Spec:** docs/superpowers/specs/2026-08-11-platform-enhancement-design.md (section 2.3 P2), FUNCTIONAL_GAP_ANALYSIS_v2.md

## Global Constraints

- Admin auth: `is_admin` boolean field added to `users` table via migration, default `FALSE`
- Admin login uses email/password, returns JWT token with `is_admin` claim
- All admin endpoints protected by `get_current_admin` dependency (JWT + is_admin check)
- Existing user registration creates `is_admin=False` — no change to registration flow
- Dark mode: uses Tailwind `darkMode: "class"` strategy — toggled via `document.documentElement.classList.toggle("dark")`
- Dark mode preference stored in `localStorage` as `"theme"` key (`"dark"` or `"light"`)
- Dark mode initialized on page load from localStorage to prevent flash of wrong theme
- All admin page components follow existing code patterns: `useState`, `useEffect`, `useToast`, `api` client
- Frontend uses `react-hot-toast` via `useToast()` hook for all notifications
- Existing test patterns: `conftest.py` fixtures, `pytest` with `TestClient`
- No new npm dependencies required (recharts already installed)
- Build must succeed after each task: `cd src/frontend && npm run build`

---

## File Structure Overview

**Backend changes:**
```
src/backend/src/models/user.py            -- Modify: add is_admin column + to_dict
src/backend/src/database.py               -- Modify: add migration for is_admin
src/backend/src/api/admin.py              -- Create: admin API endpoints
src/backend/src/services/admin_service.py -- Create: admin auth service
src/backend/src/api/main.py               -- Modify: register admin router
src/backend/tests/test_admin.py           -- Create: admin API tests
```

**Frontend changes:**
```
src/frontend/src/contexts/ThemeContext.tsx    -- Create: dark mode context
src/frontend/src/App.tsx                      -- Modify: add ThemeProvider, admin routes
src/frontend/src/components/AdminGuard.tsx    -- Create: admin route guard
src/frontend/src/pages/AdminLoginPage.tsx     -- Create: admin login page
src/frontend/src/pages/AdminDashboardPage.tsx -- Create: admin dashboard
src/frontend/src/pages/AdminUsersPage.tsx     -- Create: user management
src/frontend/src/pages/AdminCatalogPage.tsx   -- Create: tutorial review
src/frontend/src/api/client.ts                -- Modify: add admin API methods
src/frontend/src/types.ts                     -- Modify: add is_admin to User
```

---

## Task 1: Database Migration — is_admin Column

**Files:**
- Modify: `src/backend/src/models/user.py`
- Modify: `src/backend/src/database.py`

**Interfaces:**
- Consumes: none (model modification)
- Produces: `User.is_admin` boolean column, updated `User.to_dict()` including `is_admin`

- [ ] **Step 1: Add `is_admin` column to User model**

Open `src/backend/src/models/user.py` and modify it:

Add `Boolean` to the import from sqlalchemy:
```python
from sqlalchemy import Column, String, DateTime, UniqueConstraint, Boolean
```

Add the column after `created_at`:
```python
is_admin = Column(Boolean, default=False)
```

Update `to_dict()` to include `is_admin`:
```python
def to_dict(self):
    return {
        "id": self.id,
        "username": self.username,
        "email": self.email,
        "created_at": self.created_at.isoformat(),
        "is_admin": self.is_admin,
    }
```

- [ ] **Step 2: Add migration in database.py**

Open `src/backend/src/database.py`. In the `migrate_db()` function, add before the `conn.close()`:
```python
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE")
            conn.commit()
            print("Added is_admin column to users")
        except sqlite3.OperationalError:
            pass  # Column already exists
```

- [ ] **Step 3: Run migration manually to verify**

From project root:
```bash
cd src/backend && python -c "from src.database import migrate_db; migrate_db()"
```
Expected: prints "Added is_admin column to users" (or "Column already exists" if it was already run)

- [ ] **Step 4: Run backend tests to verify no breakage**

```bash
cd src/backend && python -m pytest tests/ -v --tb=short 2>&1 | head -80
```
Expected: no new failures (pre-existing failures are acceptable)

- [ ] **Step 5: Commit**

```bash
git add src/backend/src/models/user.py src/backend/src/database.py
git commit -m "feat: add is_admin column to User model with migration"
```

---

## Task 2: Admin Auth Service + Admin API Endpoints

**Files:**
- Create: `src/backend/src/services/admin_service.py`
- Create: `src/backend/src/api/admin.py`
- Modify: `src/backend/src/api/main.py`

**Interfaces:**
- Consumes: `User` model with `is_admin`, `get_current_user` from `auth_service`
- Produces: `admin_router` with endpoints:
  - `POST /api/v1/admin/login` — admin login with is_admin check
  - `GET /api/v1/admin/me` — current admin info
  - `GET /api/v1/admin/users` — user list with pagination/search
  - `GET /api/v1/admin/users/{id}` — user detail
  - `PUT /api/v1/admin/users/{id}/status` — toggle active/inactive (uses `is_admin` to also toggle admin)
  - `DELETE /api/v1/admin/users/{id}` — delete user
  - `GET /api/v1/admin/catalog/pending` — tutorials with status="reviewing"
  - `PUT /api/v1/admin/catalog/{id}/review` — approve/reject tutorial
  - `GET /api/v1/admin/stats/overview` — platform stats
  - `GET /api/v1/admin/stats/users` — user growth stats
  - `GET /api/v1/admin/stats/tutorials` — tutorial stats

- [ ] **Step 1: Create admin service**

Create `src/backend/src/services/admin_service.py`:
```python
"""Admin authentication and authorization service."""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models.user import User
from ..services.auth_service import get_current_user, AuthService


class AdminService:
    """Service for admin authentication and authorization."""

    def __init__(self):
        self.auth_service = AuthService()

    def require_admin(
        self,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        """Check that the current user is an admin."""
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        return current_user

    def admin_login(self, db: Session, email: str, password: str) -> dict:
        """Admin login — same as regular login but requires is_admin=True."""
        auth_service = AuthService()
        user = db.query(User).filter(User.email == email).first()
        if not user or not auth_service.verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")
        if not user.is_admin:
            raise ValueError("Admin access required")
        token = auth_service.create_access_token(data={"sub": str(user.id)})
        return {"user": user.to_dict(), "token": token}


admin_service = AdminService()
```

- [ ] **Step 2: Create admin API router**

Create `src/backend/src/api/admin.py`:
```python
"""Admin API endpoints for platform management."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta

from ..database import get_db
from ..services.auth_service import get_current_user
from ..services.admin_service import admin_service, AdminService
from ..models.user import User
from ..models.tutorial import Tutorial
from ..models.public_catalog import PublicCatalog
from ..models.task_log import TaskLog

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
    from ..models.tutorial import Tutorial
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
    from ..models.public_catalog import PublicCatalog
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
    """Approve or reject a tutorial. body: {action: 'approve'|'reject', reason: str}."""
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
    from datetime import datetime, timedelta
    total_users = db.query(User).count()
    total_tutorials = db.query(Tutorial).count()
    published_tutorials = db.query(Tutorial).filter(Tutorial.status == "published").count()
    pending_tutorials = db.query(Tutorial).filter(Tutorial.status == "reviewing").count()
    total_chapters = db.query(TaskLog).count()  # proxy for activity

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
    from datetime import timedelta
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
    from datetime import timedelta
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
```

- [ ] **Step 3: Register admin router in main.py**

Open `src/backend/src/api/main.py`. Add import after existing imports:
```python
from ..api.admin import admin_router
```

Add router registration after existing routers:
```python
app.include_router(admin_router, prefix="/api/v1", tags=["admin"])
```

- [ ] **Step 4: Run backend tests**

```bash
cd src/backend && python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```
Expected: no new failures

- [ ] **Step 5: Commit**

```bash
git add src/backend/src/services/admin_service.py src/backend/src/api/admin.py src/backend/src/api/main.py
git commit -m "feat: add admin API endpoints with authentication and authorization"
```

---

## Task 3: Admin API Tests

**Files:**
- Create: `src/backend/tests/test_admin.py`

**Interfaces:**
- Consumes: `client` fixture, `test_user` fixture from `conftest.py`
- Produces: test coverage for all admin endpoints

- [ ] **Step 1: Write admin API tests**

Create `src/backend/tests/test_admin.py`:
```python
"""Tests for admin API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.database import engine, Base, get_db
from src.models.user import User
from src.services.auth_service import AuthService
from src.api.main import app

# Create test database
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


class TestAdminLogin:
    """Test admin login endpoint."""

    def test_admin_login_success(self):
        """Admin login with valid admin credentials."""
        auth = AuthService()
        with Session(bind=engine) as db:
            user = User(username="admin1", email="admin1@test.com")
            user.password_hash = auth.hash_password("adminpass123")
            user.is_admin = True
            db.add(user)
            db.commit()
            db.refresh(user)

        response = client.post("/api/v1/admin/login", json={
            "email": "admin1@test.com",
            "password": "adminpass123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["is_admin"] is True
        self.admin_token = data["token"]
        self.admin_user_id = data["user"]["id"]

    def test_admin_login_regular_user_fails(self):
        """Regular user login to admin endpoint should fail."""
        auth = AuthService()
        with Session(bind=engine) as db:
            user = User(username="regular1", email="regular1@test.com")
            user.password_hash = auth.hash_password("regularpass123")
            user.is_admin = False
            db.add(user)
            db.commit()

        response = client.post("/api/v1/admin/login", json={
            "email": "regular1@test.com",
            "password": "regularpass123"
        })
        assert response.status_code == 401

    def test_admin_login_invalid_credentials(self):
        """Admin login with invalid credentials should fail."""
        response = client.post("/api/v1/admin/login", json={
            "email": "nobody@test.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401


class TestAdminMe:
    """Test admin /me endpoint."""

    def setup_method(self):
        """Create admin token for testing."""
        auth = AuthService()
        with Session(bind=engine) as db:
            user = User(username="admintest", email="admintest@test.com")
            user.password_hash = auth.hash_password("admintestpass")
            user.is_admin = True
            db.add(user)
            db.commit()
            db.refresh(user)
            self.token = auth.create_access_token(data={"sub": str(user.id)})

    def test_admin_me_success(self):
        """Admin can get their own info."""
        response = client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {self.token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["is_admin"] is True

    def test_admin_me_requires_auth(self):
        """Admin /me without token should fail."""
        response = client.get("/api/v1/admin/me")
        assert response.status_code == 401

    def test_admin_me_regular_user_fails(self):
        """Regular user cannot access admin /me."""
        auth = AuthService()
        with Session(bind=engine) as db:
            user = User(username="regtest", email="regtest@test.com")
            user.password_hash = auth.hash_password("regtestpass")
            user.is_admin = False
            db.add(user)
            db.commit()
            db.refresh(user)
            token = auth.create_access_token(data={"sub": str(user.id)})
        response = client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403


class TestAdminUsers:
    """Test admin user management endpoints."""

    def setup_method(self):
        """Create admin token for testing."""
        auth = AuthService()
        with Session(bind=engine) as db:
            admin = User(username="admintest2", email="admintest2@test.com")
            admin.password_hash = auth.hash_password("admintestpass")
            admin.is_admin = True
            db.add(admin)
            db.commit()
            db.refresh(admin)
            self.token = auth.create_access_token(data={"sub": str(admin.id)})
            # Create some regular users
            for i in range(5):
                u = User(username=f"user{i}", email=f"user{i}@test.com")
                u.password_hash = auth.hash_password("pass123")
                u.is_admin = False
                db.add(u)
            db.commit()

    def test_list_users(self):
        """Admin can list users."""
        response = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {self.token}"})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) > 0

    def test_list_users_with_search(self):
        """Admin can search users."""
        response = client.get("/api/v1/admin/users?search=user0", headers={"Authorization": f"Bearer {self.token}"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) > 0
        # All results should contain 'user0'
        for u in data["data"]:
            assert "user0" in u["username"] or "user0" in u["email"]

    def test_get_user_detail(self):
        """Admin can get user detail."""
        with Session(bind=engine) as db:
            target = db.query(User).filter(User.email == "user0@test.com").first()
        response = client.get(f"/api/v1/admin/users/{target.id}", headers={"Authorization": f"Bearer {self.token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "user0@test.com"
        assert "tutorial_count" in data

    def test_get_user_detail_not_found(self):
        """Admin get non-existent user returns 404."""
        response = client.get("/api/v1/admin/users/nonexistent-id", headers={"Authorization": f"Bearer {self.token}"})
        assert response.status_code == 404

    def test_update_user_admin_status(self):
        """Admin can toggle user admin status."""
        with Session(bind=engine) as db:
            target = db.query(User).filter(User.email == "user0@test.com").first()
        response = client.put(
            f"/api/v1/admin/users/{target.id}/status",
            json={"is_admin": True},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["is_admin"] is True

    def test_cannot_modify_self_admin(self):
        """Admin cannot modify their own admin status."""
        with Session(bind=engine) as db:
            admin = db.query(User).filter(User.email == "admintest2@test.com").first()
        response = client.put(
            f"/api/v1/admin/users/{admin.id}/status",
            json={"is_admin": False},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert response.status_code == 400

    def test_delete_user(self):
        """Admin can delete a user."""
        with Session(bind=engine) as db:
            target = db.query(User).filter(User.email == "user1@test.com").first()
        response = client.delete(
            f"/api/v1/admin/users/{target.id}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert response.status_code == 200
        # Verify user is gone
        response2 = client.get(f"/api/v1/admin/users/{target.id}", headers={"Authorization": f"Bearer {self.token}"})
        assert response2.status_code == 404

    def test_cannot_delete_self(self):
        """Admin cannot delete their own account."""
        with Session(bind=engine) as db:
            admin = db.query(User).filter(User.email == "admintest2@test.com").first()
        response = client.delete(
            f"/api/v1/admin/users/{admin.id}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert response.status_code == 400


class TestAdminStats:
    """Test admin stats endpoints."""

    def setup_method(self):
        """Create admin token for testing."""
        auth = AuthService()
        with Session(bind=engine) as db:
            admin = User(username="admintest3", email="admintest3@test.com")
            admin.password_hash = auth.hash_password("admintestpass")
            admin.is_admin = True
            db.add(admin)
            db.commit()
            db.refresh(admin)
            self.token = auth.create_access_token(data={"sub": str(admin.id)})

    def test_stats_overview(self):
        """Admin can get stats overview."""
        response = client.get("/api/v1/admin/stats/overview", headers={"Authorization": f"Bearer {self.token}"})
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "total_tutorials" in data
        assert "pending_tutorials" in data

    def test_stats_users(self):
        """Admin can get user stats."""
        response = client.get("/api/v1/admin/stats/users?period=7d", headers={"Authorization": f"Bearer {self.token}"})
        assert response.status_code == 200
        data = response.json()
        assert "growth" in data
        assert "period" in data

    def test_stats_tutorials(self):
        """Admin can get tutorial stats."""
        response = client.get("/api/v1/admin/stats/tutorials?period=7d", headers={"Authorization": f"Bearer {self.token}"})
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_status" in data
```

- [ ] **Step 2: Run tests**

```bash
cd src/backend && python -m pytest tests/test_admin.py -v
```
Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/backend/tests/test_admin.py
git commit -m "test: add admin API tests for login, users, and stats"
```

---

## Task 4: Dark Mode — ThemeContext + Tailwind Config

**Files:**
- Create: `src/frontend/src/contexts/ThemeContext.tsx`
- Modify: `src/frontend/tailwind.config.js`
- Modify: `src/frontend/src/App.tsx`

**Interfaces:**
- Produces: `ThemeProvider` wrapping the app, `useTheme()` hook returning `{ theme, toggleTheme }`
- `ThemeContextType` interface: `{ theme: 'light' | 'dark', toggleTheme: () => void }`

- [ ] **Step 1: Update Tailwind config for dark mode**

Open `src/frontend/tailwind.config.js`. Add `darkMode: "class"` to the config:
```javascript
module.exports = {
  darkMode: 'class',
  content: [
    './src/**/*.{js,jsx,ts,tsx}',
    './public/index.html',
  ],
  // ... rest unchanged
}
```

- [ ] **Step 2: Create ThemeContext**

Create `src/frontend/src/contexts/ThemeContext.tsx`:
```tsx
import React, { createContext, useContext, useEffect, useState } from 'react';

type Theme = 'light' | 'dark';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | null>(null);

const THEME_KEY = 'theme';

function getInitialTheme(): Theme {
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === 'dark' || stored === 'light') return stored;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setTheme] = useState<Theme>(getInitialTheme);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
};
```

- [ ] **Step 3: Wrap App with ThemeProvider**

Open `src/frontend/src/App.tsx`. Add imports:
```typescript
import { ThemeProvider } from './contexts/ThemeContext';
import { useTheme } from './contexts/ThemeContext';
```

Wrap the entire return JSX with `<ThemeProvider>`:
```tsx
return (
  <ThemeProvider>
    <GlobalErrorHandler>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </GlobalErrorHandler>
  </ThemeProvider>
);
```

Also add a theme toggle button in the header. Create a new component inline or extract it. Add after the logout button:
```tsx
<ThemeToggle />
```

Where `ThemeToggle` is defined as:
```tsx
const ThemeToggle = () => {
  const { theme, toggleTheme } = useTheme();
  return (
    <button
      onClick={toggleTheme}
      className="w-9 h-9 rounded-xl flex items-center justify-center text-lg transition-all hover:bg-gray-100 dark:hover:bg-gray-700"
      title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
    >
      {theme === 'dark' ? '☀️' : '🌙'}
    </button>
  );
};
```

- [ ] **Step 4: Add dark: variants to key UI elements in App.tsx**

Update the main wrapper div to support dark mode:
```tsx
<div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
```

Update header glass effect:
```tsx
<header className="sticky top-0 z-40 glass border-b border-white/30 dark:border-gray-700 shadow-sm">
```

Update NavLink:
```tsx
<button onClick={() => navigate(href)} className="flex items-center space-x-2 px-4 py-2 text-gray-600 dark:text-gray-300 hover:text-primary-600 dark:hover:text-primary-400 hover:bg-primary-50 dark:hover:bg-gray-700 rounded-xl transition-all">
```

- [ ] **Step 5: Build frontend to verify**

```bash
cd src/frontend && npm run build
```
Expected: Compiled successfully. 239+ kB

- [ ] **Step 6: Commit**

```bash
git add src/frontend/tailwind.config.js src/frontend/src/contexts/ThemeContext.tsx src/frontend/src/App.tsx
git commit -m "feat: add dark mode with ThemeContext and Tailwind dark: class strategy"
```

---

## Task 5: Frontend Admin API Client + Types

**Files:**
- Modify: `src/frontend/src/types.ts`
- Modify: `src/frontend/src/api/client.ts`

**Interfaces:**
- Consumes: existing `User` type
- Produces: updated `User` with `is_admin` field, new API methods on `ApiClient`

- [ ] **Step 1: Update User type**

Open `src/frontend/src/types.ts`. Update the `User` interface:
```typescript
export interface User {
  id: string;
  username: string;
  email: string;
  created_at: string;
  is_admin: boolean;
}
```

- [ ] **Step 2: Add admin API methods to client**

Open `src/frontend/src/api/client.ts`. Add these methods to the `ApiClient` class:

```typescript
// Admin endpoints
async adminLogin(email: string, password: string) {
  return this.request<any>('POST', '/api/v1/admin/login', { email, password });
}

async adminMe() {
  return this.request<any>('GET', '/api/v1/admin/me');
}

async adminListUsers(page = 1, limit = 20, search?: string) {
  let url = `/api/v1/admin/users?page=${page}&limit=${limit}`;
  if (search) url += `&search=${encodeURIComponent(search)}`;
  return this.request<any>('GET', url);
}

async adminGetUser(userId: string) {
  return this.request<any>('GET', `/api/v1/admin/users/${userId}`);
}

async adminUpdateUserStatus(userId: string, data: { is_admin: boolean }) {
  return this.request<any>('PUT', `/api/v1/admin/users/${userId}/status`, data);
}

async adminDeleteUser(userId: string) {
  return this.request<any>('DELETE', `/api/v1/admin/users/${userId}`);
}

async adminListPendingTutorials(page = 1, limit = 20) {
  return this.request<any>('GET', `/api/v1/admin/catalog/pending?page=${page}&limit=${limit}`);
}

async adminReviewTutorial(tutorialId: string, action: string, reason?: string) {
  return this.request<any>('PUT', `/api/v1/admin/catalog/${tutorialId}/review`, { action, reason });
}

async adminGetStatsOverview() {
  return this.request<any>('GET', '/api/v1/admin/stats/overview');
}

async adminGetUserStats(period = '30d') {
  return this.request<any>('GET', `/api/v1/admin/stats/users?period=${period}`);
}

async adminGetTutorialStats(period = '30d') {
  return this.request<any>('GET', `/api/v1/admin/stats/tutorials?period=${period}`);
}
```

- [ ] **Step 3: Build frontend to verify**

```bash
cd src/frontend && npm run build
```
Expected: Compiled successfully with no type errors

- [ ] **Step 4: Commit**

```bash
git add src/frontend/src/types.ts src/frontend/src/api/client.ts
git commit -m "feat: add admin API client methods and update User type with is_admin"
```

---

## Task 6: Admin Guard + Admin Login Page

**Files:**
- Create: `src/frontend/src/components/AdminGuard.tsx`
- Create: `src/frontend/src/pages/AdminLoginPage.tsx`
- Modify: `src/frontend/src/App.tsx`

**Interfaces:**
- Consumes: `api.adminLogin`, `api.adminMe`, `api.setToken`
- Produces: `AdminGuard` component that checks `is_admin` and redirects non-admins

- [ ] **Step 1: Create AdminGuard component**

Create `src/frontend/src/components/AdminGuard.tsx`:
```tsx
import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { api } from '../api/client';

interface AdminGuardProps {
  children: React.ReactNode;
}

const AdminGuard = ({ children }: AdminGuardProps) => {
  const location = useLocation();
  const [checking, setChecking] = useState(true);
  const [isAuthorized, setIsAuthorized] = useState(false);

  useEffect(() => {
    const check = async () => {
      const token = localStorage.getItem('auth_token');
      if (!token) {
        setChecking(false);
        return;
      }
      try {
        const result = await api.adminMe();
        if (result.success && result.data?.user?.is_admin) {
          setIsAuthorized(true);
        } else {
          setIsAuthorized(false);
        }
      } catch {
        setIsAuthorized(false);
      } finally {
        setChecking(false);
      }
    };
    check();
  }, []);

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="relative w-12 h-12 mx-auto mb-4">
            <div className="absolute inset-0 border-4 border-primary-200 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-primary-600 rounded-full border-t-transparent animate-spin"></div>
          </div>
          <p className="text-gray-500">Checking admin access...</p>
        </div>
      </div>
    );
  }

  if (!isAuthorized) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

export default AdminGuard;
```

- [ ] **Step 2: Create AdminLoginPage**

Create `src/frontend/src/pages/AdminLoginPage.tsx`:
```tsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../hooks/useToast';

const AdminLoginPage = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const result = await api.adminLogin(email, password);
      if (!result.success) throw new Error(result.error || 'Admin login failed');
      if (result.data?.token) api.setToken(result.data.token);
      toast.success('Admin login successful!');
      navigate('/admin');
    } catch (err: any) {
      setError(err.message || 'Admin login failed');
      toast.error(err.message || 'Admin login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-md p-8">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-br from-red-500 to-orange-500 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <span className="text-3xl">🛡️</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Admin Panel</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Sign in to manage the platform</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
              placeholder="admin@example.com"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
              placeholder="••••••••"
              required
            />
          </div>

          {error && (
            <div className="text-red-500 text-sm text-center bg-red-50 dark:bg-red-900/20 rounded-lg p-3">{error}</div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-red-500 to-orange-500 text-white rounded-xl font-medium hover:from-red-600 hover:to-orange-600 transition-all disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign In as Admin'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button onClick={() => navigate('/login')} className="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600">
            ← Back to regular login
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdminLoginPage;
```

- [ ] **Step 3: Add admin routes to App.tsx**

Open `src/frontend/src/App.tsx`. Add imports:
```typescript
import AdminLoginPage from './pages/AdminLoginPage';
import AdminGuard from './components/AdminGuard';
import AdminDashboardPage from './pages/AdminDashboardPage';
import AdminUsersPage from './pages/AdminUsersPage';
import AdminCatalogPage from './pages/AdminCatalogPage';
```

In the `user` (logged in) routes section, add after the profile route:
```tsx
<Route path="/admin/login" element={<AdminLoginPage />} />
<Route
  path="/admin"
  element={
    <AdminGuard>
      <AdminDashboardPage />
    </AdminGuard>
  }
/>
<Route
  path="/admin/users"
  element={
    <AdminGuard>
      <AdminUsersPage />
    </AdminGuard>
  }
/>
<Route
  path="/admin/catalog"
  element={
    <AdminGuard>
      <AdminCatalogPage />
    </AdminGuard>
  }
/>
```

In the header navigation, add an admin link (only visible to admins — we'll handle that in the pages themselves for now):
```tsx
<NavLink href="/admin" icon="🛡️" label="Admin" />
```

- [ ] **Step 4: Build frontend to verify**

```bash
cd src/frontend && npm run build
```
Expected: Compiled successfully

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/components/AdminGuard.tsx src/frontend/src/pages/AdminLoginPage.tsx src/frontend/src/App.tsx
git commit -m "feat: add AdminGuard, AdminLoginPage, and admin routes to App.tsx"
```

---

## Task 7: Admin Dashboard + Users Page + Catalog Page

**Files:**
- Create: `src/frontend/src/pages/AdminDashboardPage.tsx`
- Create: `src/frontend/src/pages/AdminUsersPage.tsx`
- Create: `src/frontend/src/pages/AdminCatalogPage.tsx`

**Interfaces:**
- Consumes: `api.admin*` methods, `useToast()`, `useTheme()`, `useNavigate()`
- Produces: three admin pages with full CRUD interaction

- [ ] **Step 1: Create AdminDashboardPage**

Create `src/frontend/src/pages/AdminDashboardPage.tsx`:
```tsx
import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../hooks/useToast';
import { useTheme } from '../contexts/ThemeContext';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';

const AdminDashboardPage = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const { theme, toggleTheme } = useTheme();
  const [stats, setStats] = useState<any>(null);
  const [userGrowth, setUserGrowth] = useState<any[]>([]);
  const [tutorialStats, setTutorialStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const [statsRes, userRes, tutorialRes] = await Promise.all([
        api.adminGetStatsOverview(),
        api.adminGetUserStats('30d'),
        api.adminGetTutorialStats('30d'),
      ]);
      if (statsRes.success) setStats(statsRes.data);
      if (userRes.success) setUserGrowth(userRes.data?.growth || []);
      if (tutorialRes.success) setTutorialStats(tutorialRes.data);
    } catch {
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
      </div>
    );
  }

  const statCards = [
    { label: 'Total Users', value: stats?.total_users ?? 0, icon: '👥', color: 'from-blue-500 to-cyan-500' },
    { label: 'Total Tutorials', value: stats?.total_tutorials ?? 0, icon: '📚', color: 'from-purple-500 to-pink-500' },
    { label: 'Published', value: stats?.published_tutorials ?? 0, icon: '✅', color: 'from-green-500 to-emerald-500' },
    { label: 'Pending Review', value: stats?.pending_tutorials ?? 0, icon: '⏳', color: 'from-yellow-500 to-orange-500' },
    { label: 'New (7 days)', value: stats?.new_users_last_7_days ?? 0, icon: '📈', color: 'from-indigo-500 to-violet-500' },
    { label: 'Published (month)', value: stats?.published_this_month ?? 0, icon: '🆕', color: 'from-rose-500 to-red-500' },
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Admin Dashboard</h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Platform overview and statistics</p>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={toggleTheme} className="w-9 h-9 rounded-xl flex items-center justify-center text-lg hover:bg-gray-100 dark:hover:bg-gray-700">
                {theme === 'dark' ? '☀️' : '🌙'}
              </button>
              <Link to="/admin/users" className="px-4 py-2 bg-primary-600 text-white rounded-xl hover:bg-primary-700 text-sm font-medium">
                Manage Users
              </Link>
              <Link to="/admin/catalog" className="px-4 py-2 bg-purple-600 text-white rounded-xl hover:bg-purple-700 text-sm font-medium">
                Review Tutorials
              </Link>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Stat Cards */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
          {statCards.map((card) => (
            <div key={card.label} className={`bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-soft border border-gray-100 dark:border-gray-700`}>
              <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${card.color} flex items-center justify-center text-xl mb-3`}>
                {card.icon}
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">{card.value}</div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">{card.label}</div>
            </div>
          ))}
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* User Growth */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-soft border border-gray-100 dark:border-gray-700">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">User Growth (30 days)</h3>
            {userGrowth.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={userGrowth}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} tickLine={false} />
                  <YAxis tick={{ fontSize: 12 }} tickLine={false} />
                  <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)' }} />
                  <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-64 flex items-center justify-center text-gray-400">No data</div>
            )}
          </div>

          {/* Tutorial Stats */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-soft border border-gray-100 dark:border-gray-700">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Tutorial Status Distribution</h3>
            {tutorialStats && (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={Object.entries(tutorialStats.by_status ?? {}).map(([k, v]) => ({ name: k, value: v }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} tickLine={false} />
                  <YAxis tick={{ fontSize: 12 }} tickLine={false} />
                  <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)' }} />
                  <Bar dataKey="value" fill="#8b5cf6" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboardPage;
```

- [ ] **Step 2: Create AdminUsersPage**

Create `src/frontend/src/pages/AdminUsersPage.tsx`:
```tsx
import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../hooks/useToast';
import { useTheme } from '../contexts/ThemeContext';
import { User } from '../types';

const AdminUsersPage = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const { theme, toggleTheme } = useTheme();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalUsers, setTotalUsers] = useState(0);

  useEffect(() => {
    loadUsers();
  }, [page, search]);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const result = await api.adminListUsers(page, 20, search || undefined);
      if (result.success && result.data) {
        setUsers(result.data.data || []);
        setTotalPages(result.data.pagination?.pages || 1);
        setTotalUsers(result.data.pagination?.total || 0);
      }
    } catch {
      toast.error('Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleAdmin = async (user: User) => {
    try {
      const result = await api.adminUpdateUserStatus(user.id, { is_admin: !user.is_admin });
      if (result.success) {
        toast.success(`User ${user.is_admin ? 'removed from' : 'added to'} admin`);
        loadUsers();
      }
    } catch {
      toast.error('Failed to update user status');
    }
  };

  const handleDeleteUser = async (user: User) => {
    if (!window.confirm(`Delete user "${user.username}"? This cannot be undone.`)) return;
    try {
      const result = await api.adminDeleteUser(user.id);
      if (result.success) {
        toast.success('User deleted');
        loadUsers();
      }
    } catch {
      toast.error('Failed to delete user');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">User Management</h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{totalUsers} total users</p>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={toggleTheme} className="w-9 h-9 rounded-xl flex items-center justify-center text-lg hover:bg-gray-100 dark:hover:bg-gray-700">
                {theme === 'dark' ? '☀️' : '🌙'}
              </button>
              <Link to="/admin" className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-xl hover:bg-gray-200 dark:hover:bg-gray-600 text-sm font-medium">
                ← Dashboard
              </Link>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Search */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-soft border border-gray-100 dark:border-gray-700 mb-6">
          <input
            type="text"
            placeholder="Search by username or email..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="w-full px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 outline-none"
          />
        </div>

        {/* Users Table */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-soft border border-gray-100 dark:border-gray-700 overflow-hidden">
          {loading ? (
            <div className="p-12 text-center">
              <div className="w-10 h-10 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin mx-auto"></div>
            </div>
          ) : users.length === 0 ? (
            <div className="p-12 text-center text-gray-400">No users found</div>
          ) : (
            <>
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-100 dark:border-gray-700">
                    <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">User</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Email</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Joined</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Admin</th>
                    <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.id} className="border-b border-gray-50 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-750">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-white text-sm font-bold">
                            {user.username[0].toUpperCase()}
                          </div>
                          <span className="font-medium text-gray-900 dark:text-white">{user.username}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">{user.email}</td>
                      <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                        {new Date(user.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          user.is_admin
                            ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                            : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
                        }`}>
                          {user.is_admin ? 'Admin' : 'User'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleToggleAdmin(user)}
                            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-primary-50 text-primary-600 hover:bg-primary-100 dark:bg-primary-900/20 dark:text-primary-400 dark:hover:bg-primary-900/30"
                          >
                            {user.is_admin ? 'Remove Admin' : 'Make Admin'}
                          </button>
                          <button
                            onClick={() => handleDeleteUser(user)}
                            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400 dark:hover:bg-red-900/30"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between px-6 py-4 border-t border-gray-100 dark:border-gray-700">
                  <span className="text-sm text-gray-500 dark:text-gray-400">Page {page} of {totalPages}</span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                    >
                      Previous
                    </button>
                    <button
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                      className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminUsersPage;
```

- [ ] **Step 3: Create AdminCatalogPage**

Create `src/frontend/src/pages/AdminCatalogPage.tsx`:
```tsx
import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../hooks/useToast';
import { useTheme } from '../contexts/ThemeContext';

interface PendingTutorial {
  id: string;
  title: string;
  description?: string;
  owner_id: string;
  status: string;
  total_chapters?: number;
  view_count?: number;
  like_count?: number;
  reported_count?: number;
  created_at: string;
}

const AdminCatalogPage = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const { theme, toggleTheme } = useTheme();
  const [tutorials, setTutorials] = useState<PendingTutorial[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [reviewingId, setReviewingId] = useState<string | null>(null);

  useEffect(() => {
    loadTutorials();
  }, [page]);

  const loadTutorials = async () => {
    setLoading(true);
    try {
      const result = await api.adminListPendingTutorials(page, 20);
      if (result.success && result.data) {
        setTutorials(result.data.data || []);
        setTotalPages(result.data.pagination?.pages || 1);
        setTotalItems(result.data.pagination?.total || 0);
      }
    } catch {
      toast.error('Failed to load pending tutorials');
    } finally {
      setLoading(false);
    }
  };

  const handleReview = async (tutorialId: string, action: 'approve' | 'reject') => {
    setReviewingId(tutorialId);
    try {
      const reason = action === 'reject'
        ? prompt('Enter rejection reason (optional):') || ''
        : '';
      const result = await api.adminReviewTutorial(tutorialId, action, reason || undefined);
      if (result.success) {
        toast.success(`Tutorial ${action}d successfully`);
        loadTutorials();
      } else {
        toast.error(result.error || 'Failed to review tutorial');
      }
    } catch (e: any) {
      toast.error(e.message || 'Failed to review tutorial');
    } finally {
      setReviewingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Tutorial Review</h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{totalItems} tutorials pending review</p>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={toggleTheme} className="w-9 h-9 rounded-xl flex items-center justify-center text-lg hover:bg-gray-100 dark:hover:bg-gray-700">
                {theme === 'dark' ? '☀️' : '🌙'}
              </button>
              <Link to="/admin" className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-xl hover:bg-gray-200 dark:hover:bg-gray-600 text-sm font-medium">
                ← Dashboard
              </Link>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
          </div>
        ) : tutorials.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-12 text-center shadow-soft border border-gray-100 dark:border-gray-700">
            <div className="text-5xl mb-4">🎉</div>
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">All caught up!</h3>
            <p className="text-gray-500 dark:text-gray-400 mt-2">No tutorials pending review.</p>
          </div>
        ) : (
          <>
            <div className="space-y-4">
              {tutorials.map((tutorial) => (
                <div key={tutorial.id} className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-soft border border-gray-100 dark:border-gray-700">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="text-lg font-bold text-gray-900 dark:text-white">{tutorial.title}</h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                        {tutorial.description || 'No description'}
                      </p>
                      <div className="flex items-center gap-4 mt-3 text-xs text-gray-400 dark:text-gray-500">
                        <span>👤 Owner: {tutorial.owner_id.slice(0, 8)}...</span>
                        <span>📖 {tutorial.total_chapters || 0} chapters</span>
                        <span>👁️ {tutorial.view_count || 0} views</span>
                        <span>❤️ {tutorial.like_count || 0} likes</span>
                        {tutorial.reported_count && tutorial.reported_count > 0 && (
                          <span className="text-red-500">⚠️ {tutorial.reported_count} reports</span>
                        )}
                        <span>📅 {new Date(tutorial.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <div className="flex gap-2 ml-4">
                      <button
                        onClick={() => handleReview(tutorial.id, 'approve')}
                        disabled={reviewingId === tutorial.id}
                        className="px-4 py-2 bg-green-500 text-white rounded-xl hover:bg-green-600 text-sm font-medium disabled:opacity-50"
                      >
                        {reviewingId === tutorial.id ? '...' : '✓ Approve'}
                      </button>
                      <button
                        onClick={() => handleReview(tutorial.id, 'reject')}
                        disabled={reviewingId === tutorial.id}
                        className="px-4 py-2 bg-red-500 text-white rounded-xl hover:bg-red-600 text-sm font-medium disabled:opacity-50"
                      >
                        {reviewingId === tutorial.id ? '...' : '✗ Reject'}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-6">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-4 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                >
                  Previous
                </button>
                <span className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-4 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default AdminCatalogPage;
```

- [ ] **Step 4: Build frontend to verify**

```bash
cd src/frontend && npm run build
```
Expected: Compiled successfully

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/pages/AdminDashboardPage.tsx src/frontend/src/pages/AdminUsersPage.tsx src/frontend/src/pages/AdminCatalogPage.tsx
git commit -m "feat: add admin dashboard, user management, and tutorial review pages"
```

---

## Task 8: Seed Admin User + Final Verification

**Files:**
- Create: `src/backend/src/init_admin.py` (seed script)
- Run: database migration + admin seeding
- Verify: end-to-end build and test

**Interfaces:**
- Consumes: `User` model, `AuthService`
- Produces: an admin user account with `is_admin=True` for testing

- [ ] **Step 1: Create admin seed script**

Create `src/backend/src/init_admin.py`:
```python
"""Script to initialize an admin user for the platform."""

from src.database import engine, Base, get_session
from src.models.user import User
from src.services.auth_service import AuthService
import os

DEFAULT_ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@tlcw.com")
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
DEFAULT_ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")


def create_admin_user():
    """Create or update the default admin user."""
    db = get_session()
    auth = AuthService()

    # Check if admin already exists
    admin = db.query(User).filter_by(email=DEFAULT_ADMIN_EMAIL).first()
    if admin:
        admin.is_admin = True
        admin.password_hash = auth.hash_password(DEFAULT_ADMIN_PASSWORD)
        print(f"Updated existing admin: {admin.email}")
    else:
        admin = User(
            username=DEFAULT_ADMIN_USERNAME,
            email=DEFAULT_ADMIN_EMAIL,
            is_admin=True,
        )
        admin.password_hash = auth.hash_password(DEFAULT_ADMIN_PASSWORD)
        db.add(admin)
        print(f"Created admin user: {admin.email}")

    db.commit()
    db.close()
    print(f"Admin ready: {DEFAULT_ADMIN_EMAIL} / {DEFAULT_ADMIN_PASSWORD}")


if __name__ == "__main__":
    create_admin_user()
```

- [ ] **Step 2: Run migration and seed admin**

```bash
cd src/backend && python -c "from src.database import migrate_db; migrate_db()"
python -m src.init_admin
```
Expected: "Created admin user: admin@tlcw.com" and "Admin ready: admin@tlcw.com / admin123"

- [ ] **Step 3: Run all backend tests**

```bash
cd src/backend && python -m pytest tests/ -v --tb=short 2>&1 | tail -40
```
Expected: all new tests pass, no regressions

- [ ] **Step 4: Final frontend build**

```bash
cd src/frontend && npm run build
```
Expected: Compiled successfully, 239+ kB

- [ ] **Step 5: Final commit**

```bash
git add src/backend/src/init_admin.py
git commit -m "feat: add admin seed script and finalize P2 setup"
```
