"""Tests for service layer functions."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta


class TestAuthService:
    """Tests for AuthService class."""

    @pytest.fixture
    def auth_service(self):
        from src.services.auth_service import AuthService
        return AuthService()

    @pytest.fixture
    def mock_db(self):
        from unittest.mock import MagicMock
        db = MagicMock()
        return db

    def test_create_access_token(self, auth_service):
        """Test JWT token creation."""
        token = auth_service.create_access_token({"sub": "user-123"})
        assert token is not None
        assert isinstance(token, str)

    def test_hash_password(self, auth_service):
        """Test password hashing."""
        hashed = auth_service.hash_password("testpassword")
        assert hashed is not None
        assert len(hashed) > 50

    def test_verify_password(self, auth_service):
        """Test password verification."""
        password = "testpassword"
        hashed = auth_service.hash_password(password)
        assert auth_service.verify_password(password, hashed) is True
        assert auth_service.verify_password("wrongpassword", hashed) is False

    def test_login_success(self, auth_service, mock_db):
        """Test successful login."""
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.password_hash = auth_service.hash_password("testpass")
        mock_user.to_dict.return_value = {"id": "user-123", "username": "test"}

        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = auth_service.login(mock_db, "test@test.com", "testpass")
        assert "user" in result
        assert "token" in result

    def test_login_invalid_credentials(self, auth_service, mock_db):
        """Test login with invalid credentials."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Invalid credentials"):
            auth_service.login(mock_db, "test@test.com", "wrongpass")


class TestCryptoService:
    """Tests for crypto service."""

    def test_encrypt_decrypt(self):
        """Test AES-GCM encryption and decryption."""
        from src.services.crypto_service import SecureCryptoService
        import os

        key = os.urandom(32)
        crypto = SecureCryptoService(key)

        api_key = "sk-test-123456789"
        encrypted = crypto.encrypt_api_key(api_key)
        decrypted = crypto.decrypt_api_key(encrypted)

        assert decrypted == api_key


class TestKnowledgeInferencer:
    """Tests for knowledge inferencer."""

    def test_infer_knowledge_graph_default(self):
        """Test default knowledge inference."""
        from src.services.knowledge_inferencer import DynamicKnowledgeInferencer

        inferencer = DynamicKnowledgeInferencer()
        result = inferencer.infer_knowledge_graph({})

        assert isinstance(result, dict)
        assert "algorithm_fundamentals" in result
        assert "data_structures" in result

    def test_infer_knowledge_graph_with_profile(self):
        """Test knowledge inference with profile data."""
        from src.services.knowledge_inferencer import DynamicKnowledgeInferencer

        inferencer = DynamicKnowledgeInferencer()
        profile = {
            "programming_level": 4,
            "math_background": "linear algebra",
            "learning_goal": "research"
        }

        result = inferencer.infer_knowledge_graph(profile)
        assert result["algorithm_fundamentals"] == "intermediate"

    def test_validate_mastery_map(self):
        """Test mastery map validation."""
        from src.services.knowledge_inferencer import DynamicKnowledgeInferencer

        inferencer = DynamicKnowledgeInferencer()
        # Use a complete map with all required keys
        valid_map = {
            "algorithm_fundamentals": "beginner",
            "data_structures": "intermediate",
            "discrete_math": "beginner",
            "linear_algebra": "beginner",
            "calculus": "beginner",
            "probability": "beginner",
            "graph_theory": "beginner",
            "recursion": "beginner",
            "dynamic_programming": "beginner",
            "machine_learning_prerequisites": "beginner"
        }
        assert inferencer.validate_mastery_map(valid_map) is True


class TestPrerequisiteChecker:
    """Tests for prerequisite checker."""

    def test_check_prerequisites(self):
        """Test prerequisite checking."""
        from src.services.prerequisite_checker import PrerequisiteChecker

        checker = PrerequisiteChecker()
        needs_review, missing = checker.check_prerequisites(
            "dynamic_programming",
            {"recursion": "advanced", "mathematical_induction": "beginner"}
        )

        assert needs_review is True
        assert "mathematical_induction" in missing

    def test_check_prerequisites_pass(self):
        """Test when prerequisites are met."""
        from src.services.prerequisite_checker import PrerequisiteChecker

        checker = PrerequisiteChecker()
        needs_review, missing = checker.check_prerequisites(
            "dynamic_programming",
            {"recursion": "advanced", "mathematical_induction": "advanced"}
        )

        assert needs_review is False


class TestOutlineGenerator:
    """Tests for outline generator."""

    def test_build_outline_prompt(self):
        """Test prompt building for outline generation."""
        from src.services.outline_generator import OutlineGenerator
        from unittest.mock import MagicMock

        db = MagicMock()
        crypto = MagicMock()
        config_service = MagicMock()

        generator = OutlineGenerator(db, crypto, config_service)
        prompt = generator.build_outline_prompt({}, {}, ["algorithms"])

        assert "algorithms" in prompt
        assert "JSON" in prompt


class TestChapterGenerator:
    """Tests for chapter generator."""

    def test_build_chapter_prompt(self):
        """Test prompt building for chapter generation."""
        from src.services.chapter_generator import ChapterGenerator
        from unittest.mock import MagicMock

        db = MagicMock()
        crypto = MagicMock()
        config_service = MagicMock()

        generator = ChapterGenerator(db, crypto, config_service)
        prompt = generator.build_chapter_prompt(1, "Test Chapter", {})

        assert "Test Chapter" in prompt
        assert "JSON" in prompt


class TestExportService:
    """Tests for export service."""

    def test_export_to_markdown(self):
        """Test markdown export."""
        from src.services.export_service import ExportService
        from unittest.mock import MagicMock

        db = MagicMock()
        export_service = ExportService(db)

        # Create mock tutorial
        mock_tutorial = MagicMock()
        mock_tutorial.id = "test-id"
        mock_tutorial.title = "Test Tutorial"
        mock_tutorial.description = "Test Description"
        mock_tutorial.status = "published"
        mock_tutorial.created_at = datetime.utcnow()
        mock_tutorial.owner_id = "owner-123"
        mock_tutorial.to_dict.return_value = {"id": "test-id", "title": "Test Tutorial"}
        mock_tutorial.outline = {"chapters": [{"title": "Chapter 1"}]}

        db.query.return_value.filter.return_value.first.return_value = mock_tutorial
        db.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = []

        result = export_service.export_to_markdown("test-id")
        assert "Test Tutorial" in result["content"]
        assert result["format"] == "markdown"
