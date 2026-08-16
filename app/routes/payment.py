from flask import Blueprint, render_template, session, request, redirect, url_for, flash
from app import db
from app.models import Appointment, Payment, PatientProfile, AuditLog
from app.utils.translations import t
from datetime import datetime
from decimal import Decimal
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
    
    total = appointment.clinician.consultation_fee if appointment.clinician else Decimal('0.00')
    return render_template('payment/checkout.html',
        appointment=appointment,
        deposit=total * Decimal('0.25'),
        total=total
    )

@payment_bp.route('/process', methods=['POST'])
def process():
    patient = PatientProfile.query.filter_by(user_id=session.get('user_id')).first()
    if not patient:
        return redirect(url_for('auth.login'))
    
    appointment_id = request.form.get('appointment_id')
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.patient_id != patient.id:
        flash(t('Unauthorized'), 'danger')
        return redirect(url_for('patient.dashboard'))
    if appointment.status not in ('pending',):
        flash(t('This appointment is not awaiting payment.'), 'warning')
        return redirect(url_for('patient.appointments'))
    if Payment.query.filter_by(appointment_id=appointment.id, payment_status='completed').first():
        flash(t('Payment has already been recorded.'), 'warning')
        return redirect(url_for('patient.appointments'))
    
    # Simulate payment processing
    transaction_id = f"TXN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    
    fee = appointment.clinician.consultation_fee if appointment.clinician else Decimal('0.00')
    deposit = fee * Decimal('0.25')
    try:
        payment = Payment(
            appointment_id=appointment.id,
            patient_id=patient.id,
            amount=deposit,
            total_amount=fee,
            payment_method='demo',
            transaction_id=transaction_id,
            payment_status='completed'
        )
        db.session.add(payment)
        appointment.status = 'confirmed'
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    
    flash(t('Payment successful! Appointment confirmed.'), 'success')
    return redirect(url_for('payment.success', appointment_id=appointment.id))

@payment_bp.route('/success/<int:appointment_id>')
def success(appointment_id):
    patient = PatientProfile.query.filter_by(user_id=session.get('user_id')).first()
    appointment = Appointment.query.get_or_404(appointment_id)
    if not patient or appointment.patient_id != patient.id:
        flash(t('Unauthorized'), 'danger')
        return redirect(url_for('auth.login'))
    return render_template('payment/success.html', appointment=appointment)
