import pytest
from fastapi import FastAPI, Depends, Request
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded

from src.middleware.rate_limiter import limiter, rate_limit_handler


@pytest.fixture
def app_with_limiter():
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

    @app.get("/test")
    def test_endpoint(request: Request):
        return {"ok": True}

    @app.post("/restricted")
    def restricted_endpoint(request: Request):
        return {"ok": True}

    return app


@pytest.fixture
def client_with_limiter(app_with_limiter):
    return TestClient(app_with_limiter)


def test_rate_limiter_default_limit(client_with_limiter):
    """Requests without explicit rate limits should use the default limit."""
    assert client_with_limiter.get("/test").status_code == 200


def test_rate_limiter_exceeded(client_with_limiter):
    """Requests exceeding the per-endpoint limit should return 429."""
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    endpoint_limiter = Limiter(
        key_func=get_remote_address,
        storage_uri="memory://",
    )

    app = FastAPI()
    app.state.limiter = endpoint_limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

    @app.post("/restricted")
    @endpoint_limiter.limit("2/minute")
    def restricted_endpoint(request: Request):
        return {"ok": True}

    client = TestClient(app)
    assert client.post("/restricted").status_code == 200
    assert client.post("/restricted").status_code == 200
    response = client.post("/restricted")
    assert response.status_code == 429
    assert "Rate limit" in response.json()["detail"]
