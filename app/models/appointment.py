from datetime import datetime
import secrets

from app.extensions import db


class Appointment(db.Model):
    __tablename__ = "appointments"
    __table_args__ = (
        db.CheckConstraint(
            "appointment_type IN ('in_person', 'video')",
            name='ck_appointments_type',
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patient_profiles.id")
    )
    clinician_id = db.Column(
        db.Integer,
        db.ForeignKey("clinician_profiles.id")
    )

    appointment_date = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer, default=30)
    status = db.Column(db.String(20), default="pending")
    appointment_type = db.Column(
        db.String(20), nullable=False, default='in_person', index=True
    )

    reason = db.Column(db.Text)
    symptoms = db.Column(db.Text)
    notes = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.JSON, default=list)

    is_follow_up = db.Column(db.Boolean, default=False)
    previous_appointment_id = db.Column(
        db.Integer,
        db.ForeignKey("appointments.id")
    )

    reminder_sent = db.Column(db.Boolean, default=False)
    reminder_sent_at = db.Column(db.DateTime)
    video_room_token = db.Column(
        db.String(64), unique=True, nullable=False,
        default=lambda: secrets.token_urlsafe(32)
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    patient = db.relationship("PatientProfile", backref="appointments")
    clinician = db.relationship("ClinicianProfile", backref="appointments")
    video_session = db.relationship(
        'VideoConsultation', back_populates='appointment', uselist=False,
        cascade='all, delete-orphan'
    )

    def to_dict(self):
        return {
            "id": self.id,
            "appointment_date": self.appointment_date.isoformat(),
            "timezone": "Asia/Karachi",
            "status": self.status,
            "appointment_type": self.appointment_type,
            "reason": self.reason
        }
 
