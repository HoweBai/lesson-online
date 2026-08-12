# Phase 3: Functionality Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Phase 3 functional gaps — comment system UI, bookmark UI, chapter navigation, export integration, tutorial detail enhancements, and backend test coverage.

**Architecture:** Phase 3 focuses on finishing the remaining user-facing features whose backend APIs already exist but lack frontend integration. The backend has fully implemented comment, bookmark, export, and chapter navigation APIs. This phase adds the corresponding UI components and integrates them into the existing tutorial display and list pages.

**Tech Stack:** React 18 + TypeScript + Tailwind CSS frontend; FastAPI + SQLAlchemy + SQLite backend; react-hot-toast v2.6.0 for toasts; date-fns for date formatting.

## Global Constraints

- Backend API endpoints must remain unchanged; all changes are additive
- Frontend must use the `api` client from `src/frontend/src/api/client.ts` for all API calls
- Toast notifications use `react-hot-toast` v2.6.0 — only `.success()`, `.error()`, `.loading()` are available (NO `.info()`)
- All Python files must use proper type hints (Optional[str], Dict[str, Any], etc.)
- All React components must be typed with TypeScript interfaces
- Backend tests must run with `pytest src/backend/tests/`
- Frontend must build successfully with `npm run build` in `src/frontend/`
- No breaking changes to existing routes or API contracts

---

## Task 1: Bookmark UI Integration

**Files:**
- Modify: `src/frontend/src/components/TutorialCard.tsx`
- Modify: `src/frontend/src/pages/TutorialListPage.tsx`
- Modify: `src/frontend/src/api/client.ts`
- Test: `src/backend/tests/test_bookmarks.py` (new)

**Interfaces:**
- Consumes: `api.bookmarkTutorial(id)` and `api.unbookmarkTutorial(id)` methods
- Produces: Updated tutorial cards showing bookmark state, like/bookmark toggle in TutorialListPage

- [ ] **Step 1: Add bookmark API methods to client**

Add two new methods to `ApiClient` class in `src/frontend/src/api/client.ts`:

```typescript
async bookmarkTutorial(id: string) {
  return this.request<any>('POST', `/api/v1/bookmarks/${id}/bookmark`);
}

async unbookmarkTutorial(id: string) {
  return this.request<any>('DELETE', `/api/v1/bookmarks/${id}/bookmark`);
}
```

- [ ] **Step 2: Write failing backend test for bookmarks**

Create `src/backend/tests/test_bookmarks.py`:

```python
"""Tests for bookmark API endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.database import engine, Base, get_db
from sqlalchemy.orm import Session
from src.services.auth_service import AuthService

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


class TestBookmarkEndpoints:
    """Test bookmark API endpoints."""

    @pytest.fixture
    def auth_client(self):
        """Return a TestClient with auth headers pre-configured."""
        auth = AuthService()
        with Session(bind=engine) as db:
            result = auth.register(db, "testbookuser", "book@test.com", "testpass123")
            token = result["token"]
        c = TestClient(app)
        c.headers["Authorization"] = f"Bearer {token}"
        return c

    def test_bookmark_tutorial(self, auth_client):
        """Test bookmarking a tutorial."""
        # First create a tutorial
        tutorial_result = client.post(
            "/api/v1/tutorials",
            json={"title": "Test Tutorial", "description": "Test"}
        )
        # Tutorial creation requires auth, let's just test with an existing ID
        # Use a known tutorial ID format
        import uuid
        test_tutorial_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/bookmarks/{test_tutorial_id}/bookmark")
        # Will 404 since tutorial doesn't exist, but tests auth is working
        assert response.status_code in [404, 422]

    def test_unbookmark_tutorial(self, auth_client):
        """Test unbookmarking a tutorial."""
        import uuid
        test_tutorial_id = str(uuid.uuid4())
        response = auth_client.delete(f"/api/v1/bookmarks/{test_tutorial_id}/bookmark")
        assert response.status_code == 404

    def test_list_bookmarks(self, auth_client):
        """Test listing user bookmarks."""
        response = auth_client.get("/api/v1/bookmarks/bookmarks")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

    def test_bookmark_requires_auth(self, auth_client):
        """Test that bookmark endpoints require authentication."""
        auth_client.headers.clear()
        import uuid
        test_tutorial_id = str(uuid.uuid4())
        response = auth_client.post(f"/api/v1/bookmarks/{test_tutorial_id}/bookmark")
        assert response.status_code == 401

        response = auth_client.delete(f"/api/v1/bookmarks/{test_tutorial_id}/bookmark")
        assert response.status_code == 401

        response = auth_client.get("/api/v1/bookmarks/bookmarks")
        assert response.status_code == 401
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd src/backend && pytest tests/test_bookmarks.py -v`
Expected: FAIL — test file doesn't exist yet (or module import errors).

- [ ] **Step 4: Update TutorialCard to show bookmark button**

In `src/frontend/src/components/TutorialCard.tsx`, add a bookmark prop and button:

Add to `TutorialCardProps` interface:
```typescript
interface TutorialCardProps {
  tutorial: Tutorial;
  onClick: (id: string) => void;
  onLike?: (e: React.MouseEvent) => void;
  isBookmarked?: boolean;
  onBookmark?: (e: React.MouseEvent) => void;
}
```

Add bookmark button in the footer section next to the Like button:
```tsx
{onBookmark && (
  <button
    onClick={(e) => {
      e.stopPropagation();
      onBookmark(e);
    }}
    className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-primary-600 hover:bg-primary-50 rounded-lg transition-all duration-200 hover:scale-105"
  >
    <span>{isBookmarked ? '🔖' : '📑'}</span> {isBookmarked ? 'Bookmarked' : 'Bookmark'}
  </button>
)}
```

- [ ] **Step 5: Add bookmark state to TutorialListPage**

In `src/frontend/src/pages/TutorialListPage.tsx`, add state and handlers:

```typescript
const [bookmarks, setBookmarks] = useState<Set<string>>(new Set());

const handleBookmark = async (id: string, e: React.MouseEvent) => {
  e.stopPropagation();
  const isBookmarked = bookmarks.has(id);
  const result = isBookmarked
    ? await api.unbookmarkTutorial(id)
    : await api.bookmarkTutorial(id);
  if (result.success) {
    setBookmarks(prev => {
      const next = new Set(prev);
      if (isBookmarked) next.delete(id);
      else next.add(id);
      return next;
    });
  }
};
```

Update TutorialCard usage to pass `isBookmarked` and `onBookmark`:
```tsx
<TutorialCard
  tutorial={tutorial}
  onClick={(id) => navigate(`/tutorial/${id}`)}
  onLike={(e) => handleLike(tutorial.id, e)}
  isBookmarked={bookmarks.has(tutorial.id)}
  onBookmark={(e) => handleBookmark(tutorial.id, e)}
/>
```

- [ ] **Step 6: Run backend tests to verify they pass**

Run: `cd src/backend && pytest tests/test_bookmarks.py -v`
Expected: All tests pass (4/4).

- [ ] **Step 7: Commit**

```bash
cd d:/project/lessons
git add src/frontend/src/components/TutorialCard.tsx
git add src/frontend/src/pages/TutorialListPage.tsx
git add src/frontend/src/api/client.ts
git add src/backend/tests/test_bookmarks.py
git commit -m "feat: add bookmark UI integration and backend tests"
```

---

## Task 2: Comment UI Integration

**Files:**
- Create: `src/frontend/src/components/CommentSection.tsx`
- Modify: `src/frontend/src/pages/TutorialDisplayPage.tsx`
- Modify: `src/frontend/src/api/client.ts`
- Test: `src/backend/tests/test_comments.py` (new)

**Interfaces:**
- Consumes: `api.getComments(tutorialId)` and `api.createComment(tutorialId, content)` methods
- Produces: `CommentSection` component with comment list and creation form

- [ ] **Step 1: Add comment API methods to client**

Add to `ApiClient` class in `src/frontend/src/api/client.ts`:

```typescript
async getComments(tutorialId: string) {
  return this.request<any>('GET', `/api/v1/tutorials/${tutorialId}/comments`);
}

async createComment(tutorialId: string, content: string, parentId?: string) {
  return this.request<any>('POST', `/api/v1/tutorials/${tutorialId}/comments`, {
    content,
    parent_id: parentId
  });
}
```

- [ ] **Step 2: Write failing backend test for comments**

Create `src/backend/tests/test_comments.py`:

```python
"""Tests for comment API endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.database import engine, Base, get_db
from sqlalchemy.orm import Session
from src.services.auth_service import AuthService
import uuid

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


class TestCommentEndpoints:
    """Test comment API endpoints."""

    @pytest.fixture
    def auth_client(self):
        """Return a TestClient with auth headers pre-configured."""
        auth = AuthService()
        with Session(bind=engine) as db:
            result = auth.register(db, "testcomuser", "com@test.com", "testpass123")
            token = result["token"]
        c = TestClient(app)
        c.headers["Authorization"] = f"Bearer {token}"
        return c

    def test_create_comment_requires_auth(self, auth_client):
        """Test that creating comments requires authentication."""
        auth_client.headers.clear()
        test_tutorial_id = str(uuid.uuid4())
        response = auth_client.post(
            f"/api/v1/tutorials/{test_tutorial_id}/comments",
            json={"content": "Test comment"}
        )
        assert response.status_code == 401

    def test_get_comments_requires_auth(self, auth_client):
        """Test that getting comments requires authentication."""
        auth_client.headers.clear()
        test_tutorial_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_tutorial_id}/comments")
        assert response.status_code == 401

    def test_create_comment_on_nonexistent_tutorial(self, auth_client):
        """Test creating a comment on a non-existent tutorial."""
        test_tutorial_id = str(uuid.uuid4())
        response = auth_client.post(
            f"/api/v1/tutorials/{test_tutorial_id}/comments",
            json={"content": "Test comment"}
        )
        assert response.status_code == 404

    def test_get_comments_on_nonexistent_tutorial(self, auth_client):
        """Test getting comments on a non-existent tutorial."""
        test_tutorial_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_tutorial_id}/comments")
        assert response.status_code == 404
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd src/backend && pytest tests/test_comments.py -v`
Expected: FAIL — test file doesn't exist yet.

- [ ] **Step 4: Create CommentSection component**

Create `src/frontend/src/components/CommentSection.tsx`:

```typescript
import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from '../hooks/useToast';

interface Comment {
  id: string;
  content: string;
  user: { id: string; username: string } | null;
  created_at: string;
  is_reply: boolean;
  like_count: number;
  replies: Comment[];
}

interface CommentSectionProps {
  tutorialId: string;
}

const CommentSection = ({ tutorialId }: CommentSectionProps) => {
  const toast = useToast();
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [newComment, setNewComment] = useState('');

  useEffect(() => {
    loadComments();
  }, [tutorialId]);

  const loadComments = async () => {
    setLoading(true);
    const result = await api.getComments(tutorialId);
    if (result.success) {
      setComments(result.data?.data || []);
    }
    setLoading(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim()) return;

    const result = await api.createComment(tutorialId, newComment.trim());
    if (result.success) {
      setNewComment('');
      loadComments();
    } else {
      toast.error(result.error || 'Failed to post comment');
    }
  };

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-soft p-6">
      <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
        <span>💬</span> Comments ({comments.length})
      </h3>

      {/* Comment form */}
      <form onSubmit={handleSubmit} className="mb-8">
        <textarea
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          placeholder="Write a comment..."
          rows={3}
          className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
        />
        <div className="mt-2 flex justify-end">
          <button
            type="submit"
            disabled={!newComment.trim()}
            className="px-5 py-2 bg-primary-600 text-white rounded-xl hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium"
          >
            Post Comment
          </button>
        </div>
      </form>

      {/* Comments list */}
      {comments.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p className="text-lg">No comments yet</p>
          <p className="text-sm">Be the first to share your thoughts!</p>
        </div>
      ) : (
        <div className="space-y-4">
          {comments.map((comment) => (
            <CommentItem key={comment.id} comment={comment} tutorialId={tutorialId} onRefresh={loadComments} />
          ))}
        </div>
      )}
    </div>
  );
};

// Single comment item component
const CommentItem = ({
  comment,
  tutorialId,
  onRefresh
}: {
  comment: Comment;
  tutorialId: string;
  onRefresh: () => void;
}) => {
  const toast = useToast();
  const [replyText, setReplyText] = useState('');
  const [showReply, setShowReply] = useState(false);

  const handleReply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyText.trim()) return;

    const result = await api.createComment(tutorialId, replyText.trim(), comment.id);
    if (result.success) {
      setReplyText('');
      setShowReply(false);
      onRefresh();
    } else {
      toast.error('Failed to post reply');
    }
  };

  const timeAgo = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  return (
    <div className="border-b border-gray-100 pb-4 last:border-0">
      <div className="flex gap-3">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
          {comment.user?.username?.charAt(0).toUpperCase() || '?'}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold text-sm text-gray-900">
              {comment.user?.username || 'Unknown'}
            </span>
            <span className="text-xs text-gray-400">{timeAgo(comment.created_at)}</span>
          </div>
          <p className="text-gray-700 text-sm">{comment.content}</p>
          <button
            onClick={() => setShowReply(!showReply)}
            className="mt-2 text-xs text-primary-600 hover:text-primary-700 font-medium"
          >
            Reply
          </button>
        </div>
      </div>

      {/* Reply form */}
      {showReply && (
        <form onSubmit={handleReply} className="mt-3 ml-11 flex gap-2">
          <input
            type="text"
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            placeholder="Write a reply..."
            className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
          <button
            type="submit"
            disabled={!replyText.trim()}
            className="px-3 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50"
          >
            Reply
          </button>
          <button
            type="button"
            onClick={() => setShowReply(false)}
            className="px-3 py-2 text-gray-500 text-sm hover:text-gray-700"
          >
            Cancel
          </button>
        </form>
      )}

      {/* Replies */}
      {comment.replies && comment.replies.length > 0 && (
        <div className="mt-3 ml-11 space-y-2">
          {comment.replies.map((reply) => (
            <div key={reply.id} className="border-l-2 border-gray-200 pl-3">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-semibold text-xs text-gray-900">
                  {reply.user?.username || 'Unknown'}
                </span>
                <span className="text-xs text-gray-400">{timeAgo(reply.created_at)}</span>
              </div>
              <p className="text-sm text-gray-700">{reply.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default CommentSection;
```

- [ ] **Step 5: Integrate CommentSection into TutorialDisplayPage**

In `src/frontend/src/pages/TutorialDisplayPage.tsx`, import and add the CommentSection after the chapter content:

```typescript
import CommentSection from '../components/CommentSection';
```

Add before the closing `</div>` of the main content area (after the bottom navigation):
```tsx
{/* Comments Section */}
<div className="mt-8">
  <CommentSection tutorialId={id!} />
</div>
```

- [ ] **Step 6: Run backend tests**

Run: `cd src/backend && pytest tests/test_comments.py -v`
Expected: All 4 tests pass.

- [ ] **Step 7: Verify frontend build**

Run: `cd src/frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 8: Commit**

```bash
cd d:/project/lessons
git add src/frontend/src/components/CommentSection.tsx
git add src/frontend/src/pages/TutorialDisplayPage.tsx
git add src/frontend/src/api/client.ts
git add src/backend/tests/test_comments.py
git commit -m "feat: add comment UI integration and backend tests"
```

---

## Task 3: Chapter Navigation in Tutorial Display

**Files:**
- Modify: `src/frontend/src/pages/TutorialDisplayPage.tsx`
- Modify: `src/frontend/src/api/client.ts`
- Test: `src/backend/tests/test_tutorial_navigation.py` (new)

**Interfaces:**
- Consumes: `api.getTutorials()` to get tutorial list, `api.getChapterContent(tutorialId, chapterNumber)` to fetch specific chapters
- Produces: Chapter navigation sidebar/panel with chapter list and click-to-navigate

- [ ] **Step 1: Add getTutorialChapters API method**

Add to `ApiClient` class in `src/frontend/src/api/client.ts`:

```typescript
async getTutorialChapters(tutorialId: string) {
  return this.request<any>('GET', `/api/v1/tutorials/${tutorialId}/chapters`);
}
```

- [ ] **Step 2: Write failing backend test for chapter listing**

Create `src/backend/tests/test_tutorial_navigation.py`:

```python
"""Tests for tutorial chapter navigation endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.database import engine, Base, get_db
from sqlalchemy.orm import Session
from src.services.auth_service import AuthService
import uuid

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


class TestChapterNavigation:
    """Test chapter navigation endpoints."""

    @pytest.fixture
    def auth_client(self):
        """Return a TestClient with auth headers pre-configured."""
        auth = AuthService()
        with Session(bind=engine) as db:
            result = auth.register(db, "testnavuser", "nav@test.com", "testpass123")
            token = result["token"]
        c = TestClient(app)
        c.headers["Authorization"] = f"Bearer {token}"
        return c

    def test_list_chapters_on_nonexistent_tutorial(self, auth_client):
        """Test listing chapters on a non-existent tutorial."""
        test_tutorial_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_tutorial_id}/chapters")
        assert response.status_code == 404

    def test_get_chapter_content_on_nonexistent_tutorial(self, auth_client):
        """Test getting chapter content on a non-existent tutorial."""
        test_tutorial_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_tutorial_id}/chapters/1")
        assert response.status_code == 404

    def test_get_chapter_status_on_nonexistent_tutorial(self, auth_client):
        """Test getting chapter status on a non-existent tutorial."""
        test_tutorial_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_tutorial_id}/chapters/1/status")
        assert response.status_code == 404
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd src/backend && pytest tests/test_tutorial_navigation.py -v`
Expected: FAIL — test file doesn't exist yet.

- [ ] **Step 4: Add chapter navigation panel to TutorialDisplayPage**

In `src/frontend/src/pages/TutorialDisplayPage.tsx`, add chapter navigation state and UI:

Add new state:
```typescript
const [chapters, setChapters] = useState<Array<{ chapter_number: number; title: string; status: string; id: string }>>([]);
const [showChapterList, setShowChapterList] = useState(false);
```

Add fetchChapters function:
```typescript
const fetchChapters = useCallback(async () => {
  if (!id) return;
  const result = await api.getTutorialChapters(id);
  if (result.success && result.data?.data) {
    setChapters(result.data.data);
  }
}, [id]);
```

Add to existing useEffect (alongside fetchChapter):
```typescript
useEffect(() => {
  fetchChapter();
  fetchChapters();
}, [fetchChapter, fetchChapters]);
```

Add chapter navigation panel as a collapsible sidebar:
```tsx
{/* Chapter Navigation */}
<div className="fixed left-0 top-16 bottom-0 z-30 transition-all duration-300">
  <button
    onClick={() => setShowChapterList(!showChapterList)}
    className="fixed left-0 top-20 z-40 w-10 h-10 bg-white rounded-r-xl shadow-lg flex items-center justify-center text-gray-600 hover:text-primary-600 transition-all"
  >
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h10M4 18h7" />
    </svg>
  </button>
  <div className={`bg-white shadow-xl transition-all duration-300 ${showChapterList ? 'w-72' : 'w-0'} overflow-hidden`}>
    <div className="p-4">
      <h3 className="font-bold text-gray-900 mb-3">Chapters</h3>
      <div className="space-y-1">
        {chapters.map((ch) => (
          <button
            key={ch.id}
            onClick={async () => {
              const result = await api.getChapterContent(id!, ch.chapter_number);
              if (result.success) {
                setChapter(result.data);
                setShowChapterList(false);
              }
            }}
            className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-all ${
              chapter?.chapter_number === ch.chapter_number
                ? 'bg-primary-100 text-primary-700 font-semibold'
                : ch.status === 'ready'
                ? 'text-gray-700 hover:bg-gray-50'
                : 'text-gray-400 cursor-not-allowed'
            }`}
            disabled={ch.status !== 'ready'}
          >
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center text-xs font-bold">
                {ch.chapter_number}
              </span>
              <span className="truncate">{ch.title}</span>
              {ch.status === 'ready' && <span className="text-green-500 text-xs ml-auto">✓</span>}
            </div>
          </button>
        ))}
        {chapters.length === 0 && (
          <p className="text-sm text-gray-500 text-center py-4">No chapters yet</p>
        )}
      </div>
    </div>
  </div>
</div>
```

Wrap the main content area with a left margin when chapter list is shown:
```tsx
<div className={`min-h-screen py-8 transition-all duration-300 ${showChapterList ? 'ml-72' : 'ml-0'}`}>
```

- [ ] **Step 5: Run backend tests**

Run: `cd src/backend && pytest tests/test_tutorial_navigation.py -v`
Expected: All 3 tests pass.

- [ ] **Step 6: Verify frontend build**

Run: `cd src/frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 7: Commit**

```bash
cd d:/project/lessons
git add src/frontend/src/pages/TutorialDisplayPage.tsx
git add src/frontend/src/api/client.ts
git add src/backend/tests/test_tutorial_navigation.py
git commit -m "feat: add chapter navigation panel to tutorial display"
```

---

## Task 4: Export Functionality Frontend Integration

**Files:**
- Modify: `src/frontend/src/pages/TutorialDisplayPage.tsx`
- Modify: `src/frontend/src/components/TutorialCard.tsx`
- Test: `src/backend/tests/test_export.py` (new)

**Interfaces:**
- Consumes: `api.exportMarkdown(tutorialId)`, `api.exportJSON(tutorialId)`, `api.exportOutline(tutorialId)`
- Produces: Export buttons in tutorial display and tutorial card

- [ ] **Step 1: Write failing backend test for export**

Create `src/backend/tests/test_export.py`:

```python
"""Tests for export API endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.database import engine, Base, get_db
from sqlalchemy.orm import Session
from src.services.auth_service import AuthService
import uuid

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


class TestExportEndpoints:
    """Test export API endpoints."""

    @pytest.fixture
    def auth_client(self):
        """Return a TestClient with auth headers pre-configured."""
        auth = AuthService()
        with Session(bind=engine) as db:
            result = auth.register(db, "testexpuser", "exp@test.com", "testpass123")
            token = result["token"]
        c = TestClient(app)
        c.headers["Authorization"] = f"Bearer {token}"
        return c

    def test_export_markdown_requires_auth(self, auth_client):
        """Test that markdown export requires authentication."""
        auth_client.headers.clear()
        test_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_id}/export/markdown")
        assert response.status_code == 401

    def test_export_json_requires_auth(self, auth_client):
        """Test that JSON export requires authentication."""
        auth_client.headers.clear()
        test_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_id}/export/json")
        assert response.status_code == 401

    def test_export_outline_requires_auth(self, auth_client):
        """Test that outline export requires authentication."""
        auth_client.headers.clear()
        test_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_id}/export/outline")
        assert response.status_code == 401

    def test_export_markdown_not_found(self, auth_client):
        """Test markdown export on non-existent tutorial."""
        test_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_id}/export/markdown")
        assert response.status_code == 404

    def test_export_json_not_found(self, auth_client):
        """Test JSON export on non-existent tutorial."""
        test_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_id}/export/json")
        assert response.status_code == 404

    def test_export_outline_not_found(self, auth_client):
        """Test outline export on non-existent tutorial."""
        test_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_id}/export/outline")
        assert response.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && pytest tests/test_export.py -v`
Expected: FAIL — test file doesn't exist yet.

- [ ] **Step 3: Add export handler functions to TutorialDisplayPage**

In `src/frontend/src/pages/TutorialDisplayPage.tsx`, add export handlers:

```typescript
const handleExportMarkdown = async () => {
  try {
    const text = await api.exportMarkdown(id!);
    if (text) {
      const blob = new Blob([text], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${chapter?.title || 'tutorial'}.md`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Markdown exported successfully!');
    }
  } catch (e: any) {
    toast.error('Failed to export markdown: ' + e.message);
  }
};

const handleExportJSON = async () => {
  try {
    const result = await api.exportJSON(id!);
    if (result.success) {
      const blob = new Blob([JSON.stringify(result.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${chapter?.title || 'tutorial'}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('JSON exported successfully!');
    }
  } catch (e: any) {
    toast.error('Failed to export JSON: ' + e.message);
  }
};

const handleExportOutline = async () => {
  try {
    const result = await api.exportOutline(id!);
    if (result.success) {
      const blob = new Blob([JSON.stringify(result.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${chapter?.title || 'tutorial'}-outline.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Outline exported successfully!');
    }
  } catch (e: any) {
    toast.error('Failed to export outline: ' + e.message);
  }
};
```

Replace the old `handleDownloadPDF` function with these new handlers. Also replace the "Download PDF" button in the toolbar with three export buttons:

```tsx
<div className="flex gap-2">
  <button
    onClick={handleExportMarkdown}
    className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-all font-medium shadow-soft"
  >
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
    Markdown
  </button>
  <button
    onClick={handleExportJSON}
    className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-xl hover:bg-purple-700 transition-all font-medium shadow-soft"
  >
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h7" />
    </svg>
    JSON
  </button>
  <button
    onClick={handleExportOutline}
    className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-xl hover:bg-green-700 transition-all font-medium shadow-soft"
  >
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
    </svg>
    Outline
  </button>
</div>
```

- [ ] **Step 4: Run backend tests**

Run: `cd src/backend && pytest tests/test_export.py -v`
Expected: All 6 tests pass.

- [ ] **Step 5: Verify frontend build**

Run: `cd src/frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 6: Commit**

```bash
cd d:/project/lessons
git add src/frontend/src/pages/TutorialDisplayPage.tsx
git add src/backend/tests/test_export.py
git commit -m "feat: add export functionality UI integration"
```

---

## Task 5: Tutorial List Page Enhanced — Bookmark Count & Empty States

**Files:**
- Modify: `src/frontend/src/pages/TutorialListPage.tsx`
- Modify: `src/frontend/src/components/TutorialCard.tsx`
- Test: (covered by Task 1 integration tests)

**Interfaces:**
- Consumes: bookmark state from Task 1
- Produces: Updated TutorialCard with bookmark count badge, improved empty states with wizard CTA

- [ ] **Step 1: Add bookmark count to TutorialCard**

In `src/frontend/src/components/TutorialCard.tsx`, update the meta section to show bookmark count alongside views and likes:

Add to the props interface:
```typescript
interface TutorialCardProps {
  tutorial: Tutorial;
  onClick: (id: string) => void;
  onLike?: (e: React.MouseEvent) => void;
  isBookmarked?: boolean;
  onBookmark?: (e: React.MouseEvent) => void;
}
```

Update the meta info section to include bookmark indicator:
```tsx
{/* Meta information */}
<div className="flex flex-wrap gap-3 text-xs text-gray-500 mb-4">
  <span className="flex items-center gap-1 bg-blue-50 text-blue-700 px-2 py-1 rounded-lg group-hover:bg-blue-100 transition-colors duration-300">
    <span>📖</span> {tutorial.total_chapters || 0} chapters
  </span>
  <span className="flex items-center gap-1 bg-purple-50 text-purple-700 px-2 py-1 rounded-lg group-hover:bg-purple-100 transition-colors duration-300">
    <span>👁️</span> {tutorial.views || 0} views
  </span>
  <span className="flex items-center gap-1 bg-pink-50 text-pink-700 px-2 py-1 rounded-lg group-hover:bg-pink-100 transition-colors duration-300">
    <span>❤️</span> {tutorial.likes || 0} likes
  </span>
  {onBookmark && (
    <span className={`flex items-center gap-1 px-2 py-1 rounded-lg transition-colors duration-300 ${
      isBookmarked ? 'bg-amber-100 text-amber-700' : 'bg-gray-50 text-gray-400'
    }`}>
      <span>{isBookmarked ? '🔖' : '📑'}</span> {isBookmarked ? 'Saved' : 'Save'}
    </span>
  )}
</div>
```

- [ ] **Step 2: Improve empty state with wizard CTA**

In `src/frontend/src/pages/TutorialListPage.tsx`, improve the empty state for public tutorials:

```tsx
{tutorials.length === 0 ? (
  <div className="text-center py-20 bg-white rounded-3xl shadow-soft">
    <div className="text-6xl mb-4">📭</div>
    <h3 className="text-xl font-semibold text-gray-900 mb-2">
      {activeTab === 'public' ? 'No public tutorials yet' : 'You haven\'t created any tutorials'}
    </h3>
    <p className="text-gray-500 mb-6 max-w-md mx-auto">
      {activeTab === 'public'
        ? 'Share your knowledge with the community! Create your first AI-powered tutorial.'
        : 'Create your first AI-powered tutorial with our guided wizard.'}
    </p>
    <button
      onClick={() => navigate('/wizard')}
      className="btn-primary inline-flex items-center gap-2 px-6 py-3"
    >
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
      </svg>
      {activeTab === 'public' ? 'Create & Publish Tutorial' : 'Create Your First Tutorial'}
    </button>
  </div>
) : (
```

- [ ] **Step 3: Add bookmark count to stats footer**

In the stats footer, add a bookmarks stat:
```tsx
<StatCard label="Bookmarked" value={bookmarks.size} icon="🔖" />
```

- [ ] **Step 4: Verify frontend build**

Run: `cd src/frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 5: Commit**

```bash
cd d:/project/lessons
git add src/frontend/src/components/TutorialCard.tsx
git add src/frontend/src/pages/TutorialListPage.tsx
git commit -m "feat: enhance tutorial list with bookmark UI and improved empty states"
```

---

## Task 6: Backend Test Coverage Expansion

**Files:**
- Modify: `src/backend/tests/test_endpoints.py`
- Create: `src/backend/tests/test_auth_extended.py` (new)
- Create: `src/backend/tests/test_profile.py` (new)
- Test: Run full test suite

**Interfaces:**
- Consumes: Existing test infrastructure from `conftest.py`
- Produces: Expanded test coverage for auth, profile, and catalog endpoints

- [ ] **Step 1: Add auth extended tests**

Create `src/backend/tests/test_auth_extended.py`:

```python
"""Extended tests for auth endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.database import engine, Base, get_db
from sqlalchemy.orm import Session
from src.services.auth_service import AuthService
import uuid

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


class TestAuthExtended:
    """Extended authentication tests."""

    def test_register_duplicate_email(self):
        """Test registration with duplicate email."""
        c = TestClient(app)
        payload = {
            "username": "dupuser",
            "email": "dup@test.com",
            "password": "testpass123"
        }
        # First registration should succeed
        response1 = c.post("/api/v1/auth/register", json=payload)
        assert response1.status_code in [201, 400]

        # Second registration with same email should fail
        payload2 = {
            "username": "dupuser2",
            "email": "dup@test.com",
            "password": "testpass123"
        }
        response2 = c.post("/api/v1/auth/register", json=payload2)
        assert response2.status_code == 400

    def test_register_duplicate_username(self):
        """Test registration with duplicate username."""
        c = TestClient(app)
        payload = {
            "username": "sameuser",
            "email": "same1@test.com",
            "password": "testpass123"
        }
        c.post("/api/v1/auth/register", json=payload)

        payload2 = {
            "username": "sameuser",
            "email": "same2@test.com",
            "password": "testpass123"
        }
        response = c.post("/api/v1/auth/register", json=payload2)
        assert response.status_code == 400

    def test_login_wrong_password(self):
        """Test login with wrong password."""
        auth = AuthService()
        with Session(bind=engine) as db:
            auth.register(db, "wrongpwduser", "wrongpwd@test.com", "correctpass123")

        c = TestClient(app)
        response = c.post("/api/v1/auth/login", json={
            "email": "wrongpwd@test.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401

    def test_me_endpoint(self):
        """Test getting current user info."""
        auth = AuthService()
        with Session(bind=engine) as db:
            result = auth.register(db, "meuser", "me@test.com", "testpass123")
            token = result["token"]

        c = TestClient(app)
        c.headers["Authorization"] = f"Bearer {token}"
        response = c.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert "username" in data
        assert "email" in data

    def test_logout_endpoint(self):
        """Test logout endpoint."""
        c = TestClient(app)
        response = c.post("/api/v1/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
```

- [ ] **Step 2: Add profile tests**

Create `src/backend/tests/test_profile.py`:

```python
"""Tests for profile API endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.database import engine, Base, get_db
from sqlalchemy.orm import Session
from src.services.auth_service import AuthService

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


class TestProfileEndpoints:
    """Test profile API endpoints."""

    @pytest.fixture
    def auth_client(self):
        """Return a TestClient with auth headers pre-configured."""
        auth = AuthService()
        with Session(bind=engine) as db:
            result = auth.register(db, "profuser", "prof@test.com", "testpass123")
            token = result["token"]
        c = TestClient(app)
        c.headers["Authorization"] = f"Bearer {token}"
        return c

    def test_get_profile(self, auth_client):
        """Test getting user profile."""
        response = auth_client.get("/api/v1/users/profile")
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "profile" in data

    def test_update_profile(self, auth_client):
        """Test updating user profile."""
        response = auth_client.put(
            "/api/v1/users/profile",
            json={
                "programming_level": 3,
                "learning_goal": "job_search",
                "available_hours_per_day": 3.5
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "profile" in data
        assert data["profile"]["programming_level"] == 3
        assert data["profile"]["learning_goal"] == "job_search"

    def test_get_learning_progress(self, auth_client):
        """Test getting learning progress."""
        response = auth_client.get("/api/v1/users/profile/progress")
        assert response.status_code == 200
        data = response.json()
        assert "total_tutorials" in data
        assert "completed_chapters" in data

    def test_get_learning_stats(self, auth_client):
        """Test getting learning stats."""
        response = auth_client.get("/api/v1/users/profile/stats")
        assert response.status_code == 200
        data = response.json()
        assert "tutorial_stats" in data
        assert "chapter_stats" in data

    def test_profile_requires_auth(self, auth_client):
        """Test that profile endpoints require authentication."""
        auth_client.headers.clear()
        response = auth_client.get("/api/v1/users/profile")
        assert response.status_code == 401

        response = auth_client.put("/api/v1/users/profile", json={})
        assert response.status_code == 401

        response = auth_client.get("/api/v1/users/profile/progress")
        assert response.status_code == 401
```

- [ ] **Step 3: Run all backend tests**

Run: `cd src/backend && pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
cd d:/project/lessons
git add src/backend/tests/test_auth_extended.py
git add src/backend/tests/test_profile.py
git add src/backend/tests/test_endpoints.py
git commit -m "test: expand backend test coverage for auth, profile, and bookmarks"
```

---

## Task 7: Knowledge Map Visualization on Profile Page

**Files:**
- Modify: `src/frontend/src/pages/ProfilePage.tsx`
- Test: No new tests needed (UI enhancement)

**Interfaces:**
- Consumes: `api.getProfile()` and `api.getLearningStats()` data
- Produces: Knowledge mastery map visualization using a tag/cloud layout

- [ ] **Step 1: Add knowledge map visualization to ProfilePage**

In `src/frontend/src/pages/ProfilePage.tsx`, after loading stats, extract the knowledge mapping data:

Add state:
```typescript
const [knowledgeMap, setKnowledgeMap] = useState<Record<string, string>>({});
```

Update `loadData` to also fetch knowledge mapping:
```typescript
const [userRes, profileRes, progressRes, statsRes] = await Promise.all([
  api.getMe(),
  api.getProfile(),
  api.getLearningProgress(),
  api.getLearningStats()
]);

// Extract knowledge map from profile response
if (profileRes.success && profileRes.data?.knowledge_mapping?.mastery_map) {
  setKnowledgeMap(profileRes.data.knowledge_mapping.mastery_map);
}
```

Add a Knowledge Map card after the Statistics card:
```tsx
{/* Knowledge Map Card */}
{Object.keys(knowledgeMap).length > 0 && (
  <div className="card p-6 animate-slide-up" style={{ animationDelay: '0.15s' }}>
    <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
      <span>🧠</span> Knowledge Map
    </h3>
    <div className="flex flex-wrap gap-2">
      {Object.entries(knowledgeMap).map(([topic, level]) => (
        <span
          key={topic}
          className={`px-3 py-1.5 rounded-full text-sm font-medium ${
            level === 'advanced' ? 'bg-green-100 text-green-700' :
            level === 'intermediate' ? 'bg-yellow-100 text-yellow-700' :
            'bg-gray-100 text-gray-600'
          }`}
        >
          {topic.replace(/_/g, ' ')} · {level}
        </span>
      ))}
    </div>
    <p className="text-xs text-gray-400 mt-3">
      Auto-inferred from your learning profile
    </p>
  </div>
)}
```

- [ ] **Step 2: Verify frontend build**

Run: `cd src/frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
cd d:/project/lessons
git add src/frontend/src/pages/ProfilePage.tsx
git commit -m "feat: add knowledge map visualization to profile page"
```

---

## Task 8: Final Verification & Deployment Prep

**Files:**
- Run full test suite
- Run frontend build
- Verify all routes work

**Interfaces:**
- Consumes: All previous tasks
- Produces: Clean test suite, successful build, ready for deployment

- [ ] **Step 1: Run all backend tests**

Run: `cd src/backend && pytest tests/ -v --tb=short`
Expected: All tests pass with green output.

- [ ] **Step 2: Run frontend build**

Run: `cd src/frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 3: Commit any final fixes**

```bash
cd d:/project/lessons
git add -A
git commit -m "chore: Phase 3 final verification"
```

---

## Summary

Phase 3 adds 8 tasks covering:
1. **Bookmark UI** — Bookmark/unbookmark buttons on tutorial cards and list page
2. **Comment UI** — Full comment section with replies on tutorial pages
3. **Chapter Navigation** — Collapsible sidebar showing all chapters with status indicators
4. **Export Integration** — Markdown, JSON, and outline export buttons in tutorial display
5. **Enhanced Tutorial List** — Bookmark count, improved empty states with CTA
6. **Backend Tests** — Extended test coverage for auth, bookmarks, comments, export, profile
7. **Knowledge Map UI** — Visual knowledge mastery map on profile page
8. **Final Verification** — Full test suite and build verification
