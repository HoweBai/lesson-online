"""Tests for PDF export endpoint."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.api.main import app
from src.database import engine, Base, get_db
from src.services.auth_service import AuthService
from src.models.user import User
from src.models.tutorial import Tutorial
from datetime import datetime
import uuid

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


class TestPDFExport:
    """Test PDF export endpoint."""

    @pytest.fixture
    def auth_client(self):
        """Return a TestClient with auth headers pre-configured."""
        auth = AuthService()
        with Session(bind=engine) as db:
            try:
                result = auth.register(db, "pdfuser", "pdfuser@test.com", "testpass123")
                token = result["token"]
            except ValueError:
                user = db.query(User).filter(User.email == "pdfuser@test.com").first()
                token = auth.create_access_token(data={"sub": str(user.id)})
        c = TestClient(app)
        c.headers["Authorization"] = f"Bearer {token}"
        return c

    @pytest.fixture
    def test_tutorial(self, auth_client):
        """Create a test tutorial for PDF export."""
        with Session(bind=engine) as db:
            tutorial = Tutorial(
                owner_id="pdfuser",
                title="PDF Test Tutorial",
                description="A test tutorial for PDF export",
                status="published",
                is_public=True,
                total_chapters=2,
                current_chapter=1,
                created_at=datetime.utcnow(),
            )
            db.add(tutorial)
            db.commit()
            db.refresh(tutorial)
        return tutorial

    def test_pdf_export_unauthenticated(self, auth_client):
        """PDF export without auth returns 401."""
        auth_client.headers.clear()
        test_id = str(uuid.uuid4())
        resp = auth_client.get(f"/api/v1/tutorials/{test_id}/export/pdf")
        assert resp.status_code == 401

    def test_pdf_export_not_found(self, auth_client, test_tutorial):
        """PDF export for non-existent tutorial returns 404."""
        test_id = str(uuid.uuid4())
        resp = auth_client.get(f"/api/v1/tutorials/{test_id}/export/pdf")
        assert resp.status_code == 404

    @patch('src.services.export_service.ExportService.export_to_pdf')
    def test_pdf_export_success(self, mock_export, auth_client, test_tutorial):
        """PDF export returns PDF bytes with correct headers."""
        mock_export.return_value = {
            "tutorial_id": test_tutorial.id,
            "title": "PDF Test Tutorial",
            "format": "pdf",
            "size_bytes": 1024,
            "chapter_count": 2,
            "pdf_bytes": b"%PDF-1.4 mock pdf content",
        }
        resp = auth_client.get(f"/api/v1/tutorials/{test_tutorial.id}/export/pdf")
        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/pdf'
        assert 'attachment' in resp.headers['content-disposition']
        assert 'PDF_Test_Tutorial' in resp.headers['content-disposition']
        assert resp.content[:4] == b"%PDF"
        mock_export.assert_called_once()

    def test_pdf_export_with_mocked_weasyprint(self, auth_client, test_tutorial):
        """PDF export succeeds with mocked WeasyPrint (no system dependency)."""
        mock_html_cls = MagicMock()
        mock_html_instance = MagicMock()
        mock_html_instance.write_pdf.return_value = b"%PDF-1.4 test pdf content"
        mock_html_cls.return_value = mock_html_instance
        mock_css_cls = MagicMock()

        mock_weasyprint = MagicMock()
        mock_weasyprint.HTML = mock_html_cls
        mock_weasyprint.CSS = mock_css_cls

        with patch.dict('sys.modules', {'weasyprint': mock_weasyprint}):
            resp = auth_client.get(f"/api/v1/tutorials/{test_tutorial.id}/export/pdf")
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "application/pdf"
            assert "attachment" in resp.headers.get("content-disposition", "")
            assert "PDF_Test_Tutorial" in resp.headers["content-disposition"]
            assert len(resp.content) > 0
            assert resp.content[:4] == b"%PDF"

    @patch('src.services.export_service.ExportService.export_to_pdf')
    def test_pdf_export_weasyprint_not_installed(self, mock_export, auth_client, test_tutorial):
        """PDF export returns 501 when weasyprint unavailable."""
        mock_export.side_effect = RuntimeError("weasyprint is not installed")
        resp = auth_client.get(f"/api/v1/tutorials/{test_tutorial.id}/export/pdf")
        assert resp.status_code == 501
        assert "weasyprint" in resp.json()["detail"].lower()

    def test_pdf_export_unauthorized_tutorial(self, auth_client):
        """User cannot export another user's private tutorial."""
        auth = AuthService()
        with Session(bind=engine) as db:
            from src.models.user import User as UserModel
            other_user = db.query(UserModel).filter(UserModel.email == "other_testuser@test.com").first()
            if not other_user:
                other_user = User(username="other_testuser", email="other_testuser@test.com")
                other_user.password_hash = auth.hash_password("testpass123")
                db.add(other_user)
                db.commit()
                db.refresh(other_user)
            other_id = other_user.id

            from src.models.tutorial import Tutorial as TutorialModel
            other_tutorial = db.query(TutorialModel).filter(
                TutorialModel.owner_id == str(other_id),
                TutorialModel.title == "Private Tutorial"
            ).first()
            if not other_tutorial:
                other_tutorial = Tutorial(
                    owner_id=str(other_id),
                    title="Private Tutorial",
                    description="A private tutorial",
                    status="draft",
                    is_public=False,
                    created_at=datetime.utcnow(),
                )
                db.add(other_tutorial)
                db.commit()
                db.refresh(other_tutorial)

        # auth_client is pdfuser, trying to export otheruser's private tutorial
        resp = auth_client.get(f"/api/v1/tutorials/{other_tutorial.id}/export/pdf")
        assert resp.status_code == 404
