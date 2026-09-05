# ADR-002: Use PostgreSQL and PostGIS as the source of truth

- Status: Accepted
- Date: 2026-09-06

## Context

The platform needs relational consistency for rides, assignments, payments, and ratings, plus indexed radius and distance queries for drivers.

## Decision

Use PostgreSQL 16 with PostGIS 3.4. Access it through SQLAlchemy 2's async API and evolve its schema exclusively through Alembic. Redis may later hold ephemeral location and coordination data, but PostgreSQL remains authoritative.

## Consequences

RideFlow can enforce transactional and relational invariants and use native spatial indexes/functions. Development requires the PostGIS-enabled database image, and geospatial behavior needs integration tests against PostgreSQL rather than SQLite substitutes.

