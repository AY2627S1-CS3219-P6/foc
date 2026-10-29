# Admin Service API and dependency contracts

Version 1. Admin Service owns dispute cases about errands, their status history and the audit
log of dashboard actions (backlog N2F3, N2NFR3). It reads errand, credit and identity
information only through other services' versioned HTTP APIs and never reads their databases.

Status: health checks, current-session administrator authorization, the dispute workflow,
participant problem reports and the audit log are implemented.

## Conventions

- Base paths `/v1/admin` (administrators) and `/v1/disputes` (errand participants). The edge
  proxy routes `/v1/admin/disputes*`, `/v1/admin/audit-log*` and `/v1/disputes*` here; every
  other `/v1/admin/*` path stays with its owning service.
- Every request needs `Authorization: Bearer <access token>`. On every request the service calls
  User Service `GET /v1/users/me` and requires an `ACTIVE` account; `/v1/admin` routes also
  require system role `ADMIN` or `SUPER_ADMIN` (N2F1.1, N2NFR1.1-1.3).
  - Missing, malformed, expired or revoked session: `401 UNAUTHENTICATED`.
  - Ordinary User: `403 FORBIDDEN`.
  - User Service unavailable or returning an unusable response: `503 AUTH_UNAVAILABLE`.
    Nothing is read or written.
- JSON uses camelCase. Timestamps are UTC ISO 8601. Identifiers are UUIDs.
- Errors use the shared envelope
  `{"error": {"code", "message", "correlationId", "fieldErrors"}}`. Messages never echo request
  input. A safe `X-Correlation-ID` header is accepted and always returned.
- Lists take `page` (default 1) and `pageSize` (default 20, maximum 50) and return
  `{"items": [...], "page", "pageSize", "total"}`.

## Operations

| Method and path | Behaviour |
| --- | --- |
| `GET /health/live` | The process is running. Needs no database. |
| `GET /health/ready` | The Admin database is reachable and migrated; otherwise `503 SERVICE_NOT_READY`. |

## Disputes

| Method and path | Behaviour | Success |
| --- | --- | --- |
| `POST /v1/admin/disputes` | Record a dispute about an existing errand. Requires an `Idempotency-Key` UUID header. | `201` + dispute |
| `GET /v1/admin/disputes` | Newest first; optional `status` and `orderId` filters. | `200` + page |
| `GET /v1/admin/disputes/{disputeId}` | One dispute with its chronological status history. | `200` |
| `POST /v1/admin/disputes/{disputeId}/transitions` | Change the dispute's status. | `200` + dispute |
| `GET /v1/admin/audit-log` | Dashboard action records, newest first; optional `actorId`, `targetId` and `outcome` filters. | `200` + page |

### Recording a dispute

Request: `{"orderId": uuid, "description": string, "evidenceRefs": [string]}`. The description
must be non-blank after trimming (at most 2,000 characters); `evidenceRefs` is optional (at most
10 references of at most 200 characters each).

- Administrators use this to record a problem raised outside the app; participants use
  [participant reports](#participant-reports).
- The service confirms the errand with Order `GET /v1/admin/orders/{orderId}`, forwarding the
  caller's bearer token. Order `404` returns `422 ORDER_NOT_FOUND`; Order unavailable returns
  `503 ORDER_UNAVAILABLE`. Nothing is stored in either case (N2F3.2.2).
- A new dispute starts as `OPEN` with `version` 1 and records the recording administrator and
  time (N2F3.2.3).
- Retrying with the same `Idempotency-Key` and an identical body returns the original dispute
  with `200`. Reusing a key with a different body returns `409 IDEMPOTENCY_KEY_REUSED`
  (N2NFR3.3).

Dispute: `{"disputeId", "orderId", "description", "evidenceRefs", "status", "resolutionReason",
"reporterRole", "createdBy", "createdAt", "updatedAt", "version", "history": [...]}`.
`reporterRole` is `REQUESTER` or `COURIER` for a participant report and `null` when an
administrator recorded the dispute. History entries are
`{"sequence", "fromStatus", "toStatus", "actorId", "reason", "occurredAt"}`.

### Changing status

Request: `{"toStatus": "UNDER_REVIEW" | "RESOLVED" | "REJECTED", "reason": string | null,
"expectedVersion": int}`.

| From | Allowed to | Reason |
| --- | --- | --- |
| `OPEN` | `UNDER_REVIEW` | Optional |
| `UNDER_REVIEW` | `RESOLVED` or `REJECTED` | Required and non-blank |

- Any other move returns `409 INVALID_TRANSITION`; a missing reason returns
  `422 REASON_REQUIRED`. The dispute is unchanged (N2F3.3.1-3.3.3). A missing or non-UUID
  `Idempotency-Key` returns `422 IDEMPOTENCY_KEY_REQUIRED`.
- A stale `expectedVersion` returns `409 VERSION_CONFLICT`; the dashboard tells the
  administrator to refresh and review the current dispute (N2NFR3.4, N2NFR4.5).
- Each accepted change appends a history entry with the previous and new status, acting
  administrator, reason and time (N2F3.3.4).
- Resolving or rejecting records a decision only. It never changes the errand or any wallet
  (N2F3.5).

## Participant reports

| Method and path | Behaviour | Success |
| --- | --- | --- |
| `POST /v1/disputes` | Report a problem with an errand you take part in. Requires an `Idempotency-Key` UUID header. | `201` + report |
| `GET /v1/disputes` | Your own reports, newest first; optional `orderId` filter. | `200` + page |

Request: `{"orderId": uuid, "description": string}`. The description must be non-blank after
trimming (at most 2,000 characters). There is no evidence field; any detail goes in the
description.

- The service asks Order `GET /v1/orders/{orderId}` with the caller's own token and reads
  `requesterId` and `courierId` from the participant view. A caller who is neither, or an
  errand Order does not show them, returns `422 ORDER_NOT_FOUND`, so non-participants learn
  nothing about the errand. Order unavailable returns `503 ORDER_UNAVAILABLE` (N2F3.2.2).
- Reports are accepted once a courier has accepted the errand: `ACCEPTED`, `PICKED_UP`,
  `DELIVERED`, `COMPLETED` or `FAILED`. Other states return `409 REPORT_NOT_ALLOWED`.
- A participant may have one `OPEN` or `UNDER_REVIEW` report per errand; another returns
  `409 REPORT_ALREADY_OPEN`. Once it is resolved or rejected they may report again (N2F3.2.4).
- A report becomes an `OPEN` dispute that administrators review through the workflow above.
  Idempotency works as for administrator-recorded disputes (N2NFR3.3).

Report: `{"disputeId", "orderId", "description", "status", "resolutionReason", "reporterRole",
"createdAt", "updatedAt"}`. Participants see the status and the decision reason, never the
administrators involved, the status history or the audit log (N2F3.2.5).

### Audit log

Every dispute create, participant report and status-change attempt, successful or rejected,
appends
`{"auditId", "actorId", "action", "targetType", "targetId", "outcome": "SUCCESS" | "REJECTED",
"errorCode", "correlationId", "occurredAt"}` (N2F3.6). The runtime database role cannot update
or delete history or audit rows (N2NFR3.2).

## Dependencies on other services

Admin Service itself uses only these read contracts:

| Owner | Contract | Used for | Status |
| --- | --- | --- | --- |
| User | `GET /v1/users/me` | Current session, role and account status | Existing |
| Order | `GET /v1/admin/orders/{orderId}` | Confirm the errand exists before recording a dispute | Proposed; Order owner review |
| Order | `GET /v1/orders/{orderId}` | Confirm the caller takes part in the errand before accepting a report | Existing |

The dashboard pages call these owning-service contracts directly from the browser:

| Owner | Contract | Backlog | Status |
| --- | --- | --- | --- |
| Order | `GET /v1/admin/orders` with optional `orderId`, `participantId`, repeated `state`, `supplierId`, `createdFrom`, `createdTo` and `overdue` filters | N2F2.1-2.2, N2F3.1 | Proposed extension of the existing endpoint |
| Order | `GET /v1/admin/orders/{orderId}` and `GET /v1/admin/orders/{orderId}/history` | N2F2.3 | Proposed; allows administrators, not other users, past the participant check |
| Order | `GET /v1/admin/orders/analytics` and `GET /v1/admin/orders/analytics/users/{userId}` | N2F4.1-4.4 | Proposed |
| Credit | `GET /v1/admin/credit/reservations/{orderId}` | N2F3.4.2 | Proposed |
| Credit | `GET /v1/admin/credit/analytics` | N2F4.5 | Proposed |
