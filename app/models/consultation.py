from datetime import datetime

from app.extensions import db
from .mixins import EncryptionMixin


class ConsultationMessage(db.Model, EncryptionMixin):
    """Encrypted message belonging to exactly one booked consultation."""

    __tablename__ = 'consultation_messages'

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(
        db.Integer, db.ForeignKey('appointments.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    sender_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=False, index=True
    )
    _body = db.Column('body', db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    appointment = db.relationship('Appointment', backref='consultation_messages')
    sender = db.relationship('User')

    @property
    def body(self):
        return self.decrypt_field(self._body)

    @body.setter
    def body(self, value):
        self._body = self.encrypt_field(value)
