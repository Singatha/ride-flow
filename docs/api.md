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

## Drivers

All self-service driver endpoints require the `DRIVER` role.

- `POST /api/v1/drivers/profile` creates one profile per driver. It accepts `license_number` and a future `license_expiry`; new profiles start `PENDING` and `OFFLINE`.
- `GET /api/v1/drivers/me` returns the authenticated driver's profile.
- `PATCH /api/v1/drivers/me` updates licence credentials. A credential change resets verification to `PENDING` and availability to `OFFLINE`.
- `PUT /api/v1/drivers/location` atomically inserts or replaces the current PostGIS point. The public contract uses `{latitude, longitude}` and accepts optional heading, speed, accuracy, and timezone-aware recording time.
- `PUT /api/v1/drivers/status/online` moves an offline driver to `AVAILABLE` only when their profile is approved, licence is valid, an active vehicle exists, and a location has been recorded.
- `PUT /api/v1/drivers/status/offline` returns an available driver to `OFFLINE`.
- `PUT /api/v1/drivers/{driver_id}/verification` is admin-only and sets `PENDING`, `APPROVED`, `REJECTED`, or `SUSPENDED`. Removing approval also takes a non-trip driver offline.

The status operations are idempotent when the driver is already in the requested state. `RESERVED` and `ON_TRIP` transitions belong to the ride/matching domains and cannot be set through these endpoints.

## Vehicles

- `POST /api/v1/vehicles` creates a vehicle owned by the authenticated driver's profile.
- `GET /api/v1/vehicles/me` lists only the authenticated driver's vehicles.
- `PATCH /api/v1/vehicles/{vehicle_id}` updates an owned vehicle.

Vehicles can change only while the driver is `OFFLINE`. Activating one vehicle atomically deactivates the driver's others, and the database independently enforces at most one active vehicle per driver. Licence plates are normalized to uppercase and globally unique.

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
