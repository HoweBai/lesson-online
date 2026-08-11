"""Health check and monitoring endpoints."""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
import time
import os
from datetime import datetime

from ..services.metrics import metrics, get_metrics_endpoint, get_metrics_text, update_business_metrics
from ..services.alert_service import alert_manager, get_recent_alerts, get_alert_stats

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitor", tags=["monitoring"])


@router.get("/health", include_in_schema=False)
async def health_check() -> Dict[str, Any]:
    """Detailed health check endpoint."""
    # Check system metrics
    uptime = time.time() - metrics.start_time
    memory_usage = _get_memory_usage()
    disk_usage = _get_disk_usage()

    # Determine health status
    status = "healthy"
    if memory_usage.get("used_percent", 0) > 90:
        status = "degraded"
    if disk_usage.get("used_percent", 0) > 95:
        status = "critical"

    return {
        "status": status,
        "service": "online-learning-platform-api",
        "version": "1.1.0",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": round(uptime, 2),
        "system": {
            "memory": memory_usage,
            "disk": disk_usage
        },
        "dependencies": {
            "database": await _check_database(),
            "redis": await _check_redis(),
            "storage": await _check_storage()
        }
    }


@router.get("/metrics", include_in_schema=False)
async def metrics_endpoint() -> Dict[str, Any]:
    """Prometheus metrics endpoint."""
    return get_metrics_endpoint()


@router.get("/metrics/text", include_in_schema=False)
async def metrics_text_endpoint() -> str:
    """Prometheus metrics in text format."""
    return get_metrics_text()


@router.get("/alerts/recent", response_model=Dict[str, Any])
async def recent_alerts(hours: int = 24, limit: int = 50) -> Dict[str, Any]:
    """Get recent alerts."""
    alerts = get_recent_alerts(hours, limit)
    stats = get_alert_stats()
    return {
        "alerts": alerts,
        "stats": stats,
        "total": len(alerts)
    }


@router.get("/alerts/stats", response_model=Dict[str, Any])
async def alert_stats() -> Dict[str, Any]:
    """Get alert statistics."""
    return get_alert_stats()


@router.get("/status", response_model=Dict[str, Any])
async def system_status() -> Dict[str, Any]:
    """Get overall system status."""
    health = await health_check()
    alerts = get_recent_alerts(hours=1, limit=10)

    return {
        "health": health,
        "recent_alerts": alerts,
        "metrics": get_metrics_endpoint()
    }


async def _check_database() -> Dict[str, Any]:
    """Check database connectivity."""
    try:
        from ..database import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


async def _check_redis() -> Dict[str, Any]:
    """Check Redis connectivity."""
    try:
        import redis
        r = redis.Redis(host='redis', port=6379, db=0)
        r.ping()
        return {"status": "healthy"}
    except Exception:
        return {"status": "unknown", "note": "Redis check skipped (not required)"}


async def _check_storage() -> Dict[str, Any]:
    """Check storage availability."""
    try:
        # Check if backup directory exists
        backup_dir = "./backups"
        os.makedirs(backup_dir, exist_ok=True)
        return {"status": "healthy", "backup_dir": backup_dir}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def _get_memory_usage() -> Dict[str, Any]:
    """Get memory usage statistics."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            "total_mb": mem.total // (1024 * 1024),
            "used_mb": mem.used // (1024 * 1024),
            "free_mb": mem.free // (1024 * 1024),
            "used_percent": mem.percent
        }
    except ImportError:
        return {"status": "unknown"}


def _get_disk_usage() -> Dict[str, Any]:
    """Get disk usage statistics."""
    try:
        import psutil
        disk = psutil.disk_usage('/')
        return {
            "total_gb": disk.total // (1024 ** 3),
            "used_gb": disk.used // (1024 ** 3),
            "free_gb": disk.free // (1024 ** 3),
            "used_percent": disk.percent
        }
    except ImportError:
        return {"status": "unknown"}


@router.post("/alerts/test")
async def test_alert() -> Dict[str, str]:
    """Send a test alert."""
    from ..services.alert_service import AlertLevel, send_alert
    send_alert(
        AlertLevel.INFO,
        "This is a test alert",
        "monitor_test",
        {"test": True}
    )
    return {"message": "Test alert sent"}
