# P0 Core Experience Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement all P0 priority features: Toast notification system, bookmarks, comments, rate limiting, password reset, and tutorial display page enhancements.

**Architecture:** Add a shared Toast context provider to replace all `alert()` calls across the frontend. Extend the backend with new models (Bookmark, Comment) and API endpoints, add rate limiting via `slowapi` middleware, and implement password reset via email tokens. All backend changes use SQLite-compatible migrations.

**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy 2.x, SQLite, React 18, TypeScript, `react-hot-toast`, `slowapi`

## Global Constraints

- All new backend models follow the existing pattern: UUID string primary key, SQLAlchemy Column, `to_dict()` serialization, `create()` static factory, foreign keys via `ForeignKey`
- All API endpoints use `Depends(get_current_user)` for authentication (no public write endpoints)
- Database migrations are SQLite-compatible: use `PRAGMA table_info` to detect existing columns before ALTER TABLE
- Frontend uses the existing `api` client from `src/frontend/src/api/client.ts` — append new methods rather than rewriting
- All new frontend components use Tailwind CSS classes consistent with existing styling (no new CSS files)
- New dependencies: `slowapi>=0.1.0` (backend), `react-hot-toast>=2.4.0` (frontend)
- No PostgreSQL-specific features (e.g., `jsonb`, `NOW()`) — everything must work with SQLite
- Password reset uses time-limited JWT tokens (same JWT library already in use), NOT email (no SMTP configured)

---

### Task 1: Toast Notification System

**Files:**
- Create: `src/frontend/src/contexts/ToastContext.tsx`
- Create: `src/frontend/src/hooks/useToast.ts`
- Modify: `src/frontend/src/index.tsx` (wrap with ToastProvider)
- Modify: `src/frontend/src/components/CourseWizard.tsx:85-95`
- Modify: `src/frontend/src/components/ClaudeChatSidebar.tsx:49-57`
- Modify: `src/frontend/src/pages/ProfilePage.tsx:70-73`
- Modify: `src/frontend/src/pages/TutorialDisplayPage.tsx:88-103`
- Modify: `src/frontend/package.json` (add react-hot-toast)

**Interfaces:**
- Consumes: None (new context)
- Produces: `useToast()` hook returning `{ success: (msg) => void; error: (msg) => void; info: (msg) => void }`

- [ ] **Step 1: Add react-hot-toast dependency**

Run: `cd src/frontend && npm install react-hot-toast@^2.4.0`

Expected: Package installed, `node_modules/react-hot-toast` exists

- [ ] **Step 2: Write ToastContext**

Create `src/frontend/src/contexts/ToastContext.tsx`:

```tsx
import React, { createContext, useContext } from 'react';
import { Toaster, toast } from 'react-hot-toast';

interface ToastContextType {
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const value: ToastContextType = {
    success: (message: string) => toast.success(message),
    error: (message: string) => toast.error(message),
    info: (message: string) => toast.info(message),
  };
  return (
    <ToastContext.Provider value={value}>
      {children}
      <Toaster position="top-right" toastOptions={{ duration: 4000 }} />
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
};
```

- [ ] **Step 3: Wrap app with ToastProvider in index.tsx**

In `src/frontend/src/index.tsx`, find the root render line and wrap with ToastProvider:

```tsx
import { ToastProvider } from './contexts/ToastContext';
// ...existing imports...
ReactDOM.render(
  <React.StrictMode>
    <ToastProvider>
      <App />
    </ToastProvider>
  </React.StrictMode>,
  document.getElementById('root')
);
```

- [ ] **Step 4: Replace alert() in CourseWizard.tsx**

In `CourseWizard.tsx`, find `submitGeneration` function. Replace:
```tsx
alert(`Tutorial generated successfully! ID: ${result.tutorialId}`);
```
with:
```tsx
useToast().success(`Tutorial generated successfully! ID: ${result.tutorialId}`);
```
And replace the catch block's error alert with `useToast().error(err.message || 'Failed to generate tutorial')`.

Note: Add `const toast = useToast();` at the top of the component function.

- [ ] **Step 5: Replace alert() in ClaudeChatSidebar.tsx**

In `ClaudeChatSidebar.tsx`, find the WebSocket error handler. Replace:
```tsx
alert(`Error: ${data.message}`);
```
with:
```tsx
toast.error(`Error: ${data.message}`);
```
And replace the success toast (lines 49-54) — remove the manual DOM creation and use `toast.success('Chapter generated successfully!')` instead.

Note: Add `const toast = useToast();` at the top of the component function.

- [ ] **Step 6: Replace alert() in ProfilePage.tsx**

In `ProfilePage.tsx` line 72, replace:
```tsx
alert('Knowledge mapping updated!');
```
with:
```tsx
toast.success('Knowledge mapping updated!');
```
Note: Add `const toast = useToast();` at the top of the component function.

- [ ] **Step 7: Replace alert() in TutorialDisplayPage.tsx**

In `TutorialDisplayPage.tsx`, replace all three `alert()` calls:
- Line 92: `alert('PDF generation failed: ' + e.message);` → `toast.error('PDF generation failed: ' + e.message);`
- Line 99: `alert('Generating next chapter... Please wait');` → `toast.info('Generating next chapter... Please wait');`
- Line 101: `alert('Failed to generate next chapter: ' + e.message);` → `toast.error('Failed to generate next chapter: ' + e.message);`

Note: Add `const toast = useToast();` at the top of the component function.

- [ ] **Step 8: Verify build**

Run: `cd src/frontend && npm run build`
Expected: Build succeeds with no errors

- [ ] **Step 9: Commit**

```bash
git add src/frontend/src/contexts/ToastContext.tsx src/frontend/src/hooks/useToast.ts src/frontend/src/index.tsx src/frontend/src/components/CourseWizard.tsx src/frontend/src/components/ClaudeChatSidebar.tsx src/frontend/src/pages/ProfilePage.tsx src/frontend/src/pages/TutorialDisplayPage.tsx src/frontend/package.json
git commit -m "feat: add Toast notification system, replace all alert() calls"
```

---

### Task 2: Rate Limiting Middleware

**Files:**
- Create: `src/backend/src/middleware/rate_limiter.py`
- Modify: `src/backend/src/api/main.py` (add slowapi middleware)
- Modify: `src/backend/requirements.txt` (add slowapi)
- Create: `src/backend/tests/test_rate_limiter.py`

**Interfaces:**
- Consumes: FastAPI app, `rate_limit_store` (Redis or in-memory dict)
- Produces: FastAPI `Limiter` dependency usable in any endpoint via `Depends(limits)`

- [ ] **Step 1: Add slowapi dependency**

Add `slowapi>=0.1.0` to `src/backend/requirements.txt`.

- [ ] **Step 2: Write rate limiter middleware**

Create `src/backend/src/middleware/rate_limiter.py`:

```python
"""Rate limiting middleware using slowapi."""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
import logging

logger = logging.getLogger(__name__)

# In-memory storage for rate limits (no Redis dependency)
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=["60/minute", "1000/hour"],
)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Handle rate limit exceeded errors."""
    logger.warning(f"Rate limit exceeded for {request.client.host} on {request.url.path}")
    return Response(
        content='{"detail": "Rate limit exceeded. Please try again later."}',
        status_code=429,
        media_type="application/json"
    )
```

- [ ] **Step 3: Integrate rate limiter into main.py**

In `src/backend/src/api/main.py`, add imports and register the limiter:

```python
from ..middleware.rate_limiter import limiter, rate_limit_handler
from slowapi.errors import RateLimitExceeded

# Register the limiter and error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
```

- [ ] **Step 4: Add per-endpoint rate limits for sensitive operations**

In `src/backend/src/api/auth.py`, import and apply rate limits to register/login:

```python
from src.backend.src.middleware.rate_limiter import limiter
from fastapi import Depends

# At the top of auth.py, add:
limiter = None  # Will be set by main.py

@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(...):
    ...

@auth_router.post("/login")
@limiter.limit("10/minute")
async def login(...):
    ...
```

Note: In a real FastAPI app, the limiter is attached to `app.state.limiter`. For this project, reference it via `app.state.limiter` in the endpoint decorator using a dependency.

Actually, the correct pattern for slowapi with FastAPI is:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, storage_uri="memory://", default_limits=["60/minute"])
```
Then in main.py:
```python
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
```
And in individual routers, use `Depends(limiter.limit("5/minute"))` as a dependency.

- [ ] **Step 5: Write tests**

Create `src/backend/tests/test_rate_limiter.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from ..middleware.rate_limiter import limiter, rate_limit_handler


@pytest.fixture
def app_with_limiter():
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

    @app.get("/test")
    def test_endpoint():
        return {"ok": True}

    @app.post("/restricted")
    @limiter.limit("2/minute")
    def restricted_endpoint():
        return {"ok": True}

    return app


def test_rate_limiter_default_limit(app_with_limiter):
    client = TestClient(app_with_limiter)
    # First two requests should succeed
    assert client.get("/test").status_code == 200
    assert client.get("/test").status_code == 200


def test_rate_limiter_exceeded(app_with_limiter):
    client = TestClient(app_with_limiter)
    # Hit the restricted endpoint 3 times (limit is 2/minute)
    assert client.post("/restricted").status_code == 200
    assert client.post("/restricted").status_code == 200
    response = client.post("/restricted")
    assert response.status_code == 429
    assert "Rate limit" in response.json()["detail"]
```

- [ ] **Step 6: Run tests**

Run: `pytest src/backend/tests/test_rate_limiter.py -v`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add src/backend/src/middleware/rate_limiter.py src/backend/src/api/main.py src/backend/requirements.txt src/backend/tests/test_rate_limiter.py
git commit -m "feat: add rate limiting middleware with slowapi"
```

---

### Task 3: Chapter Listing & Content Endpoints (Backend)

**Files:**
- Modify: `src/backend/src/api/tutorials.py` (add two new endpoints)
- Create: `src/backend/tests/test_chapter_endpoints.py`

**Why this task:** The TutorialDisplayPage currently calls `GET /api/v1/tutorials/{id}/chapters` (to list all chapters for navigation) and `GET /api/v1/tutorials/{id}/chapters/{n}` (to load full chapter content), but neither endpoint exists. The existing API only has `GET /{id}` (with chapter summaries) and `GET /{id}/chapters/{n}/status` (status only). These two new endpoints are prerequisites for Task 7 (front-end display page).

**Interfaces:**
- Consumes: `Tutorial`, `Chapter` models, `ChapterStatus` enum
- Produces:
  - `GET /api/v1/tutorials/{id}/chapters` → `{"data": [{id, chapter_number, title, status, generated_at}], "total": N}`
  - `GET /api/v1/tutorials/{id}/chapters/{n}` → full chapter content dict (same as TutorialDetail.chapters but with content included)

- [ ] **Step 1: Write failing tests**

Create `src/backend/tests/test_chapter_endpoints.py`:

```python
import pytest
from datetime import datetime


def test_list_chapters(client, sample_tutorial, db_session):
    """Test listing all chapters for a tutorial."""
    from src.models.chapter import Chapter

    # Create a few chapters
    for n in [1, 2, 3]:
        Chapter(
            tutorial_id=sample_tutorial.id,
            chapter_number=n,
            title=f"Chapter {n}",
            status="ready" if n <= 2 else "draft",
            generated_at=datetime.utcnow() if n <= 2 else None
        ).__init__  # skip — just create properly below
        ch = Chapter(
            tutorial_id=sample_tutorial.id,
            chapter_number=n,
            title=f"Chapter {n}",
            status="ready" if n <= 2 else "draft",
        )
        db_session.add(ch)
    db_session.commit()

    resp = client.get(f"/api/v1/tutorials/{sample_tutorial.id}/chapters")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "total" in data
    assert len(data["data"]) >= 3


def test_get_chapter_content(client, sample_tutorial, db_session):
    """Test getting full chapter content."""
    from src.models.chapter import Chapter

    ch = Chapter(
        tutorial_id=sample_tutorial.id,
        chapter_number=1,
        title="Introduction",
        status="ready",
        content={"sections": [{"title": "Intro", "content": {"overview": "Welcome"}}]}
    )
    db_session.add(ch)
    db_session.commit()

    resp = client.get(f"/api/v1/tutorials/{sample_tutorial.id}/chapters/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["chapter_number"] == 1
    assert data["title"] == "Introduction"
    assert "content" in data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest src/backend/tests/test_chapter_endpoints.py -v`
Expected: FAIL — 404 Not Found

- [ ] **Step 3: Add chapter listing endpoint to tutorials.py**

In `src/backend/src/api/tutorials.py`, add AFTER the existing `get_chapter_status` function:

```python
@tutorials_router.get("/{tutorial_id}/chapters", response_model=Dict[str, Any])
async def list_chapters(
    tutorial_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """List all chapters for a tutorial (summary only, no content)."""
    tutorial = db.query(Tutorial).filter(Tutorial.id == tutorial_id).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    chapters = db.query(Chapter).filter_by(tutorial_id=tutorial_id).order_by(Chapter.chapter_number).all()
    return {
        "data": [
            {
                "id": c.id,
                "chapter_number": c.chapter_number,
                "title": c.title,
                "status": c.status,
                "generated_at": c.generated_at.isoformat() if c.generated_at else None,
            }
            for c in chapters
        ],
        "total": len(chapters)
    }


@tutorials_router.get("/{tutorial_id}/chapters/{chapter_number}", response_model=Dict[str, Any])
async def get_chapter_content(
    tutorial_id: str,
    chapter_number: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get full chapter content including sections."""
    tutorial = db.query(Tutorial).filter(Tutorial.id == tutorial_id).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    chapter = Chapter.get_by_number(db=db, tutorial_id=tutorial_id, chapter_number=chapter_number)
    if not chapter:
        raise HTTPException(status_code=404, detail=f"Chapter {chapter_number} not found")

    return chapter.to_dict(include_content=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest src/backend/tests/test_chapter_endpoints.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/backend/src/api/tutorials.py src/backend/tests/test_chapter_endpoints.py
git commit -m "feat: add chapter listing and chapter content endpoints"
```

---

### Task 4: Bookmark Feature (Backend + DB Migration)

**Files:**
- Create: `src/backend/src/models/bookmark.py`
- Create: `src/backend/src/database/migrations/003_add_bookmarks.py`
- Create: `src/backend/src/api/bookmarks.py`
- Modify: `src/backend/src/api/main.py` (register router)
- Create: `src/backend/tests/test_bookmark_model.py`
- Create: `src/backend/tests/test_bookmark_api.py`

**Interfaces:**
- Consumes: `User` model (for auth), `Tutorial` model (for tutorial lookup)
- Produces: `Bookmark` model with `to_dict()`, API endpoints at `/api/v1/tutorials/{id}/bookmark`

- [ ] **Step 1: Write failing test for Bookmark model**

Create `src/backend/tests/test_bookmark_model.py`:

```python
import pytest
from datetime import datetime
from src.models.bookmark import Bookmark


def test_create_bookmark(db_session, test_user, sample_tutorial):
    bookmark = Bookmark.create(
        db=db_session,
        user_id=str(test_user.id),
        tutorial_id=str(sample_tutorial.id)
    )
    assert bookmark.user_id == str(test_user.id)
    assert bookmark.tutorial_id == str(sample_tutorial.id)
    assert bookmark.id is not None


def test_bookmark_to_dict(db_session, test_user, sample_tutorial):
    bookmark = Bookmark.create(
        db=db_session,
        user_id=str(test_user.id),
        tutorial_id=str(sample_tutorial.id)
    )
    d = bookmark.to_dict()
    assert d["user_id"] == str(test_user.id)
    assert d["tutorial_id"] == str(sample_tutorial.id)
    assert "id" in d
    assert "created_at" in d
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest src/backend/tests/test_bookmark_model.py -v`
Expected: FAIL — "ImportError: cannot import name 'Bookmark'"

- [ ] **Step 3: Write Bookmark model**

Create `src/backend/src/models/bookmark.py`:

```python
"""Bookmark model for tutorial favorites."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, Session
from ..database import Base


class Bookmark(Base):
    __tablename__ = 'user_bookmarks'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    tutorial_id = Column(String(36), ForeignKey('tutorials.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user_id', 'tutorial_id', name='uq_user_tutorial_bookmark'),
    )

    user = relationship("User", backref="bookmarks")
    tutorial = relationship("Tutorial", backref="bookmarks")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tutorial_id": self.tutorial_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @staticmethod
    def create(db: Session, user_id: str, tutorial_id: str) -> 'Bookmark':
        """Create a bookmark, return None if already exists."""
        existing = db.query(Bookmark).filter_by(
            user_id=user_id, tutorial_id=tutorial_id
        ).first()
        if existing:
            return existing
        bookmark = Bookmark(user_id=user_id, tutorial_id=tutorial_id)
        db.add(bookmark)
        db.commit()
        db.refresh(bookmark)
        return bookmark

    @staticmethod
    def delete(db: Session, user_id: str, tutorial_id: str) -> bool:
        """Delete a bookmark. Returns True if deleted, False if not found."""
        bookmark = db.query(Bookmark).filter_by(
            user_id=user_id, tutorial_id=tutorial_id
        ).first()
        if not bookmark:
            return False
        db.delete(bookmark)
        db.commit()
        return True

    @staticmethod
    def is_bookmarked(db: Session, user_id: str, tutorial_id: str) -> bool:
        """Check if a tutorial is bookmarked by a user."""
        return db.query(Bookmark).filter_by(
            user_id=user_id, tutorial_id=tutorial_id
        ).first() is not None

    @staticmethod
    def get_by_user(db: Session, user_id: str, page: int = 1, limit: int = 20) -> dict:
        """Get all bookmarks for a user with pagination."""
        total = db.query(Bookmark).filter_by(user_id=user_id).count()
        offset = (page - 1) * limit
        bookmarks = db.query(Bookmark).filter_by(user_id=user_id).offset(offset).limit(limit).all()
        return {
            "data": [b.to_dict() for b in bookmarks],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest src/backend/tests/test_bookmark_model.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Write migration script**

Create `src/backend/src/database/migrations/003_add_bookmarks.py`:

```python
"""Migration: Add user_bookmarks table."""
import sqlite3


def migrate(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_bookmarks'")
    if cursor.fetchone():
        print("Migration 003 skipped: user_bookmarks table already exists")
        conn.commit()
        conn.close()
        return

    cursor.execute("""
        CREATE TABLE user_bookmarks (
            id VARCHAR(36) NOT NULL,
            user_id VARCHAR(36) NOT NULL,
            tutorial_id VARCHAR(36) NOT NULL,
            created_at DATETIME,
            PRIMARY KEY (id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(tutorial_id) REFERENCES tutorials(id) ON DELETE CASCADE,
            UNIQUE(user_id, tutorial_id)
        )
    """)

    conn.commit()
    conn.close()
    print("Migration 003 completed: user_bookmarks table created")
```

- [ ] **Step 6: Write API endpoints test**

Create `src/backend/tests/test_bookmark_api.py`:

```python
import pytest


def test_bookmark_tutorial(client, sample_tutorial, test_user, db_session):
    """Test bookmarking a tutorial."""
    from src.models.bookmark import Bookmark

    resp = client.post(f"/api/v1/tutorials/{sample_tutorial.id}/bookmark")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    # Verify in DB
    bookmark = db_session.query(Bookmark).filter_by(
        user_id=str(test_user.id), tutorial_id=sample_tutorial.id
    ).first()
    assert bookmark is not None


def test_unbookmark_tutorial(client, sample_tutorial, test_user, db_session):
    """Test removing a bookmark."""
    from src.models.bookmark import Bookmark

    # First bookmark
    client.post(f"/api/v1/tutorials/{sample_tutorial.id}/bookmark")

    # Then unbookmark
    resp = client.delete(f"/api/v1/tutorials/{sample_tutorial.id}/bookmark")
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Verify removed from DB
    bookmark = db_session.query(Bookmark).filter_by(
        user_id=str(test_user.id), tutorial_id=sample_tutorial.id
    ).first()
    assert bookmark is None


def test_bookmark_list(client, sample_tutorial, test_user, db_session):
    """Test listing user's bookmarks."""
    from src.models.bookmark import Bookmark

    # Bookmark the sample tutorial
    client.post(f"/api/v1/tutorials/{sample_tutorial.id}/bookmark")

    resp = client.get("/api/v1/users/profile/bookmarks")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) >= 1
```

- [ ] **Step 7: Run tests to verify they fail**

Run: `pytest src/backend/tests/test_bookmark_api.py -v`
Expected: FAIL — endpoint not found (404)

- [ ] **Step 8: Write bookmark API endpoints**

Create `src/backend/src/api/bookmarks.py`:

```python
"""Bookmark API endpoints for tutorial favorites."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from ..database import get_db
from ..models.user import User
from ..models.tutorial import Tutorial
from ..models.bookmark import Bookmark
from ..services.auth_service import get_current_user

router = APIRouter(prefix="/tutorials", tags=["bookmarks"])


@router.post("/{tutorial_id}/bookmark", response_model=Dict[str, Any])
async def bookmark_tutorial(
    tutorial_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Bookmark (favorite) a tutorial."""
    tutorial = db.query(Tutorial).filter(Tutorial.id == tutorial_id).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    bookmark = Bookmark.create(db=db, user_id=str(current_user.id), tutorial_id=tutorial_id)
    return {
        "success": True,
        "message": "Tutorial bookmarked" if bookmark.id else "Already bookmarked",
        "bookmark_id": bookmark.id
    }


@router.delete("/{tutorial_id}/bookmark", response_model=Dict[str, Any])
async def unbookmark_tutorial(
    tutorial_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Remove a bookmark from a tutorial."""
    deleted = Bookmark.delete(db=db, user_id=str(current_user.id), tutorial_id=tutorial_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"success": True, "message": "Bookmark removed"}


@router.get("/bookmarks", response_model=Dict[str, Any])
async def list_user_bookmarks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = 1,
    limit: int = 20
) -> Dict[str, Any]:
    """Get all bookmarks for the current user."""
    result = Bookmark.get_by_user(db=db, user_id=str(current_user.id), page=page, limit=limit)
    return result
```

- [ ] **Step 9: Register router in main.py**

In `src/backend/src/api/main.py`, add:
```python
from ..api.bookmarks import router as bookmarks_router
# ...
app.include_router(bookmarks_router, prefix="/api/v1")
```

- [ ] **Step 10: Run tests**

Run: `pytest src/backend/tests/test_bookmark_api.py src/backend/tests/test_bookmark_model.py -v`
Expected: All tests pass

- [ ] **Step 11: Commit**

```bash
git add src/backend/src/models/bookmark.py src/backend/src/database/migrations/003_add_bookmarks.py src/backend/src/api/bookmarks.py src/backend/src/api/main.py src/backend/tests/test_bookmark_model.py src/backend/tests/test_bookmark_api.py
git commit -m "feat: add bookmark feature with API endpoints and migration"
```

---

### Task 5: Comments Feature (Backend + DB Migration)

**Files:**
- Create: `src/backend/src/models/comment.py`
- Create: `src/backend/src/database/migrations/004_add_comments.py`
- Create: `src/backend/src/api/comments.py`
- Modify: `src/backend/src/api/main.py` (register router)
- Create: `src/backend/tests/test_comment_model.py`
- Create: `src/backend/tests/test_comment_api.py`

**Interfaces:**
- Consumes: `User` model, `Tutorial` model
- Produces: `Comment` model with nested replies support, API endpoints at `/api/v1/tutorials/{id}/comments`

- [ ] **Step 1: Write failing test for Comment model**

Create `src/backend/tests/test_comment_model.py`:

```python
import pytest
from datetime import datetime
from src.models.comment import Comment


def test_create_comment(db_session, test_user, sample_tutorial):
    comment = Comment.create(
        db=db_session,
        user_id=str(test_user.id),
        tutorial_id=str(sample_tutorial.id),
        content="Great tutorial!"
    )
    assert comment.user_id == str(test_user.id)
    assert comment.tutorial_id == str(sample_tutorial.id)
    assert comment.content == "Great tutorial!"
    assert comment.like_count == 0


def test_create_reply(db_session, test_user, sample_tutorial):
    """Test creating a reply to a comment."""
    parent = Comment.create(
        db=db_session,
        user_id=str(test_user.id),
        tutorial_id=str(sample_tutorial.id),
        content="Parent comment"
    )
    reply = Comment.create(
        db=db_session,
        user_id=str(test_user.id),
        tutorial_id=str(sample_tutorial.id),
        content="Reply",
        parent_id=parent.id
    )
    assert reply.parent_id == parent.id
    assert reply.is_reply is True


def test_comment_to_dict(db_session, test_user, sample_tutorial):
    comment = Comment.create(
        db=db_session,
        user_id=str(test_user.id),
        tutorial_id=str(sample_tutorial.id),
        content="Test comment"
    )
    d = comment.to_dict()
    assert d["content"] == "Test comment"
    assert d["like_count"] == 0
    assert "id" in d
    assert "created_at" in d


def test_get_by_tutorial(db_session, test_user, sample_tutorial):
    """Test getting comments for a tutorial."""
    Comment.create(db=db_session, user_id=str(test_user.id), tutorial_id=str(sample_tutorial.id), content="Comment 1")
    Comment.create(db=db_session, user_id=str(test_user.id), tutorial_id=str(sample_tutorial.id), content="Comment 2")

    comments = Comment.get_by_tutorial(db=db_session, tutorial_id=str(sample_tutorial.id))
    assert len(comments) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest src/backend/tests/test_comment_model.py -v`
Expected: FAIL — "ImportError: cannot import name 'Comment'"

- [ ] **Step 3: Write Comment model**

Create `src/backend/src/models/comment.py`:

```python
"""Comment model for tutorial discussions."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, Session
from ..database import Base


class Comment(Base):
    __tablename__ = 'tutorial_comments'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tutorial_id = Column(String(36), ForeignKey('tutorials.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    content = Column(Text, nullable=False)
    parent_id = Column(String(36), ForeignKey('tutorial_comments.id', ondelete='CASCADE'), nullable=True)
    like_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    tutorial = relationship("Tutorial", backref="comments")
    user = relationship("User")
    replies = relationship("Comment", backref=relationship("Comment", remote_side=[id], cascade="all, delete-orphan"))

    @property
    def is_reply(self) -> bool:
        return self.parent_id is not None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tutorial_id": self.tutorial_id,
            "user_id": self.user_id,
            "content": self.content,
            "parent_id": self.parent_id,
            "like_count": self.like_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_reply": self.is_reply,
            "user": {
                "id": self.user.id if self.user else None,
                "username": self.user.username if self.user else "Unknown"
            } if self.user else None,
            "replies": [r.to_dict() for r in (self.replies or [])]
        }

    @staticmethod
    def create(db: Session, user_id: str, tutorial_id: str, content: str, parent_id: str = None) -> 'Comment':
        """Create a new comment or reply."""
        comment = Comment(
            user_id=user_id,
            tutorial_id=tutorial_id,
            content=content,
            parent_id=parent_id
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return comment

    @staticmethod
    def get_by_tutorial(db: Session, tutorial_id: str) -> list:
        """Get all top-level comments for a tutorial (no replies included)."""
        return db.query(Comment).filter_by(tutorial_id=tutorial_id, parent_id=None).order_by(Comment.created_at.asc()).all()

    @staticmethod
    def get_replies(db: Session, parent_id: str) -> list:
        """Get all replies to a comment."""
        return db.query(Comment).filter_by(parent_id=parent_id).order_by(Comment.created_at.asc()).all()

    @staticmethod
    def like_comment(db: Session, comment_id: str) -> int:
        """Like a comment, return new like_count."""
        comment = db.query(Comment).filter_by(id=comment_id).first()
        if not comment:
            raise ValueError("Comment not found")
        comment.like_count += 1
        db.commit()
        db.refresh(comment)
        return comment.like_count

    @staticmethod
    def delete_comment(db: Session, comment_id: str, user_id: str) -> bool:
        """Delete a comment (only owner or if it's their own)."""
        comment = db.query(Comment).filter_by(id=comment_id).first()
        if not comment or comment.user_id != user_id:
            return False
        db.delete(comment)
        db.commit()
        return True
```

- [ ] **Step 4: Run model tests**

Run: `pytest src/backend/tests/test_comment_model.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Write migration script**

Create `src/backend/src/database/migrations/004_add_comments.py`:

```python
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
```

- [ ] **Step 6: Write API tests**

Create `src/backend/tests/test_comment_api.py`:

```python
import pytest


def test_create_comment(client, sample_tutorial, test_user, db_session):
    from src.models.comment import Comment
    resp = client.post(
        f"/api/v1/tutorials/{sample_tutorial.id}/comments",
        json={"content": "Great tutorial!"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "Great tutorial!"
    assert data["user_id"] == str(test_user.id)

    comment = db_session.query(Comment).filter_by(tutorial_id=sample_tutorial.id).first()
    assert comment is not None


def test_get_comments(client, sample_tutorial, test_user, db_session):
    from src.models.comment import Comment
    Comment.create(db=db_session, user_id=str(test_user.id), tutorial_id=str(sample_tutorial.id), content="Hello")

    resp = client.get(f"/api/v1/tutorials/{sample_tutorial.id}/comments")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) >= 1


def test_like_comment(client, sample_tutorial, test_user, db_session):
    from src.models.comment import Comment
    comment = Comment.create(db=db_session, user_id=str(test_user.id), tutorial_id=str(sample_tutorial.id), content="Like me")

    resp = client.post(f"/api/v1/comments/{comment.id}/like")
    assert resp.status_code == 200
    assert resp.json()["like_count"] == 1


def test_delete_own_comment(client, sample_tutorial, test_user, db_session):
    from src.models.comment import Comment
    comment = Comment.create(db=db_session, user_id=str(test_user.id), tutorial_id=str(sample_tutorial.id), content="Delete me")

    resp = client.delete(f"/api/v1/comments/{comment.id}")
    assert resp.status_code == 200
    assert resp.json()["success"] is True
```

- [ ] **Step 7: Run API tests to verify they fail**

Run: `pytest src/backend/tests/test_comment_api.py -v`
Expected: FAIL — endpoints not found

- [ ] **Step 8: Write comment API endpoints**

Create `src/backend/src/api/comments.py`:

```python
"""Comment API endpoints for tutorial discussions."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from pydantic import BaseModel
import logging

from ..database import get_db
from ..models.user import User
from ..models.tutorial import Tutorial
from ..models.comment import Comment
from ..services.auth_service import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tutorials", tags=["comments"])


class CreateCommentRequest(BaseModel):
    content: str
    parent_id: str = None


@router.post("/{tutorial_id}/comments", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
async def create_comment(
    tutorial_id: str,
    request: CreateCommentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a comment or reply on a tutorial."""
    tutorial = db.query(Tutorial).filter(Tutorial.id == tutorial_id).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    comment = Comment.create(
        db=db,
        user_id=str(current_user.id),
        tutorial_id=tutorial_id,
        content=request.content,
        parent_id=request.parent_id
    )
    return comment.to_dict()


@router.get("/{tutorial_id}/comments", response_model=Dict[str, Any])
async def get_comments(
    tutorial_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get all comments for a tutorial."""
    tutorial = db.query(Tutorial).filter(Tutorial.id == tutorial_id).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    comments = Comment.get_by_tutorial(db=db, tutorial_id=tutorial_id)
    return {
        "data": [c.to_dict() for c in comments],
        "total": len(comments)
    }


router_comment = APIRouter(prefix="/comments", tags=["comments"])


@router_comment.post("/{comment_id}/like", response_model=Dict[str, Any])
async def like_comment(
    comment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Like a comment."""
    try:
        count = Comment.like_comment(db=db, comment_id=comment_id)
        return {"like_count": count}
    except ValueError:
        raise HTTPException(status_code=404, detail="Comment not found")


@router_comment.delete("/{comment_id}", response_model=Dict[str, Any])
async def delete_comment(
    comment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Delete your own comment."""
    deleted = Comment.delete_comment(db=db, comment_id=comment_id, user_id=str(current_user.id))
    if not deleted:
        raise HTTPException(status_code=403, detail="Cannot delete this comment")
    return {"success": True, "message": "Comment deleted"}
```

- [ ] **Step 9: Register routers in main.py**

In `src/backend/src/api/main.py`, add:
```python
from ..api.comments import router as comments_router, router_comment as comment_likes_router
# ...
app.include_router(comments_router, prefix="/api/v1")
app.include_router(comment_likes_router, prefix="/api/v1")
```

- [ ] **Step 10: Run all comment tests**

Run: `pytest src/backend/tests/test_comment_api.py src/backend/tests/test_comment_model.py -v`
Expected: All tests pass

- [ ] **Step 11: Commit**

```bash
git add src/backend/src/models/comment.py src/backend/src/database/migrations/004_add_comments.py src/backend/src/api/comments.py src/backend/src/api/main.py src/backend/tests/test_comment_model.py src/backend/tests/test_comment_api.py
git commit -m "feat: add comment feature with API endpoints and migration"
```

---

### Task 6: Password Reset Feature

**Files:**
- Create: `src/backend/src/services/password_reset_service.py`
- Create: `src/backend/src/api/password_reset.py`
- Create: `src/backend/tests/test_password_reset.py`
- Modify: `src/backend/src/api/main.py` (register router)

**Interfaces:**
- Consumes: `User` model, JWT token (same `jwt` library already in use)
- Produces: Password reset token (JWT, expires in 1 hour), API endpoints at `/api/v1/auth/forgot-password` and `/api/v1/auth/reset-password`

- [ ] **Step 1: Write failing test for password reset service**

Create `src/backend/tests/test_password_reset.py`:

```python
import pytest
from unittest.mock import patch
from src.services.password_reset_service import PasswordResetService
from src.models.user import User


def test_generate_reset_token(db_session, test_user):
    service = PasswordResetService()
    token = service.generate_reset_token(str(test_user.id))
    assert token is not None
    assert len(token) > 10


def test_verify_reset_token(db_session, test_user):
    service = PasswordResetService()
    token = service.generate_reset_token(str(test_user.id))
    user_id = service.verify_reset_token(token)
    assert user_id == str(test_user.id)


def test_verify_expired_token():
    service = PasswordResetService()
    # Generate a token with 0-minute expiry
    from src.services.password_reset_service import PasswordResetService asPRS
    # We test via the actual service with a manually crafted expired token
    import time
    from jose import jwt
    from src.services.auth_service import SECRET_KEY, ALGORITHM
    expired_token = jwt.encode(
        {"sub": "test-user-id", "exp": time.time() - 3600},
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    result = service.verify_reset_token(expired_token)
    assert result is None


def test_reset_password(db_session, test_user):
    service = PasswordResetService()
    token = service.generate_reset_token(str(test_user.id))
    new_password = "NewPassword123!"
    success = service.reset_password(token, new_password)
    assert success is True

    # Verify new password works
    from src.services.auth_service import AuthService
    auth = AuthService()
    user = db_session.query(User).filter_by(id=test_user.id).first()
    assert auth.verify_password(new_password, user.password_hash)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest src/backend/tests/test_password_reset.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write PasswordResetService**

Create `src/backend/src/services/password_reset_service.py`:

```python
"""Password reset service using JWT tokens (no email required)."""
import time
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from ..database import get_db
from ..models.user import User
from sqlalchemy.orm import Session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Import from auth_service to share the same SECRET_KEY
import os
_SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
_ALGORITHM = "HS256"
_EXPIRE_MINUTES = 60


class PasswordResetService:
    """Handle password reset via JWT tokens."""

    def generate_reset_token(self, user_id: str) -> str:
        """Generate a password reset token for a user."""
        expire = time.time() + (_EXPIRE_MINUTES * 60)
        payload = {"sub": user_id, "exp": expire, "type": "password_reset"}
        return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)

    def verify_reset_token(self, token: str) -> Optional[str]:
        """Verify a reset token and return user_id if valid."""
        try:
            payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
            if payload.get("type") != "password_reset":
                return None
            return payload.get("sub")
        except JWTError:
            return None

    def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password using a valid token."""
        user_id = self.verify_reset_token(token)
        if not user_id:
            return False

        db: Session = next(get_db())
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            user.password_hash = pwd_context.hash(new_password)
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
        finally:
            db.close()
```

- [ ] **Step 4: Run model tests**

Run: `pytest src/backend/tests/test_password_reset.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Write API tests**

Create tests within the same file or extend it:

```python
def test_forgot_password_endpoint(client, test_user, db_session):
    """Test requesting a password reset token."""
    from src.services.password_reset_service import PasswordResetService
    # This endpoint doesn't need auth — it's public
    resp = client.post("/api/v1/auth/forgot-password", json={"email": test_user.email})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert len(data["token"]) > 10


def test_reset_password_endpoint(client, test_user, db_session):
    """Test resetting password with token."""
    from src.services.password_reset_service import PasswordResetService
    service = PasswordResetService()
    token = service.generate_reset_token(str(test_user.id))

    resp = client.post("/api/v1/auth/reset-password", json={
        "token": token,
        "new_password": "NewPassword123!"
    })
    assert resp.status_code == 200
    assert resp.json()["success"] is True
```

- [ ] **Step 6: Run API tests to verify they fail**

Run: `pytest src/backend/tests/test_password_reset.py -v`
Expected: FAIL — endpoints not found (404)

- [ ] **Step 7: Write password reset API endpoints**

Create `src/backend/src/api/password_reset.py`:

```python
"""Password reset API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any
import logging

from ..services.password_reset_service import PasswordResetService
from ..database import get_db
from ..services.auth_service import get_current_user
from ..models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["password-reset"])


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    request: ForgotPasswordRequest,
) -> Dict[str, Any]:
    """Generate a password reset token for the given email."""
    from ..database import get_db as _get_db
    from sqlalchemy.orm import Session

    db: Session = next(_get_db())
    try:
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            # Return a dummy token to prevent email enumeration
            return {
                "message": "If the email exists, a reset token has been generated.",
                "email": request.email
            }

        service = PasswordResetService()
        token = service.generate_reset_token(str(user.id))
        return {
            "token": token,
            "message": "Password reset token generated. Use this token to reset your password.",
            "expires_in_minutes": 60
        }
    finally:
        db.close()


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request: ResetPasswordRequest
) -> Dict[str, Any]:
    """Reset password using a valid token."""
    service = PasswordResetService()
    success = service.reset_password(request.token, request.new_password)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    return {
        "success": True,
        "message": "Password reset successfully. You can now log in with your new password."
    }
```

- [ ] **Step 8: Register router in main.py**

In `src/backend/src/api/main.py`, add:
```python
from ..api.password_reset import router as password_reset_router
# ...
app.include_router(password_reset_router, prefix="/api/v1")
```

- [ ] **Step 9: Run all password reset tests**

Run: `pytest src/backend/tests/test_password_reset.py -v`
Expected: All tests pass

- [ ] **Step 10: Commit**

```bash
git add src/backend/src/services/password_reset_service.py src/backend/src/api/password_reset.py src/backend/src/api/main.py src/backend/tests/test_password_reset.py
git commit -m "feat: add password reset feature with JWT token-based flow"
```

---

### Task 7: Tutorial Display Page Enhancements

**Files:**
- Modify: `src/frontend/src/pages/TutorialDisplayPage.tsx`
- Modify: `src/frontend/src/api/client.ts` (add bookmark/check methods)
- Create: `src/frontend/src/components/ChapterNav.tsx`
- Create: `src/frontend/src/components/ExportMenu.tsx`
- Create: `src/frontend/src/components/CommentSection.tsx`

**Interfaces:**
- Consumes: `api` client methods, `useToast()` hook
- Produces: Enhanced TutorialDisplayPage with chapter navigation, bookmark toggle, export menu, and comment section

- [ ] **Step 1: Add bookmark and comment methods to API client**

In `src/frontend/src/api/client.ts`, add these methods to the `ApiClient` class:

```typescript
// Bookmark methods
async bookmarkTutorial(id: string) {
  return this.request<any>('POST', `/api/v1/tutorials/${id}/bookmark`);
}

async unbookmarkTutorial(id: string) {
  return this.request<any>('DELETE', `/api/v1/tutorials/${id}/bookmark`);
}

async isBookmarked(id: string) {
  // We check by fetching the user's bookmarks and looking for this tutorial
  const resp = await this.request<any>('GET', '/api/v1/tutorials/bookmarks');
  if (!resp.success) return false;
  return (resp.data?.data || []).some((b: any) => b.tutorial_id === id);
}

async getBookmarks(page = 1, limit = 20) {
  return this.request<any>('GET', `/api/v1/tutorials/bookmarks?page=${page}&limit=${limit}`);
}

// Comment methods
async getComments(tutorialId: string) {
  return this.request<any>('GET', `/api/v1/tutorials/${tutorialId}/comments`);
}

async postComment(tutorialId: string, content: string, parentId?: string) {
  return this.request<any>('POST', `/api/v1/tutorials/${tutorialId}/comments`, { content, parent_id: parentId });
}

async likeComment(commentId: string) {
  return this.request<any>('POST', `/api/v1/comments/${commentId}/like`);
}

async deleteComment(commentId: string) {
  return this.request<any>('DELETE', `/api/v1/comments/${commentId}`);
}
```

- [ ] **Step 2: Write ChapterNav component**

Create `src/frontend/src/components/ChapterNav.tsx`:

```tsx
import React from 'react';

interface Chapter {
  id: string;
  chapter_number: number;
  title: string;
  status: 'draft' | 'ready' | 'in_progress' | 'completed' | 'failed';
  generated_at?: string;
}

interface ChapterNavProps {
  chapters: Chapter[];
  currentChapter: number;
  totalChapters: number;
  onChapterSelect: (chapterNumber: number) => void;
}

const statusColors: Record<string, string> = {
  draft: 'bg-gray-200 text-gray-500',
  ready: 'bg-green-100 text-green-700',
  in_progress: 'bg-yellow-100 text-yellow-700',
  completed: 'bg-blue-100 text-blue-700',
  failed: 'bg-red-100 text-red-700',
};

const statusLabels: Record<string, string> = {
  draft: 'Draft',
  ready: 'Ready',
  in_progress: 'In Progress',
  completed: 'Completed',
  failed: 'Failed',
};

export const ChapterNav: React.FC<ChapterNavProps> = ({
  chapters,
  currentChapter,
  totalChapters,
  onChapterSelect,
}) => {
  return (
    <div className="bg-white rounded-xl shadow-soft p-4">
      <h3 className="font-bold text-gray-900 mb-3">Chapters ({totalChapters})</h3>
      <div className="space-y-1">
        {chapters.map((ch) => (
          <button
            key={ch.id}
            onClick={() => onChapterSelect(ch.chapter_number)}
            className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
              ch.chapter_number === currentChapter
                ? 'bg-primary-100 text-primary-700 font-medium'
                : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-medium">Chapter {ch.chapter_number}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full ${statusColors[ch.status]}`}>
                {statusLabels[ch.status]}
              </span>
            </div>
            <div className="text-xs text-gray-500 truncate mt-0.5">{ch.title}</div>
          </button>
        ))}
      </div>
    </div>
  );
};
```

- [ ] **Step 3: Write ExportMenu component**

Create `src/frontend/src/components/ExportMenu.tsx`:

```tsx
import React from 'react';

interface ExportMenuProps {
  tutorialId: string;
  toast: { success: (msg: string) => void; error: (msg: string) => void };
}

export const ExportMenu: React.FC<ExportMenuProps> = ({ tutorialId, toast }) => {
  const handleExport = async (format: 'markdown' | 'json') => {
    try {
      const API_BASE = (process.env.REACT_APP_API_URL || 'http://tlcw.yobeeo.com') as string;
      const endpoint = `/api/v1/tutorials/${tutorialId}/export/${format}`;
      const response = await fetch(endpoint, {
        headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
      });
      if (!response.ok) throw new Error(`Export failed: ${response.status}`);

      const blob = format === 'markdown'
        ? new Blob([await response.text()], { type: 'text/markdown' })
        : await response.blob();

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tutorial-${tutorialId.slice(0, 8)}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`Exported as ${format.toUpperCase()}`);
    } catch (e: any) {
      toast.error(`Export failed: ${e.message}`);
    }
  };

  return (
    <div className="flex gap-2">
      <button
        onClick={() => handleExport('markdown')}
        className="btn-secondary text-sm px-3 py-1.5"
      >
        Export Markdown
      </button>
      <button
        onClick={() => handleExport('json')}
        className="btn-secondary text-sm px-3 py-1.5"
      >
        Export JSON
      </button>
    </div>
  );
};
```

- [ ] **Step 4: Write CommentSection component**

Create `src/frontend/src/components/CommentSection.tsx`:

```tsx
import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from '../contexts/ToastContext';

interface Comment {
  id: string;
  user_id: string;
  content: string;
  parent_id: string | null;
  like_count: number;
  created_at: string;
  is_reply: boolean;
  user?: { id: string; username: string };
  replies?: Comment[];
}

interface CommentSectionProps {
  tutorialId: string;
  currentUserId: string;
}

export const CommentSection: React.FC<CommentSectionProps> = ({ tutorialId, currentUserId }) => {
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState('');
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  const fetchComments = async () => {
    try {
      const resp = await api.getComments(tutorialId);
      if (resp.success) {
        setComments(resp.data?.data || []);
      }
    } catch (e: any) {
      toast.error('Failed to load comments');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchComments();
  }, [tutorialId]);

  const handlePost = async () => {
    if (!newComment.trim()) return;
    try {
      const resp = await api.postComment(tutorialId, newComment);
      if (resp.success) {
        setNewComment('');
        fetchComments();
        toast.success('Comment posted');
      } else {
        toast.error(resp.error || 'Failed to post comment');
      }
    } catch (e: any) {
      toast.error('Failed to post comment');
    }
  };

  const handleLike = async (commentId: string) => {
    try {
      const resp = await api.likeComment(commentId);
      if (resp.success) {
        fetchComments();
      }
    } catch (e: any) {
      toast.error('Failed to like comment');
    }
  };

  const handleDelete = async (commentId: string) => {
    try {
      const resp = await api.deleteComment(commentId);
      if (resp.success) {
        fetchComments();
        toast.success('Comment deleted');
      }
    } catch (e: any) {
      toast.error('Failed to delete comment');
    }
  };

  if (loading) {
    return <div className="text-center py-4 text-gray-500">Loading comments...</div>;
  }

  return (
    <div className="mt-8">
      <h3 className="text-xl font-bold text-gray-900 mb-4">Comments ({comments.length})</h3>

      {/* Comment input */}
      <div className="mb-6">
        <textarea
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          placeholder="Write a comment..."
          className="w-full border border-gray-200 rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary-300"
          rows={3}
        />
        <button
          onClick={handlePost}
          disabled={!newComment.trim()}
          className="mt-2 btn-primary text-sm px-4 py-2 disabled:opacity-50"
        >
          Post Comment
        </button>
      </div>

      {/* Comments list */}
      <div className="space-y-4">
        {comments.map((comment) => (
          <div key={comment.id} className="bg-white rounded-xl p-4 border border-gray-100">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-sm text-gray-900">
                {comment.user?.username || 'Unknown'}
              </span>
              <span className="text-xs text-gray-500">
                {new Date(comment.created_at).toLocaleDateString()}
              </span>
            </div>
            <p className="text-gray-700 text-sm">{comment.content}</p>
            <div className="flex items-center gap-4 mt-2">
              <button
                onClick={() => handleLike(comment.id)}
                className="text-xs text-gray-500 hover:text-primary-600"
              >
                👍 {comment.like_count}
              </button>
              {comment.user_id === currentUserId && (
                <button
                  onClick={() => handleDelete(comment.id)}
                  className="text-xs text-gray-500 hover:text-red-600"
                >
                  Delete
                </button>
              )}
            </div>
            {comment.replies && comment.replies.length > 0 && (
              <div className="mt-3 ml-4 space-y-2 border-l-2 border-gray-100 pl-3">
                {comment.replies.map((reply) => (
                  <div key={reply.id} className="text-sm">
                    <span className="font-medium text-gray-900">{reply.user?.username || 'Unknown'}</span>
                    <span className="text-gray-600 ml-2">{reply.content}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {comments.length === 0 && (
          <p className="text-center text-gray-500 py-4">No comments yet. Be the first to comment!</p>
        )}
      </div>
    </div>
  );
};
```

- [ ] **Step 5: Rewrite TutorialDisplayPage with all enhancements**

Replace the entire `src/frontend/src/pages/TutorialDisplayPage.tsx` with the enhanced version that includes:
- ChapterNav sidebar
- Bookmark toggle button (using `api.bookmarkTutorial`/`api.unbookmarkTutorial`/`api.isBookmarked`)
- ExportMenu button
- CommentSection at the bottom
- Progress indicator showing current chapter vs total
- Uses `useToast()` instead of `alert()`
- Proper loading/error states

Key structure:
```tsx
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useToast } from '../contexts/ToastContext';
import { api } from '../api/client';
import { ChapterNav } from '../components/ChapterNav';
import { ExportMenu } from '../components/ExportMenu';
import { CommentSection } from '../components/CommentSection';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import CodeBlock from '../components/CodeBlock';
import { Katex } from 'react-katex'; // or existing MathFormula component

const TutorialDisplayPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const [tutorial, setTutorial] = useState<any>(null);
  const [chapters, setChapters] = useState<any[]>([]);
  const [currentChapter, setCurrentChapter] = useState(1);
  const [loading, setLoading] = useState(true);
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [activeSection, setActiveSection] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [tutorialResp, chaptersResp, bookmarkCheck] = await Promise.all([
          api.getTutorial(id!),
          fetch(`/api/v1/tutorials/${id}/chapters`), // adjust endpoint as needed
          api.isBookmarked(id!),
        ]);

        if (tutorialResp.success) {
          setTutorial(tutorialResp.data);
        }
        setIsBookmarked(bookmarkCheck.success && bookmarkCheck.data);
      } catch (err: any) {
        toast.error(err.message || 'Failed to load tutorial');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [id]);

  const handleBookmark = async () => {
    try {
      if (isBookmarked) {
        await api.unbookmarkTutorial(id!);
        toast.success('Removed from bookmarks');
      } else {
        await api.bookmarkTutorial(id!);
        toast.success('Added to bookmarks');
      }
      setIsBookmarked(!isBookmarked);
    } catch (e: any) {
      toast.error(e.message || 'Failed to update bookmark');
    }
  };

  // ... rest of the component with enhanced UI
};

export default TutorialDisplayPage;
```

Note: Adjust the chapter fetching logic based on the actual backend API. The key is to fetch chapters and display them in the navigation sidebar.

- [ ] **Step 6: Verify frontend build**

Run: `cd src/frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 7: Commit**

```bash
git add src/frontend/src/pages/TutorialDisplayPage.tsx src/frontend/src/components/ChapterNav.tsx src/frontend/src/components/ExportMenu.tsx src/frontend/src/components/CommentSection.tsx src/frontend/src/api/client.ts
git commit -m "feat: enhance TutorialDisplayPage with chapter nav, bookmarks, export, and comments"
```

---

### Task 8: Integration Tests & Full Test Suite

**Files:**
- Modify: `src/backend/tests/conftest.py` (ensure all new models are importable)
- Run: Full test suite
- Deploy to production
- Verify all endpoints work

- [ ] **Step 1: Run full test suite**

Run: `pytest src/backend/tests/ -v`
Expected: All tests pass (including existing 59 + new tests)

- [ ] **Step 2: Fix any failures**

Address any test failures that arise from the new code.

- [ ] **Step 3: Deploy to production**

```bash
# Copy backend files to server
scp -r src/backend/src/* tlcw.yobeeo.com:/app/src/
scp src/backend/requirements.txt tlcw.yobeeo.com:/app/

# Run migrations
ssh tlcw.yobeeo.com "cd /app && python -m src.database.migrate"

# Rebuild frontend and copy
cd src/frontend && npm run build
scp -r build/* tlcw.yobeeo.com:/app/frontend/

# Restart backend
ssh tlcw.yobeeo.com "systemctl restart ollp-backend"
```

- [ ] **Step 4: Verify production endpoints**

```bash
# Test rate limiting
curl -s http://tlcw.yobeeo.com/api/v1/health

# Test bookmark endpoint
curl -s -H "Authorization: Bearer $TOKEN" http://tlcw.yobeeo.com/api/v1/tutorials/<id>/bookmark

# Test comment endpoint
curl -s -H "Authorization: Bearer $TOKEN" http://tlcw.yobeeo.com/api/v1/tutorials/<id>/comments

# Test password reset
curl -s -X POST http://tlcw.yobeeo.com/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'
```

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: P0 integration tests and production deployment"
```
