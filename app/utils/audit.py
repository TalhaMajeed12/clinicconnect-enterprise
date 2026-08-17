"""Small, explicit audit helper for important workflow events.

Only identifiers and operational metadata belong here. Clinical narrative,
credentials, tokens, and secrets must never be written to the audit log.
"""
from flask import request, session

from app.models import AuditLog


def record_audit(action, resource_type=None, resource_id=None, details=None):
    entry = AuditLog(
        user_id=session.get('user_id'),
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or None,
        ip_address=request.headers.get('X-Forwarded-For', request.remote_addr or '')[:45],
        user_agent=request.user_agent.string[:255],
    )
    from app import db
    db.session.add(entry)
    return entry
