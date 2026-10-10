# Backend implementation and verification

Verified 10–11 October 2026 (Asia/Singapore), on `feature/chat-service` in the assigned
`worktrees/foc-chat-service` checkout. Implementation/commits are restricted to `chat-service/**`.
This is a backend handoff, not full Sprint 3 UI acceptance or Sprint 4 performance certification.

## Actual results

- **40 tests passed** after a clean Chat Service Supabase migration reset and re-provisioning
  the disposable restricted login. All database/broker tests ran, including opt-in restart tests.
  Final run: 54.36 seconds. One upstream Starlette TestClient/httpx deprecation warning remains;
  no failed or skipped tests in this run.
- Ruff lint and format checks passed for `app`, `tests`, and `scripts`.
- Supabase CLI 2.120.0 clean local resets applied both timestamped migrations successfully.
  No User Service or production/cloud database was reset by this worker.
- Docker image builds with Python 3.13 and locked dependencies. Disposable API/publisher
  container smoke passes: non-root API, SQL readiness, broker subscription, independently running
  publisher and API restart. Runtime grants deny schema creation, message update/deletion and
  event-payload mutation. Only counters/read cursors/publisher state are mutable.
- Service-local optional-profile Compose configuration validates with safe example environment.
- Actual production HTTP-client integration passed against the User Service worker's disposable
  running app at loopback port 18080, backed by its isolated PostgreSQL on 18422. Public JWKS,
  current sessions, paginated search, current `Renamed` display name, tombstone redaction and
  explicit missing IDs were verified. Two Chat API processes plus the independent publisher
  exchanged a real authenticated message through RabbitMQ, repeated the send idempotently and
  retrieved recipient history. No User Service Python modules, database credentials or private
  keys were imported/copied. Demo credentials were read in memory and never printed or committed.
  The owner stopped the demo and removed its credential fixture after these checks finished.

Single real integration baseline sample (development host, not a load/p95 result): local
verification of two identities 670.45 ms; durable acceptance 82.90 ms; SQL outbox occurrence
to broker-confirmed publication 709.44 ms; sender-send to recipient live frame 800.04 ms;
authenticated history request 41.82 ms. Publisher polling/default startup/backlog affect these
samples. Do not extrapolate throughput, p95, latest-50 formal performance or 1,000 connections.

## Reproduce locally

Use only the isolated Chat project and dedicated test broker. These commands assume the current
directory is `chat-service`; none target another service. Native Windows sandbox access to
Docker, the Python base installation/uv cache, and some Git worktree operations required normal
escalation during this session. GitHub/gh was not used.

```powershell
uv sync --locked --extra dev
npx --yes supabase@2.120.0 start -x studio,imgproxy,inbucket,postgrest,realtime,storage-api,edge-runtime,logflare,vector,supavisor
npx --yes supabase@2.120.0 db reset --local
uv run python -m scripts.provision_test_role
docker run --detach --name foc-chat-test-rabbitmq --publish 127.0.0.1:17425:5672 rabbitmq:4.1-management
$env:CHAT_TEST_DATABASE_URL='postgresql+asyncpg://chat_test:local-chat-test-only@127.0.0.1:17422/postgres'
$env:CHAT_TEST_RABBITMQ_URL='amqp://guest:guest@127.0.0.1:17425/'
$env:CHAT_TEST_BROKER_RESTART='1'
$env:CHAT_TEST_DATABASE_RESTART='1'
uv run ruff check app tests scripts
uv run ruff format --check app tests scripts
uv run pytest -q --tb=short
docker build --tag foc-chat-service:test .
uv run python -m scripts.container_smoke
```

The displayed database/broker credentials are deliberately public, disposable local test values,
not production secrets. `provision_test_role` verifies the Chat container/port and creates a
test login only if absent; it does not overwrite existing passwords. Clean reset removes local
login state, so re-provision afterwards. Do not run restart tests while another job uses these
Chat resources. Tests use unique user/conversation UUIDs and do not truncate tables. They refuse
database hosts outside loopback/17422 and broker hosts outside loopback/17425. The restart tests
additionally verify their exact container port bindings. Unit tests remain runnable without
infrastructure, with integration tests explicitly skipped.

If the dedicated test broker already exists, use `docker start foc-chat-test-rabbitmq` instead
of `docker run`. After verification, stop only this broker and run Supabase `stop` from this
directory to preserve the Chat database volume. Disposable API/publisher smoke containers and
test subprocesses clean themselves up; existing root-stack containers remain untouched.

The two-process fixture starts a test-only loopback User contract fake at 17430, APIs at
17431/17432, and a publisher. It generates its own ephemeral RSA key in memory; that fake is
never shipped in the Docker image. The actual User Service smoke is separate:

```powershell
uv run python -m scripts.verify_user_service --fixture <owner-provisioned-disposable-fixture.json>
```

This starts APIs at 17433/17434 and its own publisher, consumes credentials in memory, emits
only sanitized check names/timings, and terminates its child processes. User Service owns the
fixture/app/database setup and teardown. Its fields are `userServiceBaseUrl`,
`chatServiceSharedSecret`, `callerAccessToken/callerUserId`,
`counterpartAccessToken/counterpartUserId/counterpartUsername`, `deletedUserId`, `unknownUserId`
and `usernameQuery`; the counterpart display name in this demo is `Renamed`.

## Coverage tied to implementation

| Requirement/behaviour | Delivered backend evidence | Remaining acceptance |
|---|---|---|
| `N1F1.1`, `.1.1`–`.1.3` | Real User search; unique pair creation under concurrent requests; immutable user IDs; outsider HTTP/WebSocket denial | Search/open/send UI flow |
| `N1F1.2`, `.2.1`, `.2.3`, `.2.4` | Durable SQL messages; UTC timestamps; deterministic sequences; bounded latest/older/catch-up history; current counterpart names/usernames | Final conversation-list/thread presentation |
| `N1F1.2.2`–`.2.2.4` | Own sends excluded from unread; monotonic persisted cursors; no future reads; snapshot clears messages outside initial 50; reader-only cross-process sync; concurrent incoming/read races | Selected + focused + visible detection and automatic client acknowledgements/badge behaviour |
| `N1F1.3`–`.3.4` | Directional blocks; bilateral prevention; shared pair lock with sends/creation; mutual unblock; rollback/no queued rejected sends; live skipped events consumed without unblock replay | Block management UI/state labels |
| `N1F1.4`–`.4.3` | Raw 4095/4096/4097 and outer-whitespace boundaries; supplementary Unicode; internal whitespace preserved; empty/invalid text rejected | Matching browser code-point counting and validation feedback |
| `N1F1.5`–`.5.2` (including source alias `NF1F1.5.2`) | Durable acceptance; lost acknowledgement retry; concurrent same/different-conversation retry keys; changed-text conflict; atomic message/outbox rollback | Optimistic bubble deduplication and pending/sent/failed/retry presentation |
| `N1F1.6`–`.6.5` | Retained blocked/deleted history; UUID username-reuse separation; real tombstone/missing lookup; denied new deleted/unknown interaction | Deleted counterpart UI and actual end-to-end deletion/reuse flow with final client |
| Delivery/security support | Two real API processes; confirmed publication; leases/stale ownership/backoff; duplicate/out-of-order events; real broker/database interruptions; session revocation/expiry, origin/auth timeout checks; bounded buffer | Final client reconnect/backoff/resynchronization and real slow-network UI demonstration |
| `N1NFR3.1`–`.3.4` (source M1 aliases retained in PLAN) | Backend contracts support direct start, explicit send outcomes/retry and read recovery | Three-action flow, visual states, desktop/mobile and keyboard acceptance are **not implemented** |
| Sprint 4 N1 scalability/performance aliases | Async I/O, indexes, process fan-out and baseline measurements | 1,000 connections, sustained 25 msg/s for 15 min, formal latest-50/p95 delivery/loading and errand context deferred |

## Logical commits

- `98cb471` — prepared planning/skeleton files.
- `28cc0dd` — runnable foundation and isolated schema.
- `8b17f92` — current identity and private conversations/history.
- `1d7555f` — atomic/idempotent messages and pair-locked bilateral blocking.
- `a7a19a3` — authenticated WebSockets and confirmed per-process RabbitMQ fan-out.
- `858a35a` — unread cursors and reconnect recovery.
- Final verification/handoff commit follows these phases and includes the least-privilege
  migration, expanded failure/security checks, runnable service-local configuration and docs.

No push, merge or pull request was performed. Shared integration and UI work is listed in
[integration-follow-up.md](integration-follow-up.md); concrete frames/DTOs and client obligations
are in [backend-contract.md](backend-contract.md).
