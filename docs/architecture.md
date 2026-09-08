# Architecture

## Current context

RideFlow begins as a modular monolith: one backend process and one relational source of truth. This makes transactions and local development straightforward while module boundaries preserve an extraction path if scaling or ownership later justifies it.

```mermaid
flowchart TB
    subgraph Client
        UI[React + Ant Design]
        Query[TanStack Query]
        UI --> Query
    end
    subgraph Backend[FastAPI modular monolith]
        Routes[Thin HTTP routes]
        Services[Application services]
        Domains[Auth, user, driver, ride, and matching rules]
        Persistence[SQLAlchemy repositories]
        Routes --> Services --> Domains
        Services --> Persistence
    end
    Query --> Routes
    Persistence --> PG[(PostgreSQL + PostGIS)]
    Services --> Redis[(Redis coordination)]
    Worker[Matching worker] --> Services
```

## Repository boundaries

- `backend/app/api`: transport concerns and versioned routes
- `backend/app/core`: configuration and future cross-cutting infrastructure
- `backend/app/database`: engine, sessions, metadata, and common persistence primitives
- `backend/migrations`: the only supported mechanism for schema evolution
- `frontend/src/api`: typed browser-to-API calls
- `frontend/src/app`: composition, providers, and routing
- `frontend/src/pages` and `components`: presentation

The `users`, `auth`, `drivers`, `rides`, and `matching` domains demonstrate the module pattern: HTTP routes parse and serialize, services own transactions, repositories own queries, and models/schemas define persistence and contracts. Later domains should follow this boundary without adding abstraction that has no concrete use.

## Runtime and health semantics

`GET /health` is a liveness probe and performs no dependency I/O. `GET /ready` executes a minimal database query and Redis ping, returning 503 when either required dependency is unavailable. This distinction prevents a dependency incident from causing an orchestrator to endlessly restart an otherwise healthy API process.

The API uses an async engine with connection pre-ping. Sessions are request-scoped and do not auto-commit; future services must make transaction boundaries explicit.

## Deferred infrastructure

- WebSockets arrive with real-time tracking and will call application services rather than contain business rules.
- Kafka arrives after core workflows work synchronously. Event envelopes, idempotent consumers, and eventually an outbox will be implemented together.
- Metrics and tracing arrive in the observability phase after meaningful workflows exist to instrument.

## Authentication flow

```mermaid
sequenceDiagram
    participant B as Browser
    participant A as FastAPI
    participant D as PostgreSQL
    B->>A: login(email, password)
    A->>D: load user + verify Argon2 hash
    A->>D: store refresh-token digest
    A-->>B: JWT access token + HttpOnly refresh cookie
    B->>A: protected request with Bearer JWT
    A->>D: load active user
    A-->>B: response
    B->>A: refresh with cookie
    A->>D: lock, revoke old token, insert child
    A-->>B: new access token + rotated cookie
```

The backend does not trust the JWT role claim for authorization; it reloads the active user, so deactivation and role changes take effect immediately. Public clients cannot register administrators. Production startup rejects the development JWT secret. Expected errors use a stable envelope without stack traces.

The browser holds access tokens only in memory. Refresh tokens are stored in `HttpOnly`, `SameSite=Lax` cookies and as SHA-256 digests in PostgreSQL. Non-browser clients may use the refresh token from the response body.

Rate limiting, structured request correlation, and security-event audit logs remain future reliability/observability work. A distributed rate limiter should arrive with Redis rather than using a misleading process-local counter.

## Driver availability and location

```mermaid
flowchart LR
    D[DRIVER account] --> P[Driver profile]
    P -->|admin approval| A[Approved]
    P --> V[One active vehicle]
    P --> L[(Current PostGIS location)]
    A --> O{Go online}
    V --> O
    L --> O
    O --> AV[AVAILABLE]
    AV -->|Go offline| OFF[OFFLINE]
```

The API exchanges coordinates as latitude and longitude. Persistence constructs WGS84 points in the spatial convention `POINT(longitude latitude)`. A GiST index supports `ST_DWithin` candidate filtering, while `ST_Distance` produces metre-based ordering because the column uses `geography`.

Vehicle activation and availability changes lock the driver-profile row, serializing competing changes for one driver. A partial unique index is the final safeguard that only one vehicle can be active. Location publication uses PostgreSQL `ON CONFLICT DO UPDATE`, so the single current-location row is replaced atomically.

The nearby-driver repository supplies matching candidates through an indexed `ST_DWithin` filter and `ST_Distance` ordering. Vehicle category and driver availability are applied inside the query. PostgreSQL remains authoritative for location; Redis is not a second location store.

## Ride lifecycle

```mermaid
stateDiagram-v2
    [*] --> REQUESTED
    REQUESTED --> SEARCHING
    SEARCHING --> DRIVER_ASSIGNED: accept
    DRIVER_ASSIGNED --> DRIVER_ARRIVING: mark_arriving
    DRIVER_ARRIVING --> DRIVER_ARRIVED: mark_arrived
    DRIVER_ARRIVED --> IN_PROGRESS: start
    IN_PROGRESS --> COMPLETED: complete
    REQUESTED --> CANCELLED: cancel
    SEARCHING --> CANCELLED: cancel
    DRIVER_ASSIGNED --> CANCELLED: cancel
    DRIVER_ARRIVING --> CANCELLED: cancel
    DRIVER_ARRIVED --> CANCELLED: cancel
```

The entity exposes explicit operations for this graph. Routes cannot write arbitrary status values. Application services coordinate ride and driver state in one PostgreSQL transaction.

Acceptance locks the ride row before the driver row. Competing drivers therefore observe the first committed assignment and only one can succeed. Partial unique indexes provide an independent final guard against multiple active rides for a rider or driver. All ride operations use this same lock ordering to limit deadlock risk.

Phase 5 uses targeted offers and short HTTP polling. Phase 6 replaces offer and active-ride polling with WebSocket updates.

## Driver matching

```mermaid
sequenceDiagram
    participant R as Rider
    participant A as API
    participant P as PostgreSQL/PostGIS
    participant C as Redis
    participant D as Driver
    participant W as Matching worker
    R->>A: request ride
    A->>P: create SEARCHING ride
    A->>C: acquire per-ride matching lock
    A->>P: nearest compatible untried drivers
    A->>C: atomically claim ride + driver, schedule deadline
    A->>P: persist OFFERED attempt
    D->>A: accept or reject targeted offer
    A->>P: lock rows and record outcome
    A->>C: release ephemeral claim
    W->>C: read due deadlines
    W->>P: record TIMED_OUT and select next driver
```

PostgreSQL is the durable source of truth. `ride_match_attempts` records each targeted driver and the terminal offer outcome, which prevents re-offering the same ride-driver pair. Partial unique indexes allow only one `OFFERED` attempt per ride and per driver. Final acceptance locks the ride and driver rows before assigning the vehicle and changing the driver to `RESERVED`.

Redis stores `ride:{id}:offer`, `driver:{id}:offer`, a sorted deadline set, and short per-ride matching locks. A Lua script creates the ride offer and driver claim together, so concurrent matchers cannot target one driver twice. These keys are deliberately non-durable: after Redis state loss, the worker reads `SEARCHING` rides and restores their still-valid PostgreSQL offer. Expired offers become `TIMED_OUT`; stale ephemeral keys without a corresponding durable attempt are discarded.

The worker also revisits unmatched `SEARCHING` rides, allowing newly available drivers and transient Redis outages to recover without changing ride state. Offer duration, state retention, lock duration, and worker interval are configuration values. Notifications and WebSockets remain Phase 6 concerns.
