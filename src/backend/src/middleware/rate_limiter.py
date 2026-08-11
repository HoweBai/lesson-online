"""Rate limiting middleware using slowapi."""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
import logging

logger = logging.getLogger(__name__)

# In-memory storage for rate limits (no Redis dependency)
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=["60/minute", "1000/hour"],
)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Handle rate limit exceeded errors."""
    logger.warning(f"Rate limit exceeded for {request.client.host} on {request.url.path}")
    return Response(
        content='{"detail": "Rate limit exceeded. Please try again later."}',
        status_code=429,
        media_type="application/json"
    )
