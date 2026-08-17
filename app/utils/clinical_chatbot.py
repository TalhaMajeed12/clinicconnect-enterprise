import re


DISCLAIMER = (
    'This assistant provides general information only and cannot diagnose, '
    'prescribe, or replace a clinician.'
)

URDU_DISCLAIMER = (
    'یہ معاون صرف عمومی معلومات فراہم کرتا ہے اور تشخیص، دوا تجویز یا ڈاکٹر '
    'کا متبادل نہیں ہے۔'
)

URDU_MESSAGES = {
    'empty': 'براہ کرم سوال لکھیں یا تجویز کردہ موضوع منتخب کریں۔',
    'emergency': (
        'یہ ہنگامی حالت ہو سکتی ہے۔ فوراً مقامی ایمرجنسی سروس سے رابطہ کریں '
        '(پاکستان میں جہاں دستیاب ہو ریسکیو 1122) یا قریبی ایمرجنسی جائیں۔ '
        'چیٹ بوٹ کے جواب کا انتظار نہ کریں۔'
    ),
    'medication': (
        'دوا صرف ڈاکٹر کی ہدایت کے مطابق لیں۔ چیٹ بوٹ کے مشورے پر دوا شروع، '
        'بند، دوگنی یا خوراک تبدیل نہ کریں۔ خوراک، باہمی اثرات، حمل، الرجی یا '
        'مضر اثرات کے بارے میں ڈاکٹر یا فارماسسٹ سے پوچھیں۔'
    ),
    'appointment': (
        'اپوائنٹمنٹ بک کریں کے ذریعے دستیاب ڈاکٹر اور آئندہ وقت منتخب کریں۔ '
        'موجودہ اپوائنٹمنٹس ڈیش بورڈ پر دیکھی اور اہل ہونے پر منسوخ کی جا سکتی ہیں۔'
    ),
    'records': (
        'مریض اپنی طبی تاریخ اور نسخے ہسٹری میں دیکھ سکتے ہیں۔ یہ چیٹ بوٹ کسی '
        'کا طبی ریکارڈ نہیں پڑھتا، خلاصہ نہیں بناتا اور ظاہر نہیں کرتا۔'
    ),
    'account': (
        'مریض لاگ ان صفحے پر پاس ورڈ بھول گئے کا استعمال کریں۔ اپنا پاس ورڈ یا '
        'ری سیٹ لنک چیٹ میں کبھی شیئر نہ کریں۔'
    ),
    'symptoms': (
        'میں علامات کی وجہ یا شدت طے نہیں کر سکتا۔ مستند ڈاکٹر سے اپوائنٹمنٹ لیں۔ '
        'اچانک یا شدید علامات، سینے میں درد، سانس کی شدید تکلیف، بے ہوشی، زیادہ '
        'خون بہنا یا فالج کی علامات میں فوراً ایمرجنسی مدد حاصل کریں۔'
    ),
    'general': (
        'میں اپوائنٹمنٹ، ریکارڈ تک رسائی، پاس ورڈ، دوا کی حفاظت اور ہنگامی مدد '
        'کے بارے میں عمومی رہنمائی دے سکتا ہوں۔ نجی طبی معلومات شامل نہ کریں۔'
    ),
}


def _reply(intent, message, emergency, language):
    if language == 'ur':
        message = URDU_MESSAGES[intent]
        disclaimer = URDU_DISCLAIMER
    else:
        disclaimer = DISCLAIMER
    return {
        'intent': intent,
        'emergency': emergency,
        'message': message,
        'disclaimer': disclaimer,
    }

EMERGENCY_TERMS = (
    'chest pain', 'crushing chest', 'cannot breathe', "can't breathe",
    'severe difficulty breathing', 'face drooping', 'face weakness',
    'slurred speech', 'one-sided weakness', 'unconscious', 'not breathing',
    'severe bleeding', 'suicide', 'kill myself', 'overdose', 'seizure',
    'سینے میں درد', 'سانس نہیں', 'سانس کی شدید', 'بے ہوش', 'خون بہ',
    'فالج', 'خودکشی', 'زیادہ دوا',
)


def _contains(text, terms):
    return any(term in text for term in terms)


def clinical_support_reply(message, language='en'):
    """Return conservative, deterministic guidance without accessing EHR data."""
    text = ' '.join((message or '').strip().casefold().split())
    if not text:
        return _reply('empty', 'Please type a question or choose one of the suggested topics.', False, language)

    if _contains(text, EMERGENCY_TERMS):
        return _reply('emergency', (
                'This may be an emergency. Call your local emergency service now '
                '(in Pakistan, Rescue 1122 where available) or go to the nearest '
                'emergency department. Do not wait for a chatbot response or drive '
                'yourself if you may be seriously unwell.'
            ), True, language)

    if _contains(text, ('medicine', 'medication', 'tablet', 'dose', 'prescription',
                        'side effect', 'allergy', 'drug', 'دوا', 'ادویات', 'خوراک',
                        'نسخہ', 'مضر اثر')):
        return _reply('medication', (
                'Take medicines only as prescribed. Do not start, stop, double, or '
                'change a dose based on chatbot advice. Check the medicine name and '
                'instructions, and ask your clinician or pharmacist about missed '
                'doses, interactions, pregnancy, allergies, or side effects. For '
                'breathing difficulty, facial swelling, collapse, or a suspected '
                'overdose, seek emergency help now.'
            ), False, language)

    if _contains(text, ('appointment', 'book', 'booking', 'cancel', 'doctor', 'clinician',
                        'اپوائنٹمنٹ', 'ڈاکٹر', 'بک', 'منسوخ')):
        return _reply('appointment', (
                'Use Book Appointment to select an available clinician and a future '
                'slot. Existing appointments appear on your dashboard and can be '
                'cancelled while eligible. If no clinician appears, the clinician '
                'may be inactive, unavailable, outside working hours, or on time off.'
            ), False, language)

    if _contains(text, ('history', 'record', 'diagnosis', 'visit', 'prescription',
                        'تاریخ', 'ریکارڈ', 'تشخیص', 'نسخے')):
        return _reply('records', (
                'Patients can review recorded visits and prescriptions from History. '
                'Clinicians can open an authorized Patient Folder. This chatbot does '
                'not read, summarize, or disclose anyone’s medical record.'
            ), False, language)

    if _contains(text, ('password', 'forgot', 'login', 'account', 'پاس ورڈ',
                        'لاگ ان', 'اکاؤنٹ')):
        return _reply('account', (
                'Use Forgot Password on the patient login page for a single-use reset '
                'link. Clinician and admin account issues should be handled by an '
                'administrator. Never share a password or reset link in chat.'
            ), False, language)

    symptom_words = re.search(
        r'\b(pain|fever|cough|vomit|dizzy|rash|headache|weak|sick|symptom)\b', text
    )
    if symptom_words or _contains(text, ('درد', 'بخار', 'کھانسی', 'چکر', 'علامات', 'کمزوری')):
        return _reply('symptoms', (
                'I cannot determine the cause or severity of symptoms. Arrange an '
                'appointment with a qualified clinician. If symptoms are sudden, '
                'severe, rapidly worsening, or include chest pain, severe breathing '
                'difficulty, fainting, heavy bleeding, or stroke signs, seek emergency '
                'care immediately.'
            ), False, language)

    return _reply('general', (
            'I can help with appointments, accessing records, password recovery, '
            'medication-safety questions, and deciding when to seek urgent help. '
            'Please choose one of those topics; do not include private medical details.'
        ), False, language)
