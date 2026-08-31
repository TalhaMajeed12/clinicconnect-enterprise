from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from app import db
from app.models import (User, PatientProfile, ClinicianProfile, AuditLog,
                        LoginAttempt, PasswordResetToken)
from datetime import datetime, timedelta
from flask_login import login_user, logout_user
from app.extensions import limiter
import hashlib
import secrets

from app.utils.email import send_password_reset_link

auth_bp = Blueprint('auth', __name__)

# ============================================
# HELPER FUNCTION: Redirect based on role
# ============================================
def redirect_based_on_role(role):
    if role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif role == 'clinician':
        return redirect(url_for('clinician.dashboard'))
    else:
        return redirect(url_for('patient.dashboard'))

# ============================================
# PATIENT LOGIN
# ============================================
@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute', methods=['POST'])
def login():
    # If user is already logged in, redirect to appropriate dashboard
    if session.get('user_id'):
        user = User.query.get(session['user_id'])
        if user:
            return redirect_based_on_role(user.role)
    
    if request.method == 'POST':
        try:
            identifier = request.form.get('identifier')
            password = request.form.get('password')
            
            if not identifier or not password:
                flash('Email/Phone and password are required', 'danger')
                return render_template('auth/login.html')
            
            # Find user by email or phone
            user = User.find_by_identifier(identifier)
            
            if not user:
                flash('Invalid email/phone or password', 'danger')
                return render_template('auth/login.html')
            
            if not user.check_password(password):
                flash('Invalid email/phone or password', 'danger')
                return render_template('auth/login.html')
            
            if user.role == 'admin':
                flash('Please use the Admin Login page.', 'warning')
                return redirect(url_for('auth.admin_login'))
            
            if not user.is_active:
                flash('Your account has been deactivated. Please contact admin.', 'danger')
                return render_template('auth/login.html')
            
            # Login successful
            session['user_id'] = user.id
            session['role'] = user.role
            session['username'] = user.username
            session['full_name'] = user.full_name
            session['email'] = user.email
            login_user(user)
            
            user.last_login = datetime.utcnow()
            db.session.add(AuditLog(user_id=user.id, action='login', resource_type='authentication'))
            db.session.commit()
            
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect_based_on_role(user.role)
            
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Patient login failed unexpectedly')
            flash('Login failed. Please try again.', 'danger')
            return render_template('auth/login.html')
    
    return render_template('auth/login.html')

# ============================================
# CLINICIAN LOGIN
# ============================================
@auth_bp.route('/clinician/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute', methods=['POST'])
def clinician_login():
    if session.get('user_id'):
        user = User.query.get(session['user_id'])
        if user:
            return redirect_based_on_role(user.role)

    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                flash('Username and password are required', 'danger')
                return render_template('auth/clinician_login.html')
            
            user = User.query.filter_by(username=username).first()
            
            if not user:
                flash('Invalid username or password', 'danger')
                return render_template('auth/clinician_login.html')
            
            if not user.check_password(password):
                flash('Invalid username or password', 'danger')
                return render_template('auth/clinician_login.html')
            
            if user.role != 'clinician':
                flash('Access denied. This is a clinician-only login page.', 'danger')
                return render_template('auth/clinician_login.html')
            
            if not user.is_active:
                flash('Your account has been deactivated. Please contact admin.', 'danger')
                return render_template('auth/clinician_login.html')
            
            # Login successful
            session['user_id'] = user.id
            session['role'] = user.role
            session['username'] = user.username
            session['full_name'] = user.full_name
            session['email'] = user.email
            login_user(user)
            
            user.last_login = datetime.utcnow()
            db.session.add(AuditLog(user_id=user.id, action='login', resource_type='authentication'))
            db.session.commit()
            
            flash(f'Welcome back, Dr. {user.full_name}!', 'success')
            return redirect_based_on_role(user.role)
            
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Clinician login failed unexpectedly')
            flash('Login failed. Please try again.', 'danger')
            return render_template('auth/clinician_login.html')
    
    return render_template('auth/clinician_login.html')

# ============================================
# ADMIN LOGIN
# ============================================
@auth_bp.route('/admin/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute', methods=['POST'])
def admin_login():
    if session.get('user_id'):
        user = User.query.get(session['user_id'])
        if user:
            return redirect_based_on_role(user.role)
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                flash('Username and password are required', 'danger')
                return render_template('auth/admin_login.html')
            
            user = User.query.filter_by(username=username).first()
            
            if not user:
                flash('Invalid username or password', 'danger')
                return render_template('auth/admin_login.html')
            
            if not user.check_password(password):
                flash('Invalid username or password', 'danger')
                return render_template('auth/admin_login.html')
            
            if user.role != 'admin':
                flash('Access denied. This is an admin-only login page.', 'danger')
                return render_template('auth/admin_login.html')
            
            if not user.is_active:
                flash('Your account has been deactivated.', 'danger')
                return render_template('auth/admin_login.html')
            
            # Login successful
            session['user_id'] = user.id
            session['role'] = user.role
            session['username'] = user.username
            session['full_name'] = user.full_name
            session['email'] = user.email
            login_user(user)
            
            user.last_login = datetime.utcnow()
            db.session.add(AuditLog(user_id=user.id, action='login', resource_type='authentication'))
            db.session.commit()
            
            flash('Admin login successful!', 'success')
            return redirect_based_on_role(user.role)
            
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Admin login failed unexpectedly')
            flash('Login failed. Please try again.', 'danger')
            return render_template('auth/admin_login.html')
    
    return render_template('auth/admin_login.html')

# ============================================
# REGISTRATION - PATIENT
# ============================================
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if not current_app.config.get('PUBLIC_REGISTRATION_ENABLED', False):
        if request.method == 'POST':
            flash('Patient self-registration is disabled.', 'warning')
            return render_template('auth/register.html'), 403
        return render_template('auth/register.html')
    
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            full_name = request.form.get('full_name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            # Validation
            if not all([username, full_name, email, phone, password]):
                flash('All fields are required', 'danger')
                return render_template('auth/register.html', form=request.form)
            
            if password != confirm_password:
                flash('Passwords do not match', 'danger')
                return render_template('auth/register.html', form=request.form)
            
            if len(password) < 6:
                flash('Password must be at least 6 characters', 'danger')
                return render_template('auth/register.html', form=request.form)
            
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'danger')
                return render_template('auth/register.html', form=request.form)
            
            if User.find_by_identifier(email) or User.find_by_identifier(phone):
                flash('Email already registered', 'danger')
                return render_template('auth/register.html', form=request.form)
            
            # Create user
            user = User(
                username=username,
                role='patient',
                full_name=full_name,
                email=email,
                phone=phone
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.flush()
            
            # Create patient profile
            patient = PatientProfile(
                user_id=user.id
            )
            db.session.add(patient)
            db.session.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Patient registration failed unexpectedly')
            flash('Registration failed. Please try again.', 'danger')
            return render_template('auth/register.html', form=request.form)
    
    return render_template('auth/register.html')

# ============================================
# LOGOUT (FIXED)
# ============================================
@auth_bp.route('/logout')
def logout():
    # Get user info before clearing session
    role = session.get('role')
    logout_user()
    
    # Clear the session
    session.clear()
    
    # Flash message based on user type
    if role == 'admin':
        flash('Admin logged out successfully.', 'success')
        return redirect(url_for('auth.admin_login'))
    elif role == 'clinician':
        flash('Clinician logged out successfully.', 'success')
        return redirect(url_for('auth.clinician_login'))
    else:
        flash('Logged out successfully.', 'success')
        return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit('5 per hour', methods=['POST'])
def forgot_password():
    if request.method == 'POST':
        identifier = (request.form.get('identifier') or '').strip()
        account_type = request.form.get('account_type', 'patient')
        if account_type not in {'patient', 'clinician'}:
            account_type = 'patient'
        user = User.find_by_identifier(identifier) if identifier else None

        email_matches = bool(
            user and User.normalize_identifier(identifier) == User.normalize_identifier(user.email)
        )
        eligible = bool(
            user and user.role == account_type and user.is_active and user.email
            and (
                account_type == 'patient'
                or (email_matches and (user.email_verified or user.is_verified))
            )
        )
        if eligible:
            raw_token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            PasswordResetToken.query.filter_by(
                user_id=user.id, used_at=None
            ).update({'used_at': datetime.utcnow()})
            reset_record = PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.utcnow() + timedelta(minutes=30),
                requester_ip=request.remote_addr,
            )
            db.session.add(reset_record)
            reset_url = url_for(
                'auth.reset_password', token=raw_token, _external=True
            )
            if send_password_reset_link(user.email, reset_url):
                db.session.commit()
            else:
                db.session.rollback()
                current_app.logger.warning(
                    'Password reset email delivery failed for user_id=%s',
                    user.id,
                )

        session.pop('_flashes', None)
        flash('If that account can receive email, a reset link has been sent.', 'info')
        return redirect(url_for(
            'auth.clinician_login' if account_type == 'clinician' else 'auth.login'
        ))

    account_type = request.args.get('account', 'patient')
    if account_type not in {'patient', 'clinician'}:
        account_type = 'patient'
    return render_template('auth/forgot_password.html', account_type=account_type)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
@limiter.limit('10 per hour')
def reset_password(token):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    reset_record = PasswordResetToken.query.filter_by(
        token_hash=token_hash,
        used_at=None,
    ).first()
    if not reset_record or not reset_record.is_valid:
        flash('This password reset link is invalid or expired.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password') or ''
        confirmation = request.form.get('confirm_password') or ''
        if len(password) < 12:
            flash('Password must be at least 12 characters long.', 'danger')
            return render_template('auth/reset_password.html')
        if password != confirmation:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/reset_password.html')

        reset_user = reset_record.user
        reset_user.set_password(password)
        reset_user.must_change_password = False
        reset_record.used_at = datetime.utcnow()
        db.session.add(AuditLog(
            user_id=reset_record.user_id,
            action='password_reset',
            resource_type='authentication',
            ip_address=request.remote_addr,
        ))
        db.session.commit()
        role = reset_user.role
        session.clear()
        flash('Password reset successful. Please log in.', 'success')
        return redirect(url_for(
            'auth.clinician_login' if role == 'clinician' else 'auth.login'
        ))

    return render_template('auth/reset_password.html')


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@limiter.limit('10 per hour', methods=['POST'])
def change_password():
    user = db.session.get(User, session.get('user_id')) if session.get('user_id') else None
    if not user:
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        current_password = request.form.get('current_password') or ''
        password = request.form.get('password') or ''
        confirmation = request.form.get('confirm_password') or ''
        if not user.check_password(current_password):
            flash('Current password is incorrect.', 'danger')
        elif len(password) < 12:
            flash('New password must be at least 12 characters long.', 'danger')
        elif password != confirmation:
            flash('New passwords do not match.', 'danger')
        elif user.check_password(password):
            flash('Choose a password different from the temporary password.', 'warning')
        else:
            user.set_password(password)
            user.must_change_password = False
            PasswordResetToken.query.filter_by(user_id=user.id, used_at=None).update(
                {'used_at': datetime.utcnow()}
            )
            db.session.add(AuditLog(
                user_id=user.id, action='password_changed',
                resource_type='authentication', ip_address=request.remote_addr,
            ))
            db.session.commit()
            flash('Password changed successfully.', 'success')
            return redirect_based_on_role(user.role)
    return render_template('auth/change_password.html', forced=user.must_change_password)

# ============================================
# CHANGE LANGUAGE
# ============================================
@auth_bp.route('/change_language/<lang>')
def change_language(lang):
    if lang in ['en', 'ur']:
        session['language'] = lang
    return redirect(request.referrer or url_for('main.index'))

# ============================================
# CHECK AUTH STATUS (AJAX)
# ============================================
@auth_bp.route('/status')
def status():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user:
            return jsonify({
                'authenticated': True,
                'username': user.username,
                'role': user.role,
                'full_name': user.full_name,
                'email': user.email
            })
    return jsonify({'authenticated': False})
