"""Test script to verify the backend works."""

import sys
import os

# Add backend src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set environment variables
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-development-only")
os.environ.setdefault("CRYPTO_KEY_HEX", "0" * 64)
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_ollp.db")

from src.api.main import app
from src.database import engine, Base, get_db

def test_imports():
    """Test that all imports work."""
    try:
        from src.models.user import User
        from src.models.profile import UserProfile
        from src.models.claude_config import ClaudeConfig
        from src.models.knowledge_mapping import UserKnowledgeMapping
        from src.models.tutorial import Tutorial
        from src.models.chapter import Chapter
        from src.models.public_catalog import PublicCatalog
        from src.models.task_log import TaskLog
        print("[OK] All models imported successfully")
    except ImportError as e:
        print(f"[FAIL] Import error: {e}")
        return False

    try:
        from src.services.auth_service import AuthService
        from src.services.crypto_service import SecureCryptoService
        from src.services.claude_config_service import ClaudeConfigService
        from src.services.outline_generator import OutlineGenerator
        from src.services.chapter_generator import ChapterGenerator
        print("[OK] All services imported successfully")
    except ImportError as e:
        print(f"[FAIL] Service import error: {e}")
        return False

    try:
        from src.api.auth import auth_router
        from src.api.tutorials import tutorials_router
        from src.api.catalog import catalog_router
        print("[OK] All API routers imported successfully")
    except ImportError as e:
        print(f"[FAIL] API import error: {e}")
        return False

    return True


def test_database():
    """Test database creation."""
    try:
        Base.metadata.create_all(bind=engine)
        print("[OK] Database tables created successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Database creation error: {e}")
        return False


def test_app():
    """Test the FastAPI app."""
    try:
        from fastapi.testclient import TestClient
        client = TestClient(app)

        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("[OK] Health endpoint works")

        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print("[OK] Root endpoint works")

        # Test docs endpoint exists
        response = client.get("/docs")
        assert response.status_code == 200
        print("[OK] Swagger docs endpoint works")

        return True
    except Exception as e:
        print(f"[FAIL] App test error: {e}")
        return False


def main():
    print("=" * 60)
    print("Online Learning Platform - Backend Test")
    print("=" * 60)

    all_passed = True

    print("\n[1/3] Testing imports...")
    all_passed &= test_imports()

    print("\n[2/3] Testing database...")
    all_passed &= test_database()

    print("\n[3/3] Testing API endpoints...")
    all_passed &= test_app()

    print("\n" + "=" * 60)
    if all_passed:
        print("[PASS] All tests passed!")
    else:
        print("[FAIL] Some tests failed")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
