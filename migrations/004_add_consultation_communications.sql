-- Additive migration: private video-room identifiers and encrypted messages.
ALTER TABLE appointments
    ADD COLUMN IF NOT EXISTS video_room_token VARCHAR(64);

UPDATE appointments
SET video_room_token = md5(random()::text || clock_timestamp()::text || id::text)
                       || md5(id::text || random()::text || clock_timestamp()::text)
WHERE video_room_token IS NULL;

ALTER TABLE appointments
    ALTER COLUMN video_room_token SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_appointments_video_room_token
    ON appointments (video_room_token);

CREATE TABLE IF NOT EXISTS consultation_messages (
    id SERIAL PRIMARY KEY,
    appointment_id INTEGER NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
    sender_id INTEGER NOT NULL REFERENCES users(id),
    body TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_consultation_messages_appointment_id
    ON consultation_messages (appointment_id);
CREATE INDEX IF NOT EXISTS ix_consultation_messages_sender_id
    ON consultation_messages (sender_id);
