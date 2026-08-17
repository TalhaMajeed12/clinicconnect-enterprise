from urllib.parse import quote

from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, session, url_for)

from app.extensions import db
from app.models import Appointment, ConsultationMessage, User


consultations_bp = Blueprint('consultations', __name__)


def _authorized_appointment(appointment_id):
    appointment = db.session.get(Appointment, appointment_id)
    if not appointment:
        abort(404)

    user = db.session.get(User, session.get('user_id'))
    if not user or user.role not in {'patient', 'clinician'}:
        abort(403)

    patient_user_id = appointment.patient.user_id if appointment.patient else None
    clinician_user_id = appointment.clinician.user_id if appointment.clinician else None
    if user.id not in {patient_user_id, clinician_user_id}:
        abort(403)
    return appointment, user


@consultations_bp.route('/<int:appointment_id>')
def room(appointment_id):
    appointment, user = _authorized_appointment(appointment_id)
    messages = ConsultationMessage.query.filter_by(
        appointment_id=appointment.id
    ).order_by(ConsultationMessage.created_at.asc()).all()
    base_url = current_app.config['VIDEO_CONSULTATION_BASE_URL'].rstrip('/')
    video_url = f"{base_url}/ClinicConnect-{quote(appointment.video_room_token, safe='')}"
    return render_template(
        'consultations/room.html', appointment=appointment, messages=messages,
        current_user=user, video_url=video_url
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
        db.session.commit()
    return redirect(url_for('consultations.room', appointment_id=appointment.id))
