# P0 Security Fixes — Design Spec

**Date**: 2026-08-14  
**Scope**: Startup key validation, WebSocket header auth, room-level access control

---

## Overview

Three P0 security issues identified in the function completeness audit:

1. Hardcoded key defaults allow weak encryption if env vars are missing in production
2. WebSocket JWT token passed as URL query parameter, exposed in logs and browser history
3. No room-level permission control — anyone with a tutorial URL can join its chat

## Section 1: Startup Environment Validation

### Goal
Fail fast on boot if critical environment variables are missing or use default/unsafe values.

### Required env vars (validated at startup)

| Variable | Constraint | Failure mode |
|----------|-----------|--------------|
| `SECRET_KEY` | Must exist, not default string | RuntimeError on boot |
| `CRYPTO_KEY_HEX` | Must exist, 64+ hex chars, not all zeros | RuntimeError on boot |
| `POSTGRES_PASSWORD` | Must be non-empty | RuntimeError on boot |
| `MINIO_ACCESS_KEY` | Must be non-empty | RuntimeError on boot |
| `MINIO_SECRET_KEY` | Must be non-empty | RuntimeError on boot |

### Implementation
- New function `validate_required_env()` in `src/backend/src/api/main.py`
- Called at end of existing `startup_event()`
- Uses `logging.ERROR` + `raise RuntimeError()` on failure

### Files changed
- `src/backend/src/api/main.py` (+~25 lines)

## Section 2: WebSocket Header Authentication

### Goal
Move JWT token from URL query parameter to WebSocket subprotocol header.

### Backend change (`websocket.py`)
- Replace `websocket.query_params.get("token")` with `websocket.headers.get("token")`
- Support both `token` header and `authorization: Bearer <token>` format
- Same JWT decode logic, same rejection behavior (WS_1008_POLICY_VIOLATION)

### Frontend change (`ClaudeChatSidebar.tsx`)
- Replace `new WebSocket(url)` with `new WebSocket(url, ['token', authToken])`
- Token still read from `localStorage.getItem('auth_token')`
- No other frontend changes needed

### Files changed
- `src/backend/src/api/websocket.py` (~5 lines changed)
- `src/frontend/src/components/ClaudeChatSidebar.tsx` (~1 line changed)

## Section 3: Room-Level Access Control

### Permission rules

| User status | Tutorial state | Result |
|-------------|---------------|--------|
| Authenticated owner | Any status | ✅ Allowed |
| Authenticated user | Public + published | ✅ Allowed |
| Unauthenticated | Public + published | ✅ Allowed (existing behavior) |
| Unauthenticated | Private or non-published | ❌ Rejected |
| Authenticated non-owner | Private or draft | ❌ Rejected |

### Implementation
- After auth token validation, query tutorial from DB
- Check `tutorial.owner_id == user_id` → allow
- Check `tutorial.is_public and tutorial.status == 'published'` → allow
- Otherwise → reject with `WS_1008_POLICY_VIOLATION` and reason "No access to this tutorial"

### Files changed
- `src/backend/src/api/websocket.py` (~20 lines added)

## Scope Summary

| File | Lines changed | Risk |
|------|--------------|------|
| `main.py` | +25 | Low — new startup function |
| `websocket.py` | ~25 net | Medium — auth flow change |
| `ClaudeChatSidebar.tsx` | ~1 | Low — subprotocol only |

**No database migrations. No new dependencies. No API contract changes.**
