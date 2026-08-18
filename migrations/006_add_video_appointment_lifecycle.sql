-- Additive migration: explicit appointment types, video-session lifecycle,
-- guest-request type selection, and database-level exact-slot protection.
ALTER TABLE appointments
    ADD COLUMN IF NOT EXISTS appointment_type VARCHAR(20);

UPDATE appointments
SET appointment_type = CASE
    WHEN EXISTS (
        SELECT 1 FROM consultation_messages message
        WHERE message.appointment_id = appointments.id
    ) THEN 'video'
    ELSE 'in_person'
END
WHERE appointment_type IS NULL;

ALTER TABLE appointments
    ALTER COLUMN appointment_type SET DEFAULT 'in_person',
    ALTER COLUMN appointment_type SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_appointments_type'
    ) THEN
        ALTER TABLE appointments ADD CONSTRAINT ck_appointments_type
            CHECK (appointment_type IN ('in_person', 'video'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_appointments_appointment_type
    ON appointments (appointment_type);

ALTER TABLE guest_appointment_requests
    ADD COLUMN IF NOT EXISTS appointment_type VARCHAR(20);
UPDATE guest_appointment_requests
SET appointment_type = 'in_person'
WHERE appointment_type IS NULL;
ALTER TABLE guest_appointment_requests
    ALTER COLUMN appointment_type SET DEFAULT 'in_person',
    ALTER COLUMN appointment_type SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_guest_request_type'
    ) THEN
        ALTER TABLE guest_appointment_requests ADD CONSTRAINT ck_guest_request_type
            CHECK (appointment_type IN ('in_person', 'video'));
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS video_consultations (
    id SERIAL PRIMARY KEY,
    appointment_id INTEGER NOT NULL UNIQUE
        REFERENCES appointments(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    started_at TIMESTAMP WITHOUT TIME ZONE,
    ended_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_video_consultations_status
        CHECK (status IN ('scheduled', 'active', 'ended'))
);
CREATE INDEX IF NOT EXISTS ix_video_consultations_appointment_id
    ON video_consultations (appointment_id);

INSERT INTO video_consultations (appointment_id, status, started_at, ended_at)
SELECT appointment.id,
       CASE WHEN appointment.status = 'completed' THEN 'ended' ELSE 'scheduled' END,
       NULL,
       CASE WHEN appointment.status = 'completed' THEN appointment.updated_at ELSE NULL END
FROM appointments appointment
WHERE appointment.appointment_type = 'video'
ON CONFLICT (appointment_id) DO NOTHING;

-- The clinician row lock in the booking service protects overlapping ranges.
-- This partial unique index also prevents identical active start times even if
-- another code path bypasses that service. Resolve any pre-existing duplicates
-- deliberately before applying; this migration never deletes clinical data.
CREATE UNIQUE INDEX IF NOT EXISTS uq_active_clinician_exact_slot
    ON appointments (clinician_id, appointment_date)
    WHERE status IN ('pending', 'confirmed', 'checked_in');

-- One appointment owns at most one longitudinal visit record. If a legacy
-- database contains duplicates, review and resolve them instead of deleting
-- data automatically, then rerun this statement.
CREATE UNIQUE INDEX IF NOT EXISTS uq_visits_appointment
    ON visits (appointment_id)
    WHERE appointment_id IS NOT NULL;
