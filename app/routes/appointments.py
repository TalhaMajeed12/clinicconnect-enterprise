from flask import Blueprint, render_template, session, request, redirect, url_for, flash, jsonify
from app import db
from app.models import ClinicianProfile, Appointment, PatientProfile, User
from app.utils.translations import t
from datetime import datetime, timedelta
from app.utils.appointment_slots import available_slots, is_available_slot

appointments_bp = Blueprint('appointments', __name__)

@appointments_bp.route('/book', methods=['GET', 'POST'])
def book():
    patient = PatientProfile.query.filter_by(user_id=session.get('user_id')).first()
    if not patient:
        flash(t('Please login first'), 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        try:
            clinician_id = int(request.form.get('clinician_id', ''))
            appointment_date = datetime.strptime(
                request.form.get('appointment_date', '').replace('T', ' '),
                '%Y-%m-%d %H:%M'
            )
        except (TypeError, ValueError):
            flash(t('Please select a valid clinician, date, and time.'), 'danger')
            return redirect(url_for('appointments.book'))

        # Serialize bookings for this clinician so two patients cannot claim the
        # same slot between availability validation and commit on PostgreSQL.
        clinician = (ClinicianProfile.query.filter_by(id=clinician_id)
                     .with_for_update().first())
        if not clinician or not clinician.user or not clinician.user.is_active or not clinician.is_available:
            flash(t('The selected clinician is not available.'), 'danger')
            return redirect(url_for('appointments.book'))
        if appointment_date <= datetime.now():
            flash(t('Appointments must be booked in the future.'), 'danger')
            return redirect(url_for('appointments.book'))

        duration = clinician.appointment_duration or 30
        if not is_available_slot(clinician, appointment_date):
            flash(t('That time is no longer available.'), 'danger')
            return redirect(url_for('appointments.book'))
        
        appointment = Appointment(
            patient_id=patient.id,
            clinician_id=clinician_id,
            appointment_date=appointment_date,
            reason=request.form.get('reason'),
            symptoms=request.form.get('symptoms'),
            status='pending',
            duration=duration
        )
        db.session.add(appointment)
        db.session.commit()
        
        flash(t('Appointment booked! Please complete payment.'), 'success')
        return redirect(url_for('payment.checkout', appointment_id=appointment.id))
    
    clinicians = (ClinicianProfile.query.join(User, ClinicianProfile.user_id == User.id)
                   .filter(ClinicianProfile.is_available.is_(True), User.is_active.is_(True), User.role == 'clinician')
                   .all())
    return render_template('patient/book_appointment.html', clinicians=clinicians)


@appointments_bp.get('/slots')
def slots():
    patient = PatientProfile.query.filter_by(user_id=session.get('user_id')).first()
    if not patient:
        return jsonify({'error': 'Authentication required'}), 401
    clinician_id = request.args.get('clinician_id', type=int)
    date_value = request.args.get('date', '').strip()
    try:
        target_date = datetime.strptime(date_value, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Choose a valid date'}), 400
    clinician = db.session.get(ClinicianProfile, clinician_id)
    if not clinician or not clinician.user or not clinician.user.is_active or not clinician.is_available:
        return jsonify({'error': 'Clinician unavailable'}), 404
    if target_date < datetime.now().date() or target_date > (datetime.now().date() + timedelta(days=60)):
        return jsonify({'error': 'Date must be within the next 60 days'}), 400
    items = available_slots(clinician, target_date)
    return jsonify({
        'duration': clinician.appointment_duration or 30,
        'slots': [{'value': item.strftime('%Y-%m-%dT%H:%M'),
                   'label': item.strftime('%I:%M %p')} for item in items],
    })
