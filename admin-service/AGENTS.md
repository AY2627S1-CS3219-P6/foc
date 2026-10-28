# Admin Service instructions

- Admin Service supports the Admin Dashboard nice-to-have (backlog N2). It owns dispute cases,
  their status history and the dashboard action audit log. It never reads another service's
  database and is never read by one; errand, credit and identity data come from Order, Credit
  and User through their versioned HTTP APIs.
- `supabase/migrations/` is the only schema history. Do not run DDL at startup.
- Every `/v1/admin` route depends on `require_admin` (`app/admin/auth.py`): the caller's current
  session and role come from User's `GET /v1/users/me` on every request. Fail closed with `503`
  when User is unavailable; never trust role claims from the token.
- Resolving or rejecting a dispute records a decision only. Never call Order or Credit write
  endpoints, change an errand's state or move credits from this service.
- Dispute history and audit tables are append-only: the runtime role has SELECT and INSERT
  only, and triggers reject UPDATE and DELETE.
- Never log tokens, secrets, URLs, SQL, exception text, dispute descriptions or reasons. Keep
  `.env.example` and `.env.docker.example` in sync with `Settings`.
- Integration tests write data: point `ADMIN_TEST_DATABASE_URL` only at your own disposable
  Admin database, never a teammate's or a shared one.
- Tie tests and commit/PR summaries to the N2F*/N2NFR* requirement IDs they cover.
