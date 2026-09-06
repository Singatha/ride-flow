# Database

PostgreSQL is RideFlow's persistent source of truth. The `postgis/postgis:16-3.4` image provides geospatial capabilities for indexed proximity queries.

## Schema management

Alembic owns all schema changes. Revision `20260906_0001` enables PostGIS, `0002` adds authentication, `0003` adds drivers, and `0004` adds pricing and rides. SQLAlchemy metadata uses a naming convention so generated constraint and index names remain deterministic.

Alembic autogeneration is restricted to application-owned metadata. PostGIS and Tiger/geocoder tables are extension-owned and must never appear as drop operations in RideFlow migrations.

## Authentication tables

`users` stores normalized unique email addresses, Argon2 password hashes, role, profile fields, activation state, and timestamps. Passwords and refresh-token plaintext are never persisted.

`refresh_tokens` stores a unique SHA-256 token digest, user, family, optional parent, expiration, and revocation time. Family indexes support replay response: presenting an already-revoked token revokes all still-active descendants from that family. `SELECT ... FOR UPDATE` serializes rotation of the same token.

## Driver tables

`driver_profiles` has a one-to-one foreign key to `users`, globally unique licence numbers, licence expiry, verification state, availability state, and timestamps. Indexed PostgreSQL enums constrain both state fields.

`vehicles` belongs to a driver profile. It stores identifying attributes, category, and activation state. A global unique constraint protects licence plates; a partial unique index on `driver_id WHERE is_active` guarantees no driver can have two active vehicles, even under concurrency.

`driver_locations` stores one current location per driver. The driver's foreign key is also its primary key, making location updates natural upserts. `location geography(Point, 4326)` is indexed with GiST. Heading, speed, and accuracy use check constraints, while `recorded_at` is indexed for future freshness cleanup and matching policy.

## Pricing and ride tables

`pricing_rules` stores one active rule per ride type using a partial unique index. Money and rate fields use fixed-precision `NUMERIC`; `average_speed_kph` supports the initial duration estimate. The Phase 4 migration seeds ZAR rules for `STANDARD`, `PREMIUM`, and `XL` so pricing is data rather than scattered constants.

`rides` stores rider, optional assigned driver and vehicle, the pricing rule used, ride type/state, pickup and destination geography points, estimates, final fare, and lifecycle timestamps. Capturing the vehicle preserves the assignment even if the driver's active vehicle changes after completion. The pickup has a GiST index for future matching queries. Compound indexes support rider history, driver work, and open-status scans.

Partial unique indexes constrain each rider and driver to at most one ride whose status is not `COMPLETED` or `CANCELLED`. These database invariants backstop row locking and remain effective if another code path is introduced later.

Future models should use UUID identifiers, timezone-aware timestamps, foreign keys, and database constraints for invariants that the database can enforce. Monetary values must use fixed precision (`NUMERIC`/Python `Decimal`), never floating point.

## Sessions and transactions

The async session factory creates one session per request with `expire_on_commit=False`. It does not commit implicitly. Application services will own commit/rollback boundaries for atomic business operations.

## PostGIS behavior

The driver repository finds `AVAILABLE`, approved drivers with active users and vehicles inside a radius using `ST_DWithin`, then ranks them using `ST_Distance`. Both distances are in metres because locations are stored as geography. Ride estimates use the same PostGIS distance semantics for pickup-to-destination straight-line distance. Integration tests execute these functions against PostGIS rather than substituting SQLite or Python distance calculations.
