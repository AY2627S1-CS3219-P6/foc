-- Requester and courier are order-level participant relationships, not a
-- persisted User Service profile setting. This migration preserves the
-- historical schema migration and removes the obsolete preference.

BEGIN;

ALTER TABLE user_service.users
DROP COLUMN active_participation_mode;

DROP TYPE user_service.participation_mode;

COMMIT;
