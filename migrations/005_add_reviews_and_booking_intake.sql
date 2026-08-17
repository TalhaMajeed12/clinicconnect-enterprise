-- Additive migration: verified doctor reviews and encrypted guest booking intake.
CREATE TABLE IF NOT EXISTS doctor_reviews (
    id SERIAL PRIMARY KEY,
    appointment_id INTEGER NOT NULL UNIQUE REFERENCES appointments(id),
    patient_id INTEGER NOT NULL REFERENCES patient_profiles(id),
    clinician_id INTEGER NOT NULL REFERENCES clinician_profiles(id),
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_doctor_reviews_patient_id ON doctor_reviews(patient_id);
CREATE INDEX IF NOT EXISTS ix_doctor_reviews_clinician_id ON doctor_reviews(clinician_id);

CREATE TABLE IF NOT EXISTS guest_appointment_requests (
    id SERIAL PRIMARY KEY,
    reference VARCHAR(20) NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    email TEXT,
    phone TEXT NOT NULL,
    date_of_birth DATE NOT NULL,
    specialty VARCHAR(100) NOT NULL,
    clinician_id INTEGER NOT NULL REFERENCES clinician_profiles(id),
    preferred_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    reason TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'new',
    patient_id INTEGER REFERENCES patient_profiles(id),
    appointment_id INTEGER REFERENCES appointments(id),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_guest_requests_reference ON guest_appointment_requests(reference);
CREATE INDEX IF NOT EXISTS ix_guest_requests_specialty ON guest_appointment_requests(specialty);
CREATE INDEX IF NOT EXISTS ix_guest_requests_status ON guest_appointment_requests(status);
