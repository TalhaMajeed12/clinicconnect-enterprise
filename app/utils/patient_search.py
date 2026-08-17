import re
import unicodedata


def patient_reference(patient):
    """Return a stable, human-friendly reference without exposing a UUID."""
    return f'CC-P{patient.id:06d}'


def _normalize(value):
    value = unicodedata.normalize('NFKC', str(value or '')).casefold()
    return ' '.join(value.split())


def _search_values(patient):
    user = patient.user
    if not user:
        return []

    date_of_birth = user.date_of_birth.isoformat() if user.date_of_birth else ''
    values = [
        patient_reference(patient),
        patient.id,
        user.uuid,
        user.uuid[:8] if user.uuid else '',
        user.username,
        user.full_name,
        user.email,
        user.phone,
        date_of_birth,
        patient.age,
        user.gender,
    ]
    normalized = [_normalize(value) for value in values if value not in (None, '')]
    normalized.extend(
        re.sub(r'[^a-z0-9]', '', value) for value in tuple(normalized)
    )
    return normalized


def search_patients(query, search=''):
    """Search encrypted patient data after authorized application-level access."""
    patients = query.all()
    terms = [_normalize(term) for term in search.split() if _normalize(term)]

    if terms:
        matches = []
        for patient in patients:
            values = _search_values(patient)
            if all(any(term in value for value in values) for term in terms):
                matches.append(patient)
        patients = matches

    return sorted(
        patients,
        key=lambda patient: (
            _normalize(patient.user.full_name if patient.user else ''),
            patient.id,
        ),
    )
