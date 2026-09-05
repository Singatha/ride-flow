# Database

PostgreSQL is RideFlow's persistent source of truth. The `postgis/postgis:16-3.4` image provides geospatial capabilities that the driver and ride phases will use for indexed proximity queries.

## Schema management

Alembic owns all schema changes. Revision `20260906_0001` enables PostGIS; Phase 1 defines no business tables. SQLAlchemy metadata uses a naming convention so generated constraint and index names remain deterministic.

Future models should use UUID identifiers, timezone-aware timestamps, foreign keys, and database constraints for invariants that the database can enforce. Monetary values must use fixed precision (`NUMERIC`/Python `Decimal`), never floating point.

## Sessions and transactions

The async session factory creates one session per request with `expire_on_commit=False`. It does not commit implicitly. Application services will own commit/rollback boundaries for atomic business operations.

## PostGIS guidance

Driver and ride coordinates will use an appropriate PostGIS geography type with a spatial index. Nearby-driver queries should use `ST_DWithin` to limit candidates and `ST_Distance` to rank them. The exact model and index will be introduced and tested in Phase 3 rather than guessed in the foundation.

