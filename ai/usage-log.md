# AI usage log

This shared log records implementation assistance for Feng1231’s changes in `user-service/` and `chat-service/` on `main`. Times are Singapore time (UTC+08:00). Prompt excerpts preserve the relevant wording, and summaries identify the exchange when the raw prompt contains credentials or a continuation has no separate user message. Key responses are summarized. The referenced commits identify the changes supported by each exchange.

This log carries the attribution for JSON files and the empty migration directory marker.

## 2026-09-19 23:51:19 SGT — User Service development bootstrap

**Tool and mode** — ChatGPT (Codex, model: gpt-5.6-terra), generate.

**Prompt excerpts**

> Create a small generation script and `.env.example`

> Before you begin implementation, check repo root and user-service`.gitignore` files are ignoring all the files that should be ignored.

**Key response** — Created a development secret generator, an environment template, and ignore rules. Prepared local Supabase configuration and CLI package setup.

**Commits** — [`6ba0c93`](https://github.com/AY2627S1-CS3219-P6/foc/commit/6ba0c93).

**Affected files**

- [`user-service/.env.example`](../user-service/.env.example)
- [`user-service/.gitignore`](../user-service/.gitignore)
- [`user-service/package-lock.json`](../user-service/package-lock.json)
- [`user-service/package.json`](../user-service/package.json)
- [`user-service/scripts/generate_dev_secrets.py`](../user-service/scripts/generate_dev_secrets.py)
- [`user-service/supabase/.gitignore`](../user-service/supabase/.gitignore)
- [`user-service/supabase/config.toml`](../user-service/supabase/config.toml)

## 2026-09-20 00:48:59 SGT — User Service foundation (Phase 0)

**Tool and mode** — ChatGPT (Codex, model: gpt-5.6-terra), generate.

**Prompt excerpt**

> You may begin implementing the `user-service/PLAN.md`.

**Key response** — Implemented FastAPI startup and health checks, async database access, correlation IDs, redacted logs, container configuration, and a local test runner with health and readiness tests.

**Commits** — [`3968002`](https://github.com/AY2627S1-CS3219-P6/foc/commit/3968002).

**Affected files**

- [`user-service/.dockerignore`](../user-service/.dockerignore)
- [`user-service/.env.example`](../user-service/.env.example)
- [`user-service/.gitignore`](../user-service/.gitignore)
- [`user-service/Dockerfile`](../user-service/Dockerfile)
- [`user-service/app/__init__.py`](../user-service/app/__init__.py)
- [`user-service/app/core/__init__.py`](../user-service/app/core/__init__.py)
- [`user-service/app/core/config.py`](../user-service/app/core/config.py)
- [`user-service/app/core/correlation.py`](../user-service/app/core/correlation.py)
- [`user-service/app/core/logging.py`](../user-service/app/core/logging.py)
- [`user-service/app/db.py`](../user-service/app/db.py)
- [`user-service/app/main.py`](../user-service/app/main.py)
- [`user-service/compose.yaml`](../user-service/compose.yaml)
- [`user-service/pyproject.toml`](../user-service/pyproject.toml)
- [`user-service/scripts/generate_dev_secrets.py`](../user-service/scripts/generate_dev_secrets.py)
- [`user-service/scripts/run_tests_with_local_supabase.py`](../user-service/scripts/run_tests_with_local_supabase.py)
- [`user-service/supabase/migrations/.gitkeep`](../user-service/supabase/migrations/.gitkeep)
- [`user-service/tests/integration/test_database_readiness.py`](../user-service/tests/integration/test_database_readiness.py)
- [`user-service/tests/test_config.py`](../user-service/tests/test_config.py)
- [`user-service/tests/test_health.py`](../user-service/tests/test_health.py)
- [`user-service/tests/test_logging.py`](../user-service/tests/test_logging.py)

## 2026-09-20 13:24:16 SGT — Verified registration (Phase 1)

**Tool and mode** — ChatGPT (Codex, model: gpt-5.6-terra), generate.

**Prompt excerpt**

> You may then proceed with Phase 1

**Key response** — Implemented registration and OTP delivery, resend and verification, input validation, bcrypt password hashing, and verified-account persistence. Added the migration and registration tests.

**Commits** — [`251a17f`](https://github.com/AY2627S1-CS3219-P6/foc/commit/251a17f).

**Affected files**

- [`user-service/.env.example`](../user-service/.env.example)
- [`user-service/app/api/__init__.py`](../user-service/app/api/__init__.py)
- [`user-service/app/api/errors.py`](../user-service/app/api/errors.py)
- [`user-service/app/api/registration.py`](../user-service/app/api/registration.py)
- [`user-service/app/api/schemas.py`](../user-service/app/api/schemas.py)
- [`user-service/app/core/config.py`](../user-service/app/core/config.py)
- [`user-service/app/main.py`](../user-service/app/main.py)
- [`user-service/app/models.py`](../user-service/app/models.py)
- [`user-service/app/registration/__init__.py`](../user-service/app/registration/__init__.py)
- [`user-service/app/registration/mailer.py`](../user-service/app/registration/mailer.py)
- [`user-service/app/registration/service.py`](../user-service/app/registration/service.py)
- [`user-service/app/registration/validation.py`](../user-service/app/registration/validation.py)
- [`user-service/pyproject.toml`](../user-service/pyproject.toml)
- [`user-service/supabase/migrations/20260920053035_create_identity_registration_tables.sql`](../user-service/supabase/migrations/20260920053035_create_identity_registration_tables.sql)
- [`user-service/tests/integration/test_registration.py`](../user-service/tests/integration/test_registration.py)
- [`user-service/tests/test_registration_validation.py`](../user-service/tests/test_registration_validation.py)

## 2026-09-20 20:32:07 SGT — Bootstrap pull request fixes

**Tool and mode** — ChatGPT (Codex, model: gpt-5.6-terra), debug and refactor. GitHub Copilot, pull request review (model and review prompt unavailable).

**Prompt excerpt**

> Copilot have returned with some review on the PR from chore/user-service-bootstrap  to main.
>
> Can you address those and fix them on chore/user-service-bootstrap

**Key response** — Used GitHub Copilot’s PR review findings to fix redaction, PostgreSQL URL handling, liveness and readiness, correlation IDs on 500 responses, and local RabbitMQ configuration. Codex added regression coverage.

**Commits** — [`6d336ad`](https://github.com/AY2627S1-CS3219-P6/foc/commit/6d336ad).

**Affected files**

- [`user-service/.env.example`](../user-service/.env.example)
- [`user-service/app/core/logging.py`](../user-service/app/core/logging.py)
- [`user-service/app/db.py`](../user-service/app/db.py)
- [`user-service/app/main.py`](../user-service/app/main.py)
- [`user-service/compose.yaml`](../user-service/compose.yaml)
- [`user-service/scripts/generate_dev_secrets.py`](../user-service/scripts/generate_dev_secrets.py)
- [`user-service/tests/test_database.py`](../user-service/tests/test_database.py)
- [`user-service/tests/test_health.py`](../user-service/tests/test_health.py)
- [`user-service/tests/test_logging.py`](../user-service/tests/test_logging.py)

## 2026-09-20 21:26:17 SGT — Registration branch regression fixes

**Tool and mode** — ChatGPT (Codex, model: gpt-5.6-terra), debug.

**Prompt excerpt at 21:22:52**

> copilot have pushed some commits to the PR on `chore/user-service-bootstrap` . I have merged it into main. Can you do the required.

**Approval to rebase the tested Phase 1 work**

> yes

**Key response** — During the Phase 1 rebase, restored translation of `sslmode=require` to asyncpg’s SSL connection option and normalized database test formatting.

**Commits** — [`7a9a18b`](https://github.com/AY2627S1-CS3219-P6/foc/commit/7a9a18b), [`4502fa1`](https://github.com/AY2627S1-CS3219-P6/foc/commit/4502fa1).

**Affected files**

- [`user-service/app/db.py`](../user-service/app/db.py)
- [`user-service/tests/test_database.py`](../user-service/tests/test_database.py)

## 2026-09-20 22:04:18 SGT — Authentication and sessions (Phase 2)

**Tool and mode** — ChatGPT (Codex, model: gpt-5.6-terra), generate.

**Initial implementation prompt excerpt at 00:48:59**

> You may begin implementing the `user-service/PLAN.md`.

**Branch handoff prompt excerpt at 22:02:39**

> checkout to work on a new phase 2 branch.

**Key response** — Implemented login, refresh, logout, token signing and verification, JWKS, and self-profile access. Added session persistence, expiry and reuse checks, signing-key setup, and authentication tests.

**Commits** — [`9bdbd5d`](https://github.com/AY2627S1-CS3219-P6/foc/commit/9bdbd5d).

**Affected files**

- [`user-service/.env.example`](../user-service/.env.example)
- [`user-service/app/api/authentication.py`](../user-service/app/api/authentication.py)
- [`user-service/app/api/schemas.py`](../user-service/app/api/schemas.py)
- [`user-service/app/api/users.py`](../user-service/app/api/users.py)
- [`user-service/app/auth/__init__.py`](../user-service/app/auth/__init__.py)
- [`user-service/app/auth/dependencies.py`](../user-service/app/auth/dependencies.py)
- [`user-service/app/auth/jwt.py`](../user-service/app/auth/jwt.py)
- [`user-service/app/auth/service.py`](../user-service/app/auth/service.py)
- [`user-service/app/core/config.py`](../user-service/app/core/config.py)
- [`user-service/app/main.py`](../user-service/app/main.py)
- [`user-service/app/models.py`](../user-service/app/models.py)
- [`user-service/scripts/generate_dev_secrets.py`](../user-service/scripts/generate_dev_secrets.py)
- [`user-service/supabase/migrations/20260920140839_create_authentication_sessions.sql`](../user-service/supabase/migrations/20260920140839_create_authentication_sessions.sql)
- [`user-service/tests/conftest.py`](../user-service/tests/conftest.py)
- [`user-service/tests/integration/test_authentication.py`](../user-service/tests/integration/test_authentication.py)
- [`user-service/tests/test_config.py`](../user-service/tests/test_config.py)
- [`user-service/tests/test_jwt.py`](../user-service/tests/test_jwt.py)

## 2026-09-20 23:02:38 SGT — Authentication configuration smoke-test failure

**Tool and mode** — ChatGPT (Codex, model: gpt-5.6-terra), debug.

**Prompt summary (credentials omitted)**

> A local POST to `/v1/auth/sessions` returned `AUTH_NOT_CONFIGURED` during the Phase 2 smoke test.

**Key response** — Identified that the host RSA keys were missing inside the container and gave the read-only key mount used in the Phase 2 Compose change.

**Commits** — [`9bdbd5d`](https://github.com/AY2627S1-CS3219-P6/foc/commit/9bdbd5d).

**Affected files**

- [`user-service/compose.yaml`](../user-service/compose.yaml)

## 2026-09-20 23:47:41 SGT — Profile management (Phase 3)

**Tool and mode** — ChatGPT (Codex, model: gpt-5.6-terra), generate.

**Earlier prompt excerpt at 23:44:31**

> checkout to a new branch to work on phase 3.

**Implementation scope (continuation, no separate user prompt)**

> Implemented the profile update and account deletion work from the existing Phase 3 plan.

**Key response** — Implemented self-profile updates and password-confirmed deletion with protected-field validation. Added tests for profile changes and deletion.

**Commits** — [`999abea`](https://github.com/AY2627S1-CS3219-P6/foc/commit/999abea).

**Affected files**

- [`user-service/app/api/schemas.py`](../user-service/app/api/schemas.py)
- [`user-service/app/api/users.py`](../user-service/app/api/users.py)
- [`user-service/app/profile/__init__.py`](../user-service/app/profile/__init__.py)
- [`user-service/app/profile/service.py`](../user-service/app/profile/service.py)
- [`user-service/tests/integration/test_profile_management.py`](../user-service/tests/integration/test_profile_management.py)
- [`user-service/tests/test_profile_validation.py`](../user-service/tests/test_profile_validation.py)

## 2026-09-21 00:36:02 SGT — Account deletion implementation follow-up

**Tool and mode** — ChatGPT (Codex, model: gpt-5.6-terra), refactor.

**Implementation scope (continuation, no separate user prompt)**

> Apply the updated account deletion behavior in `user-service/PLAN.md` to the Phase 3 implementation and tests.

**Key response** — Updated the deletion code and SQL migration to anonymize the account, keep its user ID, and remove credentials and sessions. Updated integration checks.

**Commits** — [`999abea`](https://github.com/AY2627S1-CS3219-P6/foc/commit/999abea).

**Affected files**

- [`user-service/app/api/users.py`](../user-service/app/api/users.py)
- [`user-service/app/models.py`](../user-service/app/models.py)
- [`user-service/app/profile/service.py`](../user-service/app/profile/service.py)
- [`user-service/supabase/migrations/20260920163748_add_account_tombstones.sql`](../user-service/supabase/migrations/20260920163748_add_account_tombstones.sql)
- [`user-service/tests/integration/test_profile_management.py`](../user-service/tests/integration/test_profile_management.py)

## 2026-09-21 01:02:39 SGT — Role checks and Supplier authorization (Phase 4)

**Tool and mode** — ChatGPT (Codex, model: gpt-5.6-terra), generate.

**Prompt excerpt**

> You may begin implementing phase 4 `user-service/PLAN.md`.

**Key response** — Implemented server-side role guards and the Supplier authorization checks, wired their configuration, and added role and integration tests.

**Commits** — [`3f46e96`](https://github.com/AY2627S1-CS3219-P6/foc/commit/3f46e96).

**Affected files**

- [`user-service/.env.example`](../user-service/.env.example)
- [`user-service/app/api/authorization.py`](../user-service/app/api/authorization.py)
- [`user-service/app/api/schemas.py`](../user-service/app/api/schemas.py)
- [`user-service/app/api/users.py`](../user-service/app/api/users.py)
- [`user-service/app/auth/dependencies.py`](../user-service/app/auth/dependencies.py)
- [`user-service/app/core/config.py`](../user-service/app/core/config.py)
- [`user-service/app/main.py`](../user-service/app/main.py)
- [`user-service/compose.yaml`](../user-service/compose.yaml)
- [`user-service/scripts/generate_dev_secrets.py`](../user-service/scripts/generate_dev_secrets.py)
- [`user-service/tests/integration/test_supplier_authorization.py`](../user-service/tests/integration/test_supplier_authorization.py)
- [`user-service/tests/test_role_guards.py`](../user-service/tests/test_role_guards.py)

## 2026-09-21 14:36:14 SGT — Administrator lifecycle (Phase 5)

**Tool and mode** — ChatGPT (Codex, model: gpt-5.6-terra), generate.

**Prompt excerpt**

> You may begin implementing phase 5 `user-service/PLAN.md`.

**Key response** — Implemented Super Admin bootstrap, role changes and audit records, session invalidation, the last-Super-Admin guard, and regression coverage.

**Commits** — [`36fb6b9`](https://github.com/AY2627S1-CS3219-P6/foc/commit/36fb6b9).

**Affected files**

- [`user-service/.env.example`](../user-service/.env.example)
- [`user-service/app/admin/__init__.py`](../user-service/app/admin/__init__.py)
- [`user-service/app/admin/bootstrap.py`](../user-service/app/admin/bootstrap.py)
- [`user-service/app/admin/lifecycle.py`](../user-service/app/admin/lifecycle.py)
- [`user-service/app/api/admin.py`](../user-service/app/api/admin.py)
- [`user-service/app/api/schemas.py`](../user-service/app/api/schemas.py)
- [`user-service/app/auth/dependencies.py`](../user-service/app/auth/dependencies.py)
- [`user-service/app/core/config.py`](../user-service/app/core/config.py)
- [`user-service/app/main.py`](../user-service/app/main.py)
- [`user-service/app/models.py`](../user-service/app/models.py)
- [`user-service/app/profile/service.py`](../user-service/app/profile/service.py)
- [`user-service/pyproject.toml`](../user-service/pyproject.toml)
- [`user-service/scripts/generate_dev_secrets.py`](../user-service/scripts/generate_dev_secrets.py)
- [`user-service/supabase/migrations/20260921063952_add_admin_audit_and_lifecycle_guards.sql`](../user-service/supabase/migrations/20260921063952_add_admin_audit_and_lifecycle_guards.sql)
- [`user-service/tests/integration/test_admin_lifecycle.py`](../user-service/tests/integration/test_admin_lifecycle.py)
- [`user-service/tests/test_bootstrap_configuration.py`](../user-service/tests/test_bootstrap_configuration.py)

## 2026-09-21 16:01:08 SGT — Registration event publishing (Phase 6)

**Tool and mode** — ChatGPT (Codex, model: gpt-5.6-terra), generate.

**Prompt excerpt**

> You may begin implementing phase 6 `user-service/PLAN.md`.

**Key response** — Implemented registration outbox writes, publisher leases and retries, broker confirmation, timing instrumentation, demo scripts, and tests. The 16:57:24 follow-up corrected a demo display name rejected by validation.

**Commits** — [`8635a47`](https://github.com/AY2627S1-CS3219-P6/foc/commit/8635a47).

**Affected files**

- [`user-service/.env.example`](../user-service/.env.example)
- [`user-service/app/core/config.py`](../user-service/app/core/config.py)
- [`user-service/app/core/logging.py`](../user-service/app/core/logging.py)
- [`user-service/app/core/timing.py`](../user-service/app/core/timing.py)
- [`user-service/app/main.py`](../user-service/app/main.py)
- [`user-service/app/models.py`](../user-service/app/models.py)
- [`user-service/app/outbox/__init__.py`](../user-service/app/outbox/__init__.py)
- [`user-service/app/outbox/events.py`](../user-service/app/outbox/events.py)
- [`user-service/app/outbox/publisher.py`](../user-service/app/outbox/publisher.py)
- [`user-service/app/outbox/worker.py`](../user-service/app/outbox/worker.py)
- [`user-service/app/registration/service.py`](../user-service/app/registration/service.py)
- [`user-service/compose.yaml`](../user-service/compose.yaml)
- [`user-service/docs/d2-demo-users.example.json`](../user-service/docs/d2-demo-users.example.json)
- [`user-service/pyproject.toml`](../user-service/pyproject.toml)
- [`user-service/scripts/generate_dev_secrets.py`](../user-service/scripts/generate_dev_secrets.py)
- [`user-service/scripts/measure_d2_timings.py`](../user-service/scripts/measure_d2_timings.py)
- [`user-service/scripts/run_d2_demo.py`](../user-service/scripts/run_d2_demo.py)
- [`user-service/supabase/migrations/20260921081111_add_registration_outbox_events.sql`](../user-service/supabase/migrations/20260921081111_add_registration_outbox_events.sql)
- [`user-service/tests/integration/test_outbox.py`](../user-service/tests/integration/test_outbox.py)
- [`user-service/tests/integration/test_registration.py`](../user-service/tests/integration/test_registration.py)
- [`user-service/tests/test_outbox_events.py`](../user-service/tests/test_outbox_events.py)

## 2026-09-21 18:37:22 SGT — User Service local Compose launcher

**Tool and mode** — ChatGPT (Codex, model: gpt-5.6-terra), generate.

**Prompt excerpt**

> Add `web-client` to `user-service/compose.yaml` with build context `../web-client`, host port `3000:80`, and `depends_on.user-service.condition: service_healthy`.

**Key response** — Added the client to the local User Service Compose launcher.

**Commits** — [`b05707b`](https://github.com/AY2627S1-CS3219-P6/foc/commit/b05707b).

**Affected files**

- [`user-service/compose.yaml`](../user-service/compose.yaml)

## 2026-09-21 21:37:06 SGT — Password validation adjustment

**Tool and mode** — ChatGPT (Codex, model: gpt-5.6-terra), refactor.

**Prompt excerpt**

> Add to the special \_PASSWORD\_SPECIALS to allow fullstop `.`

**Key response** — Updated the service’s password validator and the existing validation test to cover a period as a special character.

**Commits** — [`d548121`](https://github.com/AY2627S1-CS3219-P6/foc/commit/d548121).

**Affected files**

- [`user-service/app/registration/validation.py`](../user-service/app/registration/validation.py)
- [`user-service/tests/test_registration_validation.py`](../user-service/tests/test_registration_validation.py)

## 2026-09-22 00:13:42 SGT — Remove participation preference

**Tool and mode** — ChatGPT (Codex, model: gpt-5.6-terra), refactor.

**Prompt**

> There is no UX use, you can safely remove the field, API property, toggle endpoint support and anything related to the role toggling

**Key response** — Removed participation-preference handling from profile and registration code, added the migration, and updated the demo and regression tests.

**Commits** — [`3a4ef2f`](https://github.com/AY2627S1-CS3219-P6/foc/commit/3a4ef2f).

**Affected files**

- [`user-service/app/api/schemas.py`](../user-service/app/api/schemas.py)
- [`user-service/app/api/users.py`](../user-service/app/api/users.py)
- [`user-service/app/models.py`](../user-service/app/models.py)
- [`user-service/app/profile/service.py`](../user-service/app/profile/service.py)
- [`user-service/app/registration/service.py`](../user-service/app/registration/service.py)
- [`user-service/scripts/run_d2_demo.py`](../user-service/scripts/run_d2_demo.py)
- [`user-service/supabase/migrations/20260921161440_remove_participation_mode.sql`](../user-service/supabase/migrations/20260921161440_remove_participation_mode.sql)
- [`user-service/tests/integration/test_admin_lifecycle.py`](../user-service/tests/integration/test_admin_lifecycle.py)
- [`user-service/tests/integration/test_authentication.py`](../user-service/tests/integration/test_authentication.py)
- [`user-service/tests/integration/test_profile_management.py`](../user-service/tests/integration/test_profile_management.py)
- [`user-service/tests/integration/test_supplier_authorization.py`](../user-service/tests/integration/test_supplier_authorization.py)
- [`user-service/tests/test_profile_validation.py`](../user-service/tests/test_profile_validation.py)

## 2026-09-24 16:20:37 SGT — Password updates and administrator lookup (Phase 7)

**Tool and mode** — ChatGPT (Codex, model: gpt-5.6-terra), generate.

**Earlier prompt excerpts at 15:40:51**

> 1. Allowing users to update their password
> 2. Allowing super admins and admins to view user accounts by searching their username / email (which are both unique identifiers)

**Key response** — Implemented current-password verification and password replacement, session revocation, and account lookup by username or email. Added validation and integration coverage.

**Commits** — [`79fc1e5`](https://github.com/AY2627S1-CS3219-P6/foc/commit/79fc1e5).

**Affected files**

- [`user-service/app/admin/accounts.py`](../user-service/app/admin/accounts.py)
- [`user-service/app/api/admin.py`](../user-service/app/api/admin.py)
- [`user-service/app/api/schemas.py`](../user-service/app/api/schemas.py)
- [`user-service/app/api/users.py`](../user-service/app/api/users.py)
- [`user-service/app/auth/dependencies.py`](../user-service/app/auth/dependencies.py)
- [`user-service/app/profile/service.py`](../user-service/app/profile/service.py)
- [`user-service/tests/integration/test_phase7_account_management.py`](../user-service/tests/integration/test_phase7_account_management.py)
- [`user-service/tests/test_profile_validation.py`](../user-service/tests/test_profile_validation.py)

## 2026-09-30 01:02:25 SGT — Registration event on Super Admin bootstrap

**Tool and mode** — ChatGPT (Codex, model: gpt-5.6-terra), generate and refactor.

**Prompt**

> can you update the bootstrap script

**Key response** — Updated bootstrap to persist the standard registration event in the same transaction as account creation. Updated the demo and initial bootstrap test.

**Commits** — [`f57195b`](https://github.com/AY2627S1-CS3219-P6/foc/commit/f57195b).

**Affected files**

- [`user-service/app/admin/lifecycle.py`](../user-service/app/admin/lifecycle.py)
- [`user-service/scripts/run_d2_demo.py`](../user-service/scripts/run_d2_demo.py)
- [`user-service/tests/integration/test_admin_lifecycle.py`](../user-service/tests/integration/test_admin_lifecycle.py)

## 2026-10-07 00:15:07 SGT — Super Admin-only account management and current admin list

**Tool and mode** — ChatGPT (Codex, model: gpt-6.1-sol), generate and refactor.

**Prompt excerpt**

> Restrict account management to Super Admins, rename it “Manage admins”, and add a vertically stacked list of current Super Admins and Admins with role controls.

**Key response** — Implemented the service-side Super Admin guard and active admin list, including sorting and exclusion of deleted accounts. Extended account-management tests.

**Commits** — [`622318f`](https://github.com/AY2627S1-CS3219-P6/foc/commit/622318f).

**Affected files**

- [`user-service/app/admin/accounts.py`](../user-service/app/admin/accounts.py)
- [`user-service/app/api/admin.py`](../user-service/app/api/admin.py)
- [`user-service/app/api/schemas.py`](../user-service/app/api/schemas.py)
- [`user-service/tests/integration/test_phase7_account_management.py`](../user-service/tests/integration/test_phase7_account_management.py)

## 2026-10-07 01:22:22 SGT — Remove the suspended account status

**Tool and mode** — ChatGPT (Codex, model: gpt-6.1-sol), refactor.

**Earlier prompt excerpt at 01:08:40**

> remove "SUSPENDED" altogether from the entire application

**Key response** — Removed `SUSPENDED` from the User Service status enum, implemented the approved migration, and updated migration, account, and profile tests.

**Commits** — [`58aafe1`](https://github.com/AY2627S1-CS3219-P6/foc/commit/58aafe1).

**Affected files**

- [`user-service/app/models.py`](../user-service/app/models.py)
- [`user-service/supabase/migrations/20261006172458_remove_suspended_account_status.sql`](../user-service/supabase/migrations/20261006172458_remove_suspended_account_status.sql)
- [`user-service/tests/integration/test_account_status_migration.py`](../user-service/tests/integration/test_account_status_migration.py)
- [`user-service/tests/integration/test_profile_management.py`](../user-service/tests/integration/test_profile_management.py)
- [`user-service/tests/test_account_status.py`](../user-service/tests/test_account_status.py)
- [`user-service/tests/test_profile_validation.py`](../user-service/tests/test_profile_validation.py)

## 2026-10-07 16:07:17 SGT — Bootstrap outbox and demo verification follow-up

**Tool and mode** — ChatGPT (Codex, model: gpt-6.1-sol), debug and generate.

**Prompt**

> commit and push also the update to publish an outbox event during the boostrap super admin

**Key response** — Added tests for the queued bootstrap event and for capturing the expected registration event in the D2 demo. Verified the bootstrap change and the demo against those tests.

**Commits** — [`f57195b`](https://github.com/AY2627S1-CS3219-P6/foc/commit/f57195b).

**Affected files**

- [`user-service/tests/integration/test_admin_lifecycle.py`](../user-service/tests/integration/test_admin_lifecycle.py)
- [`user-service/tests/integration/test_outbox.py`](../user-service/tests/integration/test_outbox.py)
- [`user-service/tests/test_d2_event_capture.py`](../user-service/tests/test_d2_event_capture.py)

## 2026-10-08 21:25:33 SGT — D2 test collection in CI

**Tool and mode** — ChatGPT (Codex, model: gpt-6.1-sol), debug.

**Prompt**

> this PR failed automated checks. check why

**Key response** — Added the service directory to pytest’s import path so the existing D2 event-capture tests can import `scripts` under the CI invocation.

**Commits** — [`47a4caa`](https://github.com/AY2627S1-CS3219-P6/foc/commit/47a4caa).

**Affected files**

- [`user-service/pyproject.toml`](../user-service/pyproject.toml)

## 2026-10-08 22:08:27 SGT — Local Supabase port conflict

**Tool and mode** — ChatGPT (Codex, model: gpt-6.1-sol), debug and refactor.

**Prompt (approval to apply the discussed local port fix)**

> ok do it

**Key response** — Updated local Supabase port settings and the example database URL to resolve a Windows port reservation.

**Commits** — [`b0c60a5`](https://github.com/AY2627S1-CS3219-P6/foc/commit/b0c60a5).

**Affected files**

- [`user-service/.env.example`](../user-service/.env.example)
- [`user-service/supabase/config.toml`](../user-service/supabase/config.toml)

## 2026-10-10 23:26:36 SGT — User Service code for Chat integration

**Tool and mode** — ChatGPT (Codex, model: gpt-6.1-sol), generate and test.

**Dispatch prompt excerpt at 23:23:10**

> For user-service worker, commit the changes only in user-service

**Implementation scope**

> Implement the User Service code and tests described in the existing Chat integration plan.

**Key response** — Implemented the existing Chat integration contract in User Service, including service authentication, paginated username search, and batch identity lookup for current and deleted accounts. Added automated tests, an isolated test runner, and a contract demo.

**Commits** — [`e83e995`](https://github.com/AY2627S1-CS3219-P6/foc/commit/e83e995), [`0c84614`](https://github.com/AY2627S1-CS3219-P6/foc/commit/0c84614), [`75f51ff`](https://github.com/AY2627S1-CS3219-P6/foc/commit/75f51ff), [`38dd3cb`](https://github.com/AY2627S1-CS3219-P6/foc/commit/38dd3cb) (2026-10-11 SGT).

**Affected files**

- [`user-service/.dockerignore`](../user-service/.dockerignore)
- [`user-service/.env.example`](../user-service/.env.example)
- [`user-service/app/api/chat.py`](../user-service/app/api/chat.py)
- [`user-service/app/api/chat_schemas.py`](../user-service/app/api/chat_schemas.py)
- [`user-service/app/chat/__init__.py`](../user-service/app/chat/__init__.py)
- [`user-service/app/chat/service.py`](../user-service/app/chat/service.py)
- [`user-service/app/core/config.py`](../user-service/app/core/config.py)
- [`user-service/app/core/timing.py`](../user-service/app/core/timing.py)
- [`user-service/app/main.py`](../user-service/app/main.py)
- [`user-service/scripts/run_chat_contract_demo.py`](../user-service/scripts/run_chat_contract_demo.py)
- [`user-service/scripts/run_chat_tests.py`](../user-service/scripts/run_chat_tests.py)
- [`user-service/tests/integration/conftest.py`](../user-service/tests/integration/conftest.py)
- [`user-service/tests/integration/test_chat_participants.py`](../user-service/tests/integration/test_chat_participants.py)
- [`user-service/tests/integration/test_chat_privacy.py`](../user-service/tests/integration/test_chat_privacy.py)
- [`user-service/tests/integration/test_chat_search.py`](../user-service/tests/integration/test_chat_search.py)
- [`user-service/tests/test_chat_contracts.py`](../user-service/tests/test_chat_contracts.py)
- [`user-service/tests/test_chat_participant_errors.py`](../user-service/tests/test_chat_participant_errors.py)
- [`user-service/tests/test_chat_search_contract.py`](../user-service/tests/test_chat_search_contract.py)
- [`user-service/tests/test_chat_test_resources.py`](../user-service/tests/test_chat_test_resources.py)

## 2026-10-10 23:27:29 SGT — Chat Service backend implementation

**Tool and mode** — ChatGPT (Codex, model: gpt-6.1-sol), generate and test.

**Dispatch prompt excerpt at 23:23:10**

> For chat-service worker, commit the changes only in chat-service, and work on the chat service

**Key response** — Implemented the existing Chat backend plan, covering startup, migrations, identity checks, conversations, message persistence, blocking, WebSockets, RabbitMQ delivery, and unread state. Added recovery and authorization tests and local smoke scripts.

**Commits** — [`28cc0dd`](https://github.com/AY2627S1-CS3219-P6/foc/commit/28cc0dd), [`8b17f92`](https://github.com/AY2627S1-CS3219-P6/foc/commit/8b17f92), [`1d7555f`](https://github.com/AY2627S1-CS3219-P6/foc/commit/1d7555f), [`a7a19a3`](https://github.com/AY2627S1-CS3219-P6/foc/commit/a7a19a3), [`858a35a`](https://github.com/AY2627S1-CS3219-P6/foc/commit/858a35a), [`a6c53d0`](https://github.com/AY2627S1-CS3219-P6/foc/commit/a6c53d0) (2026-10-11 SGT).

**Affected files**

- [`chat-service/.dockerignore`](../chat-service/.dockerignore)
- [`chat-service/.env.example`](../chat-service/.env.example)
- [`chat-service/Dockerfile`](../chat-service/Dockerfile)
- [`chat-service/app/__init__.py`](../chat-service/app/__init__.py)
- [`chat-service/app/config.py`](../chat-service/app/config.py)
- [`chat-service/app/correlation.py`](../chat-service/app/correlation.py)
- [`chat-service/app/db.py`](../chat-service/app/db.py)
- [`chat-service/app/errors.py`](../chat-service/app/errors.py)
- [`chat-service/app/events.py`](../chat-service/app/events.py)
- [`chat-service/app/identity.py`](../chat-service/app/identity.py)
- [`chat-service/app/live.py`](../chat-service/app/live.py)
- [`chat-service/app/main.py`](../chat-service/app/main.py)
- [`chat-service/app/outbox.py`](../chat-service/app/outbox.py)
- [`chat-service/app/routes.py`](../chat-service/app/routes.py)
- [`chat-service/app/schemas.py`](../chat-service/app/schemas.py)
- [`chat-service/app/service.py`](../chat-service/app/service.py)
- [`chat-service/compose.yaml`](../chat-service/compose.yaml)
- [`chat-service/pyproject.toml`](../chat-service/pyproject.toml)
- [`chat-service/scripts/container_smoke.py`](../chat-service/scripts/container_smoke.py)
- [`chat-service/scripts/provision_test_role.py`](../chat-service/scripts/provision_test_role.py)
- [`chat-service/scripts/verify_user_service.py`](../chat-service/scripts/verify_user_service.py)
- [`chat-service/supabase/config.toml`](../chat-service/supabase/config.toml)
- [`chat-service/supabase/migrations/20261010000000_chat_foundation.sql`](../chat-service/supabase/migrations/20261010000000_chat_foundation.sql)
- [`chat-service/supabase/migrations/20261010010000_restrict_runtime_updates.sql`](../chat-service/supabase/migrations/20261010010000_restrict_runtime_updates.sql)
- [`chat-service/tests/__init__.py`](../chat-service/tests/__init__.py)
- [`chat-service/tests/conftest.py`](../chat-service/tests/conftest.py)
- [`chat-service/tests/runtime.py`](../chat-service/tests/runtime.py)
- [`chat-service/tests/test_conversations.py`](../chat-service/tests/test_conversations.py)
- [`chat-service/tests/test_database.py`](../chat-service/tests/test_database.py)
- [`chat-service/tests/test_delivery.py`](../chat-service/tests/test_delivery.py)
- [`chat-service/tests/test_foundation.py`](../chat-service/tests/test_foundation.py)
- [`chat-service/tests/test_identity.py`](../chat-service/tests/test_identity.py)
- [`chat-service/tests/test_messages.py`](../chat-service/tests/test_messages.py)
- [`chat-service/tests/test_outbox_recovery.py`](../chat-service/tests/test_outbox_recovery.py)
- [`chat-service/tests/test_unread.py`](../chat-service/tests/test_unread.py)
- [`chat-service/tests/test_websocket_security.py`](../chat-service/tests/test_websocket_security.py)
- [`chat-service/uv.lock`](../chat-service/uv.lock)

## 2026-10-13 19:51:10 SGT — Chat username search error mapping

**Tool and mode** — ChatGPT (Codex, model: gpt-6.1-sol), debug.

**Prompt excerpt**

> {{CHAT_BASE_URL}}/v1/chat/conversations with TOKEN_A works but {{CHAT_BASE_URL}}/v1/chat/users?username={{USERNAME_A}}&limit=1 with TOKEN_A
> Throws error:

**Key response** — Traced the reported `INVALID_SESSION` to a service credential mismatch. Fixed upstream error mapping so the existing user-session failures stay distinct from unavailable service dependencies, and updated tests.

**Commits** — [`83a6d6f`](https://github.com/AY2627S1-CS3219-P6/foc/commit/83a6d6f).

**Affected files**

- [`chat-service/app/identity.py`](../chat-service/app/identity.py)
- [`chat-service/tests/conftest.py`](../chat-service/tests/conftest.py)
- [`chat-service/tests/test_identity.py`](../chat-service/tests/test_identity.py)

## 2026-10-13 22:58:54 SGT — Chat local startup configuration

**Tool and mode** — ChatGPT (Codex, model: gpt-6.1-sol), refactor.

**Prompt**

> unify the compose startup and browser routing

**Follow-up at 23:39:43**

> can you just use the default user postgres and passowrd

**Key response** — Aligned the Chat environment template and local Compose launcher with the integrated startup configuration and updated the local database defaults.

**Commits** — [`73d1253`](https://github.com/AY2627S1-CS3219-P6/foc/commit/73d1253).

**Affected files**

- [`chat-service/.env.example`](../chat-service/.env.example)
- [`chat-service/compose.yaml`](../chat-service/compose.yaml)

## 2026-10-13 23:48:58 SGT — Chat Supabase CLI setup

**Tool and mode** — ChatGPT (Codex, model: gpt-6.1-sol), generate.

**Prompt**

> can i just start supabase with npx supabase start instead of using that specific version? If yes, change all instructions in README.md and those in `chat-service` to use npx supabase start to ensure consistency in instructions.

**Key response** — Pinned the project-local CLI in the npm manifest and lockfile so `npx supabase` uses the installed version.

**Commits** — [`c32180c`](https://github.com/AY2627S1-CS3219-P6/foc/commit/c32180c).

**Affected files**

- [`chat-service/package-lock.json`](../chat-service/package-lock.json)
- [`chat-service/package.json`](../chat-service/package.json)

## 2026-10-21 17:01:10 SGT — Chat port collision during merge

**Tool and mode** — ChatGPT (Codex, model: gpt-6.1-sol), debug.

**Prompt**

> there are some changes to main. merge them in.

**Key response** — Resolved a local port collision with Credit Service by updating the Chat Compose mapping and the container smoke script to use host port 8004.

**Commits** — [`7ebcaca`](https://github.com/AY2627S1-CS3219-P6/foc/commit/7ebcaca).

**Affected files**

- [`chat-service/compose.yaml`](../chat-service/compose.yaml)
- [`chat-service/scripts/container_smoke.py`](../chat-service/scripts/container_smoke.py)

---

The entries below record implementation assistance for fjxfong’s (Fong Jing Xiang) changes in `credit-service/` and `admin-service/`, and the related wallet and Admin Dashboard changes in `web-client/`, `order-service/`, Compose, the edge proxy and CI, on `main`. Times are Singapore time (UTC+08:00). Prompt excerpts preserve the relevant wording, and a summary identifies the exchange when a prompt refers to earlier options. Key responses are summarized. The referenced commits identify the changes supported by each exchange.

These entries carry the attribution for the JSON files they list.

## 2026-10-13 20:19:17 SGT — Credit Service implementation

**Tool and mode** — Claude Code (model: Claude Opus 5.5), generate.

**Prompt excerpts**

> ok proceed with implementing credit service

> make sure everything is good, have their test following how other service is doing,

**Key response** — Generated the Credit Service foundation and CI job, the ledger migration and atomic reserve, release and transfer operations, the Order-facing reservation endpoints, the RabbitMQ consumer for registration and terminal order events, the wallet, history and admin lookup API, the Compose, edge proxy and Order wiring, a wallet page, and unit and integration tests.

**Commits** — [`0701eec`](https://github.com/AY2627S1-CS3219-P6/foc/commit/0701eec), [`8b63bfb`](https://github.com/AY2627S1-CS3219-P6/foc/commit/8b63bfb), [`c8d0ea8`](https://github.com/AY2627S1-CS3219-P6/foc/commit/c8d0ea8), [`68d20a4`](https://github.com/AY2627S1-CS3219-P6/foc/commit/68d20a4), [`8b74cb1`](https://github.com/AY2627S1-CS3219-P6/foc/commit/8b74cb1), [`ca86691`](https://github.com/AY2627S1-CS3219-P6/foc/commit/ca86691), [`057d941`](https://github.com/AY2627S1-CS3219-P6/foc/commit/057d941), [`a65add7`](https://github.com/AY2627S1-CS3219-P6/foc/commit/a65add7).

**Affected files**

- [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)
- [`compose.yaml`](../compose.yaml)
- [`credit-service/.dockerignore`](../credit-service/.dockerignore)
- [`credit-service/.env.docker.example`](../credit-service/.env.docker.example)
- [`credit-service/.env.example`](../credit-service/.env.example)
- [`credit-service/.gitignore`](../credit-service/.gitignore)
- [`credit-service/Dockerfile`](../credit-service/Dockerfile)
- [`credit-service/app/__init__.py`](../credit-service/app/__init__.py)
- [`credit-service/app/core/__init__.py`](../credit-service/app/core/__init__.py)
- [`credit-service/app/core/config.py`](../credit-service/app/core/config.py)
- [`credit-service/app/credits/__init__.py`](../credit-service/app/credits/__init__.py)
- [`credit-service/app/credits/api.py`](../credit-service/app/credits/api.py)
- [`credit-service/app/credits/consumer.py`](../credit-service/app/credits/consumer.py)
- [`credit-service/app/credits/errors.py`](../credit-service/app/credits/errors.py)
- [`credit-service/app/credits/identity.py`](../credit-service/app/credits/identity.py)
- [`credit-service/app/credits/internal_api.py`](../credit-service/app/credits/internal_api.py)
- [`credit-service/app/credits/ledger.py`](../credit-service/app/credits/ledger.py)
- [`credit-service/app/credits/schemas.py`](../credit-service/app/credits/schemas.py)
- [`credit-service/app/credits/tables.py`](../credit-service/app/credits/tables.py)
- [`credit-service/app/db.py`](../credit-service/app/db.py)
- [`credit-service/app/main.py`](../credit-service/app/main.py)
- [`credit-service/package-lock.json`](../credit-service/package-lock.json)
- [`credit-service/package.json`](../credit-service/package.json)
- [`credit-service/pyproject.toml`](../credit-service/pyproject.toml)
- [`credit-service/supabase/config.toml`](../credit-service/supabase/config.toml)
- [`credit-service/supabase/migrations/20261013000000_credit_foundation.sql`](../credit-service/supabase/migrations/20261013000000_credit_foundation.sql)
- [`credit-service/supabase/migrations/20261013000100_credit_ledger.sql`](../credit-service/supabase/migrations/20261013000100_credit_ledger.sql)
- [`credit-service/tests/__init__.py`](../credit-service/tests/__init__.py)
- [`credit-service/tests/credit_fakes.py`](../credit-service/tests/credit_fakes.py)
- [`credit-service/tests/integration/__init__.py`](../credit-service/tests/integration/__init__.py)
- [`credit-service/tests/integration/test_consumer_broker.py`](../credit-service/tests/integration/test_consumer_broker.py)
- [`credit-service/tests/integration/test_foundation.py`](../credit-service/tests/integration/test_foundation.py)
- [`credit-service/tests/integration/test_ledger.py`](../credit-service/tests/integration/test_ledger.py)
- [`credit-service/tests/test_config.py`](../credit-service/tests/test_config.py)
- [`credit-service/tests/test_consumer.py`](../credit-service/tests/test_consumer.py)
- [`credit-service/tests/test_health.py`](../credit-service/tests/test_health.py)
- [`credit-service/tests/test_identity.py`](../credit-service/tests/test_identity.py)
- [`credit-service/tests/test_internal_api.py`](../credit-service/tests/test_internal_api.py)
- [`credit-service/tests/test_user_api.py`](../credit-service/tests/test_user_api.py)
- [`order-service/.env.docker.example`](../order-service/.env.docker.example)
- [`web-client/nginx/default.conf`](../web-client/nginx/default.conf)
- [`web-client/src/api/credit-service.ts`](../web-client/src/api/credit-service.ts)
- [`web-client/src/app/routes.tsx`](../web-client/src/app/routes.tsx)
- [`web-client/src/components/app-navigation.tsx`](../web-client/src/components/app-navigation.tsx)
- [`web-client/src/pages/wallet-page.tsx`](../web-client/src/pages/wallet-page.tsx)
- [`web-client/tests/component/wallet-page.test.tsx`](../web-client/tests/component/wallet-page.test.tsx)
- [`web-client/tests/e2e/workspace-modes.spec.ts`](../web-client/tests/e2e/workspace-modes.spec.ts)
- [`web-client/tests/unit/credit-service.test.ts`](../web-client/tests/unit/credit-service.test.ts)
- [`web-client/tests/unit/order-proxy.test.ts`](../web-client/tests/unit/order-proxy.test.ts)
- [`web-client/vite.config.ts`](../web-client/vite.config.ts)

## 2026-10-13 22:46:55 SGT — Credit wallet page styling

**Tool and mode** — Claude Code (model: Claude Opus 5.5), generate.

**Prompt excerpts**

> this is my figma diagram for my app https://www.figma.com/design/1QaorStohl4p1T8PoC9YG5/CS3219---Project-6

> my credit service should follow how this looks

**Key response** — Restyled the Credits wallet page, its navigation icon and its component and browser tests to match the Figma design.

**Commits** — [`d1c8169`](https://github.com/AY2627S1-CS3219-P6/foc/commit/d1c8169).

**Affected files**

- [`web-client/src/components/app-navigation.tsx`](../web-client/src/components/app-navigation.tsx)
- [`web-client/src/components/navigation-icons.tsx`](../web-client/src/components/navigation-icons.tsx)
- [`web-client/src/main.tsx`](../web-client/src/main.tsx)
- [`web-client/src/pages/wallet-page.tsx`](../web-client/src/pages/wallet-page.tsx)
- [`web-client/src/styles/wallet.css`](../web-client/src/styles/wallet.css)
- [`web-client/tests/component/wallet-page.test.tsx`](../web-client/tests/component/wallet-page.test.tsx)
- [`web-client/tests/e2e/wallet.spec.ts`](../web-client/tests/e2e/wallet.spec.ts)
- [`web-client/tests/e2e/workspace-modes.spec.ts`](../web-client/tests/e2e/workspace-modes.spec.ts)

## 2026-10-15 22:49:54 SGT — Credit dead-letter replay and database retries

**Tool and mode** — Claude Code (model: Claude Opus 5.5), generate and debug.

**Prompt**

> do B + C but only revert/ work on those portions. should only solve this gap and not the whole reverted prototype

**Prompt summary** — B and C referred to a dead-letter replay command and continued event retries while the database is unreachable.

**Key response** — Added the `credit-replay-dlq` command to replay dead-lettered events and kept the consumer retrying while the database is unreachable, with unit and broker integration tests.

**Commits** — [`4b4cde2`](https://github.com/AY2627S1-CS3219-P6/foc/commit/4b4cde2), [`e0795c4`](https://github.com/AY2627S1-CS3219-P6/foc/commit/e0795c4).

**Affected files**

- [`credit-service/app/credits/consumer.py`](../credit-service/app/credits/consumer.py)
- [`credit-service/app/credits/replay.py`](../credit-service/app/credits/replay.py)
- [`credit-service/pyproject.toml`](../credit-service/pyproject.toml)
- [`credit-service/tests/integration/test_consumer_broker.py`](../credit-service/tests/integration/test_consumer_broker.py)
- [`credit-service/tests/test_consumer.py`](../credit-service/tests/test_consumer.py)
- [`credit-service/tests/test_replay.py`](../credit-service/tests/test_replay.py)

## 2026-10-15 23:08:30 SGT — Credit integrity check and restart policy

**Tool and mode** — Claude Code (model: Claude Opus 5.5), generate.

**Prompt**

> ok fix 2 and 4

**Prompt summary** — Items 2 and 4 referred to a ledger integrity check command and an automatic restart for the Credit API.

**Key response** — Added the read-only `credit-verify` integrity check with tests, and an automatic restart policy for the Credit API container.

**Commits** — [`8fcbb0e`](https://github.com/AY2627S1-CS3219-P6/foc/commit/8fcbb0e), [`71fbed3`](https://github.com/AY2627S1-CS3219-P6/foc/commit/71fbed3).

**Affected files**

- [`compose.yaml`](../compose.yaml)
- [`credit-service/app/credits/verify.py`](../credit-service/app/credits/verify.py)
- [`credit-service/pyproject.toml`](../credit-service/pyproject.toml)
- [`credit-service/tests/integration/test_ledger.py`](../credit-service/tests/integration/test_ledger.py)

## 2026-10-28 21:46:57 SGT — Admin Dashboard implementation

**Tool and mode** — Claude Code (model: Claude Opus 5.5), generate.

**Prompt excerpts**

> proceed with implementing admin dashboard

> there is no figma, reuse existing layouts

> so proceed with implementing admin dashboard

> make sure there is proper commits and commit messages

**Key response** — Generated the Admin Service foundation, the dispute workflow and audit log, read-only administrator errand and analytics endpoints in Order Service, administrator settlement and credit analytics endpoints in Credit Service, and the Admin Dashboard pages, with unit, integration and component tests.

**Commits** — [`9c64f19`](https://github.com/AY2627S1-CS3219-P6/foc/commit/9c64f19), [`2159b45`](https://github.com/AY2627S1-CS3219-P6/foc/commit/2159b45), [`ae479f2`](https://github.com/AY2627S1-CS3219-P6/foc/commit/ae479f2), [`66a3097`](https://github.com/AY2627S1-CS3219-P6/foc/commit/66a3097), [`316564b`](https://github.com/AY2627S1-CS3219-P6/foc/commit/316564b).

**Affected files**

- [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)
- [`admin-service/.dockerignore`](../admin-service/.dockerignore)
- [`admin-service/.env.docker.example`](../admin-service/.env.docker.example)
- [`admin-service/.env.example`](../admin-service/.env.example)
- [`admin-service/.gitignore`](../admin-service/.gitignore)
- [`admin-service/Dockerfile`](../admin-service/Dockerfile)
- [`admin-service/app/__init__.py`](../admin-service/app/__init__.py)
- [`admin-service/app/admin/__init__.py`](../admin-service/app/admin/__init__.py)
- [`admin-service/app/admin/api.py`](../admin-service/app/admin/api.py)
- [`admin-service/app/admin/auth.py`](../admin-service/app/admin/auth.py)
- [`admin-service/app/admin/disputes.py`](../admin-service/app/admin/disputes.py)
- [`admin-service/app/admin/errors.py`](../admin-service/app/admin/errors.py)
- [`admin-service/app/admin/identity.py`](../admin-service/app/admin/identity.py)
- [`admin-service/app/admin/orders.py`](../admin-service/app/admin/orders.py)
- [`admin-service/app/admin/repository.py`](../admin-service/app/admin/repository.py)
- [`admin-service/app/admin/schemas.py`](../admin-service/app/admin/schemas.py)
- [`admin-service/app/admin/tables.py`](../admin-service/app/admin/tables.py)
- [`admin-service/app/core/__init__.py`](../admin-service/app/core/__init__.py)
- [`admin-service/app/core/config.py`](../admin-service/app/core/config.py)
- [`admin-service/app/db.py`](../admin-service/app/db.py)
- [`admin-service/app/main.py`](../admin-service/app/main.py)
- [`admin-service/package-lock.json`](../admin-service/package-lock.json)
- [`admin-service/package.json`](../admin-service/package.json)
- [`admin-service/pyproject.toml`](../admin-service/pyproject.toml)
- [`admin-service/supabase/config.toml`](../admin-service/supabase/config.toml)
- [`admin-service/supabase/migrations/20261028000000_admin_foundation.sql`](../admin-service/supabase/migrations/20261028000000_admin_foundation.sql)
- [`admin-service/supabase/migrations/20261028000100_admin_disputes.sql`](../admin-service/supabase/migrations/20261028000100_admin_disputes.sql)
- [`admin-service/tests/__init__.py`](../admin-service/tests/__init__.py)
- [`admin-service/tests/admin_fakes.py`](../admin-service/tests/admin_fakes.py)
- [`admin-service/tests/integration/__init__.py`](../admin-service/tests/integration/__init__.py)
- [`admin-service/tests/integration/test_disputes.py`](../admin-service/tests/integration/test_disputes.py)
- [`admin-service/tests/integration/test_foundation.py`](../admin-service/tests/integration/test_foundation.py)
- [`admin-service/tests/test_auth.py`](../admin-service/tests/test_auth.py)
- [`admin-service/tests/test_config.py`](../admin-service/tests/test_config.py)
- [`admin-service/tests/test_dispute_rules.py`](../admin-service/tests/test_dispute_rules.py)
- [`admin-service/tests/test_disputes_api.py`](../admin-service/tests/test_disputes_api.py)
- [`admin-service/tests/test_health.py`](../admin-service/tests/test_health.py)
- [`admin-service/tests/test_identity.py`](../admin-service/tests/test_identity.py)
- [`admin-service/tests/test_orders_client.py`](../admin-service/tests/test_orders_client.py)
- [`compose.yaml`](../compose.yaml)
- [`credit-service/app/credits/api.py`](../credit-service/app/credits/api.py)
- [`credit-service/app/credits/ledger.py`](../credit-service/app/credits/ledger.py)
- [`credit-service/app/credits/schemas.py`](../credit-service/app/credits/schemas.py)
- [`credit-service/tests/credit_fakes.py`](../credit-service/tests/credit_fakes.py)
- [`credit-service/tests/test_admin_credit.py`](../credit-service/tests/test_admin_credit.py)
- [`order-service/app/orders/analytics.py`](../order-service/app/orders/analytics.py)
- [`order-service/app/orders/api.py`](../order-service/app/orders/api.py)
- [`order-service/app/orders/repository.py`](../order-service/app/orders/repository.py)
- [`order-service/app/orders/schemas.py`](../order-service/app/orders/schemas.py)
- [`order-service/supabase/migrations/20261028000000_admin_order_indexes.sql`](../order-service/supabase/migrations/20261028000000_admin_order_indexes.sql)
- [`order-service/tests/order_fakes.py`](../order-service/tests/order_fakes.py)
- [`order-service/tests/test_admin_orders.py`](../order-service/tests/test_admin_orders.py)
- [`order-service/tests/test_analytics.py`](../order-service/tests/test_analytics.py)
- [`web-client/nginx/default.conf`](../web-client/nginx/default.conf)
- [`web-client/src/api/admin-service.ts`](../web-client/src/api/admin-service.ts)
- [`web-client/src/api/credit-service.ts`](../web-client/src/api/credit-service.ts)
- [`web-client/src/api/order-service.ts`](../web-client/src/api/order-service.ts)
- [`web-client/src/app/admin-presentation.ts`](../web-client/src/app/admin-presentation.ts)
- [`web-client/src/app/routes.tsx`](../web-client/src/app/routes.tsx)
- [`web-client/src/app/use-admin-resource.ts`](../web-client/src/app/use-admin-resource.ts)
- [`web-client/src/components/admin-ui.tsx`](../web-client/src/components/admin-ui.tsx)
- [`web-client/src/components/app-navigation.tsx`](../web-client/src/components/app-navigation.tsx)
- [`web-client/src/components/navigation-icons.tsx`](../web-client/src/components/navigation-icons.tsx)
- [`web-client/src/main.tsx`](../web-client/src/main.tsx)
- [`web-client/src/pages/admin-dashboard-page.tsx`](../web-client/src/pages/admin-dashboard-page.tsx)
- [`web-client/src/pages/admin-dispute-detail-page.tsx`](../web-client/src/pages/admin-dispute-detail-page.tsx)
- [`web-client/src/pages/admin-disputes-page.tsx`](../web-client/src/pages/admin-disputes-page.tsx)
- [`web-client/src/pages/admin-order-detail-page.tsx`](../web-client/src/pages/admin-order-detail-page.tsx)
- [`web-client/src/pages/admin-orders-page.tsx`](../web-client/src/pages/admin-orders-page.tsx)
- [`web-client/src/styles/admin.css`](../web-client/src/styles/admin.css)
- [`web-client/tests/component/admin-dashboard-page.test.tsx`](../web-client/tests/component/admin-dashboard-page.test.tsx)
- [`web-client/tests/component/admin-dispute-detail-page.test.tsx`](../web-client/tests/component/admin-dispute-detail-page.test.tsx)
- [`web-client/tests/component/admin-orders-page.test.tsx`](../web-client/tests/component/admin-orders-page.test.tsx)
- [`web-client/tests/unit/order-proxy.test.ts`](../web-client/tests/unit/order-proxy.test.ts)
- [`web-client/vite.config.ts`](../web-client/vite.config.ts)

## 2026-10-29 16:09:44 SGT — Admin Dashboard credit and analytics panels

**Tool and mode** — Claude Code (model: Claude Opus 5.5), refactor.

**Prompt excerpts**

> much better to be able to see credit of a specific user, view their wallet etc

> for errands per day, currently the latest day is the last, the latest should be first and the oldest the last

> the total credit flow is still useful along with the each user credit wallet search … can still have it on the dashboard

**Key response** — Added a user wallet and credit transaction lookup alongside the platform credit totals, and listed daily errand counts newest first, with updated component tests.

**Commits** — [`316564b`](https://github.com/AY2627S1-CS3219-P6/foc/commit/316564b).

**Affected files**

- [`web-client/src/api/credit-service.ts`](../web-client/src/api/credit-service.ts)
- [`web-client/src/pages/admin-dashboard-page.tsx`](../web-client/src/pages/admin-dashboard-page.tsx)
- [`web-client/tests/component/admin-dashboard-page.test.tsx`](../web-client/tests/component/admin-dashboard-page.test.tsx)

## 2026-10-29 16:34:56 SGT — Errand problem reports

**Tool and mode** — Claude Code (model: Claude Opus 5.5), generate.

**Prompt excerpts**

> for a user to report a dispute just have a dispute and a description. no need evidence note. as it can be in description

> next go ahead with the rest of the implementation

**Key response** — Added participant report endpoints that confirm participation through Order Service, a migration allowing one open report per participant, edge and development proxy routes, a report panel on the errand page, the reporter's role in the admin views, and tests.

**Commits** — [`497078b`](https://github.com/AY2627S1-CS3219-P6/foc/commit/497078b), [`12e736e`](https://github.com/AY2627S1-CS3219-P6/foc/commit/12e736e).

**Affected files**

- [`admin-service/app/admin/api.py`](../admin-service/app/admin/api.py)
- [`admin-service/app/admin/disputes.py`](../admin-service/app/admin/disputes.py)
- [`admin-service/app/admin/orders.py`](../admin-service/app/admin/orders.py)
- [`admin-service/app/admin/reports.py`](../admin-service/app/admin/reports.py)
- [`admin-service/app/admin/repository.py`](../admin-service/app/admin/repository.py)
- [`admin-service/app/admin/schemas.py`](../admin-service/app/admin/schemas.py)
- [`admin-service/app/admin/tables.py`](../admin-service/app/admin/tables.py)
- [`admin-service/app/main.py`](../admin-service/app/main.py)
- [`admin-service/supabase/migrations/20261029000000_participant_reports.sql`](../admin-service/supabase/migrations/20261029000000_participant_reports.sql)
- [`admin-service/tests/admin_fakes.py`](../admin-service/tests/admin_fakes.py)
- [`admin-service/tests/integration/test_disputes.py`](../admin-service/tests/integration/test_disputes.py)
- [`admin-service/tests/test_orders_client.py`](../admin-service/tests/test_orders_client.py)
- [`admin-service/tests/test_reports_api.py`](../admin-service/tests/test_reports_api.py)
- [`web-client/nginx/default.conf`](../web-client/nginx/default.conf)
- [`web-client/src/api/admin-service.ts`](../web-client/src/api/admin-service.ts)
- [`web-client/src/app/admin-presentation.ts`](../web-client/src/app/admin-presentation.ts)
- [`web-client/src/components/admin-ui.tsx`](../web-client/src/components/admin-ui.tsx)
- [`web-client/src/components/errand-report.tsx`](../web-client/src/components/errand-report.tsx)
- [`web-client/src/pages/admin-dispute-detail-page.tsx`](../web-client/src/pages/admin-dispute-detail-page.tsx)
- [`web-client/src/pages/admin-disputes-page.tsx`](../web-client/src/pages/admin-disputes-page.tsx)
- [`web-client/src/pages/order-detail-page.tsx`](../web-client/src/pages/order-detail-page.tsx)
- [`web-client/tests/component/admin-dispute-detail-page.test.tsx`](../web-client/tests/component/admin-dispute-detail-page.test.tsx)
- [`web-client/tests/component/errand-report.test.tsx`](../web-client/tests/component/errand-report.test.tsx)
- [`web-client/tests/unit/order-proxy.test.ts`](../web-client/tests/unit/order-proxy.test.ts)
- [`web-client/vite.config.ts`](../web-client/vite.config.ts)

## 2026-10-29 17:07:31 SGT — Problem reports for both participants

**Tool and mode** — Claude Code (model: Claude Opus 5.5), generate.

**Prompt**

> yes implement then prepare to PR

**Prompt summary** — Continuation of the report feature: show each problem report and its status to both participants of the errand.

**Key response** — Listed every report about an errand to both participants with its status and decision reason, returned the description only to its author, and updated the errand page and tests.

**Commits** — [`9821e80`](https://github.com/AY2627S1-CS3219-P6/foc/commit/9821e80), [`693fa58`](https://github.com/AY2627S1-CS3219-P6/foc/commit/693fa58).

**Affected files**

- [`admin-service/app/admin/reports.py`](../admin-service/app/admin/reports.py)
- [`admin-service/app/admin/repository.py`](../admin-service/app/admin/repository.py)
- [`admin-service/app/admin/schemas.py`](../admin-service/app/admin/schemas.py)
- [`admin-service/tests/admin_fakes.py`](../admin-service/tests/admin_fakes.py)
- [`admin-service/tests/integration/test_disputes.py`](../admin-service/tests/integration/test_disputes.py)
- [`admin-service/tests/test_reports_api.py`](../admin-service/tests/test_reports_api.py)
- [`web-client/src/api/admin-service.ts`](../web-client/src/api/admin-service.ts)
- [`web-client/src/components/errand-report.tsx`](../web-client/src/components/errand-report.tsx)
- [`web-client/src/pages/admin-dispute-detail-page.tsx`](../web-client/src/pages/admin-dispute-detail-page.tsx)
- [`web-client/tests/component/admin-dispute-detail-page.test.tsx`](../web-client/tests/component/admin-dispute-detail-page.test.tsx)
- [`web-client/tests/component/errand-report.test.tsx`](../web-client/tests/component/errand-report.test.tsx)

## 2026-10-29 17:59:05 SGT — Admin Dashboard browser test fix

**Tool and mode** — Claude Code (model: Claude Opus 5.5), debug.

**Prompt**

> in PR 5, some CI checks fail

**Key response** — Kept the report panel's load failure out of the page alerts and kept the existing Admin mode landing page, so the existing browser tests pass, and updated the navigation test.

**Commits** — [`32e3952`](https://github.com/AY2627S1-CS3219-P6/foc/commit/32e3952).

**Affected files**

- [`web-client/src/components/errand-report.tsx`](../web-client/src/components/errand-report.tsx)
- [`web-client/tests/e2e/workspace-modes.spec.ts`](../web-client/tests/e2e/workspace-modes.spec.ts)

## 2026-11-08 15:58:21 SGT — Dispute errand outcomes

**Tool and mode** — Claude Code (model: Claude Opus 5.5), generate.

**Prompt excerpts**

> yes do 1 to 4, make sure everything flows, work correctly, have proper commits, messages, proper UI and etc

> continue where you stopped.

**Prompt summary** — Items 1 to 4 covered implementing the errand outcome choice on the dispute page, its credit preview and confirmation, and recording the decision in the errand history.

**Key response** — Added administrator fail and complete actions for disputed errands in Order Service, applied the chosen outcome when closing a dispute in Admin Service, and added the outcome choice, credit preview, confirmation and decision history to the web client, with unit, integration and component tests.

**Commits** — [`0da391f`](https://github.com/AY2627S1-CS3219-P6/foc/commit/0da391f), [`1728250`](https://github.com/AY2627S1-CS3219-P6/foc/commit/1728250), [`7059f3a`](https://github.com/AY2627S1-CS3219-P6/foc/commit/7059f3a).

**Affected files**

- [`admin-service/app/admin/api.py`](../admin-service/app/admin/api.py)
- [`admin-service/app/admin/disputes.py`](../admin-service/app/admin/disputes.py)
- [`admin-service/app/admin/orders.py`](../admin-service/app/admin/orders.py)
- [`admin-service/app/admin/reports.py`](../admin-service/app/admin/reports.py)
- [`admin-service/app/admin/repository.py`](../admin-service/app/admin/repository.py)
- [`admin-service/app/admin/schemas.py`](../admin-service/app/admin/schemas.py)
- [`admin-service/app/admin/tables.py`](../admin-service/app/admin/tables.py)
- [`admin-service/supabase/migrations/20261108000100_dispute_errand_outcomes.sql`](../admin-service/supabase/migrations/20261108000100_dispute_errand_outcomes.sql)
- [`admin-service/tests/admin_fakes.py`](../admin-service/tests/admin_fakes.py)
- [`admin-service/tests/integration/test_disputes.py`](../admin-service/tests/integration/test_disputes.py)
- [`admin-service/tests/test_dispute_outcomes.py`](../admin-service/tests/test_dispute_outcomes.py)
- [`order-service/app/orders/api.py`](../order-service/app/orders/api.py)
- [`order-service/app/orders/lifecycle.py`](../order-service/app/orders/lifecycle.py)
- [`order-service/app/orders/lifecycle_repository.py`](../order-service/app/orders/lifecycle_repository.py)
- [`order-service/app/orders/schemas.py`](../order-service/app/orders/schemas.py)
- [`order-service/app/orders/service.py`](../order-service/app/orders/service.py)
- [`order-service/app/orders/tables.py`](../order-service/app/orders/tables.py)
- [`order-service/supabase/migrations/20261108000000_admin_errand_decisions.sql`](../order-service/supabase/migrations/20261108000000_admin_errand_decisions.sql)
- [`order-service/tests/integration/test_admin_decisions.py`](../order-service/tests/integration/test_admin_decisions.py)
- [`order-service/tests/test_admin_decisions.py`](../order-service/tests/test_admin_decisions.py)
- [`web-client/src/api/admin-service.ts`](../web-client/src/api/admin-service.ts)
- [`web-client/src/api/order-service.ts`](../web-client/src/api/order-service.ts)
- [`web-client/src/app/admin-presentation.ts`](../web-client/src/app/admin-presentation.ts)
- [`web-client/src/components/admin-ui.tsx`](../web-client/src/components/admin-ui.tsx)
- [`web-client/src/components/errand-report.tsx`](../web-client/src/components/errand-report.tsx)
- [`web-client/src/components/order-lifecycle.tsx`](../web-client/src/components/order-lifecycle.tsx)
- [`web-client/src/pages/admin-dispute-detail-page.tsx`](../web-client/src/pages/admin-dispute-detail-page.tsx)
- [`web-client/src/pages/admin-order-detail-page.tsx`](../web-client/src/pages/admin-order-detail-page.tsx)
- [`web-client/src/pages/order-detail-page.tsx`](../web-client/src/pages/order-detail-page.tsx)
- [`web-client/src/styles/admin.css`](../web-client/src/styles/admin.css)
- [`web-client/tests/component/admin-dispute-detail-page.test.tsx`](../web-client/tests/component/admin-dispute-detail-page.test.tsx)
- [`web-client/tests/component/errand-report.test.tsx`](../web-client/tests/component/errand-report.test.tsx)

## 2026-11-08 19:22:38 SGT — Order Service lint fix

**Tool and mode** — Claude Code (model: Claude Opus 5.5), debug.

**Prompt**

> the first github PR fails the CI checks

**Key response** — Sorted the imports and wrapped a long line in the administrator decision integration tests so the Order Service lint step passes.

**Commits** — [`867f519`](https://github.com/AY2627S1-CS3219-P6/foc/commit/867f519).

**Affected files**

- [`order-service/tests/integration/test_admin_decisions.py`](../order-service/tests/integration/test_admin_decisions.py)


## 2026-11-10 04:29:29 SGT — Disputed errand state

**Tool and mode** — Claude Code (model: Claude Opus 5.5), generate.

**Prompt excerpts**

> report workflow should be changed. there is already a marked failed portion as part of errand, and should be build on top of that. do the workflow properly. suggest changes if necessary

> go and implement, make sure there are proper commits and commit messages, then i will also need to push it into github after

**Prompt summary** — I specified the workflow and answered every design question before implementation: a DISPUTED errand state replacing participant failure, the selected problem and its visibility, private statements, reporter-only withdrawal while OPEN, Accepted/Rejected decisions, one dispute per errand, Admin Service ownership, calling Order first with retries, and a shared service credential between Admin and Order.

**Key response** — Implemented the specified workflow: the DISPUTED state and internal dispute routes in Order Service; problems, statements, withdrawal and errand-changing decisions in Admin Service; the deployment credential; and the participant and administrator pages in the web client, with unit, integration, component and end-to-end tests.

**Commits** — [`33b6da0`](https://github.com/AY2627S1-CS3219-P6/foc/commit/33b6da0), [`1ba1f79`](https://github.com/AY2627S1-CS3219-P6/foc/commit/1ba1f79), [`032e1a7`](https://github.com/AY2627S1-CS3219-P6/foc/commit/032e1a7), [`bd01cad`](https://github.com/AY2627S1-CS3219-P6/foc/commit/bd01cad).

**Affected files**

- [`admin-service/.env.docker.example`](../admin-service/.env.docker.example)
- [`admin-service/.env.example`](../admin-service/.env.example)
- [`admin-service/AGENTS.md`](../admin-service/AGENTS.md)
- [`admin-service/API.md`](../admin-service/API.md)
- [`admin-service/README.md`](../admin-service/README.md)
- [`admin-service/app/admin/api.py`](../admin-service/app/admin/api.py)
- [`admin-service/app/admin/disputes.py`](../admin-service/app/admin/disputes.py)
- [`admin-service/app/admin/orders.py`](../admin-service/app/admin/orders.py)
- [`admin-service/app/admin/reports.py`](../admin-service/app/admin/reports.py)
- [`admin-service/app/admin/repository.py`](../admin-service/app/admin/repository.py)
- [`admin-service/app/admin/schemas.py`](../admin-service/app/admin/schemas.py)
- [`admin-service/app/admin/tables.py`](../admin-service/app/admin/tables.py)
- [`admin-service/app/core/config.py`](../admin-service/app/core/config.py)
- [`admin-service/supabase/migrations/20261110000100_dispute_workflow.sql`](../admin-service/supabase/migrations/20261110000100_dispute_workflow.sql)
- [`admin-service/tests/admin_fakes.py`](../admin-service/tests/admin_fakes.py)
- [`admin-service/tests/integration/test_disputes.py`](../admin-service/tests/integration/test_disputes.py)
- [`admin-service/tests/test_dispute_rules.py`](../admin-service/tests/test_dispute_rules.py)
- [`admin-service/tests/test_disputes_api.py`](../admin-service/tests/test_disputes_api.py)
- [`admin-service/tests/test_orders_client.py`](../admin-service/tests/test_orders_client.py)
- [`admin-service/tests/test_reports_api.py`](../admin-service/tests/test_reports_api.py)
- [`deploy/aws/.env.example`](../deploy/aws/.env.example)
- [`deploy/aws/README.md`](../deploy/aws/README.md)
- [`deploy/aws/compose.yaml`](../deploy/aws/compose.yaml)
- [`deploy/aws/scripts/generate_env.py`](../deploy/aws/scripts/generate_env.py)
- [`deploy/aws/scripts/validate.py`](../deploy/aws/scripts/validate.py)
- [`deploy/aws/tests/test_cloud_helpers.py`](../deploy/aws/tests/test_cloud_helpers.py)
- [`order-service/.env.docker.example`](../order-service/.env.docker.example)
- [`order-service/.env.example`](../order-service/.env.example)
- [`order-service/API.md`](../order-service/API.md)
- [`order-service/app/core/config.py`](../order-service/app/core/config.py)
- [`order-service/app/main.py`](../order-service/app/main.py)
- [`order-service/app/orders/analytics.py`](../order-service/app/orders/analytics.py)
- [`order-service/app/orders/api.py`](../order-service/app/orders/api.py)
- [`order-service/app/orders/lifecycle.py`](../order-service/app/orders/lifecycle.py)
- [`order-service/app/orders/lifecycle_repository.py`](../order-service/app/orders/lifecycle_repository.py)
- [`order-service/app/orders/schemas.py`](../order-service/app/orders/schemas.py)
- [`order-service/app/orders/service.py`](../order-service/app/orders/service.py)
- [`order-service/app/orders/tables.py`](../order-service/app/orders/tables.py)
- [`order-service/supabase/migrations/20261110000000_errand_disputes.sql`](../order-service/supabase/migrations/20261110000000_errand_disputes.sql)
- [`order-service/tests/integration/test_disputes.py`](../order-service/tests/integration/test_disputes.py)
- [`order-service/tests/integration/test_order_events.py`](../order-service/tests/integration/test_order_events.py)
- [`order-service/tests/test_disputes.py`](../order-service/tests/test_disputes.py)
- [`web-client/src/api/admin-service.ts`](../web-client/src/api/admin-service.ts)
- [`web-client/src/api/order-service.ts`](../web-client/src/api/order-service.ts)
- [`web-client/src/app/admin-presentation.ts`](../web-client/src/app/admin-presentation.ts)
- [`web-client/src/app/order-presentation.ts`](../web-client/src/app/order-presentation.ts)
- [`web-client/src/components/admin-ui.tsx`](../web-client/src/components/admin-ui.tsx)
- [`web-client/src/components/errand-report.tsx`](../web-client/src/components/errand-report.tsx)
- [`web-client/src/components/order-lifecycle.tsx`](../web-client/src/components/order-lifecycle.tsx)
- [`web-client/src/pages/admin-dispute-detail-page.tsx`](../web-client/src/pages/admin-dispute-detail-page.tsx)
- [`web-client/src/pages/admin-order-detail-page.tsx`](../web-client/src/pages/admin-order-detail-page.tsx)
- [`web-client/src/pages/admin-orders-page.tsx`](../web-client/src/pages/admin-orders-page.tsx)
- [`web-client/src/pages/order-detail-page.tsx`](../web-client/src/pages/order-detail-page.tsx)
- [`web-client/src/styles/admin.css`](../web-client/src/styles/admin.css)
- [`web-client/src/styles/order.css`](../web-client/src/styles/order.css)
- [`web-client/tests/component/admin-dispute-detail-page.test.tsx`](../web-client/tests/component/admin-dispute-detail-page.test.tsx)
- [`web-client/tests/component/admin-orders-page.test.tsx`](../web-client/tests/component/admin-orders-page.test.tsx)
- [`web-client/tests/component/errand-report.test.tsx`](../web-client/tests/component/errand-report.test.tsx)
- [`web-client/tests/e2e/orders.spec.ts`](../web-client/tests/e2e/orders.spec.ts)
- [`web-client/tests/unit/order-service.test.ts`](../web-client/tests/unit/order-service.test.ts)
