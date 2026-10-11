# Isolated local Order demo (simulated Credit)

This is **test infrastructure, not the Credit Service**. It uses the real Order
API, PostgreSQL transactions, recovery/expiry/outbox workers and RabbitMQ, with
a small HTTP/event Credit simulator. Real User login and Supplier APIs still run
on ports 8000/8001. It does not bypass Order's authentication or reservation checks.

The demo website is **http://localhost:3001/orders** and visibly labels simulated
credits. Port 3000 and your existing Supabase projects/settings are unchanged.
No wallet balance, real money, credit allocation or real transfer is implemented.
Completion events now record a simulated TRANSFERRED state and recipient only.
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
6. As courier B, use **Mark picked up**, then **Mark delivered** on the accepted
   errand. Refresh as requester A, choose **Confirm received**, then **Complete
   errand**. History should read OPEN → ACCEPTED → PICKED_UP → DELIVERED → COMPLETED.
   Delivery alone does not settle the reward. The UI deliberately says payment is
   unconfirmed; the inspector below shows the simulated TRANSFERRED result.
7. For overdue testing, use a near-future delivery deadline, accept before the
   acceptance deadline and wait without delivering. Refresh to see overdue status;
   delivery/completion must still work and retain the late-delivery marker.
8. In ACCEPTED or PICKED_UP, either participant can choose **Mark failed**, select
   a reason, optionally add details (required for Other), then **Confirm failure**.
   No other-party approval is needed. The errand and history show FAILED and the
   recorded reason; the inspector eventually shows RELEASED. There is no penalty.
   Failure is unavailable once DELIVERED or terminal. Test requester failure after
   acceptance and courier failure after pickup on different errands.
9. On an ambiguous/lost action response, retry the **same action/report**. Failure
   reason/details stay frozen while the result is unknown. On conflict, refresh.

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
orders stay RESERVED until requester completion. Cancellation/expiry consume actual versioned events and
change the matching simulated reservation to RELEASED; failure does the same without
assigning blame or penalties. Completion changes it to
TRANSFERRED with the assigned courier recorded. IDs and settlement deduplication
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
The historical queue name `credit-simulator.releases` now also binds completion;
it also binds order.failed.v1; keeping it preserves queued releases during upgrades.
It rejects malformed/unmatched events; it is not production consumer reliability
or wallet accounting evidence. Broker reconnection, HTTP replay/abort and terminal
release are narrow development aids, not a replacement for Credit integration.

## Checks and stopping

### Upgrading an existing demo (preserves your data)

The new migration is automatically applied only when initializing a **new** demo
database. For an existing demo from the earlier PR, apply this once from this folder
before rebuilding. Do not rerun it if `overdue_at` already exists:

```powershell
docker compose exec database psql -U postgres -d postgres -c "SELECT column_name FROM information_schema.columns WHERE table_schema='order_service' AND table_name='orders' AND column_name='overdue_at';"
# If the query returns zero rows:
Get-Content ../supabase/migrations/20261011000100_order_fulfilment_completion.sql -Raw | docker compose exec -T database psql -U postgres -d postgres -v ON_ERROR_STOP=1
docker compose up --build -d
```

For the failure extension, check/apply its separate migration once after the
fulfilment migration. Do not rerun if `failed_at` already exists:

```powershell
docker compose exec database psql -U postgres -d postgres -c "SELECT column_name FROM information_schema.columns WHERE table_schema='order_service' AND table_name='orders' AND column_name='failed_at';"
# If the query returns zero rows:
Get-Content ../supabase/migrations/20261011000200_order_participant_failure.sql -Raw | docker compose exec -T database psql -U postgres -d postgres -v ON_ERROR_STOP=1
docker compose up --build -d
```

This targets only `foc-order-demo` PostgreSQL, not your existing Supabase project.
Future migrations need their own reviewed upgrade procedure; never reset data just
to make a new API image healthy.

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
