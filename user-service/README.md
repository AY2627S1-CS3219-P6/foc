# User Service

Phases 0 through 2 provide a runnable FastAPI foundation, verified student
account creation, and revocable authentication. The service has database-aware
health checks, structured redacted logs, correlation IDs, Supabase SQL
migrations, bcrypt credential storage, Mailpit OTP verification, RS256 access
tokens, rotating refresh-token cookies, and a self-only identity endpoint.

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

3. Apply the committed schema history to the local database.

   npx supabase db reset

4. Start the service, Mailpit, and RabbitMQ. The service reaches the Supabase
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

Run the unit and ASGI integration tests:

    .\.venv\Scripts\pytest.exe

To run the real database readiness integration test, start local Supabase and
use the helper. It discovers the local database URL without echoing it:

    .\.venv\Scripts\python.exe scripts\run_tests_with_local_supabase.py

The Supabase migration directory is the only migration history. Schema changes
must be created with:

    npx supabase migration new <description>
    npx supabase db reset

For the hosted project, authenticate with the Supabase CLI and link this local
project using the actual cloud project reference for foc-user-service:

    npx supabase link --project-ref <project-ref>

The CLI link state remains local and ignored. Do not place hosted database
credentials, Supabase URLs, or Supabase keys in this repository.

## Phase 1 manual smoke test

Keep `docker compose up --build` running, then use a second PowerShell window.
First confirm the service is ready:

    Invoke-RestMethod http://localhost:8000/health/ready

Create a valid, unique student account. The password below is an example only;
do not reuse it outside local testing.

    $registration = @{
      username = "phase1-smoke-user"
      email = "phase1-smoke-user@u.nus.edu"
      password = "Phase1SmokePass1!"
    } | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri http://localhost:8000/v1/auth/registrations -ContentType "application/json" -Body $registration

Open http://localhost:8025, open the verification email, and copy its
six-digit code. Verify with that code:

    $verification = @{
      email = "phase1-smoke-user@u.nus.edu"
      otp = Read-Host "Mailpit verification code"
    } | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri http://localhost:8000/v1/auth/email-verifications -ContentType "application/json" -Body $verification

The response must report `status: active` and `systemRole: USER`. Repeat the
registration request to see duplicate protection, or replace one field with an
invalid NUS email, a username containing a space, or a weak password to see
safe field errors.

## Phase 2 manual smoke test

Start from an account already verified through the Phase 1 flow. The development
secret generator creates the RSA key pair configured by `JWT_PRIVATE_KEY_PATH`
and `JWT_PUBLIC_KEY_PATH`; never copy those values into a request, response,
or source file.

In a second PowerShell window, log in and retain the web session so the
`HttpOnly` refresh cookie is sent automatically:

    $webSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $login = Invoke-RestMethod -Method Post -WebSession $webSession -Uri http://localhost:8000/v1/auth/sessions -ContentType "application/json" -Body (@{
      email = "phase1-smoke-user@u.nus.edu"
      password = "Phase1SmokePass1!"
    } | ConvertTo-Json)
    $accessToken = $login.accessToken

The server caps every refresh session at 24 hours and invalidates a session
after 30 minutes without an authenticated request. Those limits apply even if
an older local `JWT_REFRESH_TOKEN_TTL_SECONDS` value is longer.

Read only the authenticated caller's profile:

    $authorization = @{ Authorization = "Bearer $accessToken" }
    Invoke-RestMethod -Headers $authorization -Uri http://localhost:8000/v1/users/me

Rotate the refresh session, then use the returned access token:

    $rotated = Invoke-RestMethod -Method Post -WebSession $webSession -Uri http://localhost:8000/v1/auth/sessions/refresh
    $authorization = @{ Authorization = "Bearer $($rotated.accessToken)" }
    Invoke-RestMethod -Headers $authorization -Uri http://localhost:8000/v1/users/me

The original access token is now rejected because its server-side session was
revoked during rotation. Finally, log out and confirm the rotated token is also
rejected:

    Invoke-WebRequest -Method Delete -WebSession $webSession -Headers $authorization -Uri http://localhost:8000/v1/auth/sessions/current
    Invoke-WebRequest -SkipHttpErrorCheck -Headers $authorization -Uri http://localhost:8000/v1/users/me

The final request must return `401`; the refresh token is never returned in JSON.
The public signing key is available at
`http://localhost:8000/.well-known/jwks.json`; it contains no private-key material.
