"""Tests for export API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.api.main import app
from src.database import engine, Base, get_db
from src.services.auth_service import AuthService
from unittest.mock import patch, MagicMock
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
            try:
                result = auth.register(db, "testexpuser", "exp@test.com", "testpass123")
                token = result["token"]
            except ValueError:
                from src.models.user import User
                user = db.query(User).filter(User.email == "exp@test.com").first()
                token = auth.create_access_token(data={"sub": str(user.id)})
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

    def test_export_pdf_requires_auth(self, auth_client):
        """Test that PDF export requires authentication."""
        auth_client.headers.clear()
        test_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_id}/export/pdf")
        assert response.status_code == 401

    def test_export_pdf_not_found(self, auth_client):
        """Test PDF export on non-existent tutorial."""
        test_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_id}/export/pdf")
        assert response.status_code == 404

    def test_export_pdf_success(self, auth_client):
        """Test PDF export on existing tutorial."""
        from src.models.tutorial import Tutorial
        from src.models.chapter import Chapter
        from datetime import datetime
        import sys

        # Create tutorial in the same database as auth_client
        with Session(bind=engine) as db:
            tutorial = Tutorial(
                owner_id="testexpuser",
                title="Test PDF Tutorial",
                description="A test tutorial for PDF export",
                status="published",
                is_public=True,
                total_chapters=1,
                current_chapter=1,
                created_at=datetime.utcnow()
            )
            db.add(tutorial)
            db.commit()
            db.refresh(tutorial)

            chapter = Chapter(
                tutorial_id=tutorial.id,
                chapter_number=1,
                title="Introduction",
                status="completed",
                generated_at=datetime.utcnow()
            )
            db.add(chapter)
            db.commit()
            tutorial_id = tutorial.id

        # Mock weasyprint to avoid requiring system dependencies
        mock_html_cls = MagicMock()
        mock_html_instance = MagicMock()
        mock_html_instance.write_pdf.return_value = b"%PDF-1.4 test pdf content"
        mock_html_cls.return_value = mock_html_instance
        mock_css_cls = MagicMock()

        mock_weasyprint = MagicMock()
        mock_weasyprint.HTML = mock_html_cls
        mock_weasyprint.CSS = mock_css_cls

        with patch.dict('sys.modules', {'weasyprint': mock_weasyprint}):
            response = auth_client.get(f"/api/v1/tutorials/{tutorial_id}/export/pdf")
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/pdf"
            assert "attachment" in response.headers.get("content-disposition", "")
            assert "Test_PDF_Tutorial" in response.headers["content-disposition"]
            assert len(response.content) > 0
            assert response.content[:4] == b"%PDF"
