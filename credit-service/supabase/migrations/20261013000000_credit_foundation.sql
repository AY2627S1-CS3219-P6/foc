
-- F0 establishes ownership only. Business tables and their grants belong to the ledger migration.
BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'credit_service_app') THEN
        CREATE ROLE credit_service_app NOLOGIN NOINHERIT;
    END IF;
END
$$;

CREATE SCHEMA credit_service;
REVOKE ALL ON SCHEMA credit_service FROM PUBLIC, anon, authenticated, service_role;
GRANT USAGE ON SCHEMA credit_service TO credit_service_app;

COMMIT;
