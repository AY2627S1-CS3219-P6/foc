# Order Service API and event contracts

Implemented Order-side contract, updated 2026-10-11. D3 is the main implementation/demo
guide; requirement IDs remain the team's M3/M4 identifiers. Credit's interface
below is a proposal awaiting its owner and real integration. No fake Credit
success is enabled in the runtime. This release adds acceptance, cancellation and
expiry, pickup, delivery, completion, unilateral failure and overdue tracking with durable terminal-event
publication. Real Credit consumption remains pending; publishing does not confirm wallet settlement.

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
  role/relationship denial, 404 hides inaccessible resources, 409 is a conflict or
  definitively closed creation, 422 is input validation, 503 is unavailable service/storage.

## Endpoints

| Method/path | Behavior |
| --- | --- |
| `POST /v1/orders` | Create with mandatory `Idempotency-Key`; 201 new, 200 successful replay, 202 unresolved operation. |
| `POST /v1/orders/{orderId}/accept` | Current non-requester accepts an eligible OPEN order; 200 participant view. |
| `POST /v1/orders/{orderId}/cancel` | Requester cancels an eligible OPEN order; 200 participant view, Credit release asynchronous. |
| `POST /v1/orders/{orderId}/pickup` | Assigned courier advances ACCEPTED to PICKED_UP. |
| `POST /v1/orders/{orderId}/deliver` | Assigned courier advances PICKED_UP to DELIVERED; no reward transfer yet. |
| `POST /v1/orders/{orderId}/complete` | Requester confirms DELIVERED to COMPLETED; atomically records transfer-event intent. |
| `POST /v1/orders/{orderId}/fail` | Either participant marks ACCEPTED/PICKED_UP as FAILED with a reason; atomically records release-event intent. |
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
are rejected. Courier results include orders assigned through acceptance.

Assessment data: order ID, supplier ID/pickup snapshot, description, delivery
collection point, reward, state, deadlines and created time. Participant/admin
query data additionally includes requester/courier IDs and updated time. No
reservation IDs, email, user profile or authentication information are returned.
Free-text content is not an automatic PII scrubber; do not enter contact secrets.

## Accept, cancel and expire (2026-10-11)

The two POST actions accept no body (or `{}`) and no query parameters. Caller
identity always comes from fresh User authentication. Client-supplied actors,
roles, state, deadlines and unknown fields are rejected with 422. No admin bypass.
Unlike creation, these actions do not require an idempotency key: the immutable
order/actor/action identifies the one permitted acceptance or cancellation.

| Action | Guard | Result / credit effect |
| --- | --- | --- |
| Accept | OPEN, not requester, database time strictly before acceptance deadline | ACCEPTED, assigned courier and acceptedAt; existing reservation stays reserved |
| Cancel | OPEN, requester, database time strictly before acceptance deadline | CANCELLED, cancelledAt and `order.cancelled.v1`; Credit release pending |
| Expire | OPEN, acceptance deadline reached/passed | EXPIRED, expiredAt and `order.expired.v1`; Credit release pending |

Expiry is an independent worker action, not a public endpoint or a side effect of
a rejected request. At deadline equality, both accept and cancel return 409
`DEADLINE_PASSED`, even if the worker has not persisted EXPIRED yet. OPEN listings
already exclude such orders. Expiry never changes ACCEPTED orders. `expiredAt`
is the actual persisted transition time, not a fabricated deadline timestamp;
compare it with acceptanceDeadline when measuring expiry latency.

Every mutation locks the Order row, obtains PostgreSQL `clock_timestamp()` after
the lock, rechecks guards, then commits state/timestamp, history and any terminal
outbox event in one transaction. No dependency call is made while holding the
lock. Accept/cancel races before the deadline produce one winner; at/after it,
neither is eligible and expiry wins. Worker replicas use SKIP LOCKED batches.

Retries by the assigned courier return the current participant view without
another acceptance (including after later fulfilment advances). Repeated requester
cancellation of CANCELLED returns the existing view. No duplicate history/event
is added. Conflicting or other non-OPEN actions return 409 `ORDER_NOT_OPEN`;
self-acceptance returns 403 `SELF_ACCEPTANCE`; missing order or unrelated
cancellation returns 404 `NOT_FOUND`. Conflict bodies never expose participant
IDs. Authentication/dependency errors still fail closed. A lost response can be
retried with the same action and actor; it cannot reserve or release twice in Order.

Participant responses add nullable `acceptedAt`, `cancelledAt`, `expiredAt`.
History represents expiry as `actorType: "SYSTEM", actorId: null`; user actions
retain their authenticated UUID. History ordering remains per-order sequence.

## Fulfilment, completion and overdue

Pickup/delivery/completion accept no body (or `{}`) and no query fields, with fresh
User authentication and the same per-order locking/atomic history guarantees.
Only the designated participant can perform each action; another participant
receives 403 `FORBIDDEN`, unrelated users 404 `NOT_FOUND`. Skipped/reversed actions
without a recorded prior success return 409 `INVALID_TRANSITION` without mutation.
A successful actor/action retry returns the current projection, including after
later transitions, without changing timestamps, history or events. No admin bypass.

Participant projections add nullable `pickedUpAt`, `deliveredAt`, `completedAt`
and `overdueAt`. Only requester confirmation of DELIVERED creates COMPLETED and
`order.completed.v1`; delivery alone never requests transfer. Completion does not
call Credit synchronously. Order success is not a wallet-settlement acknowledgment.
No auto-completion timer is implemented: a non-responsive requester in DELIVERED
remains a policy question, not permission to invent a payment or failure transition.

The independent `order-expiry` worker now also checks overdue delivery, in separate
bounded SKIP LOCKED transactions using the existing interval/batch settings. An
ACCEPTED/PICKED_UP errand at/after deliveryDeadline gets `overdueAt=deliveryDeadline`.
This denotes when lateness began, not the worker's detection time. The marker does
not change state, add a state-transition history entry, emit a Credit event or block
late pickup/delivery. Valid late actions also set the marker in their transaction,
so a delayed worker cannot miss lateness if delivery wins the race. Rejected actions
and replays do not cause overdue writes. Preserve the marker after late delivery
and completion. On-time DELIVERED orders awaiting confirmation are not overdue.
OPEN/CANCELLED/EXPIRED/FAILED/COMPLETED do not newly acquire markers in the worker.
A valid late failure records/preserves the marker before changing to FAILED.
A failure before deliveryDeadline never becomes overdue afterward.

## Unilateral participant failure

The user approved this strategy under the supplied mentor guidance on 2026-10-11.
It revises original M3F8's mutual confirm/reject flow: either the requester or
assigned courier can mark ACCEPTED/PICKED_UP as FAILED without second-party approval.
There is no failure from OPEN, DELIVERED or any terminal state, no admin bypass,
automatic penalty or fault determination. Physical return/compensation and
post-delivery complaints are outside this implementation.

```http
POST /v1/orders/{{orderId}}/fail
Authorization: Bearer {{accessToken}}
Content-Type: application/json
```

```json
{"reason": "ITEM_DAMAGED", "details": "Item damaged after pickup"}
```

Required `reason` is one of `ITEM_UNAVAILABLE`, `ITEM_DAMAGED`, `UNABLE_TO_PICK_UP`,
`UNABLE_TO_DELIVER`, `PARTICIPANT_UNREACHABLE`, `OTHER`. Optional `details` is trimmed
nonblank text up to 500 characters; OTHER requires details. These neutral categories
are implementation choices, not proof of fault. Unknown fields, query parameters,
client actor/state and penalties are rejected. Authentication is checked afresh.

200 returns participant detail with `failedAt`, `failedBy`, `failureReason` and
`failureDetails`. These fields and history's failureReason/failureDetails are
participant data, never public assessment fields. Row lock and database time guard
the action; FAILED, actor/time/reason, one history entry and `order.failed.v1`
release intent commit together without a Credit HTTP call. No transfer is requested.

The same actor with the same normalized reason/details returns the saved result
without writes. Changing the report or another participant reporting after failure
returns 409 `FAILURE_CONFLICT`; an invalid state returns 409 `INVALID_TRANSITION`.
Unrelated users receive 404. Failure versus delivery follows the first valid locked
transition; if delivery wins, failure is rejected unchanged. Failure versus pickup
can record pickup first then failure, or failure first then reject pickup.
The UI requires confirmation, freezes an ambiguous report for the same-body retry,
shows recorded reason/history and says credit release is processed separately.

## Terminal events: proposed Credit-facing v1 contract

Order implements these producer messages; Credit's queue, consumer and settlement
transaction still require owner agreement and implementation. Example:

```json
{
  "eventId": "550e8400-e29b-41d4-a716-446655440010",
  "eventType": "order.cancelled.v1",
  "orderId": "550e8400-e29b-41d4-a716-446655440001",
  "reservationId": "550e8400-e29b-41d4-a716-446655440011",
  "occurredAt": "2026-10-11T04:00:00Z"
}
```

- Expiry and failure use the same shape with `eventType: "order.expired.v1"` or
  `"order.failed.v1"`. Failure carries no actor, reason, details or penalty. UUID eventId
  stays identical on every publication attempt. No profile, free text, tokens or
  balances are included. Credit resolves the owner/amount from its own reservation
  and validates its binding to orderId. Reservation creation-abort recovery still
  uses its separate HTTP fence; it is not a cancellation event for a nonexistent order.
- Completion uses `eventType: "order.completed.v1"` plus `requesterId`, `courierId`
  and positive integer `amount`. These immutable fields are copied from the locked
  Order into the outbox transaction, not supplied by the caller or fetched later.
  Credit must verify the reservation/order/requester/amount, provision the recipient
  wallet if appropriate under its own contract, and atomically transfer exactly the
  reserved reward to that courier, deduplicating eventId and reservation settlement.
  A missing wallet should be retried/reconciled, not acknowledged as a successful
  payment or silently redirected. Transfer after CLOSED/RELEASED is a conflict;
  duplicate transfer cannot pay twice or change recipient. Simulator checks are
  test evidence only; real wallet accounting/reconciliation belongs to Credit.
- Match User's durable topic exchange convention, default `foc.events`; routing
  key and AMQP type equal eventType, message ID equals eventId. Messages are
  persistent; publisher confirms and mandatory routing are enabled. No public
  queue is created by Order. Credit must provision durable bindings for all four types
  before production use. Mandatory routing proves at least one queue received it,
  not specifically Credit, and certainly not that credits were released.
- `outbox_events.PENDING` includes unsent/retryable events. No route, broker outage
  or lost confirmation retains intent. `PUBLISHED` means broker-confirmed only.
  A durable Credit queue retains messages while its consumer is offline.
- Delivery is **at least once**, not exactly once. Crash after publish but before
  database acknowledgment can duplicate the identical event. Credit must dedupe
  eventId and apply settlement at most once per reservation in its own transaction;
  do not acknowledge consumption before that transaction commits. Release after
  transfer must not alter balances. These consumer rules are not implemented here.
- One terminal event per order is enforced by an Order-local unique constraint.
  No cross-order ordering is required. Consumers must tolerate duplicates and
  delayed events without reversing a completed settlement.
- Worker claims one event for 30 seconds, publishes with a 5-second total timeout,
  and fences acknowledgments/retries by lease token. Retry delays are 1, 2, 4, 8,
  16, 32, then at most 60 seconds, indefinitely; no silent discard or fake success.
  Expiry has a separate process so broker waits cannot stall deadline processing.
- Logs carry eventId/orderId/type/attempt/outcome, never credentials or exception
  text. Inspect pending rows and oldest next_attempt_at alongside worker logs.
  Retention/cleanup and consumer settlement-status reporting are deferred.

Transport reference: [aio-pika publisher confirmations and mandatory returns](https://docs.aio-pika.com/apidoc.html#exchange).

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

These advance M3F1-M3F7 (including pickup/delivery/completion/overdue), and related
security/retry invariants. M3F8 is implemented under the approved unilateral revision;
the original other-party confirm/reject criteria are not claimed as fulfilled unchanged.
They do not prove real Credit integration, NFR load targets or D3's required
meaningful terminal-event consumer effect. Credit conservation/ledger correctness
remains Credit-owned. Core lifecycle UI and isolated simulated settlement are
implemented, but neither is evidence of actual Credit integration.
