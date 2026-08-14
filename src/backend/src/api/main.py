"""Main FastAPI application entry point with all routes configured."""

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import logging
import traceback

from ..database import engine, Base, get_db, migrate_db
from ..services.auth_service import AuthService, get_current_user
from ..models.user import User
from ..api.auth import auth_router
from ..api.tutorials import tutorials_router
from ..api.catalog import catalog_router
from ..api.websocket import router as websocket_router
from ..api.profile import router as profile_router
from ..api.export import router as export_router
from ..api.monitor import router as monitor_router
from ..api.backup import router as backup_router
from ..api.alerts import router as alerts_router
from ..api.security import security_router
from ..api.bookmarks import router as bookmarks_router
from ..api.comments import router as comments_router, router_comment as comment_likes_router
from ..api.oauth import oauth_router
from ..api.password_reset import router as password_reset_router
from ..api.admin import admin_router
from ..middleware.rate_limiter import limiter, rate_limit_handler
from slowapi.errors import RateLimitExceeded

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Online Learning Platform API",
    version="1.1.0",
    description="API platform for personalized AI-generated computer science tutorials",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Include routers
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
app.include_router(tutorials_router, prefix="/api/v1", tags=["tutorials"])
app.include_router(catalog_router, prefix="/api/v1", tags=["catalog"])
app.include_router(websocket_router)
app.include_router(profile_router, prefix="/api/v1", tags=["users"])
app.include_router(export_router, prefix="/api/v1", tags=["export"])
app.include_router(monitor_router)
app.include_router(backup_router)
app.include_router(alerts_router)
app.include_router(security_router, prefix="/api/v1", tags=["security"])
app.include_router(bookmarks_router, prefix="/api/v1", tags=["bookmarks"])
app.include_router(comments_router, prefix="/api/v1", tags=["comments"])
app.include_router(comment_likes_router, prefix="/api/v1", tags=["comments"])
app.include_router(password_reset_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1", tags=["admin"])
app.include_router(oauth_router, prefix="/api/v1", tags=["oauth"])

# Register rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler for all uncaught exceptions
@app.exception_handler(SQLAlchemyError)
async def db_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"Database error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal database error"}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Health check endpoint
@app.get("/health", include_in_schema=False)
def health_check():
    """Simple health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "online-learning-platform-api",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.1.0"
    }

# Root redirect
@app.get("/", include_in_schema=False)
def root_redirect():
    return {
        "message": "Welcome to Online Learning Platform API",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "websocket_status": "/ws/status",
            "monitor": "/monitor/health",
            "metrics": "/monitor/metrics"
        }
    }

# Startup event - create database tables and validate env
@app.on_event("startup")
async def startup_event():
    """Create all database tables on startup and validate required env vars."""
    validate_required_env()
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/initialized successfully")
        migrate_db()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def validate_required_env():
    """Validate that critical environment variables are set and not default values."""
    import os
    checks = [
        ("SECRET_KEY", lambda v: len(v) >= 32, "must be at least 32 characters"),
        ("CRYPTO_KEY_HEX", lambda v: len(v) >= 64 and v != "0" * 64, "must be 64+ hex chars and not all zeros"),
        ("POSTGRES_PASSWORD", lambda v: len(v) > 0, "must not be empty"),
        ("MINIO_ACCESS_KEY", lambda v: len(v) > 0, "must not be empty"),
        ("MINIO_SECRET_KEY", lambda v: len(v) > 0, "must not be empty"),
    ]

    errors = []
    for name, validator, constraint in checks:
        value = os.getenv(name)
        if value is None or not validator(value):
            errors.append(f"{name} is missing or invalid ({constraint})")

    if errors:
        for err in errors:
            logger.error(f"Env validation failed: {err}")
        raise RuntimeError("Required environment variables are missing or invalid. Check logs for details.")

# Shutdown event - clean up resources
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down Online Learning Platform API...")
