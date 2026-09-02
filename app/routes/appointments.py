from flask import (Blueprint, current_app, render_template, session, request,
                   redirect, url_for, flash, jsonify)
from app import db
from app.extensions import limiter
from app.models import (ClinicianProfile, Appointment, PatientProfile, User,
                        DoctorReview, GuestAppointmentRequest)
from app.utils.translations import t
from datetime import datetime, timedelta
from secrets import token_hex
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from app.utils.appointment_slots import available_slots, is_available_slot
from app.utils.audit import record_audit
from app.utils.timezone import clinic_now, clinic_today

appointments_bp = Blueprint('appointments', __name__)


def _active_clinicians(specialty=None):
    query = (ClinicianProfile.query.join(User, ClinicianProfile.user_id == User.id)
             .filter(ClinicianProfile.is_available.is_(True), User.is_active.is_(True),
                     User.role == 'clinician'))
    if specialty:
        query = query.filter(func.lower(ClinicianProfile.specialty) == specialty.casefold())
    return query.order_by(ClinicianProfile.average_rating.desc(), User.username.asc()).all()


def _directory_clinicians(specialty=None):
    """Active clinician accounts, including profiles awaiting booking setup."""
    query = (ClinicianProfile.query.join(User, ClinicianProfile.user_id == User.id)
             .filter(User.is_active.is_(True), User.role == 'clinician'))
    if specialty:
        query = query.filter(func.lower(ClinicianProfile.specialty) == specialty.casefold())
    return query.order_by(
        ClinicianProfile.is_available.desc(),
        ClinicianProfile.average_rating.desc(), User.username.asc()
    ).all()


def _next_slots(clinician, start_date, days=14):
    result = []
    for offset in range(days):
        for slot in available_slots(clinician, start_date + timedelta(days=offset)):
            result.append(slot)
    return result

@appointments_bp.route('/book', methods=['GET', 'POST'])
def book():
    patient = PatientProfile.query.filter_by(user_id=session.get('user_id')).first()
    if not patient:
        flash(t('Please login first'), 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        appointment_type = request.form.get('appointment_type', 'in_person')
        if appointment_type not in {'in_person', 'video'}:
            flash(t('Choose a valid appointment type.'), 'danger')
            return redirect(url_for('appointments.book'))
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
        if appointment_date <= clinic_now():
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
            duration=duration,
            appointment_type=appointment_type,
        )
        db.session.add(appointment)
        db.session.flush()
        record_audit('appointment_requested', 'appointment', appointment.id,
                     {'clinician_id': clinician.id})
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(t('That time was just reserved by another patient. Choose another slot.'), 'warning')
            return redirect(url_for('appointments.book'))

        flash(t('Appointment requested. Complete the demo deposit to confirm it.'), 'success')
        return redirect(url_for('payment.checkout', appointment_id=appointment.id))
    
    clinicians = _directory_clinicians(request.args.get('specialty', '').strip())
    specialties = [row[0] for row in db.session.query(ClinicianProfile.specialty)
                    .join(User).filter(User.is_active.is_(True),
                                       User.role == 'clinician').distinct().order_by(ClinicianProfile.specialty)]
    return render_template('patient/book_appointment.html', clinicians=clinicians,
                           specialties=specialties,
                           selected_specialty=request.args.get('specialty', '').strip())


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
    if target_date < clinic_today() or target_date > (clinic_today() + timedelta(days=60)):
        return jsonify({'error': 'Date must be within the next 60 days'}), 400
    items = available_slots(clinician, target_date)
    return jsonify({
        'duration': clinician.appointment_duration or 30,
        'slots': [{'value': item.strftime('%Y-%m-%dT%H:%M'),
                   'label': item.strftime('%I:%M %p')} for item in items],
    })


@appointments_bp.get('/discovery')
def discovery():
    """Public, non-clinical availability used by the guided assistant."""
    specialty = request.args.get('specialty', '').strip()
    date_value = request.args.get('date', '').strip()
    try:
        start_date = datetime.strptime(date_value, '%Y-%m-%d').date() if date_value else clinic_today()
    except ValueError:
        return jsonify({'error': 'Choose a valid date'}), 400
    if start_date < clinic_today() or start_date > clinic_today() + timedelta(days=60):
        return jsonify({'error': 'Date must be within the next 60 days'}), 400

    clinicians = _active_clinicians(specialty)
    specialties = sorted({item.specialty for item in _active_clinicians()})
    doctors = []
    for clinician in clinicians:
        slots = _next_slots(clinician, start_date)
        if slots:
            doctors.append({
                'id': clinician.id,
                'name': clinician.user.full_name or clinician.user.username,
                'specialty': clinician.specialty,
                'rating': round(float(clinician.average_rating or 0), 1),
                'review_count': int(clinician.total_reviews or 0),
                'fee': float(clinician.consultation_fee or 0),
                'slots': [{'value': slot.strftime('%Y-%m-%dT%H:%M'),
                           'label': slot.strftime('%a, %d %b · %I:%M %p')} for slot in slots],
            })
    return jsonify({'specialties': specialties, 'doctors': doctors,
                    'clinic_phone': current_app.config['CLINIC_PHONE']})


@appointments_bp.post('/request')
@limiter.limit('5 per hour')
def guest_request():
    if session.get('user_id'):
        return jsonify({'error': 'Please use your patient portal to book.'}), 400
    data = request.get_json(silent=True) or {}
    appointment_type = str(data.get('appointment_type', 'in_person')).strip()
    if appointment_type not in {'in_person', 'video'}:
        return jsonify({'error': 'Choose an in-person or video appointment.'}), 400
    required = ('full_name', 'phone', 'date_of_birth', 'specialty', 'clinician_id', 'preferred_at')
    if any(not str(data.get(key, '')).strip() for key in required):
        return jsonify({'error': 'Complete all required booking details.'}), 400
    try:
        dob = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
        preferred_at = datetime.strptime(data['preferred_at'], '%Y-%m-%dT%H:%M')
        clinician = db.session.get(ClinicianProfile, int(data['clinician_id']))
    except (TypeError, ValueError):
        return jsonify({'error': 'Check the date, doctor, and time.'}), 400
    if dob >= clinic_today() or not clinician or clinician.specialty != data['specialty']:
        return jsonify({'error': 'Check the personal details and specialty.'}), 400
    if not is_available_slot(clinician, preferred_at):
        return jsonify({'error': 'That slot is no longer available. Choose another option.'}), 409
    item = GuestAppointmentRequest(
        reference=f'CCR-{token_hex(4).upper()}', date_of_birth=dob,
        specialty=clinician.specialty, clinician_id=clinician.id,
        preferred_at=preferred_at, status='new',
        appointment_type=appointment_type
    )
    item.full_name = str(data['full_name']).strip()[:150]
    item.phone = str(data['phone']).strip()[:40]
    item.email = str(data.get('email', '')).strip()[:254] or None
    item.reason = str(data.get('reason', '')).strip()[:1000] or None
    db.session.add(item)
    db.session.flush()
    record_audit('guest_appointment_requested', 'appointment_request', item.id,
                 {'clinician_id': clinician.id})
    db.session.commit()
    return jsonify({
        'success': True, 'reference': item.reference,
        'clinic_phone': current_app.config['CLINIC_PHONE'],
        'message': ('Your request is visible to clinic staff. Call the clinic and quote '
                    f'{item.reference} so staff can verify your details and create your portal.'),
    }), 201


@appointments_bp.post('/<int:appointment_id>/review')
def review(appointment_id):
    patient = PatientProfile.query.filter_by(user_id=session.get('user_id')).first()
    appointment = db.session.get(Appointment, appointment_id)
    if not patient or not appointment or appointment.patient_id != patient.id:
        return redirect(url_for('auth.login'))
    if appointment.status != 'completed' or appointment.review:
        flash('Only completed, unreviewed appointments can be rated.', 'warning')
        return redirect(url_for('patient.appointments'))
    rating = request.form.get('rating', type=int)
    if rating not in range(1, 6):
        flash('Choose a rating from 1 to 5.', 'warning')
        return redirect(url_for('patient.appointments'))
    db.session.add(DoctorReview(
        appointment_id=appointment.id, patient_id=patient.id,
        clinician_id=appointment.clinician_id, rating=rating,
        comment=request.form.get('comment', '').strip()[:1000] or None,
    ))
    db.session.flush()
    aggregate = db.session.query(func.avg(DoctorReview.rating), func.count(DoctorReview.id)).filter_by(
        clinician_id=appointment.clinician_id).one()
    appointment.clinician.average_rating = float(aggregate[0] or 0)
    appointment.clinician.total_reviews = int(aggregate[1] or 0)
    record_audit('doctor_review_created', 'appointment', appointment.id,
                 {'rating': rating})
    db.session.commit()
    flash('Thank you for reviewing your clinician.', 'success')
    return redirect(url_for('patient.appointments'))
