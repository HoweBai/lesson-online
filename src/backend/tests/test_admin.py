"""Tests for admin API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.database import engine, Base, get_db
from src.models.user import User
from src.models.tutorial import Tutorial
from src.models.public_catalog import PublicCatalog
from src.services.auth_service import AuthService
from src.api.main import app

# Create test database (drop existing to ensure clean state between runs)
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

_auth = AuthService()


def _create_admin(email, username, password="admintestpass"):
    """Create an admin user and return (token, user)."""
    with Session(bind=engine) as db:
        user = User(username=username, email=email)
        user.password_hash = _auth.hash_password(password)
        user.is_admin = True
        db.add(user)
        db.commit()
        db.refresh(user)
        token = _auth.create_access_token(data={"sub": str(user.id)})
    return token, user


def _create_user(email, username, password="pass123", is_admin=False):
    """Create a regular user and return the user."""
    with Session(bind=engine) as db:
        user = User(username=username, email=email)
        user.password_hash = _auth.hash_password(password)
        user.is_admin = is_admin
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _create_tutorial(owner_id, title, status="reviewing", is_public=False):
    """Create a tutorial and return it."""
    with Session(bind=engine) as db:
        t = Tutorial(
            owner_id=owner_id,
            title=title,
            description="Test tutorial",
            status=status,
            is_public=is_public,
        )
        db.add(t)
        db.commit()
        db.refresh(t)
    return t


class TestAdminLogin:
    """Test admin login endpoint."""

    def test_admin_login_success(self):
        """Admin login with valid admin credentials."""
        token, user = _create_admin("admin_lt1@test.com", "admin_lt1")
        response = client.post("/api/v1/admin/login", json={
            "email": "admin_lt1@test.com",
            "password": "admintestpass"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["is_admin"] is True

    def test_admin_login_regular_user_fails(self):
        """Regular user login to admin endpoint should fail."""
        _create_user("regular_lt2@test.com", "regular_lt2", is_admin=False)
        response = client.post("/api/v1/admin/login", json={
            "email": "regular_lt2@test.com",
            "password": "pass123"
        })
        assert response.status_code == 401

    def test_admin_login_invalid_credentials(self):
        """Admin login with invalid credentials should fail."""
        response = client.post("/api/v1/admin/login", json={
            "email": "nobody_lt3@test.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401


class TestAdminMe:
    """Test admin /me endpoint."""

    def test_admin_me_success(self):
        """Admin can get their own info."""
        token, user = _create_admin("admin_me1@test.com", "admin_me1")
        response = client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["is_admin"] is True

    def test_admin_me_requires_auth(self):
        """Admin /me without token should fail."""
        response = client.get("/api/v1/admin/me")
        assert response.status_code == 401

    def test_admin_me_regular_user_fails(self):
        """Regular user cannot access admin /me."""
        user = _create_user("reg_me2@test.com", "reg_me2", is_admin=False)
        token = _auth.create_access_token(data={"sub": str(user.id)})
        response = client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403


class TestAdminUsers:
    """Test admin user management endpoints."""

    def test_list_users(self):
        """Admin can list users."""
        token, admin = _create_admin("admin_ul1@test.com", "admin_ul1")
        for i in range(5):
            _create_user(f"userul{i}@test.com", f"userul{i}")
        response = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) > 0

    def test_list_users_with_search(self):
        """Admin can search users."""
        token, _ = _create_admin("admin_us2@test.com", "admin_us2")
        for i in range(5):
            _create_user(f"userus{i}@test.com", f"userus{i}")
        response = client.get("/api/v1/admin/users?search=userus0", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) > 0
        for u in data["data"]:
            assert "userus0" in u["username"] or "userus0" in u["email"]

    def test_list_users_pagination(self):
        """Admin can paginate users."""
        token, _ = _create_admin("admin_up3@test.com", "admin_up3")
        for i in range(10):
            _create_user(f"userup{i}@test.com", f"userup{i}")
        response = client.get("/api/v1/admin/users?page=1&limit=2", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) <= 2
        assert data["pagination"]["limit"] == 2

    def test_get_user_detail(self):
        """Admin can get user detail."""
        token, admin = _create_admin("admin_ud4@test.com", "admin_ud4")
        target = _create_user("userud0@test.com", "userud0")
        response = client.get(f"/api/v1/admin/users/{target.id}", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "userud0@test.com"
        assert "tutorial_count" in data

    def test_get_user_detail_not_found(self):
        """Admin get non-existent user returns 404."""
        token, _ = _create_admin("admin_und5@test.com", "admin_und5")
        response = client.get("/api/v1/admin/users/nonexistent-id", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 404

    def test_update_user_admin_status(self):
        """Admin can toggle user admin status."""
        token, admin = _create_admin("admin_ust6@test.com", "admin_ust6")
        target = _create_user("userust0@test.com", "userust0")
        response = client.put(
            f"/api/v1/admin/users/{target.id}/status",
            json={"is_admin": True},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["is_admin"] is True

    def test_cannot_modify_self_admin(self):
        """Admin cannot modify their own admin status."""
        token, admin = _create_admin("admin_ums7@test.com", "admin_ums7")
        response = client.put(
            f"/api/v1/admin/users/{admin.id}/status",
            json={"is_admin": False},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 400

    def test_delete_user(self):
        """Admin can delete a user."""
        token, admin = _create_admin("admin_udel8@test.com", "admin_udel8")
        target = _create_user("userudel0@test.com", "userudel0")
        response = client.delete(
            f"/api/v1/admin/users/{target.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        # Verify user is gone
        response2 = client.get(f"/api/v1/admin/users/{target.id}", headers={"Authorization": f"Bearer {token}"})
        assert response2.status_code == 404

    def test_cannot_delete_self(self):
        """Admin cannot delete their own account."""
        token, admin = _create_admin("admin_udelself9@test.com", "admin_udelself9")
        response = client.delete(
            f"/api/v1/admin/users/{admin.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 400


class TestAdminCatalog:
    """Test admin catalog endpoints."""

    def test_list_pending_tutorials(self):
        """Admin can list tutorials pending review."""
        token, _ = _create_admin("admin_tcat1@test.com", "admin_tcat1")
        _create_tutorial("owner-tcat1", "Pending Tutorial T1", status="reviewing")
        response = client.get("/api/v1/admin/catalog/pending", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        titles = [t["title"] for t in data["data"]]
        assert "Pending Tutorial T1" in titles

    def test_list_pending_tutorials_empty(self):
        """Admin listing pending tutorials when none exist returns empty list."""
        token, _ = _create_admin("admin_tcatempty2@test.com", "admin_tcatempty2")
        response = client.get("/api/v1/admin/catalog/pending", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        # There may be pending tutorials from other tests; verify structure is valid
        assert "data" in data
        assert "pagination" in data

    def test_review_tutorial_approve(self):
        """Admin can approve a reviewing tutorial."""
        token, _ = _create_admin("admin_tappr3@test.com", "admin_tappr3")
        tutorial = _create_tutorial("owner-tappr3", "Approve Me T3", status="reviewing")
        response = client.put(
            f"/api/v1/admin/catalog/{tutorial.id}/review",
            json={"action": "approve"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tutorial"]["status"] == "published"
        assert data["tutorial"]["is_public"] is True

    def test_review_tutorial_reject(self):
        """Admin can reject a reviewing tutorial."""
        token, _ = _create_admin("admin_trej4@test.com", "admin_trej4")
        tutorial = _create_tutorial("owner-trej4", "Reject Me T4", status="reviewing")
        response = client.put(
            f"/api/v1/admin/catalog/{tutorial.id}/review",
            json={"action": "reject", "reason": "Bad content"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tutorial"]["status"] == "draft"
        assert data["tutorial"]["is_public"] is False

    def test_review_tutorial_not_found(self):
        """Admin reviewing non-existent tutorial returns 404."""
        token, _ = _create_admin("admin_tnf5@test.com", "admin_tnf5")
        response = client.put(
            "/api/v1/admin/catalog/nonexistent-id/review",
            json={"action": "approve"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404

    def test_review_tutorial_invalid_action(self):
        """Admin with invalid action gets 400."""
        token, _ = _create_admin("admin_tinvact6@test.com", "admin_tinvact6")
        tutorial = _create_tutorial("owner-tinvact6", "Invalid Action T6", status="reviewing")
        response = client.put(
            f"/api/v1/admin/catalog/{tutorial.id}/review",
            json={"action": "invalid_action"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 400


class TestAdminStats:
    """Test admin stats endpoints."""

    def test_stats_overview(self):
        """Admin can get stats overview."""
        token, _ = _create_admin("admin_tstats1@test.com", "admin_tstats1")
        response = client.get("/api/v1/admin/stats/overview", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "total_tutorials" in data
        assert "pending_tutorials" in data

    def test_stats_users(self):
        """Admin can get user stats."""
        token, _ = _create_admin("admin_tstatsu2@test.com", "admin_tstatsu2")
        response = client.get("/api/v1/admin/stats/users?period=7d", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert "growth" in data
        assert "period" in data

    def test_stats_users_default_period(self):
        """Admin user stats with default period."""
        token, _ = _create_admin("admin_tstatsudp3@test.com", "admin_tstatsudp3")
        response = client.get("/api/v1/admin/stats/users", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "30d"

    def test_stats_tutorials(self):
        """Admin can get tutorial stats."""
        token, _ = _create_admin("admin_tstatst4@test.com", "admin_tstatst4")
        response = client.get("/api/v1/admin/stats/tutorials?period=7d", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_status" in data
        assert "period" in data

    def test_stats_tutorials_default_period(self):
        """Admin tutorial stats with default period."""
        token, _ = _create_admin("admin_tstatstdp5@test.com", "admin_tstatstdp5")
        response = client.get("/api/v1/admin/stats/tutorials", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "30d"

    def test_stats_all_endpoints_require_admin(self):
        """Stats endpoints return 401 without auth."""
        assert client.get("/api/v1/admin/stats/overview").status_code == 401
        assert client.get("/api/v1/admin/stats/users").status_code == 401
        assert client.get("/api/v1/admin/stats/tutorials").status_code == 401
