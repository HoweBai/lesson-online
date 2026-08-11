"""Alert configuration and notification service."""

import logging
import smtplib
from email.mime.text import MIMEText
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Represents a system alert."""
    level: AlertLevel
    message: str
    source: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details or {}
        }


class AlertManager:
    """Manages system alerts and notifications."""

    def __init__(self):
        self.alerts: List[Alert] = []
        self.notification_handlers: List[callable] = []
        self.max_alerts = 1000

    def add_notification_handler(self, handler: callable):
        """Add a notification handler (e.g., email, webhook)."""
        self.notification_handlers.append(handler)

    def send_alert(
        self,
        level: AlertLevel,
        message: str,
        source: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """Send an alert and notify handlers."""
        alert = Alert(
            level=level,
            message=message,
            source=source,
            timestamp=datetime.utcnow(),
            details=details
        )

        self.alerts.append(alert)

        # Keep only recent alerts
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]

        # Log the alert
        log_method = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical
        }.get(level, logger.info)

        log_method(f"[{level.value.upper()}] {message} (source: {source})")

        # Notify handlers
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")

        return alert

    def get_recent_alerts(self, hours: int = 24, limit: int = 50) -> List[Dict]:
        """Get recent alerts."""
        cutoff = datetime.utcnow().timestamp() - (hours * 3600)
        recent = [
            a.to_dict()
            for a in self.alerts
            if a.timestamp.timestamp() > cutoff
        ]
        return recent[-limit:]

    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics."""
        stats = {
            "total": len(self.alerts),
            "by_level": {
                level.value: sum(1 for a in self.alerts if a.level == level)
                for level in AlertLevel
            },
            "last_24h": len([
                a for a in self.alerts
                if a.timestamp.timestamp() > datetime.utcnow().timestamp() - 86400
            ])
        }
        return stats


class EmailNotifier:
    """Sends alert notifications via email."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        from_email: str,
        password: str,
        recipients: List[str]
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_email = from_email
        self.password = password
        self.recipients = recipients

    def send(self, alert: Alert):
        """Send alert via email."""
        if not self.recipients:
            return

        subject = f"[OLL Platform Alert] {alert.level.value.upper()}: {alert.message[:50]}"
        body = f"""
Alert Details:
==============
Level: {alert.level.value.upper()}
Message: {alert.message}
Source: {alert.source}
Time: {alert.timestamp.isoformat()}

Details:
{alert.details or "None"}
        """

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.from_email
        msg['To'] = ', '.join(self.recipients)

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.from_email, self.password)
                server.sendmail(self.from_email, self.recipients, msg.as_string())
            logger.info(f"Email alert sent to {self.recipients}")
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")


class WebhookNotifier:
    """Sends alert notifications via webhook (e.g., Slack, Discord)."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        import httpx
        self.client = httpx.AsyncClient(timeout=10.0)

    async def send(self, alert: Alert):
        """Send alert via webhook."""
        color = {
            AlertLevel.INFO: "363490",
            AlertLevel.WARNING: "FFA500",
            AlertLevel.ERROR: "FF0000",
            AlertLevel.CRITICAL: "8B0000"
        }.get(alert.level, "808080")

        payload = {
            "embeds": [{
                "title": f"Alert: {alert.message[:50]}",
                "color": int(color, 16),
                "fields": [
                    {"name": "Level", "value": alert.level.value.upper(), "inline": True},
                    {"name": "Source", "value": alert.source, "inline": True},
                    {"name": "Time", "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"), "inline": True}
                ],
                "footer": {"text": "Online Learning Platform Alert System"}
            }]
        }

        try:
            response = await self.client.post(self.webhook_url, json=payload)
            response.raise_for_status()
            logger.info(f"Webhook alert sent successfully")
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")


# Global alert manager instance
alert_manager = AlertManager()


def send_alert(
    level: AlertLevel,
    message: str,
    source: str,
    details: Optional[Dict[str, Any]] = None
) -> Alert:
    """Send an alert through the global alert manager."""
    return alert_manager.send_alert(level, message, source, details)


def get_recent_alerts(hours: int = 24, limit: int = 50) -> List[Dict]:
    """Get recent alerts."""
    return alert_manager.get_recent_alerts(hours, limit)


def get_alert_stats() -> Dict[str, Any]:
    """Get alert statistics."""
    return alert_manager.get_alert_stats()
