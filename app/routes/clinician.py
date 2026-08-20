from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app
from app import db
from app.models import (User, PatientProfile, ClinicianProfile, ClinicianTimeOff,
                        Appointment, Visit, Prescription, Attendance)
from datetime import datetime, date
from app.utils.patient_search import search_patients_by_fields
from app.utils.audit import record_audit
from app.utils.timezone import clinic_today

clinician_bp = Blueprint('clinician', __name__)


def clinician_can_access_patient(clinician_id, patient_id):
    """Patients become available to a clinician through an appointment."""
    return db.session.query(Appointment.id).filter_by(
        clinician_id=clinician_id, patient_id=patient_id
    ).first() is not None


def get_clinician():
    user_id = session.get('user_id')

    if user_id:
        return ClinicianProfile.query.filter_by(user_id=user_id).first()

    return None


def is_clinician():
    user_id = session.get('user_id')

    if user_id:
        user = User.query.get(user_id)
        return user and user.role == 'clinician'

    return False


def clinician_login_required():
    if not is_clinician():
        return redirect(url_for('auth.clinician_login'))

    return None


# ============================================
# DASHBOARD
# ============================================

@clinician_bp.route('/dashboard')
def dashboard():

    access_check = clinician_login_required()

    if access_check:
        return access_check

    try:
        clinician = get_clinician()
        today = clinic_today()

        appointments = Appointment.query.filter_by(
            clinician_id=clinician.id
        ).filter(
            db.func.date(Appointment.appointment_date) == today
        ).order_by(Appointment.appointment_date.asc()).all()

        total_patients = (db.session.query(Appointment.patient_id)
                          .filter(Appointment.clinician_id == clinician.id)
                          .distinct().count())

        total_appointments = Appointment.query.filter_by(
            clinician_id=clinician.id
        ).count()

        pending_appointments = Appointment.query.filter_by(
            clinician_id=clinician.id,
            status='pending'
        ).count()

        upcoming_time_off = (ClinicianTimeOff.query
                             .filter(ClinicianTimeOff.clinician_id == clinician.id,
                                     ClinicianTimeOff.status == 'approved',
                                     ClinicianTimeOff.end_date >= today)
                             .order_by(ClinicianTimeOff.start_date.asc()).first())

        return render_template(
            'clinician/dashboard.html',
            clinician=clinician,
            appointments=appointments,
            total_patients=total_patients,
            total_appointments=total_appointments,
            pending_appointments=pending_appointments,
            next_appointment=appointments[0] if appointments else None,
            upcoming_time_off=upcoming_time_off,
        )

    except Exception:
        current_app.logger.exception('Unable to load clinician dashboard')

        flash('Error loading dashboard', 'danger')

        return render_template(
            'clinician/dashboard.html',
            clinician=clinician,
            appointments=[]
        )


# ============================================
# PATIENTS LIST
# ============================================

@clinician_bp.route('/patients')
def patients_list():

    access_check = clinician_login_required()

    if access_check:
        return access_check

    clinician = get_clinician()
    if not clinician:
        flash('Your clinician profile is unavailable. Contact an administrator.', 'danger')
        return redirect(url_for('auth.clinician_login'))

    try:
        filters = {key: request.args.get(key, '').strip()
                   for key in ('patient_no', 'name', 'contact', 'date_of_birth')}

        # Avoid SELECT DISTINCT across PostgreSQL JSON columns. The ID subquery
        # returns each authorized patient once on both PostgreSQL and SQLite.
        assigned_patient_ids = db.session.query(Appointment.patient_id).filter(
            Appointment.clinician_id == clinician.id
        )
        query = (PatientProfile.query.join(User)
                 .filter(PatientProfile.id.in_(assigned_patient_ids)))

        patients = search_patients_by_fields(
            query, filters, request.args.get('search', '').strip()
        )

        return render_template(
            'clinician/patients_list.html',
            patients=patients,
            clinician=clinician,
            search_filters=filters,
        )

    except Exception:
        current_app.logger.exception('Patients list failed')

        flash('Error loading patients', 'danger')

        return render_template(
            'clinician/patients_list.html',
            patients=[],
            clinician=clinician
        )


# ============================================
# PATIENT FOLDER
# ============================================

@clinician_bp.route('/patient/<int:patient_id>')
def patient_folder(patient_id):

    access_check = clinician_login_required()

    if access_check:
        return access_check

    try:
        clinician = get_clinician()

        patient = PatientProfile.query.get_or_404(patient_id)
        if not clinician_can_access_patient(clinician.id, patient.id):
            return render_template('errors/403.html'), 403

        visits = Visit.query.filter_by(
            patient_id=patient.id
        ).order_by(
            Visit.visit_date.desc()
        ).all()

        appointments = Appointment.query.filter_by(
            patient_id=patient.id
        ).all()

        return render_template(
            'clinician/patient_folder.html',
            patient=patient,
            visits=visits,
            appointments=appointments,
            clinician=clinician
        )

    except Exception:
        current_app.logger.exception('Unable to load patient folder')

        flash('Error loading patient details', 'danger')

        return redirect(url_for('clinician.patients_list'))


# ============================================
# ADD PATIENT
# ============================================

@clinician_bp.route('/add_patient', methods=['GET', 'POST'])
def add_patient():

    access_check = clinician_login_required()

    if access_check:
        return access_check

    clinician = get_clinician()

    if request.method == 'POST':
        try:
            email = request.form.get('email')
            phone = request.form.get('phone')

            username = (
                email.split('@')[0]
                if email
                else phone
            )

            user = User(
                username=username,
                role='patient',
                full_name=request.form.get('full_name'),
                email=email,
                phone=phone
            )

            user.set_password(
                request.form.get('password', 'Patient@123')
            )

            db.session.add(user)
            db.session.flush()

            patient = PatientProfile(
                user_id=user.id,
                blood_group=request.form.get('blood_group'),
                allergies=request.form.get('allergies'),
                is_child=request.form.get('is_child') == 'on',
                age=int(request.form.get('age'))
                if request.form.get('age')
                else None
            )

            db.session.add(patient)
            db.session.commit()

            flash('Patient added successfully!', 'success')

            return redirect(
                url_for('clinician.patients_list')
            )

        except Exception as e:
            db.session.rollback()

            flash(
                f'Error adding patient: {str(e)}',
                'danger'
            )

            return render_template(
                'clinician/add_patient.html',
                clinician=clinician
            )

    return render_template(
        'clinician/add_patient.html',
        clinician=clinician
    )


# ============================================
# ADD VISIT
# ============================================

@clinician_bp.route(
    '/add_visit/<int:patient_id>',
    methods=['GET', 'POST']
)
def add_visit(patient_id):

    access_check = clinician_login_required()

    if access_check:
        return access_check

    clinician = get_clinician()

    patient = PatientProfile.query.get_or_404(patient_id)
    if not clinician_can_access_patient(clinician.id, patient.id):
        return render_template('errors/403.html'), 403

    appointment_id = request.form.get('appointment_id', type=int) or request.args.get('appointment_id', type=int)
    appointment = db.session.get(Appointment, appointment_id) if appointment_id else None
    if appointment and (
        appointment.patient_id != patient.id
        or appointment.clinician_id != clinician.id
    ):
        return render_template('errors/403.html'), 403
    if appointment and appointment.status not in {'confirmed', 'checked_in', 'completed'}:
        flash('A visit can only be linked to a confirmed or completed appointment.', 'warning')
        return redirect(url_for('clinician.appointments'))
    if appointment and appointment.visits:
        flash('A visit record already exists for this appointment.', 'info')
        return redirect(url_for('clinician.patient_folder', patient_id=patient.id))

    if request.method == 'POST':
        try:
            visit = Visit(
                patient_id=patient.id,
                clinician_id=clinician.id,
                appointment_id=appointment.id if appointment else None,
                visit_date=datetime.utcnow(),
                visit_type=(
                    'Video Consultation'
                    if appointment and appointment.appointment_type == 'video'
                    else 'In-Person'
                ),

                chief_complaint=request.form.get(
                    'chief_complaint'
                ),

                history_of_presenting_illness=request.form.get(
                    'history_of_presenting_illness'
                ),

                past_medical_history=request.form.get(
                    'past_medical_history'
                ),

                family_history=request.form.get(
                    'family_history'
                ),

                physical_examination=request.form.get(
                    'physical_examination'
                ),

                primary_diagnosis=request.form.get(
                    'primary_diagnosis'
                ),

                treatment_plan=request.form.get(
                    'treatment_plan'
                ),

                follow_up_required=request.form.get(
                    'follow_up_required'
                ) == 'on',

                height=float(
                    request.form.get('height')
                )
                if request.form.get('height')
                else None,

                weight=float(
                    request.form.get('weight')
                )
                if request.form.get('weight')
                else None,

                blood_pressure_systolic=int(
                    request.form.get(
                        'blood_pressure_systolic'
                    )
                )
                if request.form.get(
                    'blood_pressure_systolic'
                )
                else None,

                blood_pressure_diastolic=int(
                    request.form.get(
                        'blood_pressure_diastolic'
                    )
                )
                if request.form.get(
                    'blood_pressure_diastolic'
                )
                else None,

                heart_rate=int(
                    request.form.get('heart_rate')
                )
                if request.form.get('heart_rate')
                else None,

                temperature=float(
                    request.form.get('temperature')
                )
                if request.form.get('temperature')
                else None,

                oxygen_saturation=float(
                    request.form.get(
                        'oxygen_saturation'
                    )
                )
                if request.form.get(
                    'oxygen_saturation'
                )
                else None
            )

            if visit.height and visit.weight:
                visit.bmi = (
                    visit.weight /
                    ((visit.height / 100) ** 2)
                )

            db.session.add(visit)
            db.session.flush()

            medication = request.form.get('medication', '').strip()
            if medication:
                prescription = Prescription(
                    visit_id=visit.id,
                    patient_id=patient.id,
                    drug_name=medication,
                    dosage=request.form.get('dosage', '').strip() or None,
                    frequency=request.form.get('frequency', '').strip() or None,
                    duration=request.form.get('duration', '').strip() or None,
                    instructions=request.form.get('instructions', '').strip() or None,
                )
                db.session.add(prescription)
            record_audit('visit_created', 'visit', visit.id,
                         {'patient_id': patient.id,
                          'prescription_created': bool(medication)})
            db.session.commit()

            flash(
                'Visit added successfully!',
                'success'
            )

            return redirect(
                url_for(
                    'clinician.patient_folder',
                    patient_id=patient.id
                )
            )

        except (TypeError, ValueError):
            db.session.rollback()
            flash('Check the clinical measurements and required fields.', 'danger')

            return render_template(
                'clinician/add_visit.html',
                patient=patient,
                clinician=clinician,
                appointment=appointment,
            )
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Unable to create visit')
            flash('Unable to save the visit. Please try again.', 'danger')

            return render_template(
                'clinician/add_visit.html',
                patient=patient,
                clinician=clinician,
                appointment=appointment,
            )

    return render_template(
        'clinician/add_visit.html',
        patient=patient,
        clinician=clinician,
        appointment=appointment,
    )


@clinician_bp.route('/availability', methods=['GET', 'POST'])
def availability():
    access_check = clinician_login_required()
    if access_check:
        return access_check
    clinician = get_clinician()
    if request.method == 'POST':
        days = [day for day in request.form.getlist('working_days') if day in {
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'
        }]
        start = request.form.get('start_time', '')
        end = request.form.get('end_time', '')
        try:
            start_value = datetime.strptime(start, '%H:%M').time()
            end_value = datetime.strptime(end, '%H:%M').time()
        except ValueError:
            flash('Enter valid working hours.', 'danger')
            return render_template('clinician/availability.html', clinician=clinician)
        if not days or start_value >= end_value:
            flash('Select at least one day and ensure the end time is after the start time.', 'danger')
            return render_template('clinician/availability.html', clinician=clinician)
        clinician.working_days = days
        clinician.working_hours = {'start': start, 'end': end}
        clinician.is_available = request.form.get('is_available') == 'on'
        try:
            record_audit('availability_updated', 'clinician', clinician.id,
                         {'working_days': days, 'is_available': clinician.is_available})
            db.session.commit()
            flash('Availability updated.', 'success')
            return redirect(url_for('clinician.availability'))
        except Exception:
            db.session.rollback()
            raise
    return render_template('clinician/availability.html', clinician=clinician)


@clinician_bp.route('/time-off', methods=['GET', 'POST'])
def time_off():
    access_check = clinician_login_required()
    if access_check:
        return access_check
    clinician = get_clinician()
    if request.method == 'POST':
        try:
            start_date = datetime.strptime(request.form.get('start_date', ''), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form.get('end_date', ''), '%Y-%m-%d').date()
            full_day = request.form.get('full_day') == 'on'
            start_time = end_time = None
            if not full_day:
                start_time = datetime.strptime(request.form.get('start_time', ''), '%H:%M').time()
                end_time = datetime.strptime(request.form.get('end_time', ''), '%H:%M').time()
        except ValueError:
            flash('Enter valid time-off dates and times.', 'danger')
            return redirect(url_for('clinician.time_off'))
        if start_date < clinic_today():
            flash('Time off cannot start in the past.', 'danger')
            return redirect(url_for('clinician.time_off'))
        if end_date < start_date or (not full_day and start_time >= end_time):
            flash('The time-off end must be after its start.', 'danger')
            return redirect(url_for('clinician.time_off'))
        existing = ClinicianTimeOff.query.filter(
            ClinicianTimeOff.clinician_id == clinician.id,
            ClinicianTimeOff.status == 'approved',
            ClinicianTimeOff.start_date <= end_date,
            ClinicianTimeOff.end_date >= start_date,
        ).first()
        if existing:
            flash('This request overlaps existing approved time off.', 'danger')
            return redirect(url_for('clinician.time_off'))
        entry = ClinicianTimeOff(
            clinician_id=clinician.id,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            full_day=full_day,
            reason=request.form.get('reason', '').strip() or None,
            status='approved',
        )
        try:
            db.session.add(entry)
            db.session.flush()
            record_audit('time_off_created', 'clinician_time_off', entry.id,
                         {'full_day': full_day})
            db.session.commit()
            flash('Time off added and blocked from appointment booking.', 'success')
        except Exception:
            db.session.rollback()
            raise
        return redirect(url_for('clinician.time_off'))
    entries = ClinicianTimeOff.query.filter_by(clinician_id=clinician.id).order_by(
        ClinicianTimeOff.start_date.desc()
    ).all()
    return render_template('clinician/time_off.html', clinician=clinician, entries=entries)


@clinician_bp.route('/time-off/<int:entry_id>/cancel', methods=['POST'])
def cancel_time_off(entry_id):
    access_check = clinician_login_required()
    if access_check:
        return access_check
    clinician = get_clinician()
    entry = ClinicianTimeOff.query.get_or_404(entry_id)
    if entry.clinician_id != clinician.id:
        return jsonify({'error': 'Unauthorized'}), 403
    entry.status = 'cancelled'
    try:
        record_audit('time_off_cancelled', 'clinician_time_off', entry.id)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    flash('Time off cancelled.', 'success')
    return redirect(url_for('clinician.time_off'))


# ============================================
# APPOINTMENTS
# ============================================

@clinician_bp.route('/appointments')
def appointments():

    access_check = clinician_login_required()

    if access_check:
        return access_check

    try:
        clinician = get_clinician()

        status = request.args.get(
            'status',
            'all'
        )
        appointment_type = request.args.get('type', 'all')

        date_filter = request.args.get(
            'date',
            ''
        )

        query = Appointment.query.filter_by(
            clinician_id=clinician.id
        )

        if status != 'all':
            query = query.filter_by(
                status=status
            )

        if appointment_type in {'in_person', 'video'}:
            query = query.filter_by(appointment_type=appointment_type)
        else:
            appointment_type = 'all'

        if date_filter:
            try:
                filter_date = datetime.strptime(
                    date_filter,
                    '%Y-%m-%d'
                ).date()

                query = query.filter(
                    db.func.date(
                        Appointment.appointment_date
                    ) == filter_date
                )

            except ValueError:
                pass

        appointments = query.order_by(
            Appointment.appointment_date.desc()
        ).all()

        return render_template(
            'clinician/appointments.html',
            appointments=appointments,
            clinician=clinician,
            status_filter=status,
            type_filter=appointment_type,
            date_filter=date_filter
        )

    except Exception:
        current_app.logger.exception('Unable to load clinician appointments')

        flash(
            'Error loading appointments',
            'danger'
        )

        return render_template(
            'clinician/appointments.html',
            appointments=[],
            clinician=clinician
        )


# ============================================
# UPDATE APPOINTMENT STATUS
# ============================================

@clinician_bp.route(
    '/appointment/<int:appointment_id>/update',
    methods=['POST']
)
def update_appointment(appointment_id):

    if not is_clinician():
        return jsonify({
            'error': 'Unauthorized'
        }), 401

    try:
        clinician = get_clinician()

        appointment = Appointment.query.get_or_404(
            appointment_id
        )

        if appointment.clinician_id != clinician.id:
            return jsonify({
                'error': 'Unauthorized'
            }), 403

        data = request.get_json(silent=True) or {}

        new_status = data.get('status')

        old_status = appointment.status
        allowed_transitions = {
            'pending': {'confirmed', 'rejected', 'cancelled'},
            'confirmed': {'checked_in', 'completed', 'cancelled', 'no_show'},
            'checked_in': {'completed'},
            'completed': set(),
            'cancelled': set(),
            'rejected': set(),
            'no_show': set(),
        }

        if new_status != old_status and new_status not in allowed_transitions.get(old_status, set()):
            return jsonify({
                'error': f'Cannot change a {old_status.replace("_", " ")} appointment to {str(new_status).replace("_", " ")}.'
            }), 409

        if new_status == 'completed' and not appointment.visits:
            return jsonify({
                'error': 'Record the visit before marking this appointment completed.'
            }), 409

        appointment.status = new_status
        if new_status == 'completed' and appointment.appointment_type == 'video':
            if appointment.video_session:
                appointment.video_session.status = 'ended'
                appointment.video_session.ended_at = datetime.utcnow()
        record_audit('appointment_status_updated', 'appointment', appointment.id,
                     {'from': old_status, 'to': new_status})
        db.session.commit()

        return jsonify({
            'success': True,
            'status': appointment.status
        })

    except Exception:
        db.session.rollback()
        current_app.logger.exception('Unable to update appointment status')
        return jsonify({
            'error': 'Unable to update appointment status'
        }), 500


# ============================================
# TOGGLE ATTENDANCE
# ============================================

@clinician_bp.route(
    '/toggle_attendance',
    methods=['POST']
)
def toggle_attendance():

    if not is_clinician():
        return jsonify({
            'error': 'Unauthorized'
        }), 401

    try:
        clinician = get_clinician()

        attendance = Attendance.query.filter_by(
            clinician_id=clinician.id
        ).first()

        if not attendance:
            attendance = Attendance(
                clinician_id=clinician.id,
                status='offline'
            )

            db.session.add(attendance)

        attendance.status = (
            'online'
            if attendance.status == 'offline'
            else 'offline'
        )

        attendance.last_updated = datetime.utcnow()

        record_audit(
            'daily_attendance_updated', 'clinician', clinician.id,
            {'status': 'present' if attendance.status == 'online' else 'away'}
        )

        db.session.commit()

        return jsonify({
            'status': attendance.status
        })

    except Exception:
        db.session.rollback()
        current_app.logger.exception('Unable to update clinician attendance')
        return jsonify({
            'error': 'Unable to update daily attendance.'
        }), 500


# ============================================
# PATIENT SEARCH
# ============================================

@clinician_bp.route(
    '/search_patients',
    methods=['GET']
)
def search_patients():

    if not is_clinician():
        return jsonify([]), 401

    try:
        term = request.args.get(
            'term',
            ''
        ).strip()

        normalized = term.casefold()
        patients = [patient for patient in PatientProfile.query.join(User).all()
                    if patient.user and normalized in ' '.join([
                        patient.user.full_name or '', patient.user.phone or ''
                    ]).casefold()][:10]

        return jsonify([
            {
                'id': patient.id,
                'name': (
                    patient.user.full_name
                    if patient.user
                    else 'Unknown'
                ),
                'phone': (
                    patient.user.phone
                    if patient.user
                    else ''
                )
            }
            for patient in patients
        ])

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500
