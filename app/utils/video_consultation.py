from datetime import datetime, timedelta

from app.utils.timezone import clinic_now


JOINABLE_STATUSES = {'confirmed', 'checked_in'}


def consultation_join_state(appointment, config, now=None):
    """Return a centralized, display-safe video-room access decision."""
    now = now or clinic_now()
    if appointment.appointment_type != 'video':
        return {
            'allowed': False,
            'code': 'not_video',
            'message': 'This appointment is scheduled for an in-person visit.',
        }
    if appointment.status not in JOINABLE_STATUSES:
        return {
            'allowed': False,
            'code': 'status',
            'message': (
                'The appointment must be confirmed before the video room opens.'
                if appointment.status == 'pending'
                else 'This consultation is no longer available.'
            ),
        }

    early_minutes = max(int(config.get('VIDEO_JOIN_EARLY_MINUTES', 15)), 0)
    grace_minutes = max(int(config.get('VIDEO_JOIN_GRACE_MINUTES', 30)), 0)
    start = appointment.appointment_date
    end = start + timedelta(minutes=max(int(appointment.duration or 30), 5))
    opens_at = start - timedelta(minutes=early_minutes)
    closes_at = end + timedelta(minutes=grace_minutes)
    if now < opens_at:
        return {
            'allowed': False,
            'code': 'too_early',
            'opens_at': opens_at,
            'message': (
                f'Your video consultation will become available {early_minutes} '
                'minutes before the scheduled appointment.'
            ),
        }
    if now > closes_at:
        return {
            'allowed': False,
            'code': 'expired',
            'closes_at': closes_at,
            'message': 'The joining window for this video consultation has ended.',
        }
    return {
        'allowed': True,
        'code': 'open',
        'opens_at': opens_at,
        'closes_at': closes_at,
        'message': 'The secure video room is ready.',
    }
