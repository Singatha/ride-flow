# ADR-004: Keep authoritative driver location in PostGIS during Phase 3

- Status: Accepted
- Date: 2026-09-06

## Context

Driver onboarding needs durable current locations and indexed proximity queries. Redis could make high-frequency access cheaper, but introducing it now would create dual-write consistency and recovery questions before ride matching or live tracking exists.

## Decision

Store one current WGS84 `geography(Point, 4326)` per driver in PostgreSQL. Use an atomic upsert for publication, a GiST spatial index, `ST_DWithin` for radius filtering, and `ST_Distance` for ranking. Keep the nearby-driver operation behind the driver repository until matching consumes it.

PostgreSQL remains authoritative after Redis is introduced in Phase 5. Redis coordinates offers and reservations but does not cache driver location; expiry and recovery behavior are defined in ADR-006.

## Consequences

Phase 3 has one consistent source of truth and geospatial behavior can be verified with real PostGIS integration tests. A later tracking phase may add a higher-frequency location path, but it must define freshness and recovery without weakening persistent correctness.
