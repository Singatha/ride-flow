# Events

RideFlow does not publish events in Phase 1. Kafka is intentionally deferred until the ride lifecycle is working and there are real downstream consumers.

When events are introduced, the common envelope will include:

- `event_id`
- `event_type`
- `event_version`
- `occurred_at`
- `aggregate_id`
- `correlation_id`
- `payload`

Consumers must tolerate duplicate delivery. Database side effects will record processed event IDs, and payment operations will additionally use domain idempotency keys. A transactional outbox will later close the gap between committing domain state and publishing an event.

Likely first event: `ride.completed`, consumed by payments, notifications, and analytics only after those workflows and failure semantics exist.

