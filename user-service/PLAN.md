# User Service Implementation Plan

## Sprint 1 outcome (D2)

Deliver a near-complete User Service that can be demonstrated locally in containers. It will register and verify students, authenticate them, protect a self-owned profile, support requester/courier mode toggling, enforce User/Admin/Super Admin RBAC, provide a secure first-Super-Admin bootstrap and role lifecycle, publish a safe registration event, and give Supplier Service the information it needs to enforce administrative restrictions.

The service owns identity only. It must not create wallets, suppliers, orders, or any endpoint belonging to another microservice.

## Technology and data design

Use Python 3.13, FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2 async with `asyncpg`, Supabase CLI SQL migrations, Supabase Cloud PostgreSQL, RabbitMQ, and SMTP. Unit/integration tests use pytest, pytest-asyncio, and httpx's ASGI transport; the final smoke test uses Docker Compose, a local Supabase CLI PostgreSQL stack, RabbitMQ, and Mailpit. This produces a compact local setup while mapping directly to ECS Fargate, Supabase Cloud PostgreSQL, Amazon MQ, SES SMTP, Secrets Manager, and CloudWatch in AWS.

Supabase Cloud PostgreSQL is the appropriate User Service datastore because identity data is structured and is queried by unique email/username, stable user ID, current role/status, and later administrator search. Its PostgreSQL unique indexes prevent duplicate identity creation; transactions and row/advisory locks enforce the last-Super-Admin rule under concurrency; and it easily exceeds the 35,000-account target. The Supabase CLI supplies a local, migration-compatible PostgreSQL environment, while Supabase Cloud remains the managed production datastore for AWS-hosted compute.

### Supabase boundary and connection configuration

Supabase is PostgreSQL storage only. FastAPI owns password hashing, OTP delivery/verification, sessions, RS256 JWT issuance, RBAC, and all role lifecycle rules; Supabase Auth, Supabase client SDKs in the browser, and Supabase JWTs are explicitly out of scope.

Provision a dedicated Supabase project/database for User Service with a `user_service` schema. Supabase SQL migrations create the schema, owner, and lower-privilege FastAPI application role; the runtime role can access only that schema. Keep only `DATABASE_URL` (runtime Session Pooler URL with `sslmode=require`) in FastAPI configuration. Store it only in local secret files and AWS Secrets Manager, never in frontend configuration, source, logs, API responses, or events.

`user-service/supabase/migrations/` is the canonical and only migration history. Create each schema change with `npx supabase migration new <description>`, review and write the generated timestamped SQL, run `npx supabase db reset` to reconstruct the local database, and commit the SQL file with its dependent code. SQLAlchemy models are runtime ORM/query models only: they must neither generate migrations nor mutate schema at application startup. Do not add a second migration history or migration runner.

Initialize and link the local project from `user-service/` using `npx supabase init` and `npx supabase link` to the cloud `foc-user-service` project. The GitHub integration is configured for `AY2627-CS3219-P6/foc` with working directory `user-service`; it will read the committed migration directory. Keep automatic branching and production deployment disabled until local reset, preview, and migration checks are verified, then enable them in that order.

### Schema

| Table | Essential fields and constraints | Purpose |
| --- | --- | --- |
| `users` | `id` UUID PK; nullable original and normalized unique `username`; nullable normalized `email`; `display_name`; `system_role` enum (`USER`, `ADMIN`, `SUPER_ADMIN`); `account_status` enum (`ACTIVE`, `SUSPENDED`, `DELETED`); nullable `email_verified_at`; `active_participation_mode`; `role_version`; `deleted_at`; timestamps | Active identity and safe profile fields, plus de-identified account tombstones. Every public identifier is the immutable `id`. |
| `credentials` | one-to-one `user_id`; bcrypt password hash; password-change timestamp | Separates credentials from public profile queries. Passwords are never retrievable. |
| `registration_challenges` | proposed username/email/display name; bcrypt password hash; HMAC-peppered OTP hash; expiry; attempt and resend counters | Holds a pending registration until an OTP succeeds, so only verified accounts are activated and published. |
| `sessions` | `id`; `user_id`; hashed rotating refresh token; issued/expiry/revoked timestamps; token family | Supports logout, refresh rotation, and per-session revocation without persisting a raw refresh token. |
| `admin_audit_entries` | append-only ID; actor ID; target ID; action; outcome; role before/after; correlation ID; timestamp | Records role lifecycle actions without secrets. Application DB credentials cannot update/delete this table; migrations create the append-only protection. |
| `outbox_events` | event ID; event type/version; aggregate ID; minimal payload; occurred timestamp; publish status/attempts | Makes `user.registered.v1` durable with the user-creation transaction. |

Indexes cover non-null normalized username/email and the current active Super Admin count. PostgreSQL unique constraints permit multiple nulls, so a tombstone releases its former username and email while every active registration remains unique. Later administrator search adds appropriately scoped indexes for user ID, username, display name, and email. There are no shared tables or foreign keys to another service.

### Account-deletion tombstone

Account deletion is an irreversible, transactional anonymization, not a physical deletion of the `users` row. After password and explicit-acknowledgement verification, FastAPI deletes the credential and every session; clears `username`, `normalized_username`, `email`, `normalized_email`, and `email_verified_at`; replaces `display_name` with `Deleted User`; resets `active_participation_mode` to `REQUESTER`; increments `role_version`; and records `account_status = DELETED` with `deleted_at`. The stable `id` and former `system_role` remain as non-PII historical metadata, but `DELETED` is terminal and denies login, refresh, and every protected action.

Removing the identifiers allows a later registration to use the same email or username, but it always creates a new `id`. The User Service currently has no `payment_token`; any future PII-bearing field must be cleared or irreversibly anonymized by this same transaction. The audit and outbox tables introduced by later phases retain only their immutable, non-secret records.

### Security decisions

- Validate email syntax and normalize it for unique comparison. Enforce the backlog's username/display-name allow-list; username has no whitespace or unlisted special characters. Passwords require at least 12 characters and at least three of upper-case, lower-case, digit, and the specified special-character categories.
- Hash passwords with bcrypt using a configured production-grade work factor. OTPs are random six-digit codes stored only as a keyed HMAC digest, expire after 10 minutes, and are subject to five failed-verification attempts and bounded resend/request rate limits. Never log either value.
- Send short-lived RS256 access JWTs and issue a random opaque refresh token only as a `HttpOnly`, `Secure` (outside local HTTP), `SameSite=Lax` cookie. Store only its hash; rotate it on refresh and revoke its session on logout. Keep access tokens out of persistent browser storage.
- Restrict all decisions to server-side FastAPI dependencies and handlers. Pydantic DTOs reject undeclared fields and allow only explicitly mutable profile fields, so requests cannot set `id`, `email`, `username`, `systemRole`, `accountStatus`, `emailVerifiedAt`, `roleVersion`, or timestamps.
- Deletion never persists or logs a supplied current password. It removes credential material and PII while preserving only the stable tombstone ID and legally/project-required immutable history, maintaining M2NFR2.1's no-plaintext-password guarantee.
- Generate the JWT private key and OTP HMAC key outside source control. Use local `.env` secrets for development and AWS Secrets Manager in cloud deployment. The service exposes only its current public keys through JWKS.
- Do not expose a Supabase URL, API key, database password, service-role key, or Supabase JWT to the web client. FastAPI connects directly to PostgreSQL through SQLAlchemy; it does not use the Supabase Data API.

## User Service API contract

All application responses use a consistent error shape containing a stable code, human-readable message, correlation ID, and field errors where appropriate. Error responses and events never contain passwords, password hashes, OTPs, reset tokens, refresh tokens, or private-key material.

| Endpoint | Access | Sprint 1 behavior |
| --- | --- | --- |
| `GET /health/live`, `GET /health/ready` | internal/operations | Liveness and Supabase PostgreSQL dependency-aware readiness for Compose/ECS. |
| `POST /v1/auth/registrations` | public | Validate proposed username, email, and password; create/replace a bounded pending registration; send an OTP; return verification-pending status. |
| `POST /v1/auth/email-verifications` | public | Validate OTP and atomically create the active `USER` account, credentials, and `user.registered.v1` outbox record. |
| `POST /v1/auth/email-verifications/resend` | public | Enforce resend limits and issue a new OTP for an unexpired pending registration. |
| `POST /v1/auth/sessions` | public | Authenticate an active verified user, return an access token, and set the refresh-token cookie. Return a non-enumerating invalid-credentials response otherwise. |
| `POST /v1/auth/sessions/refresh` | refresh cookie | Rotate a valid refresh token and issue a new access token; reject expired, reused, or revoked sessions. |
| `DELETE /v1/auth/sessions/current` | authenticated/refresh cookie | Revoke the current session and clear the cookie. |
| `GET /v1/users/me` | authenticated | Return only the caller's safe profile and current participation-mode preference. |
| `PATCH /v1/users/me` | authenticated | Update only `displayName` and `activeParticipationMode`; reapply validation and reject protected fields. |
| `DELETE /v1/users/me` | authenticated | Require current password and an explicit deletion acknowledgement; transactionally anonymize the profile into a terminal `DELETED` tombstone, delete credentials/sessions, and retain the stable ID unless doing so would remove the last active Super Admin. |
| `PATCH /v1/admin/users/{userId}/system-role` | current `SUPER_ADMIN` | Promote or demote another account among `USER`, `ADMIN`, and `SUPER_ADMIN`; record an audit entry and invalidate old role state. Self role changes are rejected. |
| `GET /.well-known/jwks.json` | service/public key distribution | Return public JWT-signing keys only, with a stable key ID for local signature verification and rotation. |
| `POST /v1/internal/authorization-decisions` | authenticated Supplier Service identity | Return the current authenticated subject ID, status, role, and allow/deny decision for the declared administrative action. It is fail-closed and contains no profile or credential data. |

The immediate role/lifecycle endpoint is deliberately limited to Super Admin and another target user. It does not expose the future account-search, suspension, reactivation, password-change, or password-reset interfaces before they are needed.

## Incremental implementation phases

Each phase ends with a human-verifiable result and automated tests. Do not start a later phase with placeholder authorization or mocked persistence.

### Phase 0 - runnable service foundation

- Create the Python/FastAPI layout, Pydantic settings model, Uvicorn Docker entrypoint, SQLAlchemy async engine/session dependency, structured redacted logging, correlation-ID middleware, and live/ready health endpoints. The FastAPI startup sequence checks connectivity only; it never runs schema migrations.
- Add the project-scoped Supabase CLI configuration under `user-service/supabase/`, including the canonical `migrations/` directory for the isolated User Service database. Link it to the cloud `foc-user-service` project. Compose runs User Service, Mailpit, and RabbitMQ; local database setup uses `npx supabase start`, while `npx supabase db reset` reconstructs the schema from committed SQL. Document safe configuration placeholders in `.env.example` without adding database secrets.
- Add a CI-friendly local Supabase test-database strategy and baseline lint, pytest unit/integration-test, and container smoke-test commands using `pytest-asyncio` and `httpx.AsyncClient` with ASGI transport.

**Human check:** `docker compose up` starts User Service with a healthy readiness response; restarting it does not recreate or lose database records.

### Phase 1 - verified account creation and credential storage

- Create and commit Supabase SQL migrations for `registration_challenges`, `users`, and `credentials`, with normalized unique email/username constraints and UTC timestamps. Verify a clean `npx supabase db reset` applies them from scratch.
- Implement registration validation exactly from M1F1, clear field errors, bounded duplicate protection, Mailpit OTP delivery, OTP verification, and the atomic transition from pending registration to active `USER` account.
- Apply bcrypt password hashing and redaction tests. Store no plaintext password or OTP, and do not publish an event until the account is verified/active.

**Human check:** create a valid account, read the OTP in Mailpit, verify it, and log in. Show rejected duplicate/invalid email, username, and password cases; a database inspection shows only a bcrypt hash and no raw OTP/password.

### Phase 2 - authentication, session lifecycle, and self-only identity access

- Add RS256 key loading/JWKS publication, access-token issuance, refresh-token hashing/rotation, logout revocation, expiry handling, and authentication middleware.
- Add `GET /v1/users/me` and owner-only protection; reject unauthenticated or expired/revoked-session access with the documented error form.
- Ensure FastAPI dependencies perform all role/status checks server-side and verify token issuer, audience, signature, expiry, `sid`, and `roleVersion` before a protected User Service action.

**Human check:** a verified account can log in, refresh once, retrieve its own profile, then cannot use the old refresh token after rotation or retrieve the profile after logout. Responses never display an authentication secret.

### Phase 3 - protected profile management and requester/courier participation

- Implement allowed profile updates: validated display-name changes and `activeParticipationMode` toggling between requester and courier.
- Treat both participation modes as capabilities of the same stable `userId`, never as new accounts or privileged roles. Reject requests containing protected fields rather than silently accepting them.
- Implement the destructive account-deletion confirmation as a tombstone transaction. Preserve the immutable `userId`, replace the display name with `Deleted User`, clear all User Service PII, delete credentials and sessions, reset participation mode, increment `roleVersion`, and mark the account terminally `DELETED`; never create a replacement identity or deletion event in this phase.

**Human check:** the same account toggles requester/courier mode and retains its user ID; valid display-name changes, including duplicate names, persist. Attempts to alter email, username, role, account status, or ID fail and leave the profile unchanged. Deletion requires the warning acknowledgement, leaves the original ID with `DELETED` status and `Deleted User` display name, clears PII/credentials/sessions, prevents further login, and permits a new account with the released email and username to receive a different ID. Order, Chat, and other services retain their participant IDs and render a deleted participant as `Deleted User` without a new Phase 3 integration call or event.

### Phase 4 - RBAC and Supplier Service integration contract

- Implement fixed role guards: `USER` may use self endpoints; `ADMIN` adds supplier-management authorization; `SUPER_ADMIN` includes Admin plus role lifecycle. The service does not trust a client-supplied role.
- Publish the JWKS and implement the internal current authorization-decision endpoint protected by a Supplier Service identity. In Compose use a dedicated internal secret/network; in AWS replace it with task IAM/mTLS-equivalent service identity.
- Give the Supplier Service owner a short integration contract: verify normal access JWTs locally; call User Service immediately before supplier-management operations; send the authenticated bearer token and requested action; fail closed on any false/timeout/error. No Supplier database access is granted to User Service.

**Human check:** a `USER` receives a denied supplier-management authorization decision; an `ADMIN` receives an allow decision; malformed/expired tokens and a missing Supplier Service identity are denied. The teammate can demonstrate their service refusing an admin operation after this decision changes to deny.

### Phase 5 - secure first administrator and role lifecycle

- Add a one-shot `bootstrap-super-admin` command/profile. It runs only when no active Super Admin exists, requires explicit non-source-controlled bootstrap credentials, validates them, creates a verified `SUPER_ADMIN`, writes a redacted audit record, and exits. It refuses to run if an active Super Admin already exists.
- Implement Super Admin-only promotion/demotion of *another* user. Every role update increments `roleVersion`, revokes that target's existing sessions, records an immutable audit row, and is committed atomically.
- Enforce lifecycle invariants in a transaction with a lock: Admins cannot modify administrative roles; no user can self-change a system role; a request that would demote, suspend, tombstone-delete, or revoke the last active Super Admin is rejected, including concurrent requests. A non-last Super Admin may tombstone-delete their own account only after the normal password/acknowledgement confirmation.

**Human check:** bootstrap exactly one Super Admin without public registration. Promote a User to Admin, observe the audit record, then prove Admin cannot promote anyone. Attempt self-demotion and tombstone deletion of the sole active Super Admin (both fail); add a second Super Admin and confirm the first can tombstone-delete their own account. Run simultaneous last-Super-Admin demotion attempts and confirm all are denied.

### Phase 6 - registration event, hardening, and D2 demo evidence

- Write `user.registered.v1` to the outbox in the same transaction as verified user creation. A worker publishes to RabbitMQ with only `eventId`, `eventType`, `userId`, and `occurredAt`; retries are observable and safe. The future Credit Service must treat `eventId`/`userId` idempotently and must never receive credential/profile data.
- Add authorization-negative, validation, refresh-reuse, protected-field, last-Super-Admin, audit-immutability, outbox retry, and no-secret-leak test cases. Add a small registration/login/profile/RBAC/Supplier-authorization demo script and sample non-secret users.
- Measure and record p95 registration/login/read/write timings. Sprint 1 establishes instrumentation and realistic indexes; the planned load tests for 35,000 users, 200 logins/minute, 30 registrations/minute, and 1,000 concurrent authenticated users are executed in Sprint 4.

**Human check:** inspect a RabbitMQ event after verification and confirm it contains the four safe fields only. Run the D2 demo path end-to-end: bootstrap Super Admin, register/verify a normal user, authenticate, update/toggle profile, prove protected changes and forbidden roles fail, promote an Admin, and show the Supplier authorization decision changes accordingly.

## Deferred User Service work after D2

These remain explicitly planned so Sprint 1 does not accidentally claim them complete:

- **Sprint 2:** authenticated password change, email password-reset request/confirmation, session invalidation after password reset, administrator user lookup/listing by ID/username/display name/email, safe account-information views, suspension/reactivation, and the remaining administration audit actions. These complete M1F3.2, M1F5.3, and the remaining M1F5.4 requirements.
- **Sprint 3-4:** execute the specified scale/performance/load tests, key-rotation rehearsal, recovery testing, AWS deployment evidence, and operational dashboards/alerts. Preserve the same User Service API and data-ownership boundary.

## Acceptance mapping

| D2 expectation | Evidence delivered by this plan |
| --- | --- |
| 1. Role design | Role table, fixed permission model, requester/courier mode distinction, and test/demo script. |
| 2. Database and secure credentials | PostgreSQL justification, concrete schema, bcrypt/HMAC storage, migrations, and database verification. |
| 3. Authentication and RBAC | RS256 access/rotating refresh design, FastAPI dependency guards, server-side current-role checks, and negative tests. |
| 4. Supplier integration | JWKS plus fail-closed internal current-authorization decision contract for the Supplier Service owner. |
| 5. Protected profiles | Allow-listed profile DTO, self-only endpoints, protected-field rejection, and deletion confirmation with transactional PII anonymization, credential/session removal, stable-ID preservation, and identifier reuse. |
| 6. Administrator lifecycle | One-shot secure bootstrap, Super Admin promotion API, audit record, session/role invalidation, and last-Super-Admin concurrency protection. |
