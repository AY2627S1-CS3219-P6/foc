# Isolated local Order demo (simulated Credit)

This is **test infrastructure, not the Credit Service**. It uses the real Order
API, PostgreSQL transactions, recovery/expiry/outbox workers and RabbitMQ, with
a small HTTP/event Credit simulator. Real User login and Supplier APIs still run
on ports 8000/8001. It does not bypass Order's authentication or reservation checks.

The demo website is **http://localhost:3001/orders** and visibly labels simulated
credits. Port 3000 and your existing Supabase projects/settings are unchanged.
No wallet balance, real money, credit allocation or transfer is implemented.
The proposed Credit contract still needs agreement/integration with its owner.

## Start from VS Code PowerShell

Start Docker Desktop and your existing User/Supplier Supabase stacks first.
If those databases are already running, do not reset them. From the repo root:

```powershell
docker compose --env-file user-service/.env up -d user-service supplier-service mailpit outbox-publisher
cd order-service/demo
.\setup.ps1
docker compose up --build -d
docker compose ps
```

- `setup.ps1` generates **ignored, demo-only** random secrets once. It never
  changes another service's environment file or overwrites an existing demo file.
- Compose starts a separate `foc-order-demo` project/network, Order database,
  broker, simulator, Order API/workers and website. Only website 3001 and Order API
  18002 are published, bound to loopback. Database/broker/simulator stay internal.
- The empty demo database initializes from the canonical Order migrations, then
  a one-shot task provisions a restricted app login. No migrations run inside
  the Order API and no existing Supabase database is migrated/reset.
- Restarting preserves demo database, broker and simulator volumes. Initialization
  SQL runs only on a fresh volume; future schema changes need a reviewed migration
  or deliberate disposal of this **entire demo**, not a reset of your Supabase DB.
- Use the same demo `.env` with its volumes. Regenerating passwords while retaining
  initialized database/broker volumes will not rotate their stored passwords.

## Try the UI

1. Open port **3001**, sign in as requester A. Existing local accounts work; new
   mock `@u.nus.edu` accounts can be verified through Mailpit on port 8025.
2. Create an errand with a future acceptance deadline and later delivery deadline.
   Use any positive whole-number reward. In success mode, the simulator accepts
   it without enforcing a wallet balance. A real OPEN row is saved **only in the
   isolated demo Order database**.
3. Open its detail page. A sees **Cancel errand**, followed by a confirmation.
   **Keep errand** backs out without a request. Cancelling updates state/history.
4. Create another errand. Use a separate browser/incognito window for courier B
   (cookies are shared between tabs). Browse and open the errand, then **Accept
   errand**. B becomes the courier; both participants can view its history under
   **My errands**. A cannot accept their own errand or cancel once accepted.
5. Create another with acceptance 1–2 minutes away. Leave it unaccepted. The expiry
   worker marks it EXPIRED; **Refresh errand** updates the page and shows a System
   action. The local countdown is only a convenience; server time decides validity.
6. On an ambiguous/lost action response, retry the **same action**. On conflict,
   refresh. There is no optimistic success and no pickup/delivery/completion UI yet.

Cookies do not isolate by port: logging in/out on 3000 and 3001 in the same browser
profile can affect the same User session. Use separate browser profiles for parallel tests.
Existing real Order errands are intentionally absent from the demo database.

## Observe simulated Credit and failures

Run these from `order-service/demo`:

```powershell
docker compose exec credit-simulator python credit_stub.py
docker compose logs --tail 30 order-expiry order-outbox credit-simulator
docker compose exec database psql -U postgres -d postgres -c "SELECT id, state FROM order_service.orders;"
```

The inspector shows `orderId`, amount and simulation state, not secrets. Accepted
orders stay RESERVED. Cancellation/expiry consume actual versioned events and
change the matching simulated reservation to RELEASED. IDs and release deduplication
persist in a private SQLite volume across simulator restarts. CLOSED is a durable
creation-abort fence: a delayed reserve cannot reopen it. No cross-service DB reads.

Edit **only** this folder's ignored `.env`: set `SIMULATOR_MODE` to `success`,
`insufficient_credit`, `wallet_not_ready` or `unavailable`, then:

```powershell
docker compose up -d --no-deps credit-simulator
```

Insufficient/unready modes deny **new** reservations with 409. Existing successful
reservations keep their identity. Unavailable returns 503 for all contract calls;
an Order creation can become pending (202), not necessarily a direct 503. Restore
success, wait for recovery, then use **Check status / Finish creating errand** or
**Retry same request** in the original tab. If its deadline passed, recovery closes
it; do not expect it to open. Don't create another request to replace an unknown one.

To demonstrate delayed async release, stop the simulator, cancel an existing OPEN
errand, then start it again. Its durable queue retains messages; PUBLISHED in Order
means broker delivery, **not** completed Credit processing:

```powershell
docker compose stop credit-simulator
# Cancel an already-created errand in the UI.
docker compose start credit-simulator
docker compose exec credit-simulator python credit_stub.py
```

The simulator binds **only** its private broker/exchange, never shared `foc.events`.
It rejects malformed/unmatched events; it is not production consumer reliability
or wallet accounting evidence. Broker reconnection, HTTP replay/abort and terminal
release are narrow development aids, not a replacement for Credit integration.

## Checks and stopping

Backend simulator contract tests are part of the normal Order pytest suite.
For an additional live smoke (creates/self-deletes two temporary User accounts;
leaves ordinary User audit records and isolated demo errands):

```powershell
..\.venv\Scripts\python.exe smoke.py --allow-test-accounts
```

Stop **only the demo**, preserving data for next time:

```powershell
docker compose down
```

Do not add `--volumes` unless intentionally discarding **all** this demo's Order,
broker and simulated Credit data together. Never point these scripts at a hosted
database. No changes to `credit-service/` or the default application runtime are needed.
