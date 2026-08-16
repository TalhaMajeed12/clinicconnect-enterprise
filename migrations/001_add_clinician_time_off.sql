BEGIN;

CREATE TABLE IF NOT EXISTS clinician_time_off (
    id SERIAL PRIMARY KEY,
    clinician_id INTEGER NOT NULL REFERENCES clinician_profiles(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    start_time TIME WITHOUT TIME ZONE,
    end_time TIME WITHOUT TIME ZONE,
    full_day BOOLEAN NOT NULL DEFAULT TRUE,
    reason VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'approved',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_time_off_date_order CHECK (end_date >= start_date),
    CONSTRAINT ck_time_off_status CHECK (status IN ('approved', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS ix_clinician_time_off_clinician_id
    ON clinician_time_off (clinician_id);
CREATE INDEX IF NOT EXISTS ix_clinician_time_off_status
    ON clinician_time_off (status);

COMMIT;
