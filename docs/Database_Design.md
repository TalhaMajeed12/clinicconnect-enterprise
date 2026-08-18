# Database Design

PostgreSQL is the production source of truth. SQLAlchemy models under `app/models/` define the implemented schema; documentation must not be used as a substitute for inspecting those models and the live migration state.

## Core relationships

```text
users
  |-- clinician_profiles -- clinician_time_off
  |          |-- appointments -- payments
  |          `-- visits -- prescriptions
  `-- patient_profiles
             |-- appointments
             |-- visits
             `-- payments
```

Supporting tables include `audit_logs`, `login_attempts`, `otp_verifications`, `notifications`, `attendance`, `system_settings`, and `password_reset_tokens`.

## Important integrity rules

- Every clinician and patient profile belongs to one user.
- Appointments reference both a patient profile and clinician profile.
- Visits retain patient, clinician, and optional appointment relationships.
- Prescriptions belong to a visit and patient.
- Payments retain their patient and appointment relationships.
- Clinicians with history are deactivated through `users.is_active`; history is not hard-deleted.
- Password reset tokens store SHA-256 token hashes rather than raw reset tokens.
- JSON defaults use callables such as `list`, `dict`, or `lambda` to avoid shared mutable values.

## Sensitive data

Selected user and patient columns contain Fernet ciphertext through model properties. Fernet encryption is randomized, so ordinary SQL equality or `LIKE` searches against those encrypted columns are unreliable. Current compatibility lookups decrypt and compare in application code. A future non-destructive migration may add normalized keyed lookup hashes for indexed searches.

The existing `ENCRYPTION_KEY` must not be changed unless every encrypted value is safely re-encrypted first.

## Migrations

Reviewed additive SQL migrations are stored in `migrations/`:

- `001_add_clinician_time_off.sql`
- `002_add_password_reset_tokens.sql`

Back up PostgreSQL and verify the target before applying migrations. Never reset production or delete EHR data to resolve schema drift.

`audit_logs.archived_at` and `audit_logs.archive_batch_id` provide a non-destructive activity lifecycle. Active and archived records remain in PostgreSQL and are available through admin filters; no clinical record is purged by this workflow.
# Video lifecycle additions

Migration `006_add_video_appointment_lifecycle.sql` adds `appointment_type` to appointments and guest requests, a one-to-one `video_consultations` lifecycle table, an active exact-slot uniqueness guard, and a one-visit-per-appointment guard. Existing records are backfilled additively; no rows are deleted. Apply only after a verified backup and resolve any legacy duplicate active slots/visits deliberately if the protective indexes report a conflict.
