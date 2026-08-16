from datetime import datetime

from app.extensions import db


class Appointment(db.Model):
    __tablename__ = "appointments"

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

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    patient = db.relationship("PatientProfile", backref="appointments")
    clinician = db.relationship("ClinicianProfile", backref="appointments")

    def to_dict(self):
        return {
            "id": self.id,
            "appointment_date": self.appointment_date.isoformat(),
            "status": self.status,
            "reason": self.reason
        }
 
