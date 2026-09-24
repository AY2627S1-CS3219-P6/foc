# Supplier Service

## Create, update, and deactivate supplier APIs

`POST /api/v1/admin/suppliers` validates a new supplier, asks User Service for
a current `SUPPLIER_CREATE` admin decision, and inserts the supplier and
categories in one PostgreSQL transaction. It returns `201`. The
`PATCH /api/v1/admin/suppliers/{supplier_id}` route checks the current admin role
again, merges supplied fields with the stored record, validates the complete
result, and commits supplier and category changes together. It returns `200`.
`DELETE /api/v1/admin/suppliers/{supplier_id}` currently retains the supplier
and marks it `INACTIVE`, returning `{"id":"...","outcome":"DEACTIVATED"}`.
Permanent deletion awaits the Errand Service reference contract described in
[API.md](API.md#delete-contract-and-errand-references).
Authenticated users can also call `GET /api/v1/categories` to read supported
category codes and display names directly from the lookup table.
`GET /api/v1/suppliers` lists only active suppliers. It accepts `q`, repeated
`category`, `building_area`, `sort`, `page`, and `page_size` query parameters;
the response includes `items`, `page`, `page_size`, and `total`. For example:

```sh
curl -G http://127.0.0.1:8001/api/v1/suppliers \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  --data-urlencode "q=cafe" --data-urlencode "category=FOOD" \
  --data-urlencode "category=COFFEE"
```

This service keeps Supabase CLI `2.117.0` as a development dependency. Run
`npm ci` once after cloning, then use `npx supabase` from this folder for local
database and hosted-project commands. Node.js is not needed in the FastAPI
container.

Use Python 3.11 or newer. The macOS system `python3` may be older; use a
matching interpreter such as `python3.12`. From `supplier-service/`:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
```

Copy [`.env.example`](.env.example) to an ignored `.env` if you do not already
have one. It points to this service's local Supabase database by default. Set
`SUPPLIER_SERVICE_SHARED_SECRET` to the value configured by the User Service
operator. The FastAPI app reads environment variables, so load the file into
your shell before starting it:

```sh
set -a
source .env
set +a
.venv/bin/uvicorn app.main:app --reload --port 8001
```

Do not commit the populated `.env` file. To use the hosted Supplier Service
database instead, change only `SUPPLIER_DATABASE_URL` to its PostgreSQL
connection string.

With a User Service administrator access token, try:

```sh
curl -i -X POST http://127.0.0.1:8001/api/v1/admin/suppliers \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Example Cafe","categories":["FOOD"],"building_area":"Central Library","pickup_location_description":"Near the entrance","opening_time":"09:00","closing_time":"18:00"}'
```

The example uses port 8001 so User Service can use port 8000 on the same
machine.
To update the returned supplier ID, use the same access token:

```sh
curl -i -X PATCH http://127.0.0.1:8001/api/v1/admin/suppliers/YOUR_SUPPLIER_UUID \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Updated Cafe","categories":["COFFEE"]}'
```

Omitted fields stay unchanged. A supplied `categories` array replaces the old
set. Send `null` for optional fields to remove them; clear both coordinates or
both operating times together. `status: INACTIVE` uses User Service's current
`SUPPLIER_DEACTIVATE` authorization decision. A missing ID returns `404`, an
invalid resulting record `422`, and a normalized duplicate `409`.

To deactivate a supplier, send DELETE with the same administrator token:

```sh
curl -i -X DELETE http://127.0.0.1:8001/api/v1/admin/suppliers/YOUR_SUPPLIER_UUID \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN"
```

The Supplier Service asks User Service for a current `SUPPLIER_DEACTIVATE`
decision. A missing supplier returns `404`. Repeating DELETE on an already
inactive supplier returns `DEACTIVATED` again. The row and its category links
remain in Supplier PostgreSQL. Normal-user listing and Errand Service selection
checks are still planned, so this interim route does not complete every part
of backlog M2F1.3.

The User Service's published contract is
[`../user-service/docs/supplier-authorization-contract.md`](../user-service/docs/supplier-authorization-contract.md).
The Supplier Service verifies the access JWT using User Service's public JWKS,
then asks its internal endpoint for the current role. It does not read User
Service tables or trust a role supplied in the request.

### Run the API in Docker

Keep Docker Desktop, User Service, and this service's local Supabase stack
running. User Service's Compose stack provides the
`foc-user-service-internal` network. Stop the local `uvicorn` process if it is
using port 8001, then run from `supplier-service/`:

```sh
docker compose up --build -d
```

Open `http://127.0.0.1:8001/docs` and send the same administrator POST request
shown above. Compose loads the ignored `.env` for the shared secret. Inside the
container, it connects to Supplier PostgreSQL at `host.docker.internal:55322`
and to User Service at `http://user-service:8000`. These replace the
`127.0.0.1` addresses used when running Python directly on the Mac. For a
different database or User Service address, set `SUPPLIER_DATABASE_URL_DOCKER`
or `USER_SERVICE_BASE_URL_DOCKER` in `.env`. Never put secrets in the image.

```sh
docker compose down
```

This stops Supplier Service's API container. Its local Supabase database and
User Service containers remain running. The CI workflow also builds the image
after the Supplier Service HTTP tests.

Run the HTTP tests with `.venv/bin/python -m pytest -q`. The optional database
update and deactivation tests run when `SUPPLIER_TEST_DATABASE_URL` points to
the local Supplier database on port 55322; they remove their temporary suppliers.
To check the live authenticated path, send POST, PATCH, and DELETE requests with an
administrator token and confirm the changes in the Supplier Service database.
Seed SQL verifies the migration and sample data, but it does not exercise the
API.
The repository CI runs these HTTP tests for Supplier Service changes on pull
requests to `main` and pushes to `main`; it does not require Supabase
credentials or Docker.

## Database choice

Supplier Service owns a dedicated PostgreSQL database, hosted in its own
Supabase project. PostgreSQL fits the structured supplier fields, category
relationships, constrained status, atomic uniqueness rules, and the browsing
queries in the D2 backlog. A unique index resolves concurrent attempts to
create the same supplier; transactions keep a rejected write from changing
existing records.
The service accesses PostgreSQL through its backend API. Clients do not access
the database directly.

The D2 backlog expects at least 1,000 supplier records and, in a later
performance milestone, retrieval, search, filtering, and sorting within two
seconds at the 95th percentile. The initial schema indexes duplicate identity
and category assignment. Add listing and search indexes only
after measuring real queries against representative data and concurrent requests.

## Schema

The same migration is applied to local and hosted Supplier Service databases:
[`supabase/migrations/20260923000000_create_suppliers.sql`](supabase/migrations/20260923000000_create_suppliers.sql).
It creates the `supplier_service` schema in this service's database.

### Local database

With Docker Desktop running, start this service's local Supabase stack from
`supplier-service/`:

```sh
npx supabase start
```

The first start applies the migration and `supabase/seed.sql`. The local
database uses port 55322 and its Studio is at `http://127.0.0.1:55323`.
These ports differ from User Service's local Supabase ports so both stacks can
run at once. The ignored `.env` points FastAPI to this local database.

To discard local changes and restore the migrated schema and seed data:

```sh
npx supabase db reset --local
```

This reset affects this local Supplier Service database. Stop its containers
with `npx supabase stop` when you are finished. The hosted Supabase project is
separate and is unaffected by these local commands.

### Hosted database

From `supplier-service/`, link the Supabase CLI to a dedicated hosted Supplier
Service project. For a new development project, preview and apply the migration
with its sample data:

```sh
npx supabase login
npx supabase link --project-ref YOUR_SUPPLIER_PROJECT_REF
npx supabase db push --dry-run
npx supabase db push --include-seed
```

The project ref appears in the Dashboard URL. Run `--include-seed` only when
initializing a fresh development project; later schema migrations use
`npx supabase db push` without that flag. In the hosted Dashboard SQL Editor,
verify the import with:

```sql
SELECT count(*) FROM supplier_service.suppliers;           -- 21
SELECT count(*) FROM supplier_service.supplier_categories; -- 26
```

Keep database credentials out of Git. The Supabase CLI tracks applied
migrations in the hosted project.

The `suppliers` table contains:

| Column | PostgreSQL type | Rule and purpose |
| --- | --- | --- |
| `id` | `uuid` | Primary key generated by the database; immutable. |
| `name` | `text` | Required, nonblank supplier name. |
| `building_area` | `text` | Required, nonblank building or campus area. |
| `pickup_location_description` | `text` | Required, nonblank pickup instructions. |
| `floor` | `text` | Optional; blank values are treated as missing for duplicate detection. |
| `latitude`, `longitude` | `numeric(12,9)` | Optional pair; both must be present or absent and within geographic bounds. |
| `opening_time`, `closing_time` | `time without time zone` | Optional pair in 24-hour Singapore local time (`Asia/Singapore`). |
| `image_url` | `text` | Optional HTTP or HTTPS URL; the API validates complete URL syntax. |
| `status` | `supplier_status` | `ACTIVE` by default or `INACTIVE`. |
| `created_at`, `updated_at` | `timestamptz` | Database-generated timestamps; updates refresh `updated_at`. |

The category relationship uses two additional tables:

| Table | Columns | Relationship |
| --- | --- | --- |
| `categories` | `code` (text primary key), `display_name` (text) | Allowed category codes and UI labels. |
| `supplier_categories` | `supplier_id` (UUID), `category_code` (text) | Composite primary key; foreign keys to `suppliers.id` and `categories.code`. |

`categories` is a lookup table of category codes and display names, initially
seeded with `FOOD`, `COFFEE`, `SHOPPING`, `PRINTING`, `LANDMARK`, and `OTHERS`.
`supplier_categories` joins suppliers to one or more categories. Its foreign
keys reject unknown categories, and its primary key prevents a category being
assigned twice to the same supplier. A deferred database check requires at
least one category when the transaction commits, so the backend must save the
supplier and category assignments in one transaction.
Category assignment changes also refresh the supplier's `updated_at` value.
Adding a category means inserting a lookup row through a versioned data change;
the table structure stays the same. The backend should validate category codes
against the lookup table rather than a hard-coded list.

There are no cross-service foreign keys. Other services can store the immutable
supplier UUID and obtain supplier information through the Supplier Service API.

The unique index covers normalized `(name, building_area, floor)` across both
statuses. Normalization lowercases, trims surrounding whitespace, collapses
repeated whitespace, and maps a missing or blank floor to the same value. This
enforces the backlog's duplicate rule even when concurrent requests race.
The database checks required text, nonempty, known, and non-repeated category
assignments, paired and bounded coordinates, and paired operating times. The
API must validate original operating-time strings as exact 24-hour `HH:mm`
(`^(?:[01][0-9]|2[0-3]):[0-5][0-9]$`), validate complete HTTP(S) URL syntax
and partial-update semantics, and return field-level errors. PostgreSQL's
`time` type stores a value but cannot distinguish input `09:00` from `9:00`.
Creation requests must not accept client-supplied `id`, `created_at`, or
`updated_at` values, so the database generates them as intended.

Opening and closing times are recurring wall-clock times in `Asia/Singapore`.
The API should compare them with the current Singapore local time and allow
overnight ranges such as 11:00 to 02:00. `created_at` and `updated_at` are
absolute `timestamptz` values; display them in Singapore time when needed.

## Query patterns shaped by the schema

| Operation | Predicate and ordering | Index support |
| --- | --- | --- |
| Detail by ID | `id = ?` | Primary key. |
| Normal listing | `status = ACTIVE`, ordered by name and ID | Scan and sort initially; add an index if measurements justify it. |
| Management listing | Both statuses, optionally filtered by status | Sort the small result set; add an index if measurements justify it. |
| Building filter | Case-insensitive exact building/area match | Scan initially; add an expression index if measurements justify it. |
| Category filter | `EXISTS` on `supplier_categories` for any selected code, so each supplier appears once | Category/supplier index. |
| Search | Case-insensitive partial match on name, building/area, or pickup description | Scan initially; consider `pg_trgm` indexes if measured search latency requires them. |

Search and filters can be combined. Name is the default ascending sort; a
stable ID tie-breaker supports deterministic pagination. The API will apply
page 1 and page size 20 when the client omits them. Normal users see only
`ACTIVE` records; administrator listings may include both statuses.

## Supplier seed data

[`../data/csv/supplier-seed-data.csv`](../data/csv/supplier-seed-data.csv)
contains 21 sample suppliers. The committed
[`supabase/seed.sql`](supabase/seed.sql) inserts them after the migration.
It decodes the Windows-1252 CSV to UTF-8, splits types such as `Food/Coffee`
into two category assignments, converts `0900hrs` to `09:00`, and maps empty
image URLs to `NULL`. The database generates IDs, timestamps, and the default
`ACTIVE` status. All suppliers and their category assignments are inserted in
one transaction because the category requirement is checked at commit.

After editing the CSV, regenerate and check the seed using Python 3 (no extra
Python packages are required):

```sh
python3 scripts/generate_seed.py
python3 scripts/generate_seed.py --check
```

SQL seeding is a trusted setup operation that bypasses API role checks.
Supplier creation in the application must go through the authenticated backend
and its administrator authorization check. Use API requests, not seeded rows,
to demonstrate that a non-admin cannot create a supplier.

## Reset the hosted development database

From `supplier-service/`, check the linked project and reset it:

```sh
npx supabase projects list
npx supabase db reset --linked
```

This deletes the hosted project's data, then reruns all migrations and
`supabase/seed.sql`. Use it only when that project's data can be discarded.

## Requirement trace

- **Implemented by this migration:** D2 Supplier Service point 1 (database
  choice and concrete schema); the storage and relationships for M2F1.1.1;
  default status (M2F1.1.2); immutable ID (M2F1.1.3); timestamps
  (M2F1.1.4, M2F1.2.4-M2F1.2.5); database-enforceable parts of creation and
  update validation (M2F1.1.5, M2F1.2.2); normalized uniqueness on creation
  and update (M2F1.1.6, M2F1.2.3); and the concurrent duplicate safeguard
  (M2NFR3.1).
- **Requires Supplier Service API work:** exact input `HH:mm` and HTTP(S) URL
  validation, field-level error responses, partial-update and optional-field
  removal semantics (M2F1.1.5, M2F1.1.7, M2F1.2); deletion versus
  deactivation based on errand references (M2F1.3); listing, details, search,
  filters, sorting, and pagination (M2F2-M2F3); and authentication and
  administrator authorization (M2F4). D2 Supplier Service points 2-4 also
  require working APIs and integration. The D2 point 5 UI is separate work.
- **Requires integration and verification:** administrative supplier-action
  auditing (M1F5.4.3-M1F5.4.4) and the applicable reliability, security, and
  performance requirements in M2NFR1-M2NFR4. The database unique index is
  the safeguard for M2NFR3.1, but its concurrent behavior still needs a
  running-database test.

The source documents are `CS3219-Instructions-MilestoneD2.pdf`, page 3, and
`CS3219-Milestone-Backlog-Latest.pdf`, pages 6-10 and 19.
