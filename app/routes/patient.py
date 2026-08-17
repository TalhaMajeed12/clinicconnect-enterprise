from flask import Blueprint, render_template, session, redirect, url_for, flash
from app import db
from app.models import User, PatientProfile, Visit, Appointment, Payment, Prescription
from app.utils.translations import t
from datetime import datetime

patient_bp = Blueprint('patient', __name__)


def get_patient():
    user_id = session.get('user_id')

    if user_id:
        return PatientProfile.query.filter_by(user_id=user_id).first()

    return None


@patient_bp.route('/dashboard')
def dashboard():
    patient = get_patient()

    if not patient:
        flash(t('Access denied'), 'danger')
        return redirect(url_for('auth.login'))

    upcoming = Appointment.query.filter_by(
        patient_id=patient.id
    ).filter(
        Appointment.appointment_date >= datetime.utcnow()
    ).order_by(Appointment.appointment_date.asc()).all()

    recent_visits = Visit.query.filter_by(
        patient_id=patient.id
    ).order_by(
        Visit.visit_date.desc()
    ).limit(5).all()

    total_appointments = Appointment.query.filter_by(patient_id=patient.id).count()
    active_prescriptions = Prescription.query.filter_by(
        patient_id=patient.id, is_active=True
    ).order_by(Prescription.created_at.desc()).all()

    return render_template(
        'patient/dashboard.html',
        patient=patient,
        upcoming=upcoming,
        recent_visits=recent_visits,
        next_appointment=upcoming[0] if upcoming else None,
        total_appointments=total_appointments,
        active_prescriptions=active_prescriptions,
    )


@patient_bp.route('/history')
def history():
    patient = get_patient()

    if not patient:
        flash(t('Access denied'), 'danger')
        return redirect(url_for('auth.login'))

    visits = Visit.query.filter_by(
        patient_id=patient.id
    ).order_by(
        Visit.visit_date.desc()
    ).all()

    prescriptions = Prescription.query.filter_by(patient_id=patient.id).order_by(
        Prescription.created_at.desc()
    ).all()
    appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(
        Appointment.appointment_date.desc()
    ).all()

    return render_template(
        'patient/history.html',
        visits=visits,
        prescriptions=prescriptions,
        appointments=appointments,
    )


@patient_bp.route('/appointments')
def appointments():
    patient = get_patient()

    if not patient:
        flash(t('Access denied'), 'danger')
        return redirect(url_for('auth.login'))

    appointments = Appointment.query.filter_by(
        patient_id=patient.id
    ).all()

    return render_template(
        'patient/appointments.html',
        appointments=appointments,
        now=datetime.utcnow()
    )


@patient_bp.route(
    '/cancel-appointment/<int:appointment_id>',
    methods=['POST']
)
def cancel_appointment(appointment_id):
    patient = get_patient()

    if not patient:
        flash(t('Access denied'), 'danger')
        return redirect(url_for('auth.login'))

    appointment = Appointment.query.get_or_404(appointment_id)

    if appointment.patient_id != patient.id:
        flash(t('Unauthorized'), 'danger')
        return redirect(url_for('patient.dashboard'))

    if appointment.status not in ('pending', 'confirmed') or appointment.appointment_date <= datetime.utcnow():
        flash(t('This appointment can no longer be cancelled.'), 'warning')
        return redirect(url_for('patient.appointments'))

    appointment.status = 'cancelled'

    db.session.commit()

    flash(
        t('Appointment cancelled successfully!'),
        'success'
    )

    return redirect(url_for('patient.dashboard'))
