from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models import User, PatientProfile, ClinicianProfile, AuditLog, LoginAttempt
from datetime import datetime
import traceback

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
            user = User.query.filter(
                (User.email == identifier) | (User.phone == identifier)
            ).first()
            
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
            
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect_based_on_role(user.role)
            
        except Exception as e:
            print(f"Login Error: {str(e)}")
            print(traceback.format_exc())
            flash('Login failed. Please try again.', 'danger')
            return render_template('auth/login.html')
    
    return render_template('auth/login.html')

# ============================================
# CLINICIAN LOGIN
# ============================================
@auth_bp.route('/clinician/login', methods=['GET', 'POST'])
def clinician_login():
    # If user is already logged in as clinician, redirect to clinician dashboard
    if session.get('user_id'):
        user = User.query.get(session['user_id'])
        if user and user.role == 'clinician':
            return redirect(url_for('clinician.dashboard'))
        elif user:
            flash('You are already logged in as a different user.', 'warning')
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
            
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash(f'Welcome back, Dr. {user.full_name}!', 'success')
            return redirect(url_for('clinician.dashboard'))
            
        except Exception as e:
            print(f"Clinician Login Error: {str(e)}")
            print(traceback.format_exc())
            flash('Login failed. Please try again.', 'danger')
            return render_template('auth/clinician_login.html')
    
    return render_template('auth/clinician_login.html')

# ============================================
# ADMIN LOGIN
# ============================================
@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    # If user is already logged in as admin, redirect to admin dashboard
    if session.get('user_id'):
        user = User.query.get(session['user_id'])
        if user and user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif user:
            flash('You are already logged in as a different user.', 'warning')
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
            
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin.dashboard'))
            
        except Exception as e:
            print(f"Admin Login Error: {str(e)}")
            print(traceback.format_exc())
            flash('Login failed. Please try again.', 'danger')
            return render_template('auth/admin_login.html')
    
    return render_template('auth/admin_login.html')

# ============================================
# REGISTRATION - PATIENT
# ============================================
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # Check if registration is disabled (can be configured)
    # For now, allow registration
    
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
            
            if User.query.filter_by(email=email).first():
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
            
        except Exception as e:
            db.session.rollback()
            print(f"Registration Error: {str(e)}")
            flash(f'Error: {str(e)}', 'danger')
            return render_template('auth/register.html', form=request.form)
    
    return render_template('auth/register.html')

# ============================================
# LOGOUT (FIXED)
# ============================================
@auth_bp.route('/logout')
def logout():
    # Get user info before clearing session
    role = session.get('role')
    username = session.get('username')
    
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