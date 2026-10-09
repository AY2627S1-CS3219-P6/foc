# FoC Order Service

Phase F0 is the runnable foundation only. It contains no order business tables,
authentication, creation/lifecycle APIs, credit calls, events or frontend changes.

## Stack and boundaries

Python 3.13, FastAPI/Pydantic, SQLAlchemy async/asyncpg and a separate Supabase
PostgreSQL 17 project, following User Service's runtime conventions. Supplier
uses a different PostgreSQL driver; its implementation is unchanged. Order never
reads another service's database or imports its business logic.

The application factory owns a connection pool and closes it on shutdown. Startup
does not connect, migrate or seed the database. Readiness runs a bounded read-only
check for access to `order_service`; it does not prove future business migrations
or external service integrations are ready. Liveness remains independent of it.

## Local setup

Run from `order-service/`. Docker Desktop must already be running. These commands
do not require User, Supplier, Credit or RabbitMQ to be running.

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
   but no business-table grants yet. Dedicated runtime login provisioning and
   table-specific least-privilege grants must accompany future schema/deployment
   work; this is not a production-credential setup.

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

F0's schema has no tables; an empty Studio table list is expected. Reserved local
ports are in `1642x`, separate from User's configured `1542x` and Supplier's `5532x`.
The existing User port migration is separate work, not a prerequisite for F0.

## Migrations and preserved data

`supabase/migrations/` is the sole schema history. F0's timestamped SQL creates
only the owned schema and role; it grants no access to Supabase browser roles.
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

The integration tests skip unless explicitly configured. They do not reset,
populate or mutate the database. Migration-reset and container persistence tests
are separate operator checks, not implied by a passing unit suite.

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

No database credentials or local environment files are needed. The two current
database integration tests are explicitly deselected, not counted as passing.
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

## F0 verification (2026-10-09)

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
