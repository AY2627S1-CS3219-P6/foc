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
microservice (`user-service/`, `supplier-service/`, `order-service/`, `chat-service/`,
`credit-service/`) lives in its own top-level folder.

```text
.
├── user-service/
├── supplier-service/
├── web-client/
├── order-service/
├── chat-service/
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

This setup runs the web client, User Service, Supplier Service, Chat Service,
RabbitMQ, and Mailpit with the root [Compose file](compose.yaml). Chat is enabled
with the optional `chat` profile. Each service has its own
local Supabase database. The databases are started with the Supabase CLI, not
with the root Compose command. No hosted Supabase project is needed for local
development.

### Prerequisites

- Docker Desktop installed and running (`docker info` should connect), with
  Docker Compose 2.24 or newer.
- Node.js 22 or newer and npm.
- Python 3.13 for User Service's local secret generator. On macOS, install it
  with `brew install python@3.13` if needed.
- `uv` for Chat Service's locked Python dependencies.
- Each service installs its project-pinned Supabase CLI through `npm ci`.
  Run `npx supabase` from the service folder. No global Supabase CLI or
  Supabase cloud login is needed for these local commands.

The repository already contains each service's `supabase/config.toml` and SQL
migrations. Do not run `supabase init` again.

User Service's local Supabase stack uses ports `15420`–`15429`, with PostgreSQL
on `15422` and Studio on `15423`. Supplier Service uses its separate `5532x`
ports. Chat Service uses `1742x`, with PostgreSQL on `17422`; its Studio,
Supabase Auth and Data API are disabled. The User Service ports are below Windows' default dynamic port range,
where virtual networking can reserve ports and prevent Docker from binding them.

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

3. Start Chat Service's separate local database, install its locked dependencies,
   and create its ignored config file if it does not exist:

   ```sh
   (cd chat-service && npm ci && uv sync --locked --extra dev && npx supabase start)
   cp -n chat-service/.env.example chat-service/.env
   ```

   The first start of a fresh Chat database applies its committed migrations.
   They create the `chat_service` schema. Local development uses Supabase's
   default username `postgres`, password `postgres`, and database `postgres`.
   No extra login creation is needed. The template already contains these
   URLs; if your `.env` exists, update only its two database settings:

   ```dotenv
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:17422/postgres
   DATABASE_URL_DOCKER=postgresql+asyncpg://postgres:postgres@host.docker.internal:17422/postgres
   ```

   These defaults apply to Chat's isolated local database on port `17422`.
   Deployment uses a separate restricted login inheriting `chat_runtime`.

   Copy User Service's existing `RABBITMQ_URL` into Chat's `RABBITMQ_URL` for
   native access on port `5672`. Set Chat's Docker URL with the same broker
   username/password from `user-service/.env`, using Docker hostname `rabbitmq`:

   ```dotenv
   RABBITMQ_URL_DOCKER=amqp://REPLACE_WITH_RABBITMQ_USER:REPLACE_WITH_RABBITMQ_PASSWORD@rabbitmq:5672/
   ```

   The normal setup shares this broker. Port `17425` is reserved for the
   separate automated-test broker; no extra RabbitMQ container is needed here.
   Reuse an existing `CHAT_SERVICE_SHARED_SECRET` from User Service in Chat's
   config. If neither service has one, choose one dedicated random secret
   and add the same key/value to both `user-service/.env` and `chat-service/.env`.
   User Service's secret generator does not create this Chat-specific key.
   Do not reuse Supplier's secret or overwrite existing secret files. The root
   launcher supplies the internal User Service URL automatically.

4. To create the first local Super Admin, set
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

5. If you previously started application containers from the individual
   service folders, tear down those launchers to free ports 3000, 8000, 8001,
   and 8003. Run only the commands for launchers you previously used:

   ```sh
   (cd supplier-service && docker compose down)
   (cd user-service && docker compose down)
   (cd chat-service && docker compose --env-file .env --profile chat down)
   ```

6. Start the integrated application containers from the repository root:

   ```sh
   docker compose --env-file user-service/.env --profile chat up --build -d
   ```

   `--env-file` supplies User Service's generated database URL and RabbitMQ
   credentials to Compose. Supplier and Chat load their own `.env` files. Chat
   selects its own Docker database/broker URLs; do not supply Chat's config as
   another global `--env-file`, because User uses the same database variable
   name for its own database. The stack starts the web client, all three APIs,
   shared RabbitMQ, Mailpit, and separate User and Chat outbox publishers.


### Open and check the services

| Local address | Purpose |
| --- | --- |
| `http://localhost:3000` | Web UI and same-origin API proxy |
| `http://localhost:8000/health/ready` | User Service database readiness; expect HTTP 200 |
| `http://localhost:8001/docs` | Supplier Service API documentation |
| `http://127.0.0.1:8003/health/ready` | Optional Chat database and delivery readiness |
| `http://localhost:15672` | Shared RabbitMQ management dashboard |
| `http://localhost:8025` | Mailpit verification emails |
| `http://localhost:15423` | User Service local Supabase Studio |
| `http://localhost:55323` | Supplier Service local Supabase Studio |

The web proxy sends `/v1/chat` to Chat, Order-specific paths to Order,
remaining `/v1/` paths to User Service, and Supplier paths such as
`/api/v1/admin/suppliers` to Supplier Service. The Supplier API can also be
tested directly on port 8001 with Postman. Sign in at `http://localhost:3000`,
then open `/suppliers` to browse active suppliers. Admins and Super Admins can
open `/admin/suppliers` to manage them. The Deactivate action retains the
supplier; permanent deletion awaits the Errand Service reference contract.
Each service owns its database; services communicate through HTTP contracts.

Chat requests use `http://localhost:3000/v1/chat/...` and
`ws://localhost:3000/v1/chat/ws` through the browser proxy. Direct access on
port 8003 remains available for Postman; see the [manual Chat walkthrough](chat-service/docs/verification.md).
The root Chat profile allows exact localhost/127.0.0.1 browser origins on ports
3000 and 5173. Set the Compose variable `CHAT_ALLOWED_ORIGINS` to a JSON array
before startup for a different local allow-list. Both Nginx and Vite preserve
the browser Origin. Chat pages remain follow-up work; its backend is available.

### Later starts and stops

If your existing User Service setup used database port `54322`, run
`npx supabase stop` from `user-service/` once before starting with the updated
port configuration. In `user-service/.env`, change only the port in both
`DATABASE_URL` and `DATABASE_URL_DOCKER` to `15422`; retain their hosts and
credentials. The next start reuses the saved database volume. Keep your existing
secrets and use the normal stop command, which preserves data.

After the first setup, start the saved local databases and application
containers with:

```sh
(cd user-service && npx supabase start)
(cd supplier-service && npx supabase start)
(cd chat-service && npx supabase start)
docker compose --env-file user-service/.env --profile chat up --build -d
```

To stop application containers while leaving all local databases running:

```sh
docker compose --env-file user-service/.env --profile chat stop
``````

To tear down application containers/networks and stop all three local Supabase
stacks, preserving their saved database data:

```sh
docker compose --env-file user-service/.env --profile chat down
(cd user-service && npx supabase stop)
(cd supplier-service && npx supabase stop)
(cd chat-service && npx supabase stop)
```

`stop` retains the application containers; `down` removes them and their Compose
networks. The Supabase stop commands retain database volumes, and neither command
deletes `.env` files or JWT keys. RabbitMQ queues/dashboard statistics may reset
when its container is recreated; PostgreSQL retains Chat's history and outbox.
Use the same enabled profiles for stopping/teardown; include `--profile order`
when you also started Order. Normal stopping does not use `--no-backup` or `-v`.

The service-level Compose files remain available for working on one backend at
a time. For details, see [User Service](user-service/README.md),
[Supplier Service](supplier-service/README.md), and [Chat Service](chat-service/README.md).

### Reset local data

Only when you want to **delete a service's local database data** and reapply
its migrations and configured seeds, first stop the application containers.
Leave the local Supabase databases running:

```sh
docker compose --env-file user-service/.env --profile chat stop
```

Run only the reset command for the service you want to rebuild. Running all
three commands resets all three databases:

```sh
(cd user-service && npx supabase db reset --local)
(cd supplier-service && npx supabase db reset --local)
(cd chat-service && npx supabase db reset --local)
```

A User Service reset removes its users/sessions and local Super Admin; run
the bootstrap command from step 4 again and register/sign in with fresh users.
Existing Chat history uses immutable User IDs. Resetting only User does not
reassociate old Chat history with newly registered accounts; for a fully fresh
User/Chat test setup, deliberately reset both databases. A Supplier reset
removes local Supplier data and reapplies its configured seed.

A Chat reset removes conversations, messages, blocks, read state and outbox
events. The default local `postgres` login is supplied by Supabase, so no
extra login creation or role grant is needed after reset. Keep the database
URLs from step 3, existing `.env` files and keys; do not regenerate service
secrets as part of a database reset. Then start the application again:

```sh
docker compose --env-file user-service/.env --profile chat up --build -d
docker compose --env-file user-service/.env --profile chat ps
curl http://127.0.0.1:8003/health/ready
```

Chat readiness should return `{"status":"ready","delivery":"ready"}`. These
`--local` reset commands target only the selected service's local project;
they do not use a linked/cloud project. Root Compose startup, `stop`, and `down`
do not reset any Supabase database.
