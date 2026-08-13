"""Script to initialize an admin user for the platform."""

from src.database import engine, Base, get_session
from src.models.user import User
from src.services.auth_service import AuthService
import os

DEFAULT_ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@tlcw.com")
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
DEFAULT_ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")


def create_admin_user():
    """Create or update the default admin user."""
    db = get_session()
    auth = AuthService()

    # Check if admin already exists
    admin = db.query(User).filter_by(email=DEFAULT_ADMIN_EMAIL).first()
    if admin:
        admin.is_admin = True
        admin.password_hash = auth.hash_password(DEFAULT_ADMIN_PASSWORD)
        print(f"Updated existing admin: {admin.email}")
    else:
        admin = User(
            username=DEFAULT_ADMIN_USERNAME,
            email=DEFAULT_ADMIN_EMAIL,
            is_admin=True,
        )
        admin.password_hash = auth.hash_password(DEFAULT_ADMIN_PASSWORD)
        db.add(admin)
        print(f"Created admin user: {admin.email}")

    db.commit()
    db.close()
    print(f"Admin ready: {DEFAULT_ADMIN_EMAIL} / {DEFAULT_ADMIN_PASSWORD}")


if __name__ == "__main__":
    create_admin_user()
