from flask import (Blueprint, current_app, render_template, request, redirect,
                   url_for, flash, session, jsonify)
from app import db
from app.models import (User, PatientProfile, ClinicianProfile, Appointment, Payment,
                        AuditLog, GuestAppointmentRequest, ClinicianTimeOff)
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import func
from app.utils.patient_search import search_patients_by_fields
from app.utils.appointment_slots import is_available_slot
from app.utils.timezone import clinic_today

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/intake-requests')
def intake_requests():
    if not is_admin():
        return redirect(url_for('auth.admin_login'))
    status = request.args.get('status', 'new')
    query = GuestAppointmentRequest.query
    if status != 'all':
        query = query.filter_by(status=status)
    items = query.order_by(GuestAppointmentRequest.created_at.desc()).all()
    return render_template('admin/intake_requests.html', items=items, status=status)


@admin_bp.post('/intake-requests/<int:request_id>/convert')
def convert_intake_request(request_id):
    if not is_admin():
        return redirect(url_for('auth.admin_login'))
    item = db.session.get(GuestAppointmentRequest, request_id)
    if not item:
        return render_template('errors/404.html'), 404
    if item.status == 'converted':
        flash('This request has already been converted.', 'warning')
        return redirect(url_for('admin.intake_requests'))
    username = request.form.get('username', '').strip()
    temporary_password = request.form.get('temporary_password', '')
    if len(username) < 4 or len(temporary_password) < 10:
        flash('Use a username of at least 4 characters and temporary password of at least 10.', 'warning')
        return redirect(url_for('admin.intake_requests'))
    if User.query.filter(func.lower(User.username) == username.casefold()).first():
        flash('That username is already in use.', 'warning')
        return redirect(url_for('admin.intake_requests'))
    if User.find_by_identifier(item.email) or User.find_by_identifier(item.phone):
        flash('A patient account already uses this email or phone. Link the request manually.', 'warning')
        return redirect(url_for('admin.intake_requests'))
    clinician = item.clinician
    if not clinician or not is_available_slot(clinician, item.preferred_at):
        flash('The requested slot is no longer available. Contact the patient with alternatives.', 'warning')
        return redirect(url_for('admin.intake_requests'))
    user = User(
        username=username, role='patient', full_name=item.full_name,
        email=item.email or f'{username}@pending.clinicconnect.local',
        phone=item.phone, date_of_birth=item.date_of_birth,
        is_active=True, is_verified=True,
    )
    user.set_password(temporary_password)
    db.session.add(user)
    db.session.flush()
    patient = PatientProfile(user_id=user.id)
    db.session.add(patient)
    db.session.flush()
    appointment = Appointment(
        patient_id=patient.id, clinician_id=clinician.id,
        appointment_date=item.preferred_at,
        duration=clinician.appointment_duration or 30,
        status='pending', reason=item.reason,
        appointment_type=item.appointment_type,
    )
    db.session.add(appointment)
    db.session.flush()
    item.patient_id = patient.id
    item.appointment_id = appointment.id
    item.status = 'converted'
    db.session.add(AuditLog(
        user_id=session.get('user_id'), action='guest_request_converted',
        resource_type='appointment_request', resource_id=item.id,
        details={'appointment_id': appointment.id},
    ))
    db.session.commit()
    flash('Patient portal and pending appointment created. Give credentials by phone; patient must change the temporary password and complete payment.', 'success')
    return redirect(url_for('admin.intake_requests', status='all'))


@admin_bp.post('/intake-requests/<int:request_id>/status')
def update_intake_status(request_id):
    if not is_admin():
        return redirect(url_for('auth.admin_login'))
    item = db.session.get(GuestAppointmentRequest, request_id)
    status = request.form.get('status')
    if not item or status not in {'new', 'contacted', 'closed'} or item.status == 'converted':
        flash('Unable to update that request.', 'warning')
    else:
        item.status = status
        db.session.commit()
        flash('Request status updated.', 'success')
    return redirect(url_for('admin.intake_requests', status='all'))

def is_admin():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        return user and user.role == 'admin'
    return False

# ============================================
# DASHBOARD
# ============================================
@admin_bp.route('/dashboard')
def dashboard():
    if not is_admin():
        return redirect(url_for('auth.admin_login'))

    try:
        total_patients = PatientProfile.query.count()

        total_clinicians = (
            ClinicianProfile.query
            .join(User)
            .filter(User.role == 'clinician')
            .count()
        )

        total_appointments = Appointment.query.count()
        today = clinic_today()
        todays_appointments = Appointment.query.filter(
            func.date(Appointment.appointment_date) == today
        ).count()
        pending_requests = GuestAppointmentRequest.query.filter_by(status='new').count()
        cancelled_appointments = Appointment.query.filter_by(status='cancelled').count()
        video_appointments = Appointment.query.filter_by(appointment_type='video').count()
        in_person_appointments = Appointment.query.filter_by(appointment_type='in_person').count()
        clinicians_on_time_off = (db.session.query(ClinicianTimeOff.clinician_id)
                                  .filter(ClinicianTimeOff.status == 'approved',
                                          ClinicianTimeOff.start_date <= today,
                                          ClinicianTimeOff.end_date >= today)
                                  .distinct().count())

        total_revenue = db.session.query(
            func.sum(Payment.amount)
        ).filter_by(payment_status='completed').scalar() or 0

        return render_template(
            'admin/dashboard.html',
            total_patients=total_patients,
            total_clinicians=total_clinicians,
            total_appointments=total_appointments,
            total_revenue=total_revenue,
            todays_appointments=todays_appointments,
            pending_requests=pending_requests,
            cancelled_appointments=cancelled_appointments,
            clinicians_on_time_off=clinicians_on_time_off,
            video_appointments=video_appointments,
            in_person_appointments=in_person_appointments,
        )

    except Exception:
        current_app.logger.exception('Unable to load admin dashboard')
        return render_template('errors/500.html'), 500
# ============================================
# PATIENTS
# ============================================
@admin_bp.route('/patients')
def patients():
    if not is_admin():
        return redirect(url_for('auth.admin_login'))

    try:
        filters = {key: request.args.get(key, '').strip()
                   for key in ('patient_no', 'name', 'contact', 'date_of_birth')}
        query = PatientProfile.query.join(User)
        patients = search_patients_by_fields(
            query, filters, request.args.get('search', '').strip()
        )

        return render_template(
            'admin/patients.html',
            patients=patients,
            search_filters=filters,
        )

    except Exception:
        current_app.logger.exception('Unable to load admin patients')
        flash('Error loading patients', 'danger')
        return render_template('errors/500.html'), 500

# ============================================
# CLINICIANS LIST
# ============================================
@admin_bp.route('/clinicians')
def clinicians():
    if not is_admin():
        return redirect(url_for('auth.admin_login'))

    try:
        all_clinicians = ClinicianProfile.query.all()

        filtered = []

        for c in all_clinicians:
            if c.user and c.user.username != 'admin':
                filtered.append(c)

        return render_template(
            'admin/clinicians.html',
            clinicians=filtered
        )

    except Exception:
        current_app.logger.exception('Unable to load clinicians')
        flash('Unable to load clinicians. Please try again.', 'danger')
        return render_template(
            'admin/clinicians.html',
            clinicians=[]
        )

@admin_bp.route('/appointments')
def appointments():
    if not is_admin():
        return redirect(url_for('auth.admin_login'))
    status = request.args.get('status', 'all').strip()
    appointment_type = request.args.get('type', 'all').strip()
    date_value = request.args.get('date', '').strip()
    query = Appointment.query
    if status != 'all':
        query = query.filter_by(status=status)
    if appointment_type in {'in_person', 'video'}:
        query = query.filter_by(appointment_type=appointment_type)
    if date_value:
        try:
            query = query.filter(func.date(Appointment.appointment_date) == datetime.strptime(date_value, '%Y-%m-%d').date())
        except ValueError:
            flash('Choose a valid appointment date.', 'warning')
    records = query.order_by(Appointment.appointment_date.desc()).all()
    return render_template('admin/appointments.html', appointments=records,
                           status_filter=status, type_filter=appointment_type,
                           date_filter=date_value)
# ============================================
# VIEW CLINICIAN
# ============================================
@admin_bp.route('/clinician/<int:clinician_id>')
def view_clinician(clinician_id):
    if not is_admin():
        return redirect(url_for('auth.admin_login'))

    try:
        clinician = ClinicianProfile.query.get_or_404(clinician_id)

        return render_template(
            'admin/clinician_detail.html',
            clinician=clinician
        )

    except Exception:
        current_app.logger.exception('Unable to load clinician details')
        flash('Error loading clinician details', 'danger')
        return redirect(url_for('admin.clinicians'))
# ============================================
# VIEW PATIENT (FIXED)
# ============================================
@admin_bp.route('/patient/<int:patient_id>')
def view_patient(patient_id):
    if not is_admin():
        return redirect(url_for('auth.admin_login'))

    try:
        patient = PatientProfile.query.get_or_404(patient_id)

        return render_template(
            'admin/patient_detail.html',
            patient=patient
        )

    except Exception:
        current_app.logger.exception('Unable to load patient details')
        flash('Unable to load patient details.', 'danger')
        return redirect(url_for('admin.patients'))
# ============================================
# ADD CLINICIAN
# ============================================
@admin_bp.route('/add-clinician', methods=['GET', 'POST'])
def add_clinician():
    if not is_admin():
        return redirect(url_for('auth.admin_login'))

    if request.method == 'POST':
        try:
            # Get form data
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            full_name = request.form.get('full_name', '').strip()
            specialty = request.form.get('specialty', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            license_number = request.form.get('license_number', '').strip()

            # ----------------------------
            # Required field validation
            # ----------------------------
            if not username:
                flash('Username is required.', 'danger')
                return render_template('admin/add_clinician.html')

            if not full_name:
                flash('Full name is required.', 'danger')
                return render_template('admin/add_clinician.html')

            if not specialty:
                flash('Specialty is required.', 'danger')
                return render_template('admin/add_clinician.html')

            if not password:
                flash('Password is required.', 'danger')
                return render_template('admin/add_clinician.html')

            if not email:
                flash('Email is required.', 'danger')
                return render_template('admin/add_clinician.html')

            if not phone:
                flash('Phone is required.', 'danger')
                return render_template('admin/add_clinician.html')

            if len(password) < 8:
                flash(
                    'Password must be at least 8 characters long.',
                    'danger'
                )
                return render_template('admin/add_clinician.html')

            # ----------------------------
            # Username validation
            # ----------------------------
            existing_user = User.query.filter_by(
                username=username
            ).first()

            if existing_user:
                flash('Username already exists.', 'danger')
                return render_template('admin/add_clinician.html')

            if User.find_by_identifier(email):
                flash('Email already exists.', 'danger')
                return render_template('admin/add_clinician.html')

            if User.find_by_identifier(phone):
                flash('Phone already exists.', 'danger')
                return render_template('admin/add_clinician.html')

            # ----------------------------
            # Numeric validation
            # ----------------------------
            try:
                years_experience = int(
                    request.form.get('years_experience', 0)
                )

                consultation_fee = float(
                    request.form.get('consultation_fee', 2000)
                )

            except (ValueError, TypeError):
                flash(
                    'Experience and consultation fee must be valid numbers.',
                    'danger'
                )
                return render_template('admin/add_clinician.html')

            if years_experience < 0:
                flash(
                    'Years of experience cannot be negative.',
                    'danger'
                )
                return render_template('admin/add_clinician.html')

            if consultation_fee < 0:
                flash(
                    'Consultation fee cannot be negative.',
                    'danger'
                )
                return render_template('admin/add_clinician.html')

            # Empty license becomes NULL
            if not license_number:
                license_number = None

            # ----------------------------
            # Create user
            # ----------------------------
            user = User(
                username=username,
                role='clinician',
                full_name=full_name,
                email=email,
                phone=phone
            )

            user.set_password(password)

            db.session.add(user)
            db.session.flush()

            # ----------------------------
            # Create clinician profile
            # ----------------------------
            clinician = ClinicianProfile(
                user_id=user.id,
                specialty=specialty,
                license_number=license_number,
                years_experience=years_experience,
                consultation_fee=consultation_fee,
                is_available=request.form.get('is_available') == 'on',
            )

            db.session.add(clinician)
            db.session.flush()
            db.session.add(AuditLog(user_id=session.get('user_id'), action='clinician_created',
                                    resource_type='clinician', resource_id=clinician.id))
            db.session.commit()

            flash(
                'Clinician added successfully!',
                'success'
            )

            return redirect(url_for('admin.clinicians'))

        except Exception:
            db.session.rollback()
            current_app.logger.exception('Unable to add clinician')

            flash(
                'Unable to add clinician. Please check the information.',
                'danger'
            )

    return render_template('admin/add_clinician.html')
# ============================================
# EDIT CLINICIAN
# ============================================
@admin_bp.route(
    '/clinician/<int:clinician_id>/edit',
    methods=['GET', 'POST']
)
def edit_clinician(clinician_id):
    if not is_admin():
        return redirect(url_for('auth.admin_login'))

    clinician = ClinicianProfile.query.get_or_404(clinician_id)

    if clinician.user and clinician.user.username == 'admin':
        flash('Cannot edit admin', 'danger')
        return redirect(url_for('admin.clinicians'))

    if request.method == 'POST':
        try:
            clinician.specialty = request.form.get('specialty')

            license_number = request.form.get('license_number')

            clinician.license_number = (
                license_number if license_number else None
            )

            clinician.years_experience = int(
                request.form.get('years_experience', 0)
            )

            clinician.consultation_fee = float(
                request.form.get('consultation_fee', 2000)
            )
            clinician.is_available = request.form.get('is_available') == 'on'

            if clinician.user:
                clinician.user.full_name = request.form.get('full_name')
                clinician.user.email = request.form.get('email')
                clinician.user.phone = request.form.get('phone')

            db.session.add(AuditLog(user_id=session.get('user_id'), action='clinician_updated',
                                    resource_type='clinician', resource_id=clinician.id))

            db.session.commit()

            flash('Clinician updated successfully!', 'success')
            return redirect(url_for('admin.clinicians'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')

    return render_template(
        'admin/edit_clinician.html',
        clinician=clinician
    )
# ============================================
# ACTIVATE/DEACTIVATE CLINICIAN (keeps clinical history intact)
# ============================================
@admin_bp.route(
    '/clinician/<int:clinician_id>/delete',
    methods=['POST']
)
def delete_clinician(clinician_id):
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        clinician = ClinicianProfile.query.get_or_404(clinician_id)

        if clinician.user and clinician.user.username == 'admin':
            return jsonify({'error': 'Cannot delete admin'}), 400

        user = clinician.user
        if not user:
            return jsonify({'error': 'Clinician account not found'}), 404

        user.is_active = not user.is_active
        db.session.add(AuditLog(user_id=session.get('user_id'), action='clinician_status_changed',
                                resource_type='clinician', resource_id=clinician.id,
                                details={'is_active': user.is_active}))
        db.session.commit()

        return jsonify({'success': True, 'is_active': user.is_active})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ============================================
# AUDIT LOGS
# ============================================
@admin_bp.route('/audit-logs')
def audit_logs():
    if not is_admin():
        return redirect(url_for('auth.admin_login'))

    try:
        page = request.args.get('page', 1, type=int)

        scope = request.args.get('scope', 'active')
        action = request.args.get('action', '').strip()
        role = request.args.get('role', '').strip()
        user_filter = request.args.get('user', '').strip()
        resource_type = request.args.get('resource_type', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        query = AuditLog.query
        if scope == 'archived':
            query = query.filter(AuditLog.archived_at.isnot(None))
        elif scope != 'all':
            scope = 'active'
            query = query.filter(AuditLog.archived_at.is_(None))
        if action:
            query = query.filter(AuditLog.action.ilike(f'%{action}%'))
        if user_filter:
            matching_users = db.session.query(User.id).filter(
                User.username.ilike(f'%{user_filter}%')
            )
            if user_filter.isdigit():
                query = query.filter(
                    (AuditLog.user_id == int(user_filter))
                    | AuditLog.user_id.in_(matching_users)
                )
            else:
                query = query.filter(AuditLog.user_id.in_(matching_users))
        if role in {'admin', 'clinician', 'patient'}:
            query = query.join(User, AuditLog.user_id == User.id).filter(User.role == role)
        elif role:
            role = ''
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        try:
            if date_from:
                query = query.filter(AuditLog.timestamp >= datetime.strptime(date_from, '%Y-%m-%d'))
            if date_to:
                query = query.filter(AuditLog.timestamp < datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
        except ValueError:
            flash('Use valid dates in the activity filters.', 'warning')
            return redirect(url_for('admin.audit_logs'))

        logs = query.order_by(
            AuditLog.timestamp.desc()
        ).paginate(
            page=page,
            per_page=50
        )

        return render_template(
            'admin/audit_logs.html',
            logs=logs,
            filters={'scope': scope, 'action': action, 'user': user_filter,
                     'role': role, 'resource_type': resource_type,
                     'date_from': date_from, 'date_to': date_to},
            resource_types=[row[0] for row in db.session.query(AuditLog.resource_type)
                            .filter(AuditLog.resource_type.isnot(None)).distinct().order_by(AuditLog.resource_type)],
        )

    except Exception:
        current_app.logger.exception('Unable to load audit records')
        flash('Unable to load activity records. Please try again.', 'danger')
        return render_template('errors/500.html'), 500


@admin_bp.post('/audit-logs/archive')
def archive_audit_logs():
    if not is_admin():
        return redirect(url_for('auth.admin_login'))
    days = request.form.get('days', type=int)
    if days not in {7, 30, 90}:
        flash('Choose a valid archive period.', 'warning')
        return redirect(url_for('admin.audit_logs'))
    cutoff = datetime.utcnow() - timedelta(days=days)
    batch_id = str(uuid4())
    count = (AuditLog.query
             .filter(AuditLog.archived_at.is_(None), AuditLog.timestamp < cutoff)
             .update({'archived_at': datetime.utcnow(), 'archive_batch_id': batch_id},
                     synchronize_session=False))
    db.session.add(AuditLog(
        user_id=session.get('user_id'), action='audit_logs_archived',
        resource_type='audit_log',
        details={'older_than_days': days, 'records_archived': count, 'batch_id': batch_id},
    ))
    db.session.commit()
    flash(f'{count} activity records archived. They remain available under Archived.', 'success')
    return redirect(url_for('admin.audit_logs', scope='active'))
