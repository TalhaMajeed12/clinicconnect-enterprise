-- Additive, non-destructive audit lifecycle support.
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP;
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS archive_batch_id VARCHAR(36);
CREATE INDEX IF NOT EXISTS ix_audit_logs_archived_at ON audit_logs (archived_at);
CREATE INDEX IF NOT EXISTS ix_audit_logs_archive_batch_id ON audit_logs (archive_batch_id);
