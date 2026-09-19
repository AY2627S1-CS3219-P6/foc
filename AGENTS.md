# FoC repository instructions

## Service boundaries

- Keep one independently deployable service in each top-level service directory. Do not add cross-service database reads, writes, foreign keys, or shared business-logic modules.
- Each service owns its Supabase PostgreSQL project/database. Communicate through versioned HTTP contracts or versioned events, never through another service's tables.
- Treat the edge proxy as ingress/routing only. It must not own business logic, credentials, or role decisions.

## Security and configuration

- Never commit `.env` files, generated keys, private certificates, database passwords, access tokens, or Supabase CLI runtime state. Update `.env.example` with safe placeholders whenever configuration changes.
- The web client communicates only with FoC services. It must not call Supabase directly or receive Supabase URLs, keys, or database credentials.
- Supabase Auth and Supabase client SDKs are not part of FoC. Application services own their authentication and authorization decisions.

## User Service database workflow

- `user-service/supabase/migrations/` is the sole User Service schema history. Create and review timestamped Supabase SQL migrations, test them with `npx supabase db reset`, and commit them with dependent application changes.
- Do not add a second schema migration system or run migrations during application startup. Runtime ORM models exist only for queries and transactions.
- The repository's Supabase GitHub integration uses `AY2627-CS3219-P6/foc` with working directory `user-service`. Keep automatic branching and production deployment disabled until the migration workflow is verified.
