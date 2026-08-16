# PAYMENT
# ============================================
from datetime import datetime

from app.extensions import db

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
    insurance_claim = db.Column(db.JSON, default=dict)
    
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    appointment = db.relationship('Appointment', backref='payments')
    patient = db.relationship('PatientProfile', backref='payments')

    def to_dict(self):
        return {
            'id': self.id,
            'appointment_id': self.appointment_id,
            'amount': float(self.amount),
            'total_amount': float(self.total_amount) if self.total_amount is not None else None,
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
        }
 
