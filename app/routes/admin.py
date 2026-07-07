from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db, limiter
from app.models import User, PatientProfile, ClinicianProfile, Appointment, Payment, AuditLog
from app.utils.translations import t
from datetime import datetime
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__)

def is_admin():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        return user and user.role == 'admin'
    return False

@admin_bp.route('/dashboard')
def dashboard():
    if not is_admin():
        flash(t('Access denied'), 'danger')
        return redirect(url_for('auth.login'))
    
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

@admin_bp.route('/patients')
def patients():
    if not is_admin():
        return redirect(url_for('auth.login'))
    
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

@admin_bp.route('/clinicians')
def clinicians():
    if not is_admin():
        return redirect(url_for('auth.login'))
    
    clinicians = ClinicianProfile.query.all()
    return render_template('admin/clinicians.html', clinicians=clinicians)

@admin_bp.route('/add-clinician', methods=['GET', 'POST'])
def add_clinician():
    if not is_admin():
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        specialty = request.form.get('specialty')
        
        if User.query.filter_by(username=username).first():
            flash(t('Username already exists'), 'danger')
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
            consultation_fee=float(request.form.get('consultation_fee', 2000))
        )
        db.session.add(clinician)
        db.session.commit()
        
        flash(t('Clinician added successfully!'), 'success')
        return redirect(url_for('admin.clinicians'))
    
    return render_template('admin/add_clinician.html')

@admin_bp.route('/clinician/<int:clinician_id>/delete', methods=['POST'])
def delete_clinician(clinician_id):
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    
    clinician = ClinicianProfile.query.get_or_404(clinician_id)
    if clinician.user.username == 'admin':
        return jsonify({'error': 'Cannot delete admin'}), 400
    
    db.session.delete(clinician.user)
    db.session.delete(clinician)
    db.session.commit()
    
    return jsonify({'success': True})

@admin_bp.route('/audit-logs')
def audit_logs():
    if not is_admin():
        return redirect(url_for('auth.login'))
    
    page = request.args.get('page', 1, type=int)
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=50)
    return render_template('admin/audit_logs.html', logs=logs) 
