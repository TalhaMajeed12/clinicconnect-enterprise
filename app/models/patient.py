# PATIENT PROFILE
# ============================================
from app.extensions import db
from .mixins import EncryptionMixin
from datetime import datetime

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
    
    medical_history = db.Column(db.JSON, default=list)
    family_history = db.Column(db.JSON, default=list)
    
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
 
