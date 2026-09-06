# ADR-005: Enforce ride transitions through explicit domain operations

- Status: Accepted
- Date: 2026-09-06

## Context

Ride status affects driver availability, cancellation rights, timestamps, future payments, and notifications. A generic status update would allow impossible jumps and make concurrent acceptance unsafe.

## Decision

Define the transition graph on the `Ride` entity and expose named operations: begin search, accept, mark arriving, mark arrived, start, complete, and cancel. No API accepts an arbitrary status.

Application services lock the ride before the driver, update both aggregates in one transaction, and return domain errors for illegal transitions. Partial unique database indexes constrain active rides per rider and driver as defense in depth.

## Consequences

Lifecycle rules have one testable source and timestamps are attached to the operation that causes them. Adding a state requires an intentional graph, API, migration, and test change. PostgreSQL-specific partial indexes mean concurrency integration tests must continue to run against the real database.
