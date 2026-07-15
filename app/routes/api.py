from flask import Blueprint, request, jsonify, session, current_app
from app import db
from app.models import User, PatientProfile, ClinicianProfile, Appointment, Visit, Payment
from app.utils.auth import token_required
from datetime import datetime, timedelta
import jwt

api_bp = Blueprint('api', __name__)

# ============================================
# SESSION CHECK - For JavaScript back button fix
# ============================================
@api_bp.route('/check-session')
def check_session():
    """Check if user is authenticated"""
    authenticated = 'user_id' in session
    return jsonify({
        'authenticated': authenticated,
        'user_id': session.get('user_id'),
        'role': session.get('role'),
        'username': session.get('username')
    })

# ============================================
# HEALTH CHECK
# ============================================
@api_bp.route('/health')
def health():
    """System health check"""
    return jsonify({
        'status': 'healthy',
        'session_active': 'user_id' in session,
        'timestamp': datetime.utcnow().isoformat()
    })

# ============================================
# AUTH API
# ============================================
@api_bp.route('/auth/login', methods=['POST'])
def api_login():
    data = request.get_json()
    identifier = data.get('identifier')
    password = data.get('password')
    
    user = User.query.filter(
        (User._email == User.encrypt_field(identifier)) |
        (User._phone == User.encrypt_field(identifier))
    ).first()
    
    if user and user.check_password(password):
        token = jwt.encode(
            {'user_id': user.id, 'exp': datetime.utcnow() + timedelta(hours=24)},
            current_app.config['JWT_SECRET_KEY'],
            algorithm='HS256'
        )
        return jsonify({
            'success': True,
            'token': token,
            'user': user.to_dict()
        })
    
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@api_bp.route('/auth/register', methods=['POST'])
def api_register():
    data = request.get_json()
    
    user = User(
        username=data.get('email').split('@')[0],
        role=data.get('role', 'patient')
    )
    user.full_name = data.get('full_name')
    user.email = data.get('email')
    user.phone = data.get('phone')
    user.set_password(data.get('password'))
    
    db.session.add(user)
    db.session.flush()
    
    if user.role == 'patient':
        patient = PatientProfile(user_id=user.id)
        db.session.add(patient)
    
    db.session.commit()
    
    return jsonify({'success': True, 'user': user.to_dict()})

# ============================================
# PATIENT API
# ============================================
@api_bp.route('/patients', methods=['GET'])
@token_required
def get_patients(current_user):
    patients = PatientProfile.query.all()
    return jsonify({'patients': [p.to_dict() for p in patients]})

@api_bp.route('/patients/<int:patient_id>', methods=['GET'])
@token_required
def get_patient(current_user, patient_id):
    patient = PatientProfile.query.get_or_404(patient_id)
    return jsonify(patient.to_dict())

@api_bp.route('/patients', methods=['POST'])
@token_required
def create_patient(current_user):
    data = request.get_json()
    
    user = User(
        username=data.get('email').split('@')[0],
        role='patient'
    )
    user.full_name = data.get('full_name')
    user.email = data.get('email')
    user.phone = data.get('phone')
    user.set_password(data.get('password', 'Patient@123'))
    
    db.session.add(user)
    db.session.flush()
    
    patient = PatientProfile(
        user_id=user.id,
        blood_group=data.get('blood_group'),
        allergies=data.get('allergies'),
        is_child=data.get('is_child', False),
        age=data.get('age')
    )
    db.session.add(patient)
    db.session.commit()
    
    return jsonify({'success': True, 'patient': patient.to_dict()})

# ============================================
# APPOINTMENT API
# ============================================
@api_bp.route('/appointments', methods=['GET'])
@token_required
def get_appointments(current_user):
    if current_user.role == 'patient':
        profile = PatientProfile.query.filter_by(user_id=current_user.id).first()
        appointments = Appointment.query.filter_by(patient_id=profile.id).all()
    elif current_user.role == 'clinician':
        profile = ClinicianProfile.query.filter_by(user_id=current_user.id).first()
        appointments = Appointment.query.filter_by(clinician_id=profile.id).all()
    else:
        appointments = Appointment.query.all()
    
    return jsonify({'appointments': [a.to_dict() for a in appointments]})

@api_bp.route('/appointments', methods=['POST'])
@token_required
def create_appointment(current_user):
    data = request.get_json()
    
    patient = PatientProfile.query.filter_by(user_id=current_user.id).first()
    clinician = ClinicianProfile.query.get(data.get('clinician_id'))
    
    appointment = Appointment(
        patient_id=patient.id,
        clinician_id=clinician.id,
        appointment_date=datetime.fromisoformat(data.get('appointment_date')),
        reason=data.get('reason'),
        symptoms=data.get('symptoms'),
        status='pending'
    )
    db.session.add(appointment)
    db.session.commit()
    
    return jsonify({'success': True, 'appointment': appointment.to_dict()})

# ============================================
# CLINICIAN API
# ============================================
@api_bp.route('/clinicians', methods=['GET'])
def get_clinicians():
    clinicians = ClinicianProfile.query.all()
    return jsonify({'clinicians': [c.to_dict() for c in clinicians]})

@api_bp.route('/clinicians/available', methods=['GET'])
def get_available_clinicians():
    clinicians = ClinicianProfile.query.filter_by(is_available=True).all()
    return jsonify({'clinicians': [c.to_dict() for c in clinicians]})

# ============================================
# VISIT API
# ============================================
@api_bp.route('/visits', methods=['GET'])
@token_required
def get_visits(current_user):
    if current_user.role == 'patient':
        profile = PatientProfile.query.filter_by(user_id=current_user.id).first()
        visits = Visit.query.filter_by(patient_id=profile.id).all()
    else:
        visits = Visit.query.all()
    
    return jsonify({'visits': [v.to_dict() for v in visits]})

@api_bp.route('/visits', methods=['POST'])
@token_required
def create_visit(current_user):
    data = request.get_json()
    
    patient = PatientProfile.query.get(data.get('patient_id'))
    clinician = ClinicianProfile.query.filter_by(user_id=current_user.id).first()
    
    visit = Visit(
        patient_id=patient.id,
        clinician_id=clinician.id,
        chief_complaint=data.get('chief_complaint'),
        primary_diagnosis=data.get('primary_diagnosis'),
        treatment_plan=data.get('treatment_plan'),
        medications_prescribed=data.get('medications_prescribed', [])
    )
    db.session.add(visit)
    db.session.commit()
    
    return jsonify({'success': True, 'visit': visit.to_dict()})

# ============================================
# PAYMENT API
# ============================================
@api_bp.route('/payments', methods=['GET'])
@token_required
def get_payments(current_user):
    if current_user.role == 'patient':
        profile = PatientProfile.query.filter_by(user_id=current_user.id).first()
        payments = Payment.query.filter_by(patient_id=profile.id).all()
    else:
        payments = Payment.query.all()
    
    return jsonify({'payments': [p.to_dict() for p in payments]})

@api_bp.route('/payments', methods=['POST'])
@token_required
def create_payment(current_user):
    data = request.get_json()
    
    appointment = Appointment.query.get(data.get('appointment_id'))
    profile = PatientProfile.query.filter_by(user_id=current_user.id).first()
    
    payment = Payment(
        appointment_id=appointment.id,
        patient_id=profile.id,
        amount=data.get('amount'),
        payment_method=data.get('payment_method'),
        transaction_id=data.get('transaction_id'),
        payment_status='completed'
    )
    db.session.add(payment)
    
    appointment.status = 'confirmed'
    db.session.commit()
    
    return jsonify({'success': True, 'payment': payment.to_dict()})