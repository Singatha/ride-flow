# ADR-001: Start with a modular monolith

- Status: Accepted
- Date: 2026-09-06

## Context

RideFlow will eventually demonstrate messaging, real-time delivery, and distributed-system failure handling. Splitting undeveloped domains into services now would add deployment and consistency complexity without evidence that independent scaling or ownership is needed.

## Decision

Implement the backend as one FastAPI deployment with explicit domain modules and one PostgreSQL database. Keep transport, application, domain, and persistence concerns separable within each module. Extract a service only after documenting its ownership, data boundary, API/events, failure behavior, and scaling need.

## Consequences

Cross-domain operations can initially use database transactions and local calls. Module discipline must be maintained in code review because process boundaries do not enforce it. Later extraction remains work, but it will be guided by observed needs.

