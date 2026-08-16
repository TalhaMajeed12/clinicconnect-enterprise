from datetime import datetime

from app.extensions import db


class ClinicianTimeOff(db.Model):
    """Approved or cancelled clinician leave that blocks appointment booking."""

    __tablename__ = 'clinician_time_off'

    id = db.Column(db.Integer, primary_key=True)
    clinician_id = db.Column(
        db.Integer,
        db.ForeignKey('clinician_profiles.id'),
        nullable=False,
        index=True,
    )
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    full_day = db.Column(db.Boolean, nullable=False, default=True)
    reason = db.Column(db.String(255))
    status = db.Column(db.String(20), nullable=False, default='approved', index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    clinician = db.relationship('ClinicianProfile', backref='time_off_entries')

    __table_args__ = (
        db.CheckConstraint('end_date >= start_date', name='ck_time_off_date_order'),
        db.CheckConstraint(
            "status IN ('approved', 'cancelled')",
            name='ck_time_off_status',
        ),
    )

    def blocks(self, appointment_start, duration_minutes=30):
        if self.status != 'approved':
            return False
        appointment_end = appointment_start.timestamp() + duration_minutes * 60
        if not (self.start_date <= appointment_start.date() <= self.end_date):
            return False
        if self.full_day:
            return True
        if self.start_time is None or self.end_time is None:
            return True
        leave_start = datetime.combine(appointment_start.date(), self.start_time).timestamp()
        leave_end = datetime.combine(appointment_start.date(), self.end_time).timestamp()
        return appointment_start.timestamp() < leave_end and appointment_end > leave_start
