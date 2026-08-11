"""Pytest configuration for the project."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Use SQLite for testing
TEST_DB_URL = "sqlite:///./test_ollp.db"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables before tests
from src.database import Base
Base.metadata.create_all(bind=engine)

def override_get_db():
    """Test DB dependency override."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

def reset_database():
    """Reset database between tests."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

@pytest.fixture(scope="module")
def client():
    """Create a FastAPI test client."""
    from src.api.main import app
    from src.database import get_db

    app.dependency_overrides[get_db] = override_get_db

    test_client = TestClient(app)
    yield test_client

    app.dependency_overrides.clear()

@pytest.fixture
def get_user_db(client):
    """Helper to create test users."""
    from src.models.user import User
    from src.services.auth_service import AuthService

    auth = AuthService()

    def create_test_user(username: str, email: str, password: str):
        with TestSessionLocal() as db:
            existing = db.query(User).filter_by(email=email).first()
            if existing:
                return existing

            user = User(username=username, email=email)
            user.password_hash = auth.hash_password(password)
            db.add(user)
            db.commit()
            db.refresh(user)
            return user

    return create_test_user
