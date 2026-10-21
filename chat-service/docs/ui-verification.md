# Phase 6 — Sprint 3 Chat UI

The web client implements protected `/messages` and `/messages/:conversationId`
routes using the shared WorkspaceShell, WorkspaceTopbar, navigation and design
tokens. The desktop list/thread layout becomes a single-pane flow with back
navigation below 768px. The Figma file required a signed-in session during this
implementation; visual verification used the existing FoC shell/tokens rather
than claiming a pixel comparison with inaccessible Figma frames.

## Implemented behavior and requirement mapping

| Requirements | Browser behavior and evidence |
| --- | --- |
| N1F1.1–N1F1.1.3 | Live, paginated partial-username search; selecting a result directly creates/reopens its private conversation. Protected deep links and outsider denial. No contact-request dialog. |
| N1F1.2, N1F1.2.1, N1F1.2.3, N1F1.2.4 | Current display name with smaller `@username`, latest message/time and unread badge; latest 50 messages, explicit older pages and chronological catch-up. Refresh includes all displayed conversation pages. |
| N1F1.2.2–N1F1.2.2.4 | Read acknowledgements only after rendering a selected, visible, focused conversation. Initial acknowledgement uses the full history snapshot boundary, including messages outside its latest page. Persisted state drives badges; failed reads remain unread and can retry. Reader-only cross-tab updates are applied monotonically. |
| N1F1.3–N1F1.3.4 | Keyboard-accessible block/unblock controls and blocked-user management; bilateral messaging availability comes from the server. Unblocking one direction does not remove the other party's block. Rejected messages are never automatically replayed. |
| N1F1.4–N1F1.4.3 | Raw Unicode code-point limit before trimming, whitespace-only/NUL/surrogate rejection and plain-text rendering. Internal spaces/newlines are retained. Empty input is disabled; invalid length produces an announced error. |
| N1F1.5–N1F1.5.2 | Distinct sending/sent/not-confirmed/received states. Explicit retry preserves client message ID and original text; editing a failed draft creates a new ID. Acceptance/live/history results reconcile optimistic messages without duplicate bubbles. |
| N1F1.6–N1F1.6.5 | Deleted counterpart history stays visible, with `Deleted User`, no username and an unavailable composer. Search/status remain authoritative backend decisions, so a replacement username cannot inherit history. |
| N1NFR3.1 | Three task actions: enter a username query, select its result, compose/send. Search is live and opening does not require a separate creation confirmation. |
| N1NFR3.2 | Visible connection, pending/success/failure and retry states; read/save failures do not imply successful persistence. |
| N1NFR3.3 | Viewport-bounded Chat at 320×568, 360×640, 375×667, 667×375, 768×600, 1024×768 and 1440×900; no horizontal or vertical page overflow. History and directory scroll inside their panes while shared navigation and the composer remain visible. |
| N1NFR3.4 | Labeled search/composer, keyboard-opened search results, Enter-to-send/Shift+Enter newline, keyboard block controls, visible focus, status/error announcements and semantic lists/links/buttons. |

The socket sends the in-memory bearer in its first frame, validates the current
session through the existing refresh flow before connecting, pings every 20
seconds and reconnects with bounded backoff. Access tokens are absent from URLs
and persistent JavaScript storage. Concurrent expired HTTP/socket requests share one refresh-cookie
rotation; StrictMode restoration also rotates only once. Logout invalidates any
older refresh in flight. A dependency error after a successful refresh does not
sign the user out.

Reconnect, `sync.required`, and sequence gaps reload summaries and catch up
visited conversations from their processed sequence. Later messages are withheld
while a gap is recovered. Reconnecting never automatically resends failed drafts.
There are no sender-facing read receipts, typing indicators or first-contact states.

Chat uses the shared shell's optional viewport layout, sized with `100dvh` and a
`100vh` fallback. The mobile navigation occupies its own layout row, including
safe-area padding, rather than covering the composer. Long message histories,
conversation lists, search results and expanded blocked-user lists scroll within
bounded panes. Positioned containers prevent hidden accessibility labels from
extending the document as those lists grow. The composer has a bounded height;
long drafts scroll inside its text field.

Auto-scroll changes only the history pane and follows new messages while the
reader is near its end. Incoming messages do not move a reader browsing older
history. Loading an older page preserves the previous message's screen position.
Composer focus does not scroll ancestors, and viewport resizing keeps the latest
message visible when already following the end. Short screens use tighter
spacing; landscape screens put Send beside the text field and retain connection
status, the conversation header and both shared navigation areas.

## Viewport regression follow-up — 21 October 2026

- Ten new browser regressions cover 200 seeded messages, 40 conversations,
  40 expanded blocked users, incoming bursts, send/focus, scroll boundaries,
  older-page anchoring, viewport resizing and mobile admin validation.
- All **21 Chat browser tests passed against the rebuilt Nginx container** on
  `http://localhost:3000`, using test-only HTTP/WebSocket contract fixtures.
  Desktop, small portrait and short landscape screenshots were inspected.
- Frontend lint, TypeScript/production builds, the Docker web build and all
  **121 frontend unit/component tests passed**.
- The wider Vite browser run had **98 passed, one failed and one opt-in live case
  skipped** before the final blocked-list regression was added. Its existing
  `orders.spec.ts` deadline case also failed when rerun: the one-second deadline
  had elapsed before its initial Cancel assertion. Order code/tests were not
  changed for this Chat fix. This run is not claimed as a fully passing suite.
- This follow-up changes browser layout/scrolling only. The previous real-service
  acceptance evidence below remains historical; no database reset or backend
  restart was needed.

## Automated checks

From `web-client`:

```sh
npm ci
npm run lint
npm run build
npm test
npx playwright install chromium
npm run test:e2e
```

The normal browser suite uses test-only HTTP/WebSocket fixtures. It covers the
search/open/send flow, Unicode boundaries and HTML-looking text, uncertain retries,
edited retry identities, bilateral blocks, tombstones, pagination, broker recovery,
failed reads, cross-tab read updates and protected routes. Component tests send
focus/blur/visibility lifecycle events through the actual page/controller; unit
tests cover races, monotonic cursors, paginated recovery and token renewal.
When `E2E_BASE_URL` is unset, Playwright starts Vite automatically. If that variable
points to an existing server, start that server before running the browser suite.

The live test is deliberately opt-in. With the root local stack, Chat profile,
existing migrations and matching User/Chat secret configured, run against the
Docker web proxy from `web-client`:

```sh
CHAT_LIVE_E2E=1 E2E_BASE_URL=http://localhost:3000 npx playwright test tests/e2e/messages-live.spec.ts --workers=1
```

PowerShell:

```powershell
$env:CHAT_LIVE_E2E='1'
$env:E2E_BASE_URL='http://localhost:3000'
npx.cmd playwright test tests/e2e/messages-live.spec.ts --workers=1
Remove-Item Env:CHAT_LIVE_E2E
Remove-Item Env:E2E_BASE_URL
```

This creates three uniquely named `phase6...` test accounts through real User
  registration/verification, reads only Mailpit messages filtered to those new
recipients, and signs into separate browser contexts. Credentials remain in
memory. It exchanges real messages through Chat's PostgreSQL/outbox/RabbitMQ,
checks unread state, reload persistence, blocking/unblocking and outsider denial,
and captures 360/1440px screenshots under the ignored Playwright output directory.
It leaves the new local test accounts/history in place; it never resets databases,
deletes existing accounts, purges mail or truncates another service's tables.
Headless Playwright forces focus, so the real-service test checks active/unselected
thread behavior; the component suite separately verifies hidden/unfocused gating.

## Acceptance evidence — 21 October 2026

- Frontend lint and production build passed, including TypeScript checking tests.
- Full browser suite: **90 passed**, with the opt-in live test skipped in that run.
- **121 frontend unit/component tests passed**, including focus/visibility,
  refresh-cookie concurrency and paginated counterpart-name refresh.
- The opt-in real User/Chat/PostgreSQL/RabbitMQ test passed separately through both
  Vite and the rebuilt Nginx proxy on port 3000. Docker image build and healthy local
  startup passed; real mobile/desktop screenshots were inspected.
- **25 Chat backend unit tests passed**; the 19 database/broker restart/transaction
  cases were not rerun for this frontend phase. The live browser check uses real
  PostgreSQL/outbox/RabbitMQ without resetting or restarting shared dependencies.
- No backend business rules, database migrations, service secrets or existing
  database records were changed for this UI work. Live checks add their own test
  accounts, messages, blocks and read state through public APIs.

## Manual two-browser check

1. Start the application using the root README and open `/messages` after signing
   in. Sign in as a different active account in an incognito/separate browser.
2. Search part of the other username, select it, and compose/send a message.
   Confirm one sent bubble, one received bubble, and retained internal whitespace.
3. Leave the recipient on the conversation list or another conversation. Send
   again; its unread badge should increase. Open the conversation in a focused,
   visible tab; the badge should clear after the read acknowledgement succeeds.
4. Background or hide the selected tab, send another message, then return. It
   should accumulate unread while inactive and acknowledge after presentation.
5. Refresh/reconnect and verify retained ordered history without duplicate bubbles.
   Use the existing Postman walkthrough for controlled backend outage scenarios.
6. Block/unblock, open blocked-user management, and verify history remains visible.
   In a disposable-account scenario, counterpart deletion retains tombstone history
   and disables new sends. A third user must not open the private conversation.
7. Repeat keyboard-only and at 360px: search, open, send, retry and block controls
   remain reachable; mobile back navigation returns to conversations.

## Excluded scope

Sprint 4 errand status/requester/courier context, 1,000-connection tests,
25-messages/second sustained load, formal latest-50 performance and p95 targets
are not implemented or certified here. Production deployment and an automatically
provisioned real User + Chat CI job remain separate integration work. The existing
Chat CI job still uses a User identity contract fake for backend isolation.
