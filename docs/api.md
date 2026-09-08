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

## Rides

### `POST /api/v1/rides/estimate`

Requires `RIDER`. Accepts pickup and destination coordinates plus `STANDARD`, `PREMIUM`, or `XL`:

```json
{
  "pickup": {"latitude": -26.2041, "longitude": 28.0473},
  "destination": {"latitude": -26.1076, "longitude": 28.0567},
  "ride_type": "STANDARD"
}
```

Returns PostGIS distance, estimated duration, a database-priced fare and currency, and the compatible `AVAILABLE` driver count within 5 km. Distance is straight-line in Phase 5; a routing provider can later implement the same estimate boundary.

### Ride operations

- `POST /api/v1/rides` requires `RIDER`, recalculates the estimate, creates the ride, moves it from `REQUESTED` to `SEARCHING`, and starts proximity matching.
- `GET /api/v1/rides` returns the authenticated rider's or driver's ride history.
- `GET /api/v1/rides/{ride_id}` returns a participant's ride; administrators may inspect any ride.
- `GET /api/v1/rides/offers/current` requires `DRIVER` and returns that driver's single active targeted offer or `null`. The offer includes pickup distance and its response deadline.
- `POST /api/v1/rides/{ride_id}/accept` accepts only an active offer targeted to that driver. It atomically assigns the compatible driver and active vehicle, then changes the driver to `RESERVED`.
- `POST /api/v1/rides/{ride_id}/reject` declines the targeted offer, records the outcome, releases the driver, and immediately tries the next-nearest eligible driver. It returns 204.
- `POST /api/v1/rides/{ride_id}/arriving` moves the assigned ride to `DRIVER_ARRIVING`.
- `POST /api/v1/rides/{ride_id}/arrive` moves it to `DRIVER_ARRIVED`.
- `POST /api/v1/rides/{ride_id}/start` moves it to `IN_PROGRESS` and the driver to `ON_TRIP`.
- `POST /api/v1/rides/{ride_id}/complete` moves it to `COMPLETED`, records the Phase 4 final fare, and returns the driver to `AVAILABLE`.
- `POST /api/v1/rides/{ride_id}/cancel` allows the owning rider to cancel before the trip starts and releases an assigned driver.

Offers expire after the configured response window. The matching worker records `TIMED_OUT`, releases the driver claim, and advances to the next-nearest driver. Previously rejected or timed-out drivers are not offered the same ride again. Ride responses include assigned driver and vehicle details after acceptance. There is deliberately no generic status-update endpoint.

Invalid or repeated transitions return `INVALID_RIDE_TRANSITION`. Missing, expired, or already-processed offers return `RIDE_OFFER_NOT_FOUND`; an offer targeted to another driver returns `RIDE_ACCESS_DENIED`. One rider and one driver can each participate in at most one non-terminal ride.

## Health

- `GET /health` is a dependency-free liveness probe.
- `GET /ready` verifies PostgreSQL and Redis and returns 503 when either required dependency is unavailable.

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
