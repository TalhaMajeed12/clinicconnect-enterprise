from flask import Blueprint, render_template, session, request, redirect, url_for, flash
from app import db
from app.models import Appointment, Payment, PatientProfile, AuditLog
from app.utils.translations import t
from datetime import datetime
import uuid

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/checkout/<int:appointment_id>')
def checkout(appointment_id):
    patient = PatientProfile.query.filter_by(user_id=session.get('user_id')).first()
    if not patient:
        flash(t('Please login first'), 'danger')
        return redirect(url_for('auth.login'))
    
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.patient_id != patient.id:
        flash(t('Unauthorized'), 'danger')
        return redirect(url_for('patient.dashboard'))
    
    return render_template('payment/checkout.html',
        appointment=appointment,
        deposit=500,
        total=2000
    )

@payment_bp.route('/process', methods=['POST'])
def process():
    patient = PatientProfile.query.filter_by(user_id=session.get('user_id')).first()
    if not patient:
        return redirect(url_for('auth.login'))
    
    appointment_id = request.form.get('appointment_id')
    appointment = Appointment.query.get_or_404(appointment_id)
    
    # Simulate payment processing
    transaction_id = f"TXN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    
    payment = Payment(
        appointment_id=appointment.id,
        patient_id=patient.id,
        amount=500,
        payment_method='card',
        transaction_id=transaction_id,
        payment_status='completed'
    )
    db.session.add(payment)
    
    appointment.status = 'confirmed'
    db.session.commit()
    
    flash(t('Payment successful! Appointment confirmed.'), 'success')
    return redirect(url_for('payment.success', appointment_id=appointment.id))

@payment_bp.route('/success/<int:appointment_id>')
def success(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    return render_template('payment/success.html', appointment=appointment)