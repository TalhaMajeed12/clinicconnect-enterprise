from app import db
from datetime import datetime
from flask import current_app
from cryptography.fernet import Fernet
import bcrypt
import json
import uuid

# ============================================
# ENCRYPTION MIXIN
# ============================================
class EncryptionMixin:
    _fernet = None
    
    @classmethod
    def _get_fernet(cls):
        if cls._fernet is None:
            key = current_app.config['ENCRYPTION_KEY']
            cls._fernet = Fernet(key.encode())
        return cls._fernet
    
    def encrypt_field(self, value):
        if value is None:
            return None
        fernet = self._get_fernet()
        return fernet.encrypt(value.encode()).decode()
    
    def decrypt_field(self, encrypted_value):
        if encrypted_value is None:
            return None
        fernet = self._get_fernet()
        return fernet.decrypt(encrypted_value.encode()).decode()


# ============================================
# USER MODEL
# ============================================
class User(db.Model, EncryptionMixin):
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
    
    language = db.Column(db.String(5), default='en')
    timezone = db.Column(db.String(50), default='Asia/Karachi')
    notifications_enabled = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    clinician_profile = db.relationship('ClinicianProfile', backref='user', uselist=False)
    patient_profile = db.relationship('PatientProfile', backref='user', uselist=False)
    
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


# ============================================
# PATIENT PROFILE
# ============================================
class PatientProfile(db.Model, EncryptionMixin):
    __tablename__ = 'patient_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    
    _blood_group = db.Column('blood_group', db.Text)
    _allergies = db.Column('allergies', db.Text)
    _chronic_conditions = db.Column('chronic_conditions', db.Text)
    _current_medications = db.Column('current_medications', db.Text)
    
    _emergency_contact_name = db.Column('emergency_contact_name', db.Text)
    _emergency_contact_phone = db.Column('emergency_contact_phone', db.Text)
    _emergency_contact_relation = db.Column('emergency_contact_relation', db.Text)
    
    _insurance_provider = db.Column('insurance_provider', db.Text)
    _insurance_number = db.Column('insurance_number', db.Text)
    insurance_expiry = db.Column(db.Date)
    
    is_child = db.Column(db.Boolean, default=False)
    guardian_id = db.Column(db.Integer, db.ForeignKey('patient_profiles.id'))
    relationship_to_guardian = db.Column(db.String(50))
    age = db.Column(db.Integer)
    
    medical_history = db.Column(db.JSON, default=[])
    family_history = db.Column(db.JSON, default=[])
    
    guardian = db.relationship('PatientProfile', remote_side=[id], backref='children')
    
    @property
    def blood_group(self):
        return self.decrypt_field(self._blood_group)
    
    @blood_group.setter
    def blood_group(self, value):
        self._blood_group = self.encrypt_field(value)
    
    @property
    def allergies(self):
        return self.decrypt_field(self._allergies)
    
    @allergies.setter
    def allergies(self, value):
        self._allergies = self.encrypt_field(value)
    
    @property
    def emergency_contact_name(self):
        return self.decrypt_field(self._emergency_contact_name)
    
    @emergency_contact_name.setter
    def emergency_contact_name(self, value):
        self._emergency_contact_name = self.encrypt_field(value)
    
    def to_dict(self):
        return {
            'id': self.id,
            'blood_group': self.blood_group,
            'allergies': self.allergies,
            'is_child': self.is_child,
            'age': self.age,
        }


# ============================================
# CLINICIAN PROFILE
# ============================================
class ClinicianProfile(db.Model):
    __tablename__ = 'clinician_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    
    specialty = db.Column(db.String(100), nullable=False)
    license_number = db.Column(db.String(50), unique=True)
    years_experience = db.Column(db.Integer, default=0)
    qualifications = db.Column(db.JSON, default=[])
    certifications = db.Column(db.JSON, default=[])
    bio = db.Column(db.Text)
    
    consultation_fee = db.Column(db.Numeric(10,2), default=2000)
    working_days = db.Column(db.JSON, default=['monday', 'tuesday', 'wednesday', 'thursday', 'friday'])
    working_hours = db.Column(db.JSON, default={'start': '09:00', 'end': '17:00'})
    
    is_available = db.Column(db.Boolean, default=False)
    max_patients_per_day = db.Column(db.Integer, default=30)
    appointment_duration = db.Column(db.Integer, default=30)
    
    average_rating = db.Column(db.Float, default=0)
    total_reviews = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'specialty': self.specialty,
            'license_number': self.license_number,
            'consultation_fee': float(self.consultation_fee),
            'is_available': self.is_available,
            'rating': float(self.average_rating)
        }


# ============================================
# APPOINTMENT
# ============================================
class Appointment(db.Model):
    __tablename__ = 'appointments'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient_profiles.id'))
    clinician_id = db.Column(db.Integer, db.ForeignKey('clinician_profiles.id'))
    
    appointment_date = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer, default=30)
    status = db.Column(db.String(20), default='pending')
    
    reason = db.Column(db.Text)
    symptoms = db.Column(db.Text)
    notes = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.JSON, default=[])
    
    is_follow_up = db.Column(db.Boolean, default=False)
    previous_appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'))
    
    reminder_sent = db.Column(db.Boolean, default=False)
    reminder_sent_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'appointment_date': self.appointment_date.isoformat(),
            'status': self.status,
            'reason': self.reason
        }


# ============================================
# PAYMENT
# ============================================
class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'))
    patient_id = db.Column(db.Integer, db.ForeignKey('patient_profiles.id'))
    
    amount = db.Column(db.Numeric(10,2), nullable=False)
    discount = db.Column(db.Numeric(10,2), default=0)
    tax = db.Column(db.Numeric(10,2), default=0)
    total_amount = db.Column(db.Numeric(10,2))
    
    payment_method = db.Column(db.String(50))
    transaction_id = db.Column(db.String(100), unique=True)
    payment_status = db.Column(db.String(20), default='pending')
    
    receipt_number = db.Column(db.String(50), unique=True)
    receipt_url = db.Column(db.String(255))
    
    billing_address = db.Column(db.Text)
    insurance_claim = db.Column(db.JSON, default={})
    
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================
# AUDIT LOG
# ============================================
class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.Integer)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    session_id = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    user = db.relationship('User', backref='audit_logs')


# ============================================
# OTP VERIFICATION
# ============================================
class OtpVerification(db.Model):
    __tablename__ = 'otp_verifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    phone = db.Column(db.String(15), nullable=False)
    otp_code = db.Column(db.String(6), nullable=False)
    purpose = db.Column(db.String(20), default='registration')
    expires_at = db.Column(db.DateTime, nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    attempts = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================
# LOGIN ATTEMPT
# ============================================
class LoginAttempt(db.Model):
    __tablename__ = 'login_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(200))
    success = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)


# ============================================
# SYSTEM SETTING
# ============================================
class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    is_encrypted = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)