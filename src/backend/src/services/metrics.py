"""Prometheus metrics and monitoring for the Online Learning Platform."""

import time
import logging
from datetime import datetime
from typing import Dict, Any
from collections import defaultdict

logger = logging.getLogger(__name__)

# Global metrics storage
_metrics: Dict[str, Any] = {
    "request_count": defaultdict(int),
    "error_count": defaultdict(int),
    "response_time": defaultdict(list),
    "active_users": 0,
    "total_tutorials": 0,
    "total_chapters": 0,
    "outline_generations": 0,
    "chapter_generations": 0,
    "failed_generations": 0,
    "start_time": time.time()
}

# Metrics names for Prometheus
METRIC_NAMES = {
    "http_requests_total": "Total HTTP requests",
    "http_errors_total": "Total HTTP errors",
    "http_request_duration_seconds": "HTTP request duration",
    "ollp_active_users": "Active users",
    "ollp_total_tutorials": "Total tutorials",
    "ollp_total_chapters": "Total chapters",
    "ollp_outline_generations": "Outline generations",
    "ollp_chapter_generations": "Chapter generations",
    "ollp_failed_generations": "Failed generations",
}


class MetricsCollector:
    """Collects and exposes application metrics."""

    def __init__(self):
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.response_times: Dict[str, list] = defaultdict(list)

    def increment_request(self, path: str, status_code: int = 200):
        """Increment request counter."""
        self.request_count += 1
        _metrics["request_count"][path] += 1

        if status_code >= 400:
            self.error_count += 1
            _metrics["error_count"][path] += 1

    def record_response_time(self, path: str, duration: float):
        """Record response time for a request."""
        self.response_times[path].append(duration)
        # Keep only last 1000 measurements
        if len(self.response_times[path]) > 1000:
            self.response_times[path] = self.response_times[path][-1000:]

    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics in Prometheus format."""
        return {
            "http_requests_total": self.request_count,
            "http_errors_total": self.error_count,
            "ollp_active_users": _metrics["active_users"],
            "ollp_total_tutorials": _metrics["total_tutorials"],
            "ollp_total_chapters": _metrics["total_chapters"],
            "ollp_outline_generations": _metrics["outline_generations"],
            "ollp_chapter_generations": _metrics["chapter_generations"],
            "ollp_failed_generations": _metrics["failed_generations"],
            "uptime_seconds": time.time() - self.start_time,
            "response_times": {
                path: {
                    "avg": sum(times) / len(times) if times else 0,
                    "max": max(times) if times else 0,
                    "min": min(times) if times else 0,
                    "count": len(times)
                }
                for path, times in self.response_times.items()
            }
        }

    def reset(self):
        """Reset metrics."""
        self.request_count = 0
        self.error_count = 0
        self.response_times.clear()
        logger.info("Metrics reset")


# Global metrics collector instance
metrics = MetricsCollector()


def get_metrics_endpoint() -> Dict[str, Any]:
    """Get metrics in JSON format for Prometheus scraping."""
    return metrics.get_metrics()


def get_metrics_text() -> str:
    """Get metrics in Prometheus text format."""
    m = metrics.get_metrics()
    lines = []
    lines.append("# HELP http_requests_total Total HTTP requests")
    lines.append("# TYPE http_requests_total counter")
    lines.append(f'http_requests_total {{status="all"}} {m["http_requests_total"]}')

    lines.append("# HELP http_errors_total Total HTTP errors")
    lines.append("# TYPE http_errors_total counter")
    lines.append(f'http_errors_total {{status="all"}} {m["http_errors_total"]}')

    lines.append("# HELP ollp_active_users Active users")
    lines.append("# TYPE ollp_active_users gauge")
    lines.append(f'ollp_active_users {m["ollp_active_users"]}')

    lines.append("# HELP ollp_total_tutorials Total tutorials")
    lines.append("# TYPE ollp_total_tutorials gauge")
    lines.append(f'ollp_total_tutorials {m["ollp_total_tutorials"]}')

    lines.append("# HELP ollp_total_chapters Total chapters")
    lines.append("# TYPE ollp_total_chapters gauge")
    lines.append(f'ollp_total_chapters {m["ollp_total_chapters"]}')

    lines.append("# HELP ollp_outline_generations Outline generations")
    lines.append("# TYPE ollp_outline_generations gauge")
    lines.append(f'ollp_outline_generations {m["ollp_outline_generations"]}')

    lines.append("# HELP ollp_chapter_generations Chapter generations")
    lines.append("# TYPE ollp_chapter_generations gauge")
    lines.append(f'ollp_chapter_generations {m["ollp_chapter_generations"]}')

    lines.append("# HELP ollp_failed_generations Failed generations")
    lines.append("# TYPE ollp_failed_generations gauge")
    lines.append(f'ollp_failed_generations {m["ollp_failed_generations"]}')

    lines.append("# HELP uptime_seconds Uptime in seconds")
    lines.append("# TYPE uptime_seconds gauge")
    lines.append(f'uptime_seconds {m["uptime_seconds"]}')

    return "\n".join(lines)


def update_business_metrics(db_stats: Dict[str, int]):
    """Update metrics from database statistics."""
    _metrics["total_tutorials"] = db_stats.get("tutorials", 0)
    _metrics["total_chapters"] = db_stats.get("chapters", 0)
