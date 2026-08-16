# SYSTEM SETTING
# ============================================
from datetime import datetime

from app.extensions import db

class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    is_encrypted = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
# ATTENDANCE
# ============================================
from datetime import datetime

from app.extensions import db

class Attendance(db.Model):
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    clinician_id = db.Column(db.Integer, db.ForeignKey('clinician_profiles.id'), unique=True)
    status = db.Column(db.String(20), default='offline')
    check_in_time = db.Column(db.DateTime)
    check_out_time = db.Column(db.DateTime)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    clinician = db.relationship('ClinicianProfile', backref=db.backref('attendance', uselist=False))
 
