# Order Service create/read contract

Implemented Order-side contract, 2026-10-09. D3 is the main implementation/demo
guide; requirement IDs remain the team's M3/M4 identifiers. Credit's interface
below is a proposal awaiting its owner and real integration. No fake Credit
success is enabled in the runtime. Later lifecycle/event/UI work is not included.

## Identity and conventions

- Base `/v1`, camelCase JSON, UUID identifiers, whole-number credit units.
- Every business request needs `Authorization: Bearer <access token>`. Order
  forwards it to User `GET /v1/users/me`, which verifies the token/current session.
  Order uses only current user ID, ACTIVE status and system role; it neither
  trusts client actor IDs nor stores user tokens/profile data.
- Order owns relationship/role checks. User/Supplier failures are not bypassed.
  Health endpoints remain unauthenticated and do not check these dependencies.
- Fixed configured HTTP origins, redirects disabled, bounded dependency requests.
  Protect inter-service traffic with TLS or the deployment's trusted internal
  network. Never send credentials to browser-configured destinations.
- Safe errors: `{error: {code, message, correlationId, fieldErrors}}`; dependency
  bodies, SQL and credentials are not echoed. 401 means invalid identity, 403 is
  administrator denial, 404 hides inaccessible resources, 409 is a conflict or
  definitively closed creation, 422 is input validation, 503 is unavailable service/storage.

## Endpoints

| Method/path | Behavior |
| --- | --- |
| `POST /v1/orders` | Create with mandatory `Idempotency-Key`; 201 new, 200 successful replay, 202 unresolved operation. |
| `GET /v1/order-creations/{operationId}` | Creator-only progress; no mutation/finalization. 404 for other users. |
| `GET /v1/orders` | Available OPEN assessment list; excludes reached acceptance deadlines even before an expiry worker exists. Optional `supplierId`. |
| `GET /v1/orders/mine?relationship=requester` | Current user's requested orders across states. `courier` selects their assigned orders. |
| `GET /v1/orders/{orderId}` | Participant detail; other authenticated users get assessment data only while available, otherwise 404. |
| `GET /v1/orders/{orderId}/history` | Participant-only chronological transitions; initially null to OPEN. No privileged admin history bypass. |
| `GET /v1/admin/orders?requesterId={uuid}` | Current ADMIN/SUPER_ADMIN only; minimal D3 requester-order lookup. No admin mutations/disputes. |

Lists/history use `page` (1–1,000,000) and `pageSize` (1–50, default 20).
Response: `{items, page, pageSize, total}`. Lists sort created time descending,
then order ID descending; history sorts sequence ascending. Pagination is stable
within each request, not a frozen snapshot across requests. Unknown query fields
are rejected. Courier results remain empty until the later acceptance feature exists.

Assessment data: order ID, supplier ID/pickup snapshot, description, delivery
collection point, reward, state, deadlines and created time. Participant/admin
query data additionally includes requester/courier IDs and updated time. No
reservation IDs, email, user profile or authentication information are returned.
Free-text content is not an automatic PII scrubber; do not enter contact secrets.

## Create example

Use future timestamps, not the illustrative dates below. Keys accept 1–128 ASCII
letters/digits or `.`, `_`, `:`, `-`. Retain the same key and body across retries.

```http
POST /v1/orders
Authorization: Bearer {{accessToken}}
Idempotency-Key: {{creationKey}}
Content-Type: application/json
```

```json
{
  "supplierId": "550e8400-e29b-41d4-a716-446655440000",
  "itemDescription": "One vegetarian sandwich",
  "deliveryLocation": "COM3 level 1 collection point",
  "reward": 10,
  "acceptanceDeadline": "2026-10-10T12:30:00+08:00",
  "deliveryDeadline": "2026-10-10T13:00:00+08:00"
}
```

Descriptions are trimmed/nonblank, max 1000 characters; delivery location max 300.
Reward is an integer from 1 to 2,147,483,647; floats/booleans are rejected. These
limits are implementation choices, not extra backlog targets. Deadlines must be
ISO timestamps with offsets, normalized to UTC. Delivery is strictly later than
acceptance; acceptance must still be future at finalization. Protected/unknown
fields are rejected. Identity is never taken from the body.

Supplier normal detail `/api/v1/suppliers/{id}` must confirm ACTIVE. Name, building
area, pickup description, floor, optional coordinates and source updated time are
snapshotted. Later reads do not depend on Supplier. Validation is at a particular
instant, not an atomic cross-service lock against later deactivation. Permanent
Supplier deletion still needs a separately agreed race-safe reference protocol.

201/200 return the participant Order projection with generated `orderId`, OPEN,
requester ID, null courier, pickup snapshot and timestamps. Successful retry
returns the current Order projection without reserving twice or adding history.

202 includes `operationId`, `stage`, `statusUrl`, `retryCreation`, `errorCode` and
nullable `orderId`, plus Location and Retry-After headers. It means no successful
OPEN result is being claimed. Poll the status URL, then resend the **same POST
body and key** when `retryCreation=true`. The user's current session and Supplier
eligibility are rechecked. SUCCEEDED exposes the order ID; ABORTED is a final
failed attempt. A new attempt after ABORTED needs a new key. There is no operation
cleanup in this slice, so used keys remain reserved to their original request.

## Storage and recovery

- `creation_operations`: durable validated payload, request/key hashes, generated
  IDs, stage, lease token/deadline, retry timing and safe result. No balances/tokens.
- `orders`: only confirmed-funded records; external UUIDs are not foreign keys
  into another service. `order_history` has an Order-local foreign key.
- Finalization atomically inserts the Order and initial history and marks the
  operation SUCCEEDED. A storage error does not trigger an immediate blind release:
  a later attempt first rereads durable state to resolve an uncertain commit.
- Unique requester/key and order IDs arbitrate duplicate creation. A short durable
  lease with an unguessable fencing token prevents stale processors from changing
  current records. External HTTP calls happen outside DB transactions.
- The independent worker queries reservation status. Before deadline, it makes an
  attempt READY_TO_FINALIZE for a fresh requester retry; it never saves user tokens.
- After deadline or a definite failure, persist ABORTING before external compensation.
  Finalization cannot cross that fence. Persist ABORTED only after Credit confirms
  its own durable CLOSED fence. SUCCEEDED operations are never compensated here.
- Default scan 5 seconds, batch 50, 30-second lease; transient failures use capped
  exponential backoff/jitter (up to 60 seconds), without discarding operations.
  Safe deferred logs carry operation/order IDs and error codes, not request contents.
  Unavailable Credit or an incompatible contract remains visible/pending, not success.

## Proposed Credit interface — coordinate before implementation

The runtime client uses a dedicated `CREDIT_SERVICE_SECRET` as
`X-FoC-Service-Secret`. Credit must provision/validate an Order-specific identity
with only the permitted operations. This is **not** Supplier's secret or a user
bearer token. Credential rotation and final contract compatibility require the
Credit owner's agreement. Leave Credit settings blank until it is compatible;
new creation then returns 503 without creating an operation/reserving anything.

| Request | Required behavior |
| --- | --- |
| `PUT /v1/internal/order-reservations/{orderId}` | Body `{operationId, requesterId, amount}`; reserve atomically at most once per order. 201 first/200 replay; immutable identifiers and amount. 409 codes `INSUFFICIENT_CREDIT` or `WALLET_NOT_READY` are definitive negative responses. |
| `GET /v1/internal/order-reservations/{orderId}` | 200 authoritative status or 404 absent at that instant. A 404 does not rule out a delayed in-flight reserve. |
| `PUT /v1/internal/order-reservations/{orderId}/creation-abort` | Same body; 200/201 CLOSED only after releasing any reservation and durably fencing future reserve requests, even if no reservation exists yet. Idempotent; never reverse a transferred reward. |

Every successful response contains `operationId`, `orderId`, `requesterId`, integer
`amount`, `reservationId` and `state`. RESERVED/RELEASED/TRANSFERRED require a UUID
reservation ID; CLOSED may have null. Reserve must return RESERVED; abort must
return CLOSED. Order validates identifiers/amount, rejects unexpected fields and
fails safely on malformed or mismatched responses. RESERVED is not proof of
completion/transfer; those belong to later terminal-event integration.

Credit abort must serialize against reserve for the same order. Merely releasing
an existing reservation is insufficient: a delayed reserve could arrive afterward.
This proposed creation-abort operation compensates an unpublished attempt; it is
not cancellation of an OPEN Order and does not fabricate a lifecycle event.

## Verification and remaining work

Unit/API tests cover validation, current identity, privacy/admin checks, replay,
timeout/deadline recovery and dependency contracts with explicit doubles. Real
PostgreSQL tests exercise competing requests, leases, transaction rollback,
lost commit acknowledgments, grants and queries in a disposable database.

These advance M3F1/M3F2, initial M3F7 history and related security/retry invariants.
They do not prove real Credit integration, NFR load targets or D3's required
meaningful terminal-event consumer effect. Credit conservation/ledger correctness
remains Credit-owned. Acceptance, terminal events, later state changes, UI and
shared container orchestration are future branches.
