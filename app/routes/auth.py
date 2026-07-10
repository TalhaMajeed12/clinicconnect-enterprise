from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models import User, PatientProfile, ClinicianProfile, AuditLog, LoginAttempt
from app.utils.translations import t
from datetime import datetime
import re
import traceback

auth_bp = Blueprint('auth', __name__)

# ============================================
# PATIENT REGISTRATION
# ============================================
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # Initialize form data with empty values
    form_data = {
        'full_name': '',
        'email': '',
        'phone': '',
        'password': '',
        'confirm_password': ''
    }
    
    if request.method == 'POST':
        # Capture form data to preserve on error
        form_data = {
            'full_name': request.form.get('full_name', ''),
            'email': request.form.get('email', ''),
            'phone': request.form.get('phone', ''),
            'password': request.form.get('password', ''),
            'confirm_password': request.form.get('confirm_password', '')
        }
        
        try:
            full_name = form_data['full_name']
            email = form_data['email']
            phone = form_data['phone']
            password = form_data['password']
            confirm_password = form_data['confirm_password']
            
            # Validation
            if not full_name or not email or not phone or not password:
                flash('All fields are required', 'danger')
                return render_template('auth/register.html', form=form_data)
            
            if password != confirm_password:
                flash('Passwords do not match', 'danger')
                return render_template('auth/register.html', form=form_data)
            
            if len(password) < 6:
                flash('Password must be at least 6 characters', 'danger')
                return render_template('auth/register.html', form=form_data)
            
            if not any(c.isupper() for c in password):
                flash('Password must contain at least one uppercase letter', 'danger')
                return render_template('auth/register.html', form=form_data)
            
            # Check if user exists
            if User.query.filter_by(email=email).first():
                flash('Email already registered', 'danger')
                return render_template('auth/register.html', form=form_data)
            
            if User.query.filter_by(phone=phone).first():
                flash('Phone number already registered', 'danger')
                return render_template('auth/register.html', form=form_data)
            
            # Create user (role is always 'patient' for registration)
            username = email.split('@')[0]
            # Make username unique if it already exists
            if User.query.filter_by(username=username).first():
                username = f"{username}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            user = User(
                username=username,
                role='patient',  # Force role to patient
                full_name=full_name,
                email=email,
                phone=phone
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.flush()
            
            # Create patient profile
            patient = PatientProfile(user_id=user.id)
            db.session.add(patient)
            db.session.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Registration Error: {str(e)}")
            print(traceback.format_exc())
            flash('Registration failed. Please try again.', 'danger')
            return render_template('auth/register.html', form=form_data)
    
    return render_template('auth/register.html', form=form_data)

# ============================================
# PATIENT LOGIN
# ============================================
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            identifier = request.form.get('email') or request.form.get('phone')
            password = request.form.get('password')
            
            if not identifier or not password:
                flash('Email/Phone and password required', 'danger')
                return render_template('auth/login.html')
            
            # Find user by email or phone
            user = User.query.filter(
                (User.email == identifier) | (User.phone == identifier)
            ).first()
            
            if not user:
                flash('Invalid credentials', 'danger')
                return render_template('auth/login.html')
            
            if not user.check_password(password):
                flash('Invalid credentials', 'danger')
                return render_template('auth/login.html')
            
            if not user.is_active:
                flash('Account is deactivated', 'danger')
                return render_template('auth/login.html')
            
            # Login successful
            session['user_id'] = user.id
            session['role'] = user.role
            session['username'] = user.username
            session['full_name'] = user.full_name
            
            user.last_login = datetime.utcnow()
            
            # Log login attempt
            login_attempt = LoginAttempt(
                identifier=identifier,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                success=True
            )
            db.session.add(login_attempt)
            db.session.commit()
            
            # Redirect based on role
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'clinician':
                return redirect(url_for('clinician.dashboard'))
            else:
                return redirect(url_for('patient.dashboard'))
                
        except Exception as e:
            print(f"Login Error: {str(e)}")
            print(traceback.format_exc())
            flash('Login failed. Please try again.', 'danger')
            return render_template('auth/login.html')
    
    return render_template('auth/login.html')

# ============================================
# ADMIN LOGIN
# ============================================
@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                flash('Username and password required', 'danger')
                return render_template('auth/admin_login.html')
            
            user = User.query.filter_by(username=username).first()
            
            if not user:
                flash('Invalid credentials', 'danger')
                return render_template('auth/admin_login.html')
            
            if not user.check_password(password):
                flash('Invalid credentials', 'danger')
                return render_template('auth/admin_login.html')
            
            if user.role != 'admin':
                flash('Access denied. Admin only.', 'danger')
                return render_template('auth/admin_login.html')
            
            if not user.is_active:
                flash('Account is deactivated', 'danger')
                return render_template('auth/admin_login.html')
            
            session['user_id'] = user.id
            session['role'] = user.role
            session['username'] = user.username
            session['full_name'] = user.full_name
            
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin.dashboard'))
            
        except Exception as e:
            print(f"Admin Login Error: {str(e)}")
            print(traceback.format_exc())
            flash('Login failed', 'danger')
            return render_template('auth/admin_login.html')
    
    return render_template('auth/admin_login.html')

# ============================================
# ADMIN REGISTRATION (For creating admin accounts)
# ============================================
@auth_bp.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    form_data = {
        'username': '',
        'full_name': '',
        'email': '',
        'phone': '',
        'password': '',
        'confirm_password': ''
    }
    
    if request.method == 'POST':
        form_data = {
            'username': request.form.get('username', ''),
            'full_name': request.form.get('full_name', ''),
            'email': request.form.get('email', ''),
            'phone': request.form.get('phone', ''),
            'password': request.form.get('password', ''),
            'confirm_password': request.form.get('confirm_password', '')
        }
        
        try:
            username = form_data['username']
            full_name = form_data['full_name']
            email = form_data['email']
            phone = form_data['phone']
            password = form_data['password']
            confirm_password = form_data['confirm_password']
            
            if not username or not full_name or not email or not phone or not password:
                flash('All fields are required', 'danger')
                return render_template('auth/admin_register.html', form=form_data)
            
            if password != confirm_password:
                flash('Passwords do not match', 'danger')
                return render_template('auth/admin_register.html', form=form_data)
            
            if len(password) < 6:
                flash('Password must be at least 6 characters', 'danger')
                return render_template('auth/admin_register.html', form=form_data)
            
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'danger')
                return render_template('auth/admin_register.html', form=form_data)
            
            if User.query.filter_by(email=email).first():
                flash('Email already registered', 'danger')
                return render_template('auth/admin_register.html', form=form_data)
            
            user = User(
                username=username,
                role='admin',
                full_name=full_name,
                email=email,
                phone=phone
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.flush()
            
            # Create admin clinician profile
            clinician = ClinicianProfile(
                user_id=user.id,
                specialty='Administration',
                consultation_fee=0
            )
            db.session.add(clinician)
            db.session.commit()
            
            flash('Admin created successfully! Please login.', 'success')
            return redirect(url_for('auth.admin_login'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Admin Registration Error: {str(e)}")
            flash(f'Error: {str(e)}', 'danger')
            return render_template('auth/admin_register.html', form=form_data)
    
    return render_template('auth/admin_register.html', form=form_data)

# ============================================
# LOGOUT
# ============================================
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
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
                'full_name': user.full_name
            })
    return jsonify({'authenticated': False})