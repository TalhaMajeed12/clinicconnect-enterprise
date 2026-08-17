from flask import Blueprint, jsonify, request, session

from app.extensions import limiter
from app.utils.clinical_chatbot import clinical_support_reply


chatbot_bp = Blueprint('chatbot', __name__)


@chatbot_bp.post('/message')
@limiter.limit('20 per minute')
def message():
    if not session.get('user_id') or session.get('role') not in {
        'admin', 'clinician', 'patient'
    }:
        return jsonify({'error': 'Authentication required'}), 401

    data = request.get_json(silent=True) or {}
    user_message = data.get('message', '')
    if not isinstance(user_message, str):
        return jsonify({'error': 'Message must be text'}), 400
    if len(user_message) > 1000:
        return jsonify({'error': 'Message is too long'}), 400

    return jsonify(clinical_support_reply(user_message))
