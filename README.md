# CS3219 — Software Design and Architecture (AY2627 Sem 1)

## Friend on Campus (FoC)

**Friend on Campus (FoC)** is a peer-to-peer campus errand platform where
students can request items to be collected from stores or facilities on
campus, and other students can fulfil (and deliver) those requests. The
platform runs on a closed credit economy — credits cannot be bought,
withdrawn, or exchanged for money, and only circulate within the platform.

---

## Team Members

| Name | Role |
| ----- | ----- |
| Your Name | Your ownership |
| Your Name | Your ownership |
| Your Name | Your ownership |
| Your Name | Your ownership |
| Your Name | Your ownership |

---

## Repository Structure

This repository follows a **one-service-per-folder** structure: each
microservice (`user-service/`, `supplier-service/`, `order-service/`,
`credit-service/`) lives in its own top-level folder.

```text
.
├── user-service/
├── supplier-service/
├── web-client/
├── order-service/
├── credit-service/
├── <n2h-service>/
└── README.md
```

- Any **nice-to-have (N2H)** feature that warrants its own service should
  be added as an **additional folder** at the same level, following the
  same per-service structure.
- Files for agentic coding tools (e.g. agent configs, prompts, skills)
  may be added as needed, but must still **respect the
  one-service-per-folder skeleton** for core implementation.

---

## Local setup (macOS)

This setup runs the web client, User Service, Supplier Service, RabbitMQ, and
Mailpit with the root [Compose file](compose.yaml). Each service has its own
local Supabase database. The databases are started with the Supabase CLI, not
with the root Compose command. No hosted Supabase project is needed for local
development.

### Prerequisites

- Docker Desktop installed and running (`docker info` should connect).
- Node.js 22 or newer and npm.
- Python 3.13 for User Service's local secret generator. On macOS, install it
  with `brew install python@3.13` if needed.
- Both services install the same project-pinned Supabase CLI through `npm ci`.
  Run it with `npx supabase` from the service folder; no global CLI is needed.

The repository already contains both `supabase/config.toml` files and all SQL
migrations. Do not run `supabase init` again.

### First-time setup

Run these commands from the repository root in a macOS terminal.

1. Start User Service's local database and generate its ignored development
   secrets:

   ```sh
   cd user-service
   npm ci
   npx supabase start
   python3.13 -m venv .venv
   .venv/bin/python -m pip install -e '.[dev]'
   .venv/bin/python scripts/generate_dev_secrets.py
   cd ..
   ```

   The generator creates `user-service/.env` and local JWT keys. Run it only
   once; it refuses to overwrite existing secrets. If `.env` already exists,
   skip the generator. The first `npx supabase start` applies the committed User
   Service migrations.

2. Start Supplier Service's separate local database and create its ignored
   config file if it does not exist:

   ```sh
   (cd supplier-service && npm ci && npx supabase start)
   cp -n supplier-service/.env.example supplier-service/.env
   ```

   The first start applies Supplier Service's migration and seed data. Open
   `user-service/.env` and `supplier-service/.env` in a text editor. Replace
   Supplier Service's `SUPPLIER_SERVICE_SHARED_SECRET` placeholder with the
   exact value generated under the same name in User Service's `.env`. Keep
   both files out of Git.

3. To create the first local Super Admin, set
   `BOOTSTRAP_SUPER_ADMIN_USERNAME`, `BOOTSTRAP_SUPER_ADMIN_EMAIL`, and
   `BOOTSTRAP_SUPER_ADMIN_PASSWORD` in `user-service/.env`. The email must end
   in `@u.nus.edu`. Use a username without spaces. The password needs 12–72
   characters from at least three of uppercase letters, lowercase letters,
   digits, and symbols; only letters, digits, and `!@#$%^&*()-_=+?.` are
   allowed. Then run once:

   ```sh
   (cd user-service && .venv/bin/bootstrap-super-admin)
   ```

   Skip this step if the local User database already has a Super Admin. The
   bootstrap command refuses to create a second one.

4. If you previously started the application containers from the individual
   service folders, stop them to free ports 3000, 8000, and 8001:

   ```sh
   (cd supplier-service && docker compose down)
   (cd user-service && docker compose down)
   ```

5. Start the integrated application containers from the repository root:

   ```sh
   docker compose --env-file user-service/.env up --build -d
   ```

   `--env-file` supplies User Service's generated database URL and RabbitMQ
   credentials to Compose. Supplier Service loads its own `.env`. The root
   stack starts the web client, both APIs, RabbitMQ, Mailpit, and the User
   Service outbox publisher.

### Open and check the services

| Local address | Purpose |
| --- | --- |
| `http://localhost:3000` | Web UI and same-origin API proxy |
| `http://localhost:8000/health/ready` | User Service database readiness; expect HTTP 200 |
| `http://localhost:8001/docs` | Supplier Service API documentation |
| `http://localhost:8025` | Mailpit verification emails |
| `http://localhost:54323` | User Service local Supabase Studio |
| `http://localhost:55323` | Supplier Service local Supabase Studio |

The web proxy sends `/v1/` to User Service and Supplier paths such as
`/api/v1/admin/suppliers` to Supplier Service. The Supplier API can also be
tested directly on port 8001 with Postman. Sign in at `http://localhost:3000`,
then open `/suppliers` to browse active suppliers. Admins and Super Admins can
open `/admin/suppliers` to manage them. The current Remove action deactivates a
supplier; permanent deletion awaits the Errand Service reference contract.
Neither backend reads the other's database.

### Later starts and stops

After the first setup, start the saved local databases and application
containers with:

```sh
(cd user-service && npx supabase start)
(cd supplier-service && npx supabase start)
docker compose --env-file user-service/.env up --build -d
```

To stop the application containers and both local Supabase stacks:

```sh
docker compose --env-file user-service/.env down
(cd user-service && npx supabase stop)
(cd supplier-service && npx supabase stop)
```

Stopping preserves local database data. The service-level Compose files remain
available for working on one backend at a time. For detailed service-specific
instructions, see [User Service](user-service/README.md) and
[Supplier Service](supplier-service/README.md).

### Reset local data

Only when you want to **delete all local data** and reapply migrations and seed
files, run the reset for the service you want to rebuild:

```sh
(cd user-service && npx supabase db reset --local)
(cd supplier-service && npx supabase db reset --local)
```

A User Service reset removes the local Super Admin, so run its bootstrap
command again afterward. These `--local` commands do not reset hosted Supabase
projects.
