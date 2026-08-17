import re


DISCLAIMER = (
    'This assistant provides general information only and cannot diagnose, '
    'prescribe, or replace a clinician.'
)

EMERGENCY_TERMS = (
    'chest pain', 'crushing chest', 'cannot breathe', "can't breathe",
    'severe difficulty breathing', 'face drooping', 'face weakness',
    'slurred speech', 'one-sided weakness', 'unconscious', 'not breathing',
    'severe bleeding', 'suicide', 'kill myself', 'overdose', 'seizure',
)


def _contains(text, terms):
    return any(term in text for term in terms)


def clinical_support_reply(message):
    """Return conservative, deterministic guidance without accessing EHR data."""
    text = ' '.join((message or '').strip().casefold().split())
    if not text:
        return {
            'intent': 'empty',
            'emergency': False,
            'message': 'Please type a question or choose one of the suggested topics.',
            'disclaimer': DISCLAIMER,
        }

    if _contains(text, EMERGENCY_TERMS):
        return {
            'intent': 'emergency',
            'emergency': True,
            'message': (
                'This may be an emergency. Call your local emergency service now '
                '(in Pakistan, Rescue 1122 where available) or go to the nearest '
                'emergency department. Do not wait for a chatbot response or drive '
                'yourself if you may be seriously unwell.'
            ),
            'disclaimer': DISCLAIMER,
        }

    if _contains(text, ('medicine', 'medication', 'tablet', 'dose', 'prescription',
                        'side effect', 'allergy', 'drug')):
        return {
            'intent': 'medication',
            'emergency': False,
            'message': (
                'Take medicines only as prescribed. Do not start, stop, double, or '
                'change a dose based on chatbot advice. Check the medicine name and '
                'instructions, and ask your clinician or pharmacist about missed '
                'doses, interactions, pregnancy, allergies, or side effects. For '
                'breathing difficulty, facial swelling, collapse, or a suspected '
                'overdose, seek emergency help now.'
            ),
            'disclaimer': DISCLAIMER,
        }

    if _contains(text, ('appointment', 'book', 'booking', 'cancel', 'doctor', 'clinician')):
        return {
            'intent': 'appointment',
            'emergency': False,
            'message': (
                'Use Book Appointment to select an available clinician and a future '
                'slot. Existing appointments appear on your dashboard and can be '
                'cancelled while eligible. If no clinician appears, the clinician '
                'may be inactive, unavailable, outside working hours, or on time off.'
            ),
            'disclaimer': DISCLAIMER,
        }

    if _contains(text, ('history', 'record', 'diagnosis', 'visit', 'prescription')):
        return {
            'intent': 'records',
            'emergency': False,
            'message': (
                'Patients can review recorded visits and prescriptions from History. '
                'Clinicians can open an authorized Patient Folder. This chatbot does '
                'not read, summarize, or disclose anyone’s medical record.'
            ),
            'disclaimer': DISCLAIMER,
        }

    if _contains(text, ('password', 'forgot', 'login', 'account')):
        return {
            'intent': 'account',
            'emergency': False,
            'message': (
                'Use Forgot Password on the patient login page for a single-use reset '
                'link. Clinician and admin account issues should be handled by an '
                'administrator. Never share a password or reset link in chat.'
            ),
            'disclaimer': DISCLAIMER,
        }

    symptom_words = re.search(
        r'\b(pain|fever|cough|vomit|dizzy|rash|headache|weak|sick|symptom)\b', text
    )
    if symptom_words:
        return {
            'intent': 'symptoms',
            'emergency': False,
            'message': (
                'I cannot determine the cause or severity of symptoms. Arrange an '
                'appointment with a qualified clinician. If symptoms are sudden, '
                'severe, rapidly worsening, or include chest pain, severe breathing '
                'difficulty, fainting, heavy bleeding, or stroke signs, seek emergency '
                'care immediately.'
            ),
            'disclaimer': DISCLAIMER,
        }

    return {
        'intent': 'general',
        'emergency': False,
        'message': (
            'I can help with appointments, accessing records, password recovery, '
            'medication-safety questions, and deciding when to seek urgent help. '
            'Please choose one of those topics; do not include private medical details.'
        ),
        'disclaimer': DISCLAIMER,
    }
