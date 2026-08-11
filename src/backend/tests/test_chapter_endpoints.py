"""Tests for chapter listing and content endpoints."""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import text

from src.api.main import app
from src.database import engine, Base, get_db
from sqlalchemy.orm import Session


# Create test database
Base.metadata.create_all(bind=engine)

# Override dependencies
def override_get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def _clean_db():
    """Remove all tutorials and chapters."""
    db = Session(bind=engine)
    db.execute(text("DELETE FROM chapters"))
    db.execute(text("DELETE FROM tutorials"))
    db.commit()
    db.close()


def _insert_tutorial(db, tutorial_id, owner_id="test-user-1"):
    db.execute(text(
        "INSERT INTO tutorials (id, owner_id, title, description, status, is_public, total_chapters, current_chapter, created_at, updated_at) VALUES (:id, :owner_id, :title, :description, :status, :is_public, :total_chapters, :current_chapter, :created_at, :updated_at)"
    ), {
        "id": tutorial_id,
        "owner_id": owner_id,
        "title": "Test Tutorial",
        "description": "A test tutorial",
        "status": "published",
        "is_public": True,
        "total_chapters": 3,
        "current_chapter": 1,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    db.commit()


def test_list_chapters():
    """Test listing all chapters for a tutorial."""
    _clean_db()
    tutorial_id = "test-tutorial-list"

    db = Session(bind=engine)
    _insert_tutorial(db, tutorial_id)

    for n in [1, 2, 3]:
        db.execute(text(
            "INSERT INTO chapters (id, tutorial_id, chapter_number, title, status, content, prerequisite_check_passed, generated_at, completed_at, version) VALUES (:id, :tutorial_id, :chapter_number, :title, :status, :content, :prerequisite_check_passed, :generated_at, :completed_at, :version)"
        ), {
            "id": f"ch-{n}-{tutorial_id}",
            "tutorial_id": tutorial_id,
            "chapter_number": n,
            "title": f"Chapter {n}",
            "status": "ready" if n <= 2 else "draft",
            "content": None,
            "prerequisite_check_passed": False,
            "generated_at": datetime.utcnow() if n <= 2 else None,
            "completed_at": None,
            "version": 1
        })
    db.commit()
    db.close()

    resp = client.get(f"/api/v1/tutorials/{tutorial_id}/chapters")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "total" in data
    assert len(data["data"]) == 3
    assert data["total"] == 3

    # Verify ordered by chapter_number
    numbers = [c["chapter_number"] for c in data["data"]]
    assert numbers == [1, 2, 3]


def test_get_chapter_content():
    """Test getting full chapter content."""
    _clean_db()
    tutorial_id = "test-tutorial-content"

    db = Session(bind=engine)
    _insert_tutorial(db, tutorial_id)

    db.execute(text(
        "INSERT INTO chapters (id, tutorial_id, chapter_number, title, status, content, prerequisite_check_passed, generated_at, completed_at, version) VALUES (:id, :tutorial_id, :chapter_number, :title, :status, :content, :prerequisite_check_passed, :generated_at, :completed_at, :version)"
    ), {
        "id": "ch-1-content",
        "tutorial_id": tutorial_id,
        "chapter_number": 1,
        "title": "Introduction",
        "status": "ready",
        "content": '{"sections": [{"title": "Intro", "content": {"overview": "Welcome"}}]}',
        "prerequisite_check_passed": False,
        "generated_at": datetime.utcnow(),
        "completed_at": None,
        "version": 1
    })
    db.commit()
    db.close()

    resp = client.get(f"/api/v1/tutorials/{tutorial_id}/chapters/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["chapter_number"] == 1
    assert data["title"] == "Introduction"
    assert "content" in data
    assert data["content"]["sections"][0]["title"] == "Intro"


def test_list_chapters_tutorial_not_found():
    """Test listing chapters for non-existent tutorial."""
    resp = client.get("/api/v1/tutorials/nonexistent-id/chapters")
    assert resp.status_code == 404


def test_get_chapter_content_not_found():
    """Test getting chapter that doesn't exist."""
    resp = client.get("/api/v1/tutorials/nonexistent-id/chapters/1")
    assert resp.status_code == 404
