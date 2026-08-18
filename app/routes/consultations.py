from urllib.parse import quote
from datetime import datetime

from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, session, url_for)

from app.extensions import db
from app.models import (Appointment, ConsultationMessage, User,
                        VideoConsultation)
from app.utils.audit import record_audit
from app.utils.video_consultation import consultation_join_state


consultations_bp = Blueprint('consultations', __name__)


def _authorize(appointment):
    if not appointment:
        abort(404)

    user_id = session.get('user_id')
    user = db.session.get(User, user_id) if user_id else None
    if not user or user.role not in {'patient', 'clinician'}:
        abort(403)

    patient_user_id = appointment.patient.user_id if appointment.patient else None
    clinician_user_id = appointment.clinician.user_id if appointment.clinician else None
    if user.id not in {patient_user_id, clinician_user_id}:
        abort(403)
    return appointment, user


def _authorized_appointment(appointment_id):
    return _authorize(db.session.get(Appointment, appointment_id))


def _authorized_room(room_token):
    return _authorize(Appointment.query.filter_by(
        video_room_token=room_token
    ).first())


@consultations_bp.route('/<int:appointment_id>')
def room(appointment_id):
    """Backward-compatible entry point that never exposes the room token early."""
    appointment, user = _authorized_appointment(appointment_id)
    if appointment.appointment_type != 'video':
        flash('This is an in-person appointment and has no video room.', 'info')
        return redirect(
            url_for('patient.appointments')
            if user.role == 'patient'
            else url_for('clinician.appointments')
        )
    return redirect(url_for(
        'consultations.token_room', room_token=appointment.video_room_token
    ))


@consultations_bp.route('/room/<string:room_token>')
def token_room(room_token):
    appointment, user = _authorized_room(room_token)
    messages = ConsultationMessage.query.filter_by(
        appointment_id=appointment.id
    ).order_by(ConsultationMessage.created_at.asc()).all()
    join_state = consultation_join_state(
        appointment, current_app.config, now=datetime.now()
    )
    if join_state['allowed']:
        video_session = appointment.video_session
        if not video_session:
            video_session = VideoConsultation(
                appointment_id=appointment.id, status='active',
                started_at=datetime.utcnow()
            )
            db.session.add(video_session)
        elif video_session.status == 'scheduled':
            video_session.status = 'active'
            video_session.started_at = video_session.started_at or datetime.utcnow()
        record_audit(
            'video_consultation_joined', 'appointment', appointment.id,
            {'role': user.role}
        )
        db.session.commit()
    base_url = current_app.config['VIDEO_CONSULTATION_BASE_URL'].rstrip('/')
    video_url = f"{base_url}/ClinicConnect-{quote(appointment.video_room_token, safe='')}"
    return render_template(
        'consultations/room.html', appointment=appointment, messages=messages,
        current_user=user, video_url=video_url, join_state=join_state
    )


@consultations_bp.post('/<int:appointment_id>/messages')
def send_message(appointment_id):
    appointment, user = _authorized_appointment(appointment_id)
    body = ' '.join(request.form.get('message', '').strip().split())
    if not body:
        flash('Enter a message before sending.', 'warning')
    elif len(body) > 2000:
        flash('Messages must be 2,000 characters or fewer.', 'warning')
    elif appointment.status == 'cancelled':
        flash('Messaging is unavailable for a cancelled appointment.', 'warning')
    else:
        message = ConsultationMessage(
            appointment_id=appointment.id, sender_id=user.id
        )
        message.body = body
        db.session.add(message)
        record_audit(
            'consultation_message_sent', 'appointment', appointment.id,
            {'sender_role': user.role}
        )
        db.session.commit()
    return redirect(url_for(
        'consultations.token_room', room_token=appointment.video_room_token
    ))
