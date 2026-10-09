# FoC Order Service

Order creation and read APIs are implemented on top of the F0 foundation.
Identity is checked through User; Supplier details are captured through its API.
Credit HTTP calls follow the **proposed** contract in [API.md](API.md). Credit is
not implemented in this checkout: real funded creation is not yet integrated.
Test doubles exist only under tests. Later lifecycle actions, terminal events and
frontend changes are outside this slice.

## Stack and boundaries

Python 3.13, FastAPI/Pydantic, SQLAlchemy async/asyncpg and a separate Supabase
PostgreSQL 17 project, following User Service's runtime conventions. Supplier
uses a different PostgreSQL driver; its implementation is unchanged. Order never
reads another service's database or imports its business logic.

The application factory owns a connection pool and closes it on shutdown. Startup
does not connect, migrate or seed the database. Readiness runs a bounded read-only
check for schema access and SELECT access to the three required tables. It does
not prove external services are ready or replace migration validation. Liveness
remains independent of it.

## Local setup

Run from `order-service/`. Docker Desktop must already be running. Health checks
need only Order's database. Protected APIs require User; creation also requires
Supplier and a compatible Credit service. RabbitMQ is not used by this slice.

1. Create an isolated Python environment using Python 3.13 and install dependencies.

   Windows Git Bash:

   ```bash
   py -3.13 -m venv .venv
   .venv/Scripts/python.exe -m pip install -e '.[dev]'
   ```

   If `py` cannot find your Python installation, use the path to your Python 3.13
   executable. On macOS/Linux use `python3.13` and `.venv/bin/python` instead.
   PowerShell can use `py -3.13` and `.\.venv\Scripts\python.exe`.

2. Install the team-pinned Supabase CLI and start **this service's** database:

   ```bash
   npm ci
   npx supabase start
   ```

   The project ID is `order-service`. Auth, Data API, storage, realtime, analytics,
   SMTP and edge functions are disabled because F0 does not use them. Studio is
   an operator UI, never a browser dependency of FoC. No hosted project is linked.

3. Copy `.env.example` to an ignored `.env` using VS Code, only if `.env` does not
   already exist. Set `DATABASE_URL` to the connection URL from this project's
   `npx supabase status`. Keep that output and its credentials local. Do not reuse
   a User or Supplier URL. Host applications use `127.0.0.1:16422`.

   The local CLI's administrative database credential is for development only.
   The migration creates an `order_service_app` NOLOGIN role with schema USAGE,
   with table-specific grants from the creation migration. A deployment operator
   must provision a dedicated login that inherits this role and keep its password
   local; no login/password is embedded in migrations. The local administrative
   URL is not a production-credential setup.

4. Start the API in that terminal:

   ```bash
   .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002
   ```

   Stop it with Ctrl+C. On PowerShell use `.\.venv\Scripts\python.exe`.

| Purpose | Address |
| --- | --- |
| Order API / Swagger | `http://localhost:8002/docs` |
| Process liveness | `http://localhost:8002/health/live` |
| Database readiness | `http://localhost:8002/health/ready` |
| Order Studio | `http://localhost:16423` (select `order_service`) |
| Order PostgreSQL | `127.0.0.1:16422` (not a webpage) |

The schema contains `orders`, `order_history` and `creation_operations` after
applying the creation migration. On an existing F0 database, review and run
`npx supabase migration up --local` before expecting readiness to pass; do not
reset existing data. Reserved local
ports are in `1642x`, separate from User's configured `1542x` and Supplier's `5532x`.
The existing User port migration is separate work, not a prerequisite for F0.

## Migrations and preserved data

`supabase/migrations/` is the sole schema history. The migrations create the owned
schema, role and tables; they grant no access to Supabase browser roles.
Never use SQLAlchemy `create_all`, an additional migration framework or startup DDL.

```bash
npx supabase migration new <description>
npx supabase migration up --local
```

Review the generated SQL before applying it. Reconstruct migrations with
`npx supabase db reset --local` **only in an explicitly disposable/new Order
database**, never in a teammate's project or a populated development database.
The reset deletes local application data. Ordinary stop/start retains it:

```bash
npx supabase stop
npx supabase start
```

Do not use `--no-backup` for normal stops. Never reset User/Supplier to test Order.

## Independent Docker run

From `order-service/`:

```bash
docker build -t foc-order-service:dev .
docker run --name foc-order-service-dev --env-file .env.docker --add-host host.docker.internal:host-gateway -p 127.0.0.1:8002:8002 -d foc-order-service:dev
```

Before running, create an ignored `.env.docker` in VS Code with the same settings
as `.env`, but change only the database hostname to `host.docker.internal`.
Keep port `16422` and the database's own credentials. Containers cannot reach the
host database through their own `127.0.0.1`. The image runs as a non-root user and
contains neither environment files nor Supabase CLI runtime state.

Use `docker logs foc-order-service-dev`, `docker stop foc-order-service-dev` and
`docker start foc-order-service-dev` to inspect/stop/restart it. Rebuilding the
image does not update an existing container: stop and remove that API container,
then repeat `docker run`; the separate database volume is unaffected. Do not run
the host API and container on port 8002 simultaneously.

Root Compose and frontend routing are intentionally unchanged. This is an
independent F0 run, not the complete M7 one-command application deployment.

## Tests

Windows Git Bash (PowerShell accepts the equivalent backslash paths):

```bash
.venv/Scripts/python.exe -m pytest -q -m 'not integration'
.venv/Scripts/ruff.exe check app tests
```

To include the two read-only database checks, set `ORDER_TEST_DATABASE_URL` in
your terminal environment to an isolated, migrated Order database URL, then run:

```bash
.venv/Scripts/python.exe -m pytest -q
```

The two foundation integration tests are read-only. Creation integration tests
require a separate `ORDER_WRITE_TEST_DATABASE_URL` pointed at a **disposable,
migrated Order-only database**; they insert generated test data and intentionally
retain it for inspection. Never point that variable at production or another
service's database. These tests skip unless explicitly configured. Neither suite
runs migrations or resets automatically. Migration/container checks remain separate.

## Creation recovery worker

Install/update the package after pulling this slice (`pip install -e '.[dev]'`).
In a separate terminal using Order's environment, run:

```bash
.venv/Scripts/python.exe -m app.orders.worker
```

The installed `order-recovery` command is equivalent. The API does not start a
background worker implicitly. Run the worker alongside it to recover abandoned
attempts after crashes/timeouts. It uses the same Order DB and dedicated Credit
credential, never a persisted user token. Configure fixed User/Supplier/Credit
origins using `.env.example`; do not overwrite an existing `.env` blindly.

The worker marks unresolved reservations ready for an authenticated requester retry;
it never creates orders using stale user authentication. At the acceptance deadline,
it closes the creation intent and retries Credit compensation. See [API.md](API.md)
for the required abort-fence contract. Without Credit, recovery remains pending.
Health endpoints probe Order storage, not this independent worker's progress.

## Continuous integration

The shared GitHub Actions workflow validates Order on pull requests targeting
`main` and pushes to `main` when `order-service/**` or the workflow file changes.
It follows User Service's Python 3.13 setup and installs `.[dev]`, then runs:

```bash
ruff check app tests
python -m pytest -m "not integration" -q
```

The existing shared Docker build step builds the Order image without publishing
or deploying it. Order validation contributes to the shared `CI passed` result.
Existing checks for other components are preserved; workflow edits also trigger
Supplier validation under its existing change filter.

No database credentials or local environment files are needed. All tests marked
`integration` are explicitly deselected, not counted as passing.
CI does not start Supabase, apply/reset migrations, run the container or verify
cross-service integration. Continue running those checks locally as described
above; a green image build does not prove runtime database connectivity.

## Postman / HTTP smoke checks

Create a local Postman variable `orderBaseUrl = http://localhost:8002`.
No account or token is required for the operational endpoints.

| Request | Expected result |
| --- | --- |
| `GET {{orderBaseUrl}}/health/live` | `200`, `{"status":"live"}` even if the database is down |
| `GET {{orderBaseUrl}}/health/ready` | `200`, `{"status":"ready"}` when the migrated database is accessible |
| Ready with an unset URL, inaccessible DB or missing schema | `503`, safe `SERVICE_NOT_READY` error; no URL/password/SQL details |

Supply `X-Correlation-ID: order-f0-demo` and check the same response header. An
absent/malformed ID is replaced with a generated ID. Readiness errors include
`error.correlationId`, `error.message` and empty `error.fieldErrors`, following
User Service's operational envelope. Business API naming/casing is still pending.

For an outage demo, stop only the Order database container, repeat both requests,
then restart it and verify readiness recovers without restarting the API. This
interrupts Order connections; do it only in your own test environment.

TLS URL support preserves the requested `sslmode` using asyncpg's documented
SSL modes. `require` encrypts without guaranteeing certificate verification;
use `verify-full` with a trusted certificate for verified remote connections.
See [asyncpg connection options](https://magicstack.github.io/asyncpg/current/api/index.html)
and [Supabase CLI configuration](https://supabase.com/docs/guides/local-development/cli/config).

## Create/read verification (2026-10-09)

- Full suite: 105 passed, including 12 real-PostgreSQL tests. CI selection:
  93 passed, 12 deselected. Ruff and whitespace checks passed.
- Canonical SQL migrations applied to a fresh disposable PostgreSQL 17 container
  with Supabase role names bootstrapped for grants. This verifies PostgreSQL SQL,
  not a new Supabase CLI reset; existing development databases were not migrated/reset.
- Real-DB tests cover concurrent same-key creation, stale leases, rollback after
  inserting an Order but before history, lost post-commit acknowledgment, recovery,
  filtering and API queries. Credit/User/Supplier responses are test doubles.
- Four creation/recovery/API tests also passed under a restricted login inheriting
  `order_service_app`. The built non-root image returned 200 for live/ready/docs/
  OpenAPI, remained ready after its restart, packaged `order-recovery`, and contained
  no `.env` files. Only disposable test containers were used for these checks.
- Real Credit integration and real User/Supplier runtime smoke, Postman GUI execution,
  workload measurements and future lifecycle/events are not claimed by this evidence.

## Historical F0 verification (2026-10-09)

- 39 pytest tests passed, including two read-only real-PostgreSQL checks; Ruff passed.
- The new empty Order database was rebuilt with `supabase db reset --local --yes`;
  the schema-only migration applied successfully. Existing service databases were untouched.
- The Docker image built and ran as `order_service` (non-root). Both health endpoints
  returned 200 and Studio returned 200.
- With only Order PostgreSQL stopped, liveness stayed at 200 and readiness returned
  503. Readiness recovered after the database started, without an API restart.
- An independent API restart succeeded; migration metadata survived the database restart.

These checks advance Order's portion of M7NFR1.2, M7NFR2.1-2.2 and M7NFR3.2-3.3.
They do not complete an M3 business feature, the shared one-command deployment,
production credential provisioning, NFR load targets or a real Order/Credit workflow.
HTTP smoke checks were automated; the Postman GUI was not exercised.
