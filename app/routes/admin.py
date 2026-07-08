from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db, limiter
from app.models import User, PatientProfile, ClinicianProfile, Appointment, Payment, AuditLog
from app.utils.translations import t
from datetime import datetime
from sqlalchemy import func
import traceback

admin_bp = Blueprint('admin', __name__)

def is_admin():
    """Check if current user is admin"""
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        return user and user.role == 'admin'
    return False

# ============================================
# TEST ROUTE
# ============================================
@admin_bp.route('/test-db')
def test_db():
    try:
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        required_tables = ['user', 'patient_profile', 'clinician_profile', 'appointment', 'payment', 'audit_log']
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            return f"❌ Missing tables: {', '.join(missing_tables)}"
        
        patient_count = PatientProfile.query.count()
        clinician_count = ClinicianProfile.query.count()
        appointment_count = Appointment.query.count()
        
        return f"""
        ✅ Database is working!
        - Patients: {patient_count}
        - Clinicians: {clinician_count}
        - Appointments: {appointment_count}
        - Tables exist: {', '.join(tables)}
        """
    except Exception as e:
        return f"❌ Database Error: {str(e)}\n\n{traceback.format_exc()}"

# ============================================
# ADMIN DASHBOARD
# ============================================
@admin_bp.route('/dashboard')
def dashboard():
    if not is_admin():
        flash(t('Access denied'), 'danger')
        return redirect(url_for('auth.login'))
    
    try:
        total_patients = PatientProfile.query.count()
        total_clinicians = ClinicianProfile.query.count()
        total_appointments = Appointment.query.count()
        total_revenue = db.session.query(func.sum(Payment.amount)).filter_by(payment_status='completed').scalar() or 0
        
        today = datetime.utcnow().date()
        today_appointments = Appointment.query.filter(
            func.date(Appointment.appointment_date) == today
        ).count()
        
        pending = Appointment.query.filter_by(status='pending').count()
        confirmed = Appointment.query.filter_by(status='confirmed').count()
        completed = Appointment.query.filter_by(status='completed').count()
        cancelled = Appointment.query.filter_by(status='cancelled').count()
        
        recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(20).all()
        
        return render_template('admin/dashboard.html',
            total_patients=total_patients,
            total_clinicians=total_clinicians,
            total_appointments=total_appointments,
            total_revenue=total_revenue,
            today_appointments=today_appointments,
            pending=pending,
            confirmed=confirmed,
            completed=completed,
            cancelled=cancelled,
            recent_logs=recent_logs
        )
    except Exception as e:
        print(f"❌ Dashboard Error: {str(e)}")
        print(traceback.format_exc())
        flash(f'Dashboard error: {str(e)}', 'danger')
        return render_template('errors/500.html'), 500

# ============================================
# PATIENTS LIST
# ============================================
@admin_bp.route('/patients')
def patients():
    if not is_admin():
        return redirect(url_for('auth.login'))
    
    try:
        search = request.args.get('search', '')
        query = PatientProfile.query.join(User)
        
        if search:
            query = query.filter(
                User.full_name.like(f'%{search}%') |
                User.phone.like(f'%{search}%') |
                User.email.like(f'%{search}%')
            )
        
        patients = query.all()
        return render_template('admin/patients.html', patients=patients)
    except Exception as e:
        print(f"❌ Patients Error: {str(e)}")
        flash(f'Error loading patients: {str(e)}', 'danger')
        return render_template('errors/500.html'), 500

# ============================================
# CLINICIANS LIST (FIXED - Simple query)
# ============================================
@admin_bp.route('/clinicians')
def clinicians():
    if not is_admin():
        return redirect(url_for('auth.login'))
    
    try:
        # Get all clinicians and filter out admin in Python
        all_clinicians = ClinicianProfile.query.all()
        
        # Filter out the admin user (username 'admin')
        clinicians = []
        for c in all_clinicians:
            if c.user and c.user.username != 'admin':
                clinicians.append(c)
        
        return render_template('admin/clinicians.html', clinicians=clinicians)
    except Exception as e:
        print(f"❌ Clinicians Error: {str(e)}")
        print(traceback.format_exc())
        flash(f'Error loading clinicians: {str(e)}', 'danger')
        return render_template('errors/500.html'), 500

# ============================================
# ADD CLINICIAN
# ============================================
@admin_bp.route('/add-clinician', methods=['GET', 'POST'])
def add_clinician():
    if not is_admin():
        return redirect(url_for('auth.login'))
    
    try:
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            full_name = request.form.get('full_name')
            specialty = request.form.get('specialty')
            consultation_fee = float(request.form.get('consultation_fee', 2000))
            
            # Check if username exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('Username already exists', 'danger')
                return render_template('admin/add_clinician.html')
            
            # Create user
            user = User(username=username, role='clinician')
            user.full_name = full_name
            user.email = request.form.get('email')
            user.phone = request.form.get('phone')
            user.set_password(password)
            
            db.session.add(user)
            db.session.flush()
            
            # Create clinician profile
            clinician = ClinicianProfile(
                user_id=user.id,
                specialty=specialty,
                license_number=request.form.get('license_number'),
                years_experience=int(request.form.get('years_experience', 0)),
                consultation_fee=consultation_fee
            )
            db.session.add(clinician)
            db.session.commit()
            
            flash('Clinician added successfully!', 'success')
            return redirect(url_for('admin.clinicians'))
        
        return render_template('admin/add_clinician.html')
    except Exception as e:
        print(f"❌ Add Clinician Error: {str(e)}")
        print(traceback.format_exc())
        db.session.rollback()
        flash(f'Error adding clinician: {str(e)}', 'danger')
        return render_template('admin/add_clinician.html')

# ============================================
# EDIT CLINICIAN
# ============================================
@admin_bp.route('/clinician/<int:clinician_id>/edit', methods=['GET', 'POST'])
def edit_clinician(clinician_id):
    if not is_admin():
        return redirect(url_for('auth.login'))
    
    try:
        clinician = ClinicianProfile.query.get_or_404(clinician_id)
        
        # Prevent editing admin
        if clinician.user and clinician.user.username == 'admin':
            flash('Cannot edit admin user', 'danger')
            return redirect(url_for('admin.clinicians'))
        
        if request.method == 'POST':
            clinician.specialty = request.form.get('specialty')
            clinician.license_number = request.form.get('license_number')
            clinician.years_experience = int(request.form.get('years_experience', 0))
            clinician.consultation_fee = float(request.form.get('consultation_fee', 2000))
            
            # Also update user info
            if clinician.user:
                clinician.user.full_name = request.form.get('full_name')
                clinician.user.email = request.form.get('email')
                clinician.user.phone = request.form.get('phone')
            
            db.session.commit()
            flash('Clinician updated successfully!', 'success')
            return redirect(url_for('admin.clinicians'))
        
        return render_template('admin/edit_clinician.html', clinician=clinician)
    except Exception as e:
        print(f"❌ Edit Clinician Error: {str(e)}")
        print(traceback.format_exc())
        db.session.rollback()
        flash(f'Error updating clinician: {str(e)}', 'danger')
        return render_template('admin/edit_clinician.html', clinician=clinician)

# ============================================
# DELETE CLINICIAN
# ============================================
@admin_bp.route('/clinician/<int:clinician_id>/delete', methods=['POST'])
def delete_clinician(clinician_id):
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        clinician = ClinicianProfile.query.get_or_404(clinician_id)
        if clinician.user and clinician.user.username == 'admin':
            return jsonify({'error': 'Cannot delete admin'}), 400
        
        # Delete user and clinician profile
        user = clinician.user
        if user:
            db.session.delete(user)
        db.session.delete(clinician)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ============================================
# AUDIT LOGS
# ============================================
@admin_bp.route('/audit-logs')
def audit_logs():
    if not is_admin():
        return redirect(url_for('auth.login'))
    
    try:
        page = request.args.get('page', 1, type=int)
        logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=50)
        return render_template('admin/audit_logs.html', logs=logs)
    except Exception as e:
        print(f"❌ Audit Logs Error: {str(e)}")
        flash(f'Error loading audit logs: {str(e)}', 'danger')
        return render_template('errors/500.html'), 500

# ============================================
# VIEW PATIENT DETAILS
# ============================================
@admin_bp.route('/patient/<int:patient_id>')
def view_patient(patient_id):
    if not is_admin():
        return redirect(url_for('auth.login'))
    
    try:
        patient = PatientProfile.query.get_or_404(patient_id)
        return render_template('admin/patient_detail.html', patient=patient)
    except Exception as e:
        print(f"❌ Patient Detail Error: {str(e)}")
        flash(f'Error loading patient: {str(e)}', 'danger')
        return render_template('errors/500.html'), 500

# ============================================
# VIEW CLINICIAN DETAILS
# ============================================
@admin_bp.route('/clinician/<int:clinician_id>')
def view_clinician(clinician_id):
    if not is_admin():
        return redirect(url_for('auth.login'))
    
    try:
        clinician = ClinicianProfile.query.get_or_404(clinician_id)
        return render_template('admin/clinician_detail.html', clinician=clinician)
    except Exception as e:
        print(f"❌ Clinician Detail Error: {str(e)}")
        flash(f'Error loading clinician: {str(e)}', 'danger')
        return render_template('errors/500.html'), 500