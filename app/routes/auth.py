from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app import db, limiter
from app.models import User, PatientProfile, ClinicianProfile, AuditLog, LoginAttempt
from app.utils.otp import create_otp, verify_otp
from app.utils.email import send_email
from app.utils.translations import t
from datetime import datetime, timedelta
import re

auth_bp = Blueprint('auth', __name__)

def validate_password(password):
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain an uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain a lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain a number"
    return True, "Valid password"


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'patient')
        
        if not password:
            flash(t('Please enter a password'), 'danger')
            return redirect(url_for('auth.register'))
        
        is_valid, msg = validate_password(password)
        if not is_valid:
            flash(t(msg), 'danger')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=email).first():
            flash(t('Email already registered'), 'danger')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(phone=phone).first():
            flash(t('Phone already registered'), 'danger')
            return redirect(url_for('auth.register'))
        
        user = User(
            username=email.split('@')[0],
            role=role
        )
        user.full_name = full_name
        user.email = email
        user.phone = phone
        user.set_password(password)
        
        db.session.add(user)
        db.session.flush()
        
        if role == 'patient':
            patient_profile = PatientProfile(user_id=user.id)
            db.session.add(patient_profile)
        elif role == 'clinician':
            clinician_profile = ClinicianProfile(user_id=user.id, specialty='General')
            db.session.add(clinician_profile)
        
        otp_record = create_otp(phone, user.id, purpose='registration')
        send_email(
            subject='ClinicConnect OTP Verification',
            recipient=email,
            body_html=f'''
            <h2>{t('Welcome to ClinicConnect!')}</h2>
            <p>{t('Your OTP for registration is:')} <strong>{otp_record.otp_code}</strong></p>
            <p>{t('This OTP expires in 5 minutes.')}</p>
            '''
        )
        
        session['registration_phone'] = phone
        flash(t('OTP sent to your email. Please verify.'), 'info')
        return redirect(url_for('auth.verify_otp_registration'))
    
    return render_template('patient/register.html')


@auth_bp.route('/verify-otp-registration', methods=['GET', 'POST'])
def verify_otp_registration():
    phone = session.get('registration_phone')
    if not phone:
        flash(t('Session expired. Please register again.'), 'warning')
        return redirect(url_for('auth.register'))
    
    if request.method == 'POST':
        otp_code = request.form.get('otp', '')
        if verify_otp(phone, otp_code):
            db.session.commit()
            session.pop('registration_phone', None)
            flash(t('Registration complete! You can now log in.'), 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(t('Invalid or expired OTP.'), 'danger')
    
    return render_template('patient/verify_otp.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter(
            (User._email == User.encrypt_field(identifier)) |
            (User._phone == User.encrypt_field(identifier))
        ).first()
        
        if not user:
            flash(t('Invalid credentials'), 'danger')
            return render_template('patient/login.html')
        
        if user.check_password(password):
            session['user_id'] = user.id
            session['role'] = user.role
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash(t('Login successful!'), 'success')
            
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'clinician':
                return redirect(url_for('clinician.dashboard'))
            else:
                return redirect(url_for('patient.dashboard'))
        else:
            flash(t('Invalid credentials'), 'danger')
    
    return render_template('patient/login.html')


@auth_bp.route('/change-language/<lang>')
def change_language(lang):
    if lang in ['en', 'ur']:
        session['language'] = lang
    return redirect(request.referrer or url_for('main.index'))


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash(t('Logged out successfully.'), 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username, role='admin').first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['role'] = user.role
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash(t('Admin login successful!'), 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash(t('Invalid admin credentials'), 'danger')
    
    return render_template('admin/login.html')


@auth_bp.route('/clinician/login', methods=['GET', 'POST'])
def clinician_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username, role='clinician').first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['role'] = user.role
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash(t('Clinician login successful!'), 'success')
            return redirect(url_for('clinician.dashboard'))
        else:
            flash(t('Invalid clinician credentials'), 'danger')
    
    return render_template('clinician/login.html') 
