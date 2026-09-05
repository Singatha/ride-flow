# API

The HTTP API uses JSON and will place business endpoints under `/api/v1`. Interactive OpenAPI documentation is available at `/docs` while the server is running.

## Foundation endpoints

### `GET /health`

Liveness probe. Returns 200 without checking dependencies:

```json
{"status": "ok"}
```

### `GET /ready`

Readiness probe. Returns `200 {"status":"ready"}` when PostgreSQL accepts a query. Returns 503 when the database cannot be reached.

Health endpoints are intentionally unversioned because infrastructure consumes them rather than product clients. Product endpoints added in later phases will be mounted under `/api/v1`.

## Error contract

Phase 2 will add a central exception boundary for product errors in this shape:

```json
{
  "error": {
    "code": "MACHINE_READABLE_CODE",
    "message": "Safe client-facing explanation",
    "details": {}
  }
}
```

No business endpoints exist in Phase 1.

