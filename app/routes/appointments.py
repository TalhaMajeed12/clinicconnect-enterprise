from flask import Blueprint, render_template, session, request, redirect, url_for, flash
from app import db
from app.models import ClinicianProfile, ClinicianTimeOff, Appointment, PatientProfile, User
from app.utils.translations import t
from datetime import datetime

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

        clinician = ClinicianProfile.query.get(clinician_id)
        if not clinician or not clinician.user or not clinician.user.is_active or not clinician.is_available:
            flash(t('The selected clinician is not available.'), 'danger')
            return redirect(url_for('appointments.book'))
        if appointment_date <= datetime.now():
            flash(t('Appointments must be booked in the future.'), 'danger')
            return redirect(url_for('appointments.book'))

        working_days = [str(day).lower() for day in (clinician.working_days or [])]
        hours = clinician.working_hours or {}
        try:
            start = datetime.strptime(hours.get('start', ''), '%H:%M').time()
            end = datetime.strptime(hours.get('end', ''), '%H:%M').time()
        except (TypeError, ValueError):
            flash(t('The clinician schedule is not configured correctly.'), 'danger')
            return redirect(url_for('appointments.book'))
        if appointment_date.strftime('%A').lower() not in working_days or not (start <= appointment_date.time() < end):
            flash(t('Please choose a time within the clinician working hours.'), 'danger')
            return redirect(url_for('appointments.book'))

        duration = clinician.appointment_duration or 30
        leave_entries = ClinicianTimeOff.query.filter(
            ClinicianTimeOff.clinician_id == clinician.id,
            ClinicianTimeOff.status == 'approved',
            ClinicianTimeOff.start_date <= appointment_date.date(),
            ClinicianTimeOff.end_date >= appointment_date.date(),
        ).all()
        if any(entry.blocks(appointment_date, duration) for entry in leave_entries):
            flash(t('The clinician is on approved time off at that time.'), 'danger')
            return redirect(url_for('appointments.book'))

        requested_end = appointment_date.timestamp() + duration * 60
        conflicts = Appointment.query.filter(
            Appointment.clinician_id == clinician.id,
            Appointment.status.notin_(['cancelled', 'completed', 'no_show'])
        ).all()
        if any(
            appointment_date.timestamp() < existing.appointment_date.timestamp() + (existing.duration or 30) * 60
            and requested_end > existing.appointment_date.timestamp()
            for existing in conflicts
        ):
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
