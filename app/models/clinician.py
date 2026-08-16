# CLINICIAN PROFILE
# ============================================
from app.extensions import db


class ClinicianProfile(db.Model):
    __tablename__ = "clinician_profiles"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    
    specialty = db.Column(db.String(100), nullable=False)
    license_number = db.Column(db.String(50), unique=True)
    years_experience = db.Column(db.Integer, default=0)
    qualifications = db.Column(db.JSON, default=list)
    certifications = db.Column(db.JSON, default=list)
    bio = db.Column(db.Text)
    
    consultation_fee = db.Column(db.Numeric(10,2), default=2000)
    working_days = db.Column(db.JSON, default=lambda: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'])
    working_hours = db.Column(db.JSON, default=lambda: {'start': '09:00', 'end': '17:00'})
    
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
