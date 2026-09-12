# DrukAgriLink — API Guide

Interactive OpenAPI documentation: `GET /api/docs` (Swagger UI) and
`GET /api/openapi.json`. All endpoints are versioned under `/api/v1`.

## Endpoint groups

| Prefix | Purpose |
| --- | --- |
| `/auth` | register, login, refresh (rotating), logout |
| `/users` | profile, notification preferences, deactivation request |
| `/farmers`, `/farms`, `/farmer-groups` | farmer onboarding, membership, verification |
| `/locations`, `/products` | Bhutan location hierarchy, catalogue, varieties, grades |
| `/harvest-listings` | forecast → confirm lifecycle, revisions, publish/cancel |
| `/buyers`, `/buyer-orders` | organizations, procurement orders, publish/cancel |
| `/match-proposals` | generation, review chain, farmer allocation responses |
| `/transport-providers`, `/vehicles` | provider + fleet management |
| `/shipments` | planning, offers, trip acceptance, status, stop reorder |
| `/collections`, `/deliveries` | receipts, delivery confirmation |
| `/payments`, `/disputes` | obligation tracking, dispute workflow |
| `/notifications` | in-app centre |
| `/analytics` | role-scoped analytics |
| `/admin` | verification queues, users, audit logs, configuration |

## Authentication

`POST /api/v1/auth/login` returns an access token (30 min JWT) and a refresh
token (opaque, 14 days). Send `Authorization: Bearer <access_token>`. Refresh
tokens are single-use: `POST /auth/refresh` returns a new pair and invalidates
the old token; reusing a rotated token revokes the whole session family.

## Authorization

Role-based route guards plus object-level ownership policies. Cross-tenant
reads return **404** (existence is not leaked). Verification gates: unverified
farmers/buyers can create drafts but not publish.

## Pagination, filtering, sorting

List endpoints accept `page` (default 1) and `page_size` (default 20, max 100)
and return `{items, total, page, page_size}`. Domain filters are query
parameters (e.g. `status=`, `dzongkhag=`, `location_type=`, `unread_only=`).
Results have stable default orderings (documented per endpoint in OpenAPI).

## Error format

Every error uses one envelope:

```json
{
  "error": {
    "code": "HARVEST_QUANTITY_INVALID",
    "message": "Confirmed quantity cannot exceed available quantity.",
    "field": "confirmed_quantity",
    "request_id": "1f0c…"
  }
}
```

Validation errors add an `errors[]` list with per-field messages. State-machine
violations return `409 INVALID_STATE_TRANSITION` with `current`, `target`, and
`allowed`. Every response carries `X-Request-ID` for correlation.

## Concurrency / offline idempotency

Writes that offline clients replay (`PATCH /harvest-listings/{id}`,
`POST /harvest-listings/{id}/confirm`) accept `expected_row_version`. On
mismatch the API returns `409 CONFLICT_STALE_VERSION` including
`server_row_version` and a `server_state` snapshot so clients can render a
conflict-resolution screen instead of overwriting. Creation endpoints for
receipts and deliveries are naturally idempotent per stop/shipment
(`409 ALREADY_RECORDED` on duplicates).

## Example: the happy path

```bash
BASE=http://localhost:8000/api/v1
TOKEN=$(curl -s $BASE/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"coordinator@demo.drukagrilink.bt","password":"DrukDemo2026!"}' | jq -r .access_token)
AUTH="Authorization: Bearer $TOKEN"

curl -s $BASE/buyer-orders -H "$AUTH" | jq '.[0].id'          # published demand
curl -s $BASE/match-proposals/generate -H "$AUTH" \
  -H 'Content-Type: application/json' \
  -d '{"buyer_order_item_id":"<item-id>"}' | jq '.proposals[0].score_explanation'
```
