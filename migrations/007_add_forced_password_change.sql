-- Additive security migration for administrator-issued temporary passwords.
-- Existing accounts remain unchanged and no records are deleted.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN;

UPDATE users
SET must_change_password = FALSE
WHERE must_change_password IS NULL;

ALTER TABLE users
    ALTER COLUMN must_change_password SET DEFAULT FALSE,
    ALTER COLUMN must_change_password SET NOT NULL;
