# ADR-004: Keep authoritative driver location in PostGIS during Phase 3

- Status: Accepted
- Date: 2026-09-06

## Context

Driver onboarding needs durable current locations and indexed proximity queries. Redis could make high-frequency access cheaper, but introducing it now would create dual-write consistency and recovery questions before ride matching or live tracking exists.

## Decision

Store one current WGS84 `geography(Point, 4326)` per driver in PostgreSQL. Use an atomic upsert for publication, a GiST spatial index, `ST_DWithin` for radius filtering, and `ST_Distance` for ranking. Keep the nearby-driver operation behind the driver repository until matching consumes it.

PostgreSQL remains authoritative when Redis is introduced in Phase 5. That phase must define cache population, expiry, atomic reservation, and fallback behavior rather than treating cached location as durable state.

## Consequences

Phase 3 has one consistent source of truth and geospatial behavior can be verified with real PostGIS integration tests. PostgreSQL will not be the final high-frequency fan-out path, and a later phase must add freshness policy plus Redis without weakening persistent correctness.
