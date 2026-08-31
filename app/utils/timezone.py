"""Timezone helpers for clinic-facing schedules.

Appointment columns currently contain naive clinic-local wall times.  Keep that
storage contract until a dedicated UTC data migration is performed, but always
derive "now" from the configured clinic timezone so hosting-region time cannot
change booking and video-room behaviour.
"""

from datetime import datetime, timedelta, timezone
from flask import current_app, has_app_context


DEFAULT_CLINIC_TIMEZONE = 'Asia/Karachi'


def clinic_timezone():
    name = (
        current_app.config.get('CLINIC_TIMEZONE', DEFAULT_CLINIC_TIMEZONE)
        if has_app_context()
        else DEFAULT_CLINIC_TIMEZONE
    )
    # Pakistan has observed UTC+05:00 without daylight-saving changes since
    # 2009. A fixed offset keeps production and Windows development identical
    # without requiring an operating-system timezone database.
    if name != DEFAULT_CLINIC_TIMEZONE:
        current_app.logger.warning(
            'Unsupported CLINIC_TIMEZONE %s; using %s',
            name, DEFAULT_CLINIC_TIMEZONE,
        )
    return timezone(timedelta(hours=5), name='PKT')


def clinic_now():
    """Return a naive datetime matching stored appointment wall times."""
    return datetime.now(clinic_timezone()).replace(tzinfo=None)


def clinic_today():
    return clinic_now().date()


def utc_to_clinic(value):
    """Convert a stored naive UTC timestamp to an aware clinic timestamp."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(clinic_timezone())


def format_clinic_datetime(value, pattern='%d %b %Y, %I:%M %p'):
    converted = utc_to_clinic(value)
    return f'{converted.strftime(pattern)} PKT' if converted else 'N/A'
