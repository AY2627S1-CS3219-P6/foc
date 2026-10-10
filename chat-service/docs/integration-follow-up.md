# External integration follow-up

This branch changes only `chat-service/**`. No User Service changes are imported/cherry-picked,
and no root Compose, root CI or web-client file is changed. The User Service interface worker's
production endpoints were exercised over HTTP independently of contract-fake tests.

## User Service

Integrate `feature/user-service-chat-interface` separately. Match the dedicated
`CHAT_SERVICE_SHARED_SECRET` through secret management and configure `USER_SERVICE_BASE_URL`
to the direct internal User Service address. No Supplier secret fallback, signing private key,
User Service database URL or Supabase client key belongs in Chat Service. Public JWKS use
`/.well-known/jwks.json`, issuer `foc-user-service` and audience `foc-services` by default.

Search: `GET /v1/internal/chat/users` with service header and caller bearer.
Batch: `POST /v1/internal/chat/participants` with service header only and 1–100 user IDs.
Use the worker's `user-service/docs/chat-integration-contract.md` as the authoritative contract.

## Compose and secrets

`chat-service/compose.yaml` is a standalone optional `chat` profile launcher on the existing
root stack's `foc-dev_edge`, `foc-dev_user-internal`, and `foc-dev_support` networks. The API
publishes loopback port 8003; the publisher has its own `chat-outbox` command and can restart
independently. For a unified root invocation, add equivalent services to root Compose with
build context `./chat-service`, env file `./chat-service/.env`, appropriate network references
and `profiles: [chat]`. Do not change User Service's publisher. Keep `DATABASE_URL_DOCKER` and
`RABBITMQ_URL_DOCKER` service-specific. The shared broker must permit Chat Service to declare
the durable `foc.chat.events` topic exchange and per-process server-named exclusive queues.

Production migration tooling provisions a dedicated Chat Service Supabase project and a
restricted login inheriting `chat_runtime`. Migrations contain no passwords and execute only
via the deployment/migration workflow. Use TLS/database and broker secret policy appropriate
to deployment; never run the local test login in production. Browser configuration receives
only application routes and no infrastructure credentials.

## Proxy routing

In `web-client/vite.config.ts`, insert `/v1/chat` before the existing generic `/v1` route,
point to `http://127.0.0.1:8003` (or the configured Chat Service URL), and set `ws: true`.
Preserve the original path. Configure origin allow-list to the actual browser origin.

In `web-client/nginx/default.conf`, route `/v1/chat/` before generic User Service handling.
Use HTTP/1.1, forward `Upgrade` and the matching `Connection` upgrade value, preserve bearer
and correlation headers, and allow an idle WebSocket timeout suitable for keepalive pings
(for example `proxy_read_timeout 60s` with client pings every 20s). Use the existing Docker
DNS resolver and a variable/dynamic upstream for `chat-service:8003`, so Nginx startup still
works while the optional profile is disabled. Test both enabled and disabled startup.

## CI

Add `chat-service/**` to change detection and add a Chat backend job using Python 3.13:

1. From `chat-service`, `uv sync --locked --extra dev`.
2. `uv run ruff check app tests scripts` and `uv run ruff format --check app tests scripts`.
3. Run unit tests without infrastructure, then provision a separate local Chat Supabase project
   from the committed migration/config. Run a clean local reset and
   `uv run python -m scripts.provision_test_role` afterwards.
4. Start a dedicated test RabbitMQ container at loopback port 17425 and configure
   `CHAT_TEST_DATABASE_URL`, `CHAT_TEST_RABBITMQ_URL` as in verification documentation.
   Run the full suite. Restart tests are opt-in and guarded by container/port checks.
5. Build `chat-service/Dockerfile`; run the non-root API/publisher smoke.
6. Exercise actual User Service HTTP/JWKS integration with owner-provisioned disposable
   accounts. The Chat worker must not reset User Service resources. Never use real credentials
   in repository examples or print the fixture. Persist only sanitized counts/timings.

Do not run database tests in parallel against the same disposable state or restart resources
used by other jobs. The test suite uses unique UUID fixtures rather than truncating tables.

## Final UI and acceptance

Implement protected `/messages` and `/messages/:conversationId` with shared WorkspaceShell,
WorkspaceTopbar/styles and the Figma source of truth. Search opens/creates directly; no
first-contact dialog. Render current display names with smaller `@username`; null usernames
are omitted. Render message text as plain text. Distinguish pending/sent/failed/received,
retain uncertain retry identity, and handle blocked/deleted/reconnect conditions explicitly.

Follow the focus/visibility, monotonic read, optimistic deduplication and recovery obligations
in `backend-contract.md`. A `sync.required` frame requires summary reload and history catch-up,
including when the WebSocket itself never disconnected. Refresh metadata after profile/block
changes; `conversation.updated` is reserved and is not currently emitted.

Run lint/build, components/end-to-end, two real signed-in browsers, keyboard checks and
360/768/1024/1440px viewport checks. Three-action search-to-send, visual feedback, accessibility
and responsive acceptance are pending. Sprint 4 formal scale/p95 criteria remain deferred.
