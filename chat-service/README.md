# Chat Service

Python 3.13/FastAPI backend, isolated Supabase PostgreSQL storage, and RabbitMQ live delivery.
Only `chat-service/**` is part of this branch. See [PLAN.md](PLAN.md) for requirement aliases.

## Local setup

From this directory, run `uv sync --extra dev`, then copy `.env.example` to an ignored `.env`
and provide local credentials. Never use User Service database credentials or private RSA keys.
The dedicated `CHAT_SERVICE_SHARED_SECRET` must match User Service's configuration.

Use `npx supabase start` and `npx supabase db reset --local` here only. Project ID is
`foc-chat-service`; database/shadow ports are 17422/17420. Auth and Data API are disabled.
Migrations are the sole schema history; API startup never creates or migrates tables.
Provision a separate login with a secret password using an administrator connection, grant
`chat_runtime` to that login, and use it in `DATABASE_URL`. The migration's runtime role has
no DDL, cross-service privileges, or schema ownership. Do not use `postgres` at runtime.

Start the API with `uv run uvicorn app.main:app --port 8003 --no-access-log --ws-max-size 65536`.
Start the independent publisher with `uv run chat-outbox` after broker configuration.
`/health/live` checks the process; `/health/ready` checks every owned database table.

## Verification

`uv run ruff check app tests` and `uv run pytest -q` run local checks. Real database and
broker verification require the explicit isolated test settings documented with the tests.
No test resets or truncates another service's database.

## External integration work

The service-only scope excludes root Compose/CI and web-client edits. The shared integration
owner must add optional `chat` profile API/publisher services built from this directory,
route `/v1/chat/` before generic User Service routes with WebSocket upgrades/timeouts, and
add Chat Service change detection plus lint/unit/integration checks to CI. Use port 8003,
an independently restartable `chat-outbox` command, the shared RabbitMQ support network,
and direct User Service network access. Do not reuse User Service's publisher or identity.

Final chat UI, focus/visibility detection, plain-text rendering, optimistic deduplication,
retry UX, responsive/keyboard checks and two-browser acceptance remain external follow-up.
No Sprint 4 scale/performance compliance is claimed.
