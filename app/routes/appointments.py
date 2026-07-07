from flask import Blueprint, render_template, session, request, redirect, url_for, flash
from app import db
from app.models import ClinicianProfile, Appointment, PatientProfile
from app.utils.translations import t
from datetime import datetime, timedelta

appointments_bp = Blueprint('appointments', __name__)

@appointments_bp.route('/book', methods=['GET', 'POST'])
def book():
    patient = PatientProfile.query.filter_by(user_id=session.get('user_id')).first()
    if not patient:
        flash(t('Please login first'), 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        clinician_id = request.form.get('clinician_id')
        appointment_date = datetime.strptime(
            request.form.get('appointment_date').replace('T', ' '),
            '%Y-%m-%d %H:%M'
        )
        
        appointment = Appointment(
            patient_id=patient.id,
            clinician_id=clinician_id,
            appointment_date=appointment_date,
            reason=request.form.get('reason'),
            symptoms=request.form.get('symptoms'),
            status='pending'
        )
        db.session.add(appointment)
        db.session.commit()
        
        flash(t('Appointment booked! Please complete payment.'), 'success')
        return redirect(url_for('payment.checkout', appointment_id=appointment.id))
    
    clinicians = ClinicianProfile.query.filter_by(is_available=True).all()
    return render_template('patient/book_appointment.html', clinicians=clinicians) 
