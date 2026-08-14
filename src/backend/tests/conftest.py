"""Conftest for pytest fixtures."""

import os
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base, get_db

# Set required env vars for tests (P0 startup validation)
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-at-least-32-chars-long")
os.environ.setdefault("CRYPTO_KEY_HEX", "a" * 64)
os.environ.setdefault("POSTGRES_PASSWORD", "test-db-pass")
os.environ.setdefault("MINIO_ACCESS_KEY", "test-minio-user")
os.environ.setdefault("MINIO_SECRET_KEY", "test-minio-secret")



@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    with patch('src.database.get_db', override_get_db):
        yield SessionLocal()


@pytest.fixture
def test_user(db_session):
    """Create test user."""
    from src.models.user import User
    from src.services.auth_service import AuthService

    auth = AuthService()
    user = User(username="testuser", email="test@test.com")
    user.password_hash = auth.hash_password("testpass123")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_token(db_session, test_user):
    """Create test JWT token."""
    from src.services.auth_service import AuthService

    auth = AuthService()
    return auth.create_access_token(data={"sub": str(test_user.id)})


@pytest.fixture
def client(db_session, test_token):
    """Create test client with authentication."""
    from fastapi.testclient import TestClient
    from src.api.main import app

    def override_get_db():
        yield db_session

    def override_get_current_user():
        from src.models.user import User
        return test_user

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        test_client.headers["Authorization"] = f"Bearer {test_token}"
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_tutorial(db_session, test_user):
    """Create sample tutorial."""
    from src.models.tutorial import Tutorial
    from src.models.chapter import Chapter
    from datetime import datetime

    tutorial = Tutorial(
        owner_id=str(test_user.id),
        title="Test Tutorial",
        description="A test tutorial for unit testing",
        status="published",
        is_public=True,
        total_chapters=5,
        current_chapter=1,
        created_at=datetime.utcnow()
    )
    db_session.add(tutorial)
    db_session.commit()
    db_session.refresh(tutorial)

    chapter = Chapter(
        tutorial_id=tutorial.id,
        chapter_number=1,
        title="Introduction",
        status="completed",
        generated_at=datetime.utcnow()
    )
    db_session.add(chapter)
    db_session.commit()

    return tutorial


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset slowapi rate limiter storage between test runs to avoid cross-test 429s."""
    from src.middleware.rate_limiter import limiter
    if hasattr(limiter, "_storage") and hasattr(limiter._storage, "reset"):
        limiter._storage.reset()
    yield
