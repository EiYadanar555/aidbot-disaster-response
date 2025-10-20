-- wipe.sqlite.sql
PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;

-- Delete child/dependent tables first
DELETE FROM emergency_forms;
DELETE FROM notifications;
DELETE FROM preposition_plans;
DELETE FROM audit_log;

-- Then parents
DELETE FROM cases;
DELETE FROM contact_messages;
DELETE FROM blood_inventory;
DELETE FROM resources_allocations;
DELETE FROM shelters;
DELETE FROM users;

COMMIT;
VACUUM;
