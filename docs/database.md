# Database

PostgreSQL is RideFlow's persistent source of truth. The `postgis/postgis:16-3.4` image provides geospatial capabilities that the driver and ride phases will use for indexed proximity queries.

## Schema management

Alembic owns all schema changes. Revision `20260906_0001` enables PostGIS. Revision `20260906_0002` adds `users`, the PostgreSQL `user_role` enum, and `refresh_tokens`. SQLAlchemy metadata uses a naming convention so generated constraint and index names remain deterministic.

Alembic autogeneration is restricted to application-owned metadata. PostGIS and Tiger/geocoder tables are extension-owned and must never appear as drop operations in RideFlow migrations.

## Authentication tables

`users` stores normalized unique email addresses, Argon2 password hashes, role, profile fields, activation state, and timestamps. Passwords and refresh-token plaintext are never persisted.

`refresh_tokens` stores a unique SHA-256 token digest, user, family, optional parent, expiration, and revocation time. Family indexes support replay response: presenting an already-revoked token revokes all still-active descendants from that family. `SELECT ... FOR UPDATE` serializes rotation of the same token.

Future models should use UUID identifiers, timezone-aware timestamps, foreign keys, and database constraints for invariants that the database can enforce. Monetary values must use fixed precision (`NUMERIC`/Python `Decimal`), never floating point.

## Sessions and transactions

The async session factory creates one session per request with `expire_on_commit=False`. It does not commit implicitly. Application services will own commit/rollback boundaries for atomic business operations.

## PostGIS guidance

Driver and ride coordinates will use an appropriate PostGIS geography type with a spatial index. Nearby-driver queries should use `ST_DWithin` to limit candidates and `ST_Distance` to rank them. The exact model and index will be introduced and tested in Phase 3 rather than guessed in the foundation.
