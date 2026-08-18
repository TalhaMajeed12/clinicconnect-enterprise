# VISIT
# ============================================
from datetime import datetime

from app.extensions import db

class Visit(db.Model):
    __tablename__ = 'visits'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient_profiles.id'))
    clinician_id = db.Column(db.Integer, db.ForeignKey('clinician_profiles.id'))
    appointment_id = db.Column(
        db.Integer, db.ForeignKey('appointments.id'), nullable=True, unique=True
    )
    
    visit_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    visit_type = db.Column(db.String(50))
    
    chief_complaint = db.Column(db.Text)
    history_of_presenting_illness = db.Column(db.Text)
    past_medical_history = db.Column(db.Text)
    family_history = db.Column(db.Text)
    
    physical_examination = db.Column(db.Text)
    
    height = db.Column(db.Float)
    weight = db.Column(db.Float)
    bmi = db.Column(db.Float)
    blood_pressure_systolic = db.Column(db.Integer)
    blood_pressure_diastolic = db.Column(db.Integer)
    heart_rate = db.Column(db.Integer)
    temperature = db.Column(db.Float)
    oxygen_saturation = db.Column(db.Float)
    
    primary_diagnosis = db.Column(db.Text)
    secondary_diagnosis = db.Column(db.JSON, default=list)
    
    treatment_plan = db.Column(db.Text)
    medications_prescribed = db.Column(db.JSON, default=list)
    referrals = db.Column(db.JSON, default=list)
    
    follow_up_required = db.Column(db.Boolean, default=False)
    follow_up_date = db.Column(db.DateTime)
    
    attachments = db.Column(db.JSON, default=list)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship('PatientProfile', backref='visits')
    clinician = db.relationship('ClinicianProfile', backref='visits')
    appointment = db.relationship('Appointment', backref='visits')

    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'clinician_id': self.clinician_id,
            'appointment_id': self.appointment_id,
            'visit_date': self.visit_date.isoformat() if self.visit_date else None,
            'chief_complaint': self.chief_complaint,
            'primary_diagnosis': self.primary_diagnosis,
            'treatment_plan': self.treatment_plan,
        }


# ============================================
# PRESCRIPTION
# ============================================

from datetime import datetime

from app.extensions import db

class Prescription(db.Model):
    __tablename__ = 'prescriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'))
    patient_id = db.Column(db.Integer, db.ForeignKey('patient_profiles.id'))
    
    drug_name = db.Column(db.String(100), nullable=False)
    generic_name = db.Column(db.String(100))
    strength = db.Column(db.String(50))
    dosage = db.Column(db.String(50))
    frequency = db.Column(db.String(100))
    duration = db.Column(db.String(50))
    quantity = db.Column(db.Integer)
    refills = db.Column(db.Integer)
    
    instructions = db.Column(db.Text)
    special_instructions = db.Column(db.Text)
    
    is_active = db.Column(db.Boolean, default=True)
    is_dispensed = db.Column(db.Boolean, default=False)
    dispensed_date = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    visit = db.relationship('Visit', backref='prescriptions')
    patient = db.relationship('PatientProfile', backref='prescriptions')
 
