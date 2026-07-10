from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app import db
from app.models import User, PatientProfile, ClinicianProfile, Appointment, AuditLog, Visit, Prescription, Attendance
from app.utils.translations import t
from datetime import datetime, date
import traceback

clinician_bp = Blueprint('clinician', __name__)

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

# ============================================
# DASHBOARD
# ============================================
@clinician_bp.route('/dashboard')
def dashboard():
    if not is_clinician():
        flash('Access denied', 'danger')
        return redirect(url_for('auth.login'))
    
    try:
        clinician = get_clinician()
        today = date.today()
        
        # Get today's appointments
        appointments = Appointment.query.filter_by(clinician_id=clinician.id).filter(
            db.func.date(Appointment.appointment_date) == today
        ).all()
        
        # Get counts
        total_patients = PatientProfile.query.count()
        total_appointments = Appointment.query.filter_by(clinician_id=clinician.id).count()
        pending_appointments = Appointment.query.filter_by(clinician_id=clinician.id, status='pending').count()
        
        return render_template('clinician/dashboard.html',
            clinician=clinician,
            appointments=appointments,
            total_patients=total_patients,
            total_appointments=total_appointments,
            pending_appointments=pending_appointments
        )
    except Exception as e:
        print(f"Dashboard Error: {str(e)}")
        print(traceback.format_exc())
        flash('Error loading dashboard', 'danger')
        return render_template('clinician/dashboard.html', clinician=clinician, appointments=[])

# ============================================
# PATIENTS LIST
# ============================================
@clinician_bp.route('/patients')
def patients_list():
    if not is_clinician():
        return redirect(url_for('auth.login'))
    
    try:
        clinician = get_clinician()
        search = request.args.get('search', '')
        
        query = PatientProfile.query.join(User)
        if search:
            query = query.filter(
                User.full_name.like(f'%{search}%') |
                User.phone.like(f'%{search}%') |
                User.email.like(f'%{search}%')
            )
        
        patients = query.all()
        return render_template('clinician/patients_list.html', patients=patients, clinician=clinician)
    except Exception as e:
        print(f"Patients List Error: {str(e)}")
        flash('Error loading patients', 'danger')
        return render_template('clinician/patients_list.html', patients=[], clinician=clinician)

# ============================================
# PATIENT FOLDER (View Patient Details)
# ============================================
@clinician_bp.route('/patient/<int:patient_id>')
def patient_folder(patient_id):
    if not is_clinician():
        return redirect(url_for('auth.login'))
    
    try:
        clinician = get_clinician()
        patient = PatientProfile.query.get_or_404(patient_id)
        visits = Visit.query.filter_by(patient_id=patient.id).order_by(Visit.visit_date.desc()).all()
        appointments = Appointment.query.filter_by(patient_id=patient.id).all()
        
        return render_template('clinician/patient_folder.html',
            patient=patient,
            visits=visits,
            appointments=appointments,
            clinician=clinician
        )
    except Exception as e:
        print(f"Patient Folder Error: {str(e)}")
        flash('Error loading patient details', 'danger')
        return redirect(url_for('clinician.patients_list'))

# ============================================
# ADD PATIENT
# ============================================
@clinician_bp.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if not is_clinician():
        return redirect(url_for('auth.login'))
    
    clinician = get_clinician()
    
    if request.method == 'POST':
        try:
            # Create user
            username = request.form.get('email').split('@')[0] if request.form.get('email') else request.form.get('phone')
            user = User(
                username=username,
                role='patient',
                full_name=request.form.get('full_name'),
                email=request.form.get('email'),
                phone=request.form.get('phone')
            )
            user.set_password(request.form.get('password', 'Patient@123'))
            
            db.session.add(user)
            db.session.flush()
            
            # Create patient profile
            patient = PatientProfile(
                user_id=user.id,
                blood_group=request.form.get('blood_group'),
                allergies=request.form.get('allergies'),
                is_child=request.form.get('is_child') == 'on',
                age=int(request.form.get('age')) if request.form.get('age') else None
            )
            db.session.add(patient)
            db.session.commit()
            
            flash('Patient added successfully!', 'success')
            return redirect(url_for('clinician.patients_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding patient: {str(e)}', 'danger')
            return render_template('clinician/add_patient.html', clinician=clinician)
    
    return render_template('clinician/add_patient.html', clinician=clinician)

# ============================================
# ADD VISIT
# ============================================
@clinician_bp.route('/add_visit/<int:patient_id>', methods=['GET', 'POST'])
def add_visit(patient_id):
    if not is_clinician():
        return redirect(url_for('auth.login'))
    
    clinician = get_clinician()
    patient = PatientProfile.query.get_or_404(patient_id)
    
    if request.method == 'POST':
        try:
            visit = Visit(
                patient_id=patient.id,
                clinician_id=clinician.id,
                visit_date=datetime.utcnow(),
                chief_complaint=request.form.get('chief_complaint'),
                history_of_presenting_illness=request.form.get('history_of_presenting_illness'),
                past_medical_history=request.form.get('past_medical_history'),
                family_history=request.form.get('family_history'),
                physical_examination=request.form.get('physical_examination'),
                primary_diagnosis=request.form.get('primary_diagnosis'),
                treatment_plan=request.form.get('treatment_plan'),
                follow_up_required=request.form.get('follow_up_required') == 'on',
                height=float(request.form.get('height')) if request.form.get('height') else None,
                weight=float(request.form.get('weight')) if request.form.get('weight') else None,
                blood_pressure_systolic=int(request.form.get('blood_pressure_systolic')) if request.form.get('blood_pressure_systolic') else None,
                blood_pressure_diastolic=int(request.form.get('blood_pressure_diastolic')) if request.form.get('blood_pressure_diastolic') else None,
                heart_rate=int(request.form.get('heart_rate')) if request.form.get('heart_rate') else None,
                temperature=float(request.form.get('temperature')) if request.form.get('temperature') else None,
                oxygen_saturation=float(request.form.get('oxygen_saturation')) if request.form.get('oxygen_saturation') else None
            )
            
            # Calculate BMI
            if visit.height and visit.weight:
                visit.bmi = visit.weight / ((visit.height / 100) ** 2)
            
            db.session.add(visit)
            db.session.commit()
            
            flash('Visit added successfully!', 'success')
            return redirect(url_for('clinician.patient_folder', patient_id=patient.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding visit: {str(e)}', 'danger')
            return render_template('clinician/add_visit.html', patient=patient, clinician=clinician)
    
    return render_template('clinician/add_visit.html', patient=patient, clinician=clinician)

# ============================================
# APPOINTMENTS
# ============================================
@clinician_bp.route('/appointments')
def appointments():
    if not is_clinician():
        return redirect(url_for('auth.login'))
    
    try:
        clinician = get_clinician()
        
        # Get filter parameters
        status = request.args.get('status', 'all')
        date_filter = request.args.get('date', '')
        
        query = Appointment.query.filter_by(clinician_id=clinician.id)
        
        if status != 'all':
            query = query.filter_by(status=status)
        
        if date_filter:
            try:
                filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                query = query.filter(db.func.date(Appointment.appointment_date) == filter_date)
            except ValueError:
                pass
        
        appointments = query.order_by(Appointment.appointment_date.desc()).all()
        
        return render_template('clinician/appointments.html',
            appointments=appointments,
            clinician=clinician,
            status_filter=status,
            date_filter=date_filter
        )
    except Exception as e:
        print(f"Appointments Error: {str(e)}")
        flash('Error loading appointments', 'danger')
        return render_template('clinician/appointments.html', appointments=[], clinician=clinician)

# ============================================
# UPDATE APPOINTMENT STATUS
# ============================================
@clinician_bp.route('/appointment/<int:appointment_id>/update', methods=['POST'])
def update_appointment(appointment_id):
    if not is_clinician():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        appointment = Appointment.query.get_or_404(appointment_id)
        new_status = request.json.get('status')
        
        if new_status in ['pending', 'confirmed', 'completed', 'cancelled']:
            appointment.status = new_status
            db.session.commit()
            return jsonify({'success': True, 'status': appointment.status})
        
        return jsonify({'error': 'Invalid status'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ============================================
# TOGGLE ATTENDANCE
# ============================================
@clinician_bp.route('/toggle_attendance', methods=['POST'])
def toggle_attendance():
    if not is_clinician():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        clinician = get_clinician()
        attendance = Attendance.query.filter_by(clinician_id=clinician.id).first()
        
        if not attendance:
            attendance = Attendance(clinician_id=clinician.id, status='offline')
            db.session.add(attendance)
        
        attendance.status = 'online' if attendance.status == 'offline' else 'offline'
        attendance.last_updated = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'status': attendance.status})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ============================================
# PATIENT SEARCH (AJAX)
# ============================================
@clinician_bp.route('/search_patients', methods=['GET'])
def search_patients():
    if not is_clinician():
        return jsonify([]), 401
    
    try:
        term = request.args.get('term', '')
        patients = PatientProfile.query.join(User).filter(
            User.full_name.ilike(f'%{term}%') |
            User.phone.ilike(f'%{term}%')
        ).limit(10).all()
        
        return jsonify([{
            'id': p.id,
            'name': p.user.full_name if p.user else 'Unknown',
            'phone': p.user.phone if p.user else ''
        } for p in patients])
    except Exception as e:
        return jsonify({'error': str(e)}), 500