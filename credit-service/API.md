# Credit Service API and event contracts

Implemented Credit-side contract, 2026-10-13. Requirement IDs are the team backlog's
M4 (Credit) and M6 (async) identifiers. The Order-facing interface is the one Order
proposed in `order-service/API.md`, accepted unchanged.

## Identity and conventions

- Base `/v1`, camelCase JSON, UUID identifiers, whole-number credit units.
- User routes need `Authorization: Bearer <access token>`. Credit forwards it to User
  `GET /v1/users/me` (as Order does) and uses only the current user ID and system role.
  The caller's identity is never taken from a path, query or body.
- Order-only routes need `X-FoC-Service-Secret` equal to `ORDER_SERVICE_SECRET`
  (Order's `CREDIT_SERVICE_SECRET`). They are not routed by the edge proxy; Order calls
  `http://credit-service:8003` directly over the internal Compose network.
- Safe errors: `{error: {code, message, correlationId, fieldErrors}}`. 401 invalid
  identity or service credential, 403 role denial, 404 missing, 409 definitive business
  rejection, 422 validation, 503 dependency/storage unavailable or Credit unconfigured.
- Every wallet starts with `INITIAL_CREDIT_ALLOCATION` credits (team value: **20**).

## Endpoints

| Method/path | Caller | Behaviour |
| --- | --- | --- |
| `GET /v1/wallets/me` | Any active user | Own `{userId, available, reserved, total, updatedAt}`; `total = available + reserved`. A user who predates Credit gets their wallet (and the allocation) here on first use. |
| `GET /v1/wallets/me/transactions?page&pageSize` | Any active user | Own ledger page, newest first, including incoming transfers. `pageSize` 1–50 (default 20). |
| `GET /v1/admin/wallets/{userId}` | ADMIN, SUPER_ADMIN | Read-only; 404 `WALLET_NOT_READY` if none. Never creates a wallet. |
| `GET /v1/admin/wallets/{userId}/transactions` | ADMIN, SUPER_ADMIN | Read-only ledger page for that user. |
| `PUT /v1/internal/order-reservations/{orderId}` | Order | Body `{operationId, requesterId, amount}`. 201 reserved, 200 replay (same identity). 409 `INSUFFICIENT_CREDIT`, `WALLET_NOT_READY` (only if no allocation is configured) or `IDENTITY_CONFLICT`. A missing requester wallet is get-or-created first. |
| `GET /v1/internal/order-reservations/{orderId}` | Order | 200 current reservation or 404 absent at that instant. |
| `PUT /v1/internal/order-reservations/{orderId}/creation-abort` | Order | Same body. 201 new CLOSED fence (no reservation existed), 200 otherwise. Releases a RESERVED hold; 409 `SETTLEMENT_CONFLICT` after a transfer. |
| `GET /health/live`, `GET /health/ready` | Operators | Liveness never touches the database; readiness checks the schema and tables. |

Reservation responses contain exactly `operationId, orderId, requesterId, amount,
reservationId, state`; Order's client rejects any extra field.

## Reservation states

| From | Trigger | To | Balances |
| --- | --- | --- | --- |
| (none) | reserve | RESERVED | requester available −amount, reserved +amount |
| (none) | creation-abort | CLOSED (no reservationId) | none; later reserves return the fence |
| RESERVED | `order.cancelled/expired/failed.v1` | RELEASED | requester reserved −amount, available +amount |
| RESERVED | `order.completed.v1` | TRANSFERRED | requester reserved −amount, courier available +amount |
| RESERVED | creation-abort | CLOSED | released as above |
| RELEASED | creation-abort | CLOSED | none |
| RELEASED/CLOSED | release event | unchanged | none (`NO_CHANGE`) |
| TRANSFERRED | release event | unchanged | none (M4F5.2) |
| RELEASED/CLOSED | completion event | unchanged | DLQ `SETTLEMENT_CONFLICT` |
| TRANSFERRED | creation-abort | unchanged | 409 `SETTLEMENT_CONFLICT` |

## Consumed events

Credit binds the durable queue `credit-service.events` to the topic exchange `foc.events`
for exactly these routing keys. The AMQP `type` must equal the payload's `eventType`.

```json
{"eventId": "…", "eventType": "user.registered.v1", "userId": "…", "occurredAt": "2026-10-13T00:00:00Z"}
{"eventId": "…", "eventType": "order.cancelled.v1", "orderId": "…", "reservationId": "…", "occurredAt": "…"}
{"eventId": "…", "eventType": "order.completed.v1", "orderId": "…", "reservationId": "…",
 "occurredAt": "…", "requesterId": "…", "courierId": "…", "amount": 5}
```

`order.expired.v1` and `order.failed.v1` have the cancellation shape. Unknown fields are
rejected. Completion must match the reservation's requester and amount; a missing
courier wallet is get-or-created before the transfer.

## Delivery, retries and dead letters

- Delivery is at least once. Each event is applied in one transaction that also records
  its `eventId` in `processed_events`; a redelivery returns `DUPLICATE` with no change.
  The message is acknowledged only after that transaction commits.
- Temporary failures (database unavailable, wallet not ready) are republished to
  `credit-service.events.retry`, whose TTL (`CONSUMER_RETRY_DELAY_SECONDS`, default 5)
  dead-letters them back to the main queue. After `CONSUMER_MAX_ATTEMPTS` (default 5,
  minimum 3) they go to `credit-service.events.dlq`. The attempt is carried in the
  `x-foc-attempt` header and the error code in `x-foc-error`.
- Permanent failures (invalid event, unknown reservation, identity or settlement
  conflict) go straight to the DLQ. Every failure is logged and recorded in
  `event_failures`. A DLQ message needs an operator: fix the cause, then move it back
  to `credit-service.events` from the RabbitMQ UI.
- Republishing waits for the broker's publisher confirm before the original is
  acknowledged; if the broker fails, the original stays unacknowledged and is redelivered.
- Events for different orders are processed independently. A completion for a courier
  without a wallet get-or-creates that wallet before transferring.

## Storage

| Table | Guarantees |
| --- | --- |
| `wallets` | One row per user (PK); `available >= 0`, `reserved >= 0` checks. |
| `order_reservations` | One row per order (PK); state machine checks; `TRANSFERRED` iff courier set. |
| `credit_transactions` | Append-only ledger (runtime role: SELECT/INSERT). One allocation per wallet and one reservation/release/transfer row per reservation (unique indexes). |
| `processed_events` | Inbox: one row per successfully processed event (`APPLIED`/`NO_CHANGE`). |
| `event_failures` | Every failed attempt, with `dead_lettered`. |

Each operation takes a transaction-scoped advisory lock on its order (or user), then
locks the affected wallet rows `FOR UPDATE` in user-ID order, then checks and updates.

## Verification

`tests/` covers the HTTP contract, validation, identity and role checks, and consumer
routing with explicit doubles. `tests/integration/` runs against a disposable migrated
Credit database (`CREDIT_TEST_DATABASE_URL`) and RabbitMQ (`CREDIT_TEST_RABBITMQ_URL`):
grants and constraints, one allocation per user under concurrency, no overdraw under
20 concurrent reserves, exactly-once transfer under 5 concurrent duplicate events,
release-after-transfer, abort racing reserve, credit conservation, and real-broker
deduplication and dead-lettering. Load targets (M4NFR2/M4NFR3) are not yet measured.
