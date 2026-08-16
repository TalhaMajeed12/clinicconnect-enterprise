from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models import User, PatientProfile, ClinicianProfile, Appointment, Payment, AuditLog
from datetime import datetime
from sqlalchemy import func
import traceback

admin_bp = Blueprint('admin', __name__)

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

        total_revenue = db.session.query(
            func.sum(Payment.amount)
        ).filter_by(payment_status='completed').scalar() or 0

        return render_template(
            'admin/dashboard.html',
            total_patients=total_patients,
            total_clinicians=total_clinicians,
            total_appointments=total_appointments,
            total_revenue=total_revenue
        )

    except Exception as e:
        print(f"Dashboard Error: {str(e)}")
        return render_template('errors/500.html'), 500
# ============================================
# PATIENTS
# ============================================
@admin_bp.route('/patients')
def patients():
    if not is_admin():
        return redirect(url_for('auth.admin_login'))

    try:
        search = request.args.get('search', '')
        query = PatientProfile.query.join(User)

        if search:
            term = search.casefold()
            patients = [patient for patient in query.all() if patient.user and term in ' '.join([
                patient.user.full_name or '', patient.user.phone or '', patient.user.email or ''
            ]).casefold()]
        else:
            patients = query.all()

        return render_template(
            'admin/patients.html',
            patients=patients
        )

    except Exception as e:
        print(f"Patients Error: {str(e)}")
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

    except Exception as e:
        print(f"Clinicians Error: {str(e)}")
        print(traceback.format_exc())
        flash(f'Error loading clinicians: {str(e)}', 'danger')
        return render_template(
            'admin/clinicians.html',
            clinicians=[]
        )

@admin_bp.route('/appointments')
def appointments():
    if not is_admin():
        return redirect(url_for('auth.admin_login'))
    records = Appointment.query.order_by(Appointment.appointment_date.desc()).all()
    return render_template('admin/appointments.html', appointments=records)
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

    except Exception as e:
        print(f"View Clinician Error: {str(e)}")
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

    except Exception as e:
        print(f"View Patient Error: {str(e)}")
        print(traceback.format_exc())
        flash(f'Error loading patient details: {str(e)}', 'danger')
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
                email=email or None,
                phone=phone or None
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
                consultation_fee=consultation_fee
            )

            db.session.add(clinician)
            db.session.add(AuditLog(user_id=session.get('user_id'), action='clinician_created',
                                    resource_type='clinician', resource_id=clinician.id))
            db.session.commit()

            flash(
                'Clinician added successfully!',
                'success'
            )

            return redirect(url_for('admin.clinicians'))

        except Exception as e:
            db.session.rollback()

            print(f"Add Clinician Error: {str(e)}")
            print(traceback.format_exc())

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

        logs = AuditLog.query.order_by(
            AuditLog.timestamp.desc()
        ).paginate(
            page=page,
            per_page=50
        )

        return render_template(
            'admin/audit_logs.html',
            logs=logs
        )

    except Exception as e:
        print(f"Audit Logs Error: {str(e)}")
        flash('Error loading logs', 'danger')
        return render_template('errors/500.html'), 500
