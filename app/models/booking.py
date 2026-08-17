from datetime import datetime

from app.extensions import db
from .mixins import EncryptionMixin


class DoctorReview(db.Model, EncryptionMixin):
    __tablename__ = 'doctor_reviews'

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False, unique=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient_profiles.id'), nullable=False, index=True)
    clinician_id = db.Column(db.Integer, db.ForeignKey('clinician_profiles.id'), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)
    _comment = db.Column('comment', db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    appointment = db.relationship('Appointment', backref=db.backref('review', uselist=False))
    patient = db.relationship('PatientProfile')
    clinician = db.relationship('ClinicianProfile', backref='reviews')

    @property
    def comment(self):
        return self.decrypt_field(self._comment)

    @comment.setter
    def comment(self, value):
        self._comment = self.encrypt_field(value)


class GuestAppointmentRequest(db.Model, EncryptionMixin):
    __tablename__ = 'guest_appointment_requests'

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(20), nullable=False, unique=True, index=True)
    _full_name = db.Column('full_name', db.Text, nullable=False)
    _email = db.Column('email', db.Text)
    _phone = db.Column('phone', db.Text, nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    specialty = db.Column(db.String(100), nullable=False, index=True)
    clinician_id = db.Column(db.Integer, db.ForeignKey('clinician_profiles.id'), nullable=False)
    preferred_at = db.Column(db.DateTime, nullable=False)
    _reason = db.Column('reason', db.Text)
    status = db.Column(db.String(20), nullable=False, default='new', index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient_profiles.id'))
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    clinician = db.relationship('ClinicianProfile')
    patient = db.relationship('PatientProfile')
    appointment = db.relationship('Appointment')

    def _protected(name):
        def getter(self):
            return self.decrypt_field(getattr(self, f'_{name}'))
        def setter(self, value):
            setattr(self, f'_{name}', self.encrypt_field(value))
        return property(getter, setter)

    full_name = _protected('full_name')
    email = _protected('email')
    phone = _protected('phone')
    reason = _protected('reason')
