from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app import db
from app.models import User, PatientProfile, ClinicianProfile, Appointment, AuditLog, Visit, Prescription, Attendance
from app.utils.translations import t
from datetime import datetime, date

clinician_bp = Blueprint('clinician', __name__)

def get_clinician():
    user_id = session.get('user_id')
    if user_id:
        return ClinicianProfile.query.filter_by(user_id=user_id).first()
    return None

@clinician_bp.route('/dashboard')
def dashboard():
    clinician = get_clinician()
    if not clinician:
        flash(t('Access denied'), 'danger')
        return redirect(url_for('auth.login'))
    
    today = date.today()
    appointments = Appointment.query.filter_by(clinician_id=clinician.id).filter(
        db.func.date(Appointment.appointment_date) == today
    ).all()
    
    return render_template('clinician/dashboard.html',
        clinician=clinician,
        appointments=appointments
    )

@clinician_bp.route('/patients')
def patients_list():
    clinician = get_clinician()
    if not clinician:
        return redirect(url_for('auth.login'))
    
    patients = PatientProfile.query.all()
    return render_template('clinician/patients_list.html', patients=patients)

@clinician_bp.route('/patient/<int:patient_id>')
def patient_folder(patient_id):
    clinician = get_clinician()
    if not clinician:
        return redirect(url_for('auth.login'))
    
    patient = PatientProfile.query.get_or_404(patient_id)
    visits = Visit.query.filter_by(patient_id=patient.id).order_by(Visit.visit_date.desc()).all()
    appointments = Appointment.query.filter_by(patient_id=patient.id).all()
    
    return render_template('clinician/patient_folder.html',
        patient=patient,
        visits=visits,
        appointments=appointments
    )

@clinician_bp.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    clinician = get_clinician()
    if not clinician:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        try:
            # Create user
            user = User(
                username=request.form.get('email').split('@')[0],
                role='patient'
            )
            user.full_name = request.form.get('full_name')
            user.email = request.form.get('email')
            user.phone = request.form.get('phone')
            user.set_password(request.form.get('password', 'Patient@123'))
            
            db.session.add(user)
            db.session.flush()
            
            patient = PatientProfile(
                user_id=user.id,
                blood_group=request.form.get('blood_group'),
                allergies=request.form.get('allergies'),
                is_child=request.form.get('is_child') == 'on',
                age=int(request.form.get('age')) if request.form.get('age') else None
            )
            db.session.add(patient)
            db.session.commit()
            
            flash(t('Patient added successfully!'), 'success')
            return redirect(url_for('clinician.patients_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding patient: {str(e)}', 'danger')
            return render_template('clinician/add_patient.html')
    
    return render_template('clinician/add_patient.html')

@clinician_bp.route('/add_visit/<int:patient_id>', methods=['GET', 'POST'])
def add_visit(patient_id):
    clinician = get_clinician()
    if not clinician:
        return redirect(url_for('auth.login'))
    
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
                secondary_diagnosis=request.form.get('secondary_diagnosis', '').split(',') if request.form.get('secondary_diagnosis') else [],
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
            
            # Calculate BMI if height and weight are provided
            if visit.height and visit.weight:
                visit.bmi = visit.weight / ((visit.height / 100) ** 2)
            
            db.session.add(visit)
            db.session.commit()
            
            flash(t('Visit added successfully!'), 'success')
            return redirect(url_for('clinician.patient_folder', patient_id=patient.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding visit: {str(e)}', 'danger')
            return render_template('clinician/add_visit.html', patient=patient)
    
    return render_template('clinician/add_visit.html', patient=patient)

@clinician_bp.route('/toggle_attendance', methods=['POST'])
def toggle_attendance():
    clinician = get_clinician()
    if not clinician:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        attendance = Attendance.query.filter_by(clinician_id=clinician.id).first()
        if not attendance:
            attendance = Attendance(clinician_id=clinician.id, status='offline')
            db.session.add(attendance)
        
        attendance.status = 'online' if attendance.status == 'offline' else 'offline'
        attendance.last_updated = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'status': attendance.status})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@clinician_bp.route('/appointments')
def appointments():
    clinician = get_clinician()
    if not clinician:
        return redirect(url_for('auth.login'))
    
    appointments = Appointment.query.filter_by(clinician_id=clinician.id).all()
    return render_template('clinician/appointments.html', appointments=appointments)