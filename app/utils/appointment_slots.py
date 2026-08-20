from datetime import datetime, time, timedelta

from app.models import Appointment, ClinicianTimeOff
from app.utils.timezone import clinic_now


ACTIVE_SLOT_STATUSES = ('pending', 'confirmed', 'checked_in')


def available_slots(clinician, target_date, now=None):
    """Return valid appointment starts for one clinician/day."""
    now = now or clinic_now()
    working_days = [str(day).lower() for day in (clinician.working_days or [])]
    if target_date.strftime('%A').lower() not in working_days:
        return []

    hours = clinician.working_hours or {}
    try:
        day_start = datetime.combine(target_date, time.fromisoformat(hours['start']))
        day_end = datetime.combine(target_date, time.fromisoformat(hours['end']))
    except (KeyError, TypeError, ValueError):
        return []

    duration = max(int(clinician.appointment_duration or 30), 5)
    appointments = Appointment.query.filter(
        Appointment.clinician_id == clinician.id,
        Appointment.appointment_date >= day_start,
        Appointment.appointment_date < day_start + timedelta(days=1),
        Appointment.status.in_(ACTIVE_SLOT_STATUSES),
    ).all()
    if len(appointments) >= int(clinician.max_patients_per_day or 30):
        return []

    leave_entries = ClinicianTimeOff.query.filter(
        ClinicianTimeOff.clinician_id == clinician.id,
        ClinicianTimeOff.status == 'approved',
        ClinicianTimeOff.start_date <= target_date,
        ClinicianTimeOff.end_date >= target_date,
    ).all()

    results = []
    cursor = day_start
    while cursor + timedelta(minutes=duration) <= day_end:
        cursor_end = cursor + timedelta(minutes=duration)
        conflict = any(
            cursor < item.appointment_date + timedelta(minutes=item.duration or 30)
            and cursor_end > item.appointment_date
            for item in appointments
        )
        on_leave = any(item.blocks(cursor, duration) for item in leave_entries)
        if cursor > now and not conflict and not on_leave:
            results.append(cursor)
        cursor += timedelta(minutes=duration)
    return results


def is_available_slot(clinician, appointment_start, now=None):
    return any(slot == appointment_start for slot in available_slots(
        clinician, appointment_start.date(), now=now
    ))
