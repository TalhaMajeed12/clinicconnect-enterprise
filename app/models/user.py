# USER MODEL
# ============================================
from datetime import datetime
import uuid
import bcrypt
from flask_login import UserMixin

from app.extensions import db
from .mixins import EncryptionMixin

class User(UserMixin, db.Model, EncryptionMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    _email = db.Column('email', db.Text, unique=True, nullable=False)
    _phone = db.Column('phone', db.Text, unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    role = db.Column(db.String(20), nullable=False, default='patient')
    
    _full_name = db.Column('full_name', db.Text, nullable=False)
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    _address = db.Column('address', db.Text)
    profile_picture = db.Column(db.String(255))
    
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    email_verified = db.Column(db.Boolean, default=False)
    phone_verified = db.Column(db.Boolean, default=False)
    
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(255))
    last_login = db.Column(db.DateTime)
    login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    must_change_password = db.Column(db.Boolean, nullable=False, default=False)
    
    language = db.Column(db.String(5), default='en')
    timezone = db.Column(db.String(50), default='Asia/Karachi')
    notifications_enabled = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    clinician_profile = db.relationship('ClinicianProfile', backref='user', uselist=False)
    patient_profile = db.relationship('PatientProfile', backref='user', uselist=False)

    @staticmethod
    def normalize_identifier(value):
        return (value or '').strip().casefold()

    @classmethod
    def find_by_identifier(cls, value):
        """Compatibility lookup for randomized encrypted email/phone columns.

        A future migration can replace this scan with keyed lookup hashes without
        changing callers. Plaintext is never persisted by this method.
        """
        target = cls.normalize_identifier(value)
        if not target:
            return None
        for user in cls.query.all():
            if target in {
                cls.normalize_identifier(user.email),
                cls.normalize_identifier(user.phone),
            }:
                return user
        return None
    
    @property
    def email(self):
        return self.decrypt_field(self._email)
    
    @email.setter
    def email(self, value):
        self._email = self.encrypt_field(value)
    
    @property
    def phone(self):
        return self.decrypt_field(self._phone)
    
    @phone.setter
    def phone(self, value):
        self._phone = self.encrypt_field(value)
    
    @property
    def full_name(self):
        return self.decrypt_field(self._full_name)
    
    @full_name.setter
    def full_name(self, value):
        self._full_name = self.encrypt_field(value)
    
    @property
    def address(self):
        return self.decrypt_field(self._address)
    
    @address.setter
    def address(self, value):
        self._address = self.encrypt_field(value)
    
    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt(rounds=12)
        ).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_clinician(self):
        return self.role == 'clinician'
    
    def is_patient(self):
        return self.role == 'patient'
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'username': self.username,
            'email': self.email,
            'phone': self.phone,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'language': self.language
        }
 
