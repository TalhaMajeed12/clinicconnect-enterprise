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


def search_patients_by_fields(query, filters=None, legacy_search=''):
    """Apply independent patient search slots while preserving legacy links."""
    filters = filters or {}
    patients = search_patients(query, legacy_search)

    def contains(value, query_value):
        target = _normalize(query_value)
        if not target:
            return True
        normalized = _normalize(value)
        compact_target = re.sub(r'[^a-z0-9]', '', target)
        compact_value = re.sub(r'[^a-z0-9]', '', normalized)
        return target in normalized or (compact_target and compact_target in compact_value)

    matches = []
    for patient in patients:
        user = patient.user
        if not user:
            continue
        reference_values = (patient_reference(patient), patient.id, user.uuid,
                            user.uuid[:8] if user.uuid else '')
        name_values = (user.full_name, user.username)
        contact_values = (user.email, user.phone)
        dob_value = user.date_of_birth.isoformat() if user.date_of_birth else ''
        if filters.get('patient_no') and not any(
                contains(value, filters['patient_no']) for value in reference_values):
            continue
        name_terms = [_normalize(term) for term in filters.get('name', '').split() if _normalize(term)]
        if name_terms and not all(
                any(term in _normalize(value) for value in name_values) for term in name_terms):
            continue
        if filters.get('contact') and not any(
                contains(value, filters['contact']) for value in contact_values):
            continue
        if filters.get('date_of_birth') and dob_value != filters['date_of_birth']:
            continue
        matches.append(patient)
    return matches
