# FoC Credit Service

Credit owns FoC's closed credit economy: one wallet per user, the initial allocation,
atomic reserve/release/transfer for errands, and an append-only transaction ledger.

## Stack and boundaries

Python 3.13, FastAPI/Pydantic, SQLAlchemy async/asyncpg and a separate Supabase
PostgreSQL 17 project, following Order Service's runtime conventions. Credit never
reads another service's database and is never read by one; other services reach it
only through its versioned HTTP API and `foc.events` messages.

The application factory owns a connection pool and closes it on shutdown. Startup
does not connect, migrate or seed the database. Readiness runs a bounded read-only
check that the `credit_service` schema is reachable; liveness is independent of it.

## Local setup

Run from `credit-service/`. Docker Desktop must already be running.

1. Create an isolated Python 3.13 environment and install dependencies.

   Windows Git Bash:

   ```bash
   py -3.13 -m venv .venv
   .venv/Scripts/python.exe -m pip install -e '.[dev]'
   ```

   On macOS/Linux use `python3.13` and `.venv/bin/python`. PowerShell can use
   `py -3.13` and `.\.venv\Scripts\python.exe`.

2. Install the team-pinned Supabase CLI and start **this service's** database:

   ```bash
   npm ci
   npx supabase start
   ```

   The project ID is `credit-service`. Auth, Data API, storage, realtime, analytics,
   SMTP and edge functions are disabled. Studio is an operator UI, never a browser
   dependency of FoC.

3. Copy `.env.example` to an ignored `.env` only if `.env` does not already exist.
   Set `DATABASE_URL` to the connection URL from this project's `npx supabase status`.
   Host applications use `127.0.0.1:16522`. Do not reuse a User, Supplier or Order URL.

   The migration creates a `credit_service_app` NOLOGIN role with schema USAGE and
   table-specific grants. A deployment operator provisions a dedicated login that
   inherits this role; no login/password is embedded in migrations.

4. Start the API:

   ```bash
   .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8003
   ```

| Purpose | Address |
| --- | --- |
| Credit API / Swagger | `http://localhost:8003/docs` |
| Process liveness | `http://localhost:8003/health/live` |
| Database readiness | `http://localhost:8003/health/ready` |
| Credit Studio | `http://localhost:16523` (select `credit_service`) |
| Credit PostgreSQL | `127.0.0.1:16522` (not a webpage) |

Reserved local ports are in `1652x`, separate from User's `1542x`, Supplier's `5532x`
and Order's `1642x`.

## Migrations and preserved data

`supabase/migrations/` is the sole schema history. Never use SQLAlchemy `create_all`,
an additional migration framework or startup DDL.

```bash
npx supabase migration new <description>
npx supabase migration up --local
```

Reconstruct migrations with `npx supabase db reset --local` **only in an explicitly
disposable Credit database**. The reset deletes local application data. Ordinary
`npx supabase stop` / `npx supabase start` retains it.

## Tests

```bash
.venv/Scripts/python.exe -m pytest -q -m "not integration"
.venv/Scripts/python.exe -m ruff check app tests
```

Integration tests **write and truncate data**. Set `CREDIT_TEST_DATABASE_URL` in your
terminal to your own disposable, migrated Credit database (for example the local
administrative URL from `npx supabase status`), then run:

```bash
.venv/Scripts/python.exe -m pytest -q -m integration
```

CI runs lint, the unit/ASGI tests and an image build. Tests marked `integration` are
explicitly deselected there, not counted as passing.
