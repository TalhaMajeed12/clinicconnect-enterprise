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
        flash('Access denied', 'danger')
        return redirect(url_for('auth.login'))
    
    try:
        total_patients = PatientProfile.query.count()
        total_clinicians = ClinicianProfile.query.count()
        total_appointments = Appointment.query.count()
        total_revenue = db.session.query(func.sum(Payment.amount)).filter_by(payment_status='completed').scalar() or 0
        
        return render_template('admin/dashboard.html',
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
        print(f"Patients Error: {str(e)}")
        flash('Error loading patients', 'danger')
        return render_template('errors/500.html'), 500

# ============================================
# CLINICIANS (SIMPLIFIED - NO COMPLEX QUERIES)
# ============================================
@admin_bp.route('/clinicians')
def clinicians():
    if not is_admin():
        return redirect(url_for('auth.login'))
    
    try:
        # Simple query - get all clinicians
        clinicians = ClinicianProfile.query.all()
        
        # Filter out admin in Python (safer)
        filtered = []
        for c in clinicians:
            if c.user and c.user.username != 'admin':
                filtered.append(c)
        
        return render_template('admin/clinicians.html', clinicians=filtered)
    except Exception as e:
        print(f"Clinicians Error: {str(e)}")
        print(traceback.format_exc())
        flash('Error loading clinicians', 'danger')
        return render_template('errors/500.html'), 500

# ============================================
# ADD CLINICIAN
# ============================================
@admin_bp.route('/add-clinician', methods=['GET', 'POST'])
def add_clinician():
    if not is_admin():
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            full_name = request.form.get('full_name')
            specialty = request.form.get('specialty')
            fee = float(request.form.get('consultation_fee', 2000))
            
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'danger')
                return render_template('admin/add_clinician.html')
            
            user = User(username=username, role='clinician')
            user.full_name = full_name
            user.email = request.form.get('email')
            user.phone = request.form.get('phone')
            user.set_password(password)
            
            db.session.add(user)
            db.session.flush()
            
            clinician = ClinicianProfile(
                user_id=user.id,
                specialty=specialty,
                license_number=request.form.get('license_number'),
                years_experience=int(request.form.get('years_experience', 0)),
                consultation_fee=fee
            )
            db.session.add(clinician)
            db.session.commit()
            
            flash('Clinician added successfully!', 'success')
            return redirect(url_for('admin.clinicians'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return render_template('admin/add_clinician.html')
    
    return render_template('admin/add_clinician.html')

# ============================================
# EDIT CLINICIAN
# ============================================
@admin_bp.route('/clinician/<int:clinician_id>/edit', methods=['GET', 'POST'])
def edit_clinician(clinician_id):
    if not is_admin():
        return redirect(url_for('auth.login'))
    
    clinician = ClinicianProfile.query.get_or_404(clinician_id)
    
    if clinician.user and clinician.user.username == 'admin':
        flash('Cannot edit admin', 'danger')
        return redirect(url_for('admin.clinicians'))
    
    if request.method == 'POST':
        try:
            clinician.specialty = request.form.get('specialty')
            clinician.license_number = request.form.get('license_number')
            clinician.years_experience = int(request.form.get('years_experience', 0))
            clinician.consultation_fee = float(request.form.get('consultation_fee', 2000))
            
            if clinician.user:
                clinician.user.full_name = request.form.get('full_name')
                clinician.user.email = request.form.get('email')
                clinician.user.phone = request.form.get('phone')
            
            db.session.commit()
            flash('Clinician updated!', 'success')
            return redirect(url_for('admin.clinicians'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    
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
        flash('Error loading logs', 'danger')
        return render_template('errors/500.html'), 500

# ============================================
# VIEW PATIENT
# ============================================
@admin_bp.route('/patient/<int:patient_id>')
def view_patient(patient_id):
    if not is_admin():
        return redirect(url_for('auth.login'))
    
    patient = PatientProfile.query.get_or_404(patient_id)
    return render_template('admin/patient_detail.html', patient=patient)

# ============================================
# VIEW CLINICIAN
# ============================================
@admin_bp.route('/clinician/<int:clinician_id>')
def view_clinician(clinician_id):
    if not is_admin():
        return redirect(url_for('auth.login'))
    
    clinician = ClinicianProfile.query.get_or_404(clinician_id)
    return render_template('admin/clinician_detail.html', clinician=clinician)