"""Logging configuration and utilities for the Online Learning Platform."""

import logging
import sys
import os
from datetime import datetime
from typing import Optional
import json


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }

        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            log_data["data"] = record.extra_data

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""

    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[35m",   # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        log_message = super().format(record)
        return f"{color}{log_message}{self.RESET}"


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    json_format: bool = False
):
    """Setup logging configuration."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    if json_format:
        console_formatter = JSONFormatter()
    else:
        console_formatter = ColoredFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_formatter = JSONFormatter()
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Log startup message
    logging.info(f"Logging configured: level={level}, file={log_file}, json={json_format}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


class LogContext:
    """Context manager for structured logging."""

    def __init__(self, logger: logging.Logger, context: dict):
        self.logger = logger
        self.context = context

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def info(self, message: str, **kwargs):
        extra = {**self.context, **kwargs}
        self.logger.info(message, extra={"extra_data": extra})

    def error(self, message: str, **kwargs):
        extra = {**self.context, **kwargs}
        self.logger.error(message, exc_info=True, extra={"extra_data": extra})

    def warning(self, message: str, **kwargs):
        extra = {**self.context, **kwargs}
        self.logger.warning(message, extra={"extra_data": extra})


def log_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration: float,
    user_id: Optional[str] = None
):
    """Log HTTP request details."""
    log_data = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration * 1000, 2),
        "user_id": user_id
    }

    if status_code >= 500:
        logger.error(f"HTTP {status_code} - {method} {path}", extra={"extra_data": log_data})
    elif status_code >= 400:
        logger.warning(f"HTTP {status_code} - {method} {path}", extra={"extra_data": log_data})
    else:
        logger.info(f"HTTP {status_code} - {method} {path}", extra={"extra_data": log_data})
