# API

The JSON product API is rooted at `/api/v1`. Interactive OpenAPI documentation is available at `/docs`.

## Authentication

### `POST /api/v1/auth/register`

Creates a `RIDER` or `DRIVER`. Public `ADMIN` registration is rejected. Passwords require 12–128 characters.

```json
{
  "email": "rider@example.com",
  "password": "correct-horse-battery-staple",
  "role": "RIDER",
  "first_name": "Amina",
  "last_name": "Dlamini",
  "phone_number": "+27111234567"
}
```

Returns 201 with the user, a 15-minute JWT access token, and a rotating refresh token. Browser clients also receive the refresh token as an `HttpOnly` cookie.

### `POST /api/v1/auth/login`

Accepts `email` and `password`. Invalid email, password, and inactive-account attempts intentionally share the same 401 response to reduce account disclosure.

### `POST /api/v1/auth/refresh`

Accepts an optional `refresh_token` body field or the browser refresh cookie. The current database row is locked, revoked, and replaced atomically. Reusing a rotated token revokes its active family.

### `POST /api/v1/auth/logout`

Accepts the same refresh-token sources, revokes an active token, clears the browser cookie, and returns 204. Repeated logout is idempotent.

## Profile

- `GET /api/v1/users/me` returns the authenticated user's profile.
- `PATCH /api/v1/users/me` updates `first_name`, `last_name`, and `phone_number` only. Email, role, activation state, and identifiers cannot be changed through this endpoint.

Protected endpoints require `Authorization: Bearer <access_token>`. The API reloads the user for every authenticated request and rejects missing, invalid, expired, or deactivated subjects.

## Health

- `GET /health` is a dependency-free liveness probe.
- `GET /ready` verifies PostgreSQL and returns 503 when unavailable.

## Error contract

Expected application errors use:

```json
{
  "error": {
    "code": "INVALID_TOKEN",
    "message": "Access token is invalid or expired",
    "details": {}
  }
}
```

Request validation uses the same envelope with code `VALIDATION_ERROR`. Its details identify fields and safe messages but never echo rejected values such as passwords. Internal exceptions and stack traces are not returned to clients.
