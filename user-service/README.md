# User Service

Phase 0 provides the runnable FastAPI foundation only. It has database-aware
health checks, structured redacted logs, correlation IDs, local supporting
services, and test commands. Registration, credentials, OTPs, sessions, and
schema migrations begin in later phases.

## Local development

Run these commands from this directory.

1. Install the pinned Supabase CLI package and start the isolated local
   PostgreSQL stack.

   npm install
   npx supabase start

2. Create a Python 3.13 environment, install the service, and generate
   development-only secrets. The generator reads the local database URL without
   printing it, writes ignored files only, and does not overwrite existing
   secrets unless explicitly run with --force.

   py -3.13 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install --upgrade pip
   .\.venv\Scripts\pip.exe install -e ".[dev]"
   .\.venv\Scripts\python.exe scripts\generate_dev_secrets.py

3. Start the service, Mailpit, and RabbitMQ. The service reaches the Supabase
   CLI PostgreSQL container through the derived DATABASE_URL_DOCKER value and
   reaches RabbitMQ with the generated non-guest development credentials.

   docker compose up --build

The liveness probe is available at http://localhost:8000/health/live. Once
Supabase PostgreSQL is reachable, http://localhost:8000/health/ready returns
200. Mailpit is available at http://localhost:8025 and RabbitMQ management at
http://localhost:15672.

The liveness endpoint never waits for PostgreSQL; the readiness endpoint
performs the database probe. The application never creates, modifies, or
migrates schema objects at startup. Standard `postgresql://` database URLs are
accepted and normalized to the asyncpg dialect internally.

## Tests and local database reset

Run the baseline unit and ASGI integration tests:

    .\.venv\Scripts\pytest.exe

To run the real database readiness integration test, start local Supabase and
use the helper. It discovers the local database URL without echoing it:

    .\.venv\Scripts\python.exe scripts\run_tests_with_local_supabase.py

The Supabase migration directory is the only migration history. Phase 0 does
not add a schema migration. Later schema changes must be created with:

    npx supabase migration new <description>
    npx supabase db reset

For the hosted project, authenticate with the Supabase CLI and link this local
project using the actual cloud project reference for foc-user-service:

    npx supabase link --project-ref <project-ref>

The CLI link state remains local and ignored. Do not place hosted database
credentials, Supabase URLs, or Supabase keys in this repository.
