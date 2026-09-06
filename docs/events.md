# Events

RideFlow does not publish events yet. The synchronous ride lifecycle now provides event-producing operations, but Kafka remains intentionally deferred until Phase 8, after payments and notifications provide real downstream consumers.

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
