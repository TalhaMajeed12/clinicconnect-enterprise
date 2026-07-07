import random
import string
from datetime import datetime, timedelta
from app import db
from app.models import OtpVerification

def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

def create_otp(phone, patient_id=None, purpose='registration', expiry_minutes=5):
    """Create and store a new OTP"""
    # Delete any old unverified OTPs for this phone and purpose
    OtpVerification.query.filter_by(
        phone=phone, 
        purpose=purpose,
        is_verified=False
    ).delete()
    
    otp = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
    
    otp_record = OtpVerification(
        phone=phone,
        patient_id=patient_id,
        otp_code=otp,
        purpose=purpose,
        expires_at=expires_at,
        is_verified=False,
        attempts=0
    )
    db.session.add(otp_record)
    db.session.commit()
    return otp_record

def verify_otp(phone, otp_code, purpose=None):
    """Verify if the OTP is valid and not expired"""
    query = OtpVerification.query.filter_by(
        phone=phone, 
        otp_code=otp_code, 
        is_verified=False
    )
    
    if purpose:
        query = query.filter_by(purpose=purpose)
    
    record = query.order_by(OtpVerification.created_at.desc()).first()
    
    if record:
        if record.attempts >= 3:
            db.session.delete(record)
            db.session.commit()
            return False
        
        if record.expires_at > datetime.utcnow():
            record.is_verified = True
            db.session.commit()
            return True
        else:
            db.session.delete(record)
            db.session.commit()
    
    if record:
        record.attempts += 1
        db.session.commit()
    
    return False

def resend_otp(phone, purpose='registration'):
    from app.models import Patient
    patient = Patient.query.filter_by(phone=phone).first()
    
    OtpVerification.query.filter_by(
        phone=phone, 
        purpose=purpose,
        is_verified=False
    ).delete()
    
    otp_record = create_otp(phone, patient.id if patient else None, purpose)
    return otp_record