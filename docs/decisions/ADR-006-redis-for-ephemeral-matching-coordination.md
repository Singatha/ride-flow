# ADR-006: Use Redis for ephemeral matching coordination

- Status: Accepted
- Date: 2026-09-08

## Context

Matching can run concurrently in API requests and background workers. One ride must have only one active offer, and one driver must not receive simultaneous offers. Offers and response deadlines are short-lived, but outcomes must survive process or cache failure.

## Decision

Use Redis Lua scripts for atomic ride/driver offer claims, expiring offer state, deadline ordering, and short per-ride distributed locks. Keep rides, driver availability, locations, and match attempts authoritative in PostgreSQL.

Persist every claimed offer as a `ride_match_attempts` row. PostgreSQL partial unique indexes independently enforce one live offer per ride and driver. On Redis state loss, the matching worker reconstructs a still-valid offer from PostgreSQL or records it as timed out before continuing.

Redis persistence is disabled in local Compose because no Redis value is authoritative.

## Consequences

- Concurrent API and worker processes coordinate without process-local locks.
- A Redis restart can temporarily delay matching but cannot erase ride or offer history.
- Matching depends on both PostgreSQL and Redis, so readiness checks both.
- The application must maintain compensation and recovery paths around the Redis-to-PostgreSQL boundary.
- Redis is not used as a duplicate driver-location database.
