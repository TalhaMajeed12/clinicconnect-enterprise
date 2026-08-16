import unittest
import re
import json
from unittest.mock import patch
from urllib.parse import urlparse
from datetime import datetime, timedelta

from app import create_app
from app.extensions import db
from app.models import (Appointment, ClinicianProfile, ClinicianTimeOff,
                        PasswordResetToken, PatientProfile, User)


class CoreFlowTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()

        self.admin = self._user('admin', 'admin', 'admin@example.test', '1000')
        self.clinician_user = self._user('doctor', 'clinician', 'doctor@example.test', '2000')
        self.clinician = ClinicianProfile(
            user_id=self.clinician_user.id,
            specialty='General Medicine',
            is_available=True,
            working_days=['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'],
            working_hours={'start': '00:00', 'end': '23:59'},
        )
        self.patient_user = self._user('patient', 'patient', 'patient@example.test', '3000')
        self.patient = PatientProfile(user_id=self.patient_user.id)
        db.session.add_all([self.clinician, self.patient])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _user(self, username, role, email, phone):
        user = User(username=username, role=role, full_name=username.title(), email=email, phone=phone)
        user.set_password('StrongPass123!')
        db.session.add(user)
        db.session.flush()
        return user

    def _session_as(self, user):
        with self.client.session_transaction() as session:
            session['user_id'] = user.id
            session['role'] = user.role

    def test_role_protected_dashboards(self):
        self._session_as(self.patient_user)
        self.assertEqual(self.client.get('/patient/dashboard').status_code, 200)
        self.assertEqual(self.client.get('/admin/dashboard').status_code, 302)
        self.assertEqual(self.client.get('/clinician/dashboard').status_code, 302)

    def test_admin_can_add_clinician_with_required_contact_details(self):
        self._session_as(self.admin)
        response = self.client.post('/admin/add-clinician', data={
            'username': 'newdoctor',
            'password': 'StrongPass123!',
            'full_name': 'New Doctor',
            'email': 'newdoctor@example.test',
            'phone': '5550100',
            'specialty': 'Cardiology',
            'license_number': 'LIC-100',
            'years_experience': '5',
            'consultation_fee': '2500',
        })
        self.assertEqual(response.status_code, 302)
        created = User.query.filter_by(username='newdoctor').one()
        self.assertEqual(created.clinician_profile.specialty, 'Cardiology')

    def test_add_clinician_explains_missing_required_contact(self):
        self._session_as(self.admin)
        response = self.client.post('/admin/add-clinician', data={
            'username': 'newdoctor',
            'password': 'StrongPass123!',
            'full_name': 'New Doctor',
            'specialty': 'Cardiology',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Email is required.', response.data)
        self.assertIsNone(User.query.filter_by(username='newdoctor').first())

    def test_encrypted_identifier_login_and_role_logout(self):
        response = self.client.post('/auth/login', data={
            'identifier': 'PATIENT@EXAMPLE.TEST', 'password': 'StrongPass123!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('/patient/dashboard', response.location)
        response = self.client.get('/auth/logout')
        self.assertIn('/auth/login', response.location)

    def test_patient_cannot_cancel_another_patients_appointment(self):
        other_user = self._user('other', 'patient', 'other@example.test', '4000')
        other = PatientProfile(user_id=other_user.id)
        db.session.add(other)
        db.session.flush()
        appointment = Appointment(patient_id=other.id, clinician_id=self.clinician.id,
                                  appointment_date=datetime.utcnow() + timedelta(days=1))
        db.session.add(appointment)
        db.session.commit()
        self._session_as(self.patient_user)
        self.client.post(f'/patient/cancel-appointment/{appointment.id}')
        self.assertNotEqual(db.session.get(Appointment, appointment.id).status, 'cancelled')

    def test_booking_rejects_conflict(self):
        slot = (datetime.utcnow() + timedelta(days=2)).replace(second=0, microsecond=0)
        existing = Appointment(patient_id=self.patient.id, clinician_id=self.clinician.id,
                               appointment_date=slot, duration=30, status='confirmed')
        db.session.add(existing)
        db.session.commit()
        self._session_as(self.patient_user)
        response = self.client.post('/appointments/book', data={
            'clinician_id': self.clinician.id,
            'appointment_date': slot.strftime('%Y-%m-%dT%H:%M'),
            'reason': 'Checkup',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Appointment.query.count(), 1)

    def test_patient_can_open_checkout_and_record_demo_payment(self):
        appointment = Appointment(
            patient_id=self.patient.id,
            clinician_id=self.clinician.id,
            appointment_date=datetime.utcnow() + timedelta(days=1),
            status='pending',
        )
        db.session.add(appointment)
        db.session.commit()
        self._session_as(self.patient_user)

        checkout = self.client.get(f'/payment/checkout/{appointment.id}')
        self.assertEqual(checkout.status_code, 200)
        self.assertIn(b'PKR 500.00', checkout.data)

        processed = self.client.post('/payment/process', data={
            'appointment_id': appointment.id,
        })
        self.assertEqual(processed.status_code, 302)
        self.assertIn(f'/payment/success/{appointment.id}', processed.location)
        self.assertEqual(db.session.get(Appointment, appointment.id).status, 'confirmed')

    def test_clinician_can_update_appointment_status_with_csrf_enabled(self):
        appointment = Appointment(
            patient_id=self.patient.id,
            clinician_id=self.clinician.id,
            appointment_date=datetime.utcnow() + timedelta(days=1),
            status='confirmed',
        )
        db.session.add(appointment)
        db.session.commit()
        self._session_as(self.clinician_user)
        self.app.config['WTF_CSRF_ENABLED'] = True

        page = self.client.get('/clinician/appointments')
        token_match = re.search(rb"const csrfToken = '([^']+)'", page.data)
        self.assertIsNotNone(token_match)
        response = self.client.post(
            f'/clinician/appointment/{appointment.id}/update',
            json={'status': 'completed'},
            headers={'X-CSRFToken': token_match.group(1).decode()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['success'])
        self.assertEqual(db.session.get(Appointment, appointment.id).status, 'completed')

    def test_inactive_clinician_cannot_login(self):
        self.clinician_user.is_active = False
        db.session.commit()
        response = self.client.post('/auth/clinician/login', data={
            'username': 'doctor', 'password': 'StrongPass123!'
        })
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as session:
            self.assertNotIn('user_id', session)

    def test_public_registration_is_disabled(self):
        response = self.client.post('/api/auth/register', json={
            'email': 'new@example.test', 'phone': '5000',
            'password': 'StrongPass123!', 'full_name': 'New User', 'role': 'admin'
        })
        self.assertEqual(response.status_code, 403)
        self.assertIsNone(User.find_by_identifier('new@example.test'))

        web_response = self.client.post('/auth/register', data={
            'username': 'new', 'email': 'new@example.test', 'phone': '5000',
            'password': 'StrongPass123!', 'confirm_password': 'StrongPass123!',
            'full_name': 'New User',
        })
        self.assertEqual(web_response.status_code, 403)
        self.assertIsNone(User.find_by_identifier('new@example.test'))

    def test_security_headers_are_present(self):
        response = self.client.get('/')
        self.assertIn("default-src 'self'", response.headers['Content-Security-Policy'])
        self.assertEqual(
            response.headers['Referrer-Policy'],
            'strict-origin-when-cross-origin',
        )
        self.assertIn('camera=()', response.headers['Permissions-Policy'])

    @patch('app.routes.auth.send_password_reset_link', return_value=True)
    def test_patient_password_reset_is_single_use(self, send_reset):
        response = self.client.post('/auth/forgot-password', data={
            'identifier': 'patient@example.test',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(send_reset.call_count, 1)
        self.assertEqual(PasswordResetToken.query.count(), 1)

        reset_url = send_reset.call_args.args[1]
        reset_path = urlparse(reset_url).path
        reset = self.client.post(reset_path, data={
            'password': 'ChangedPass123!',
            'confirm_password': 'ChangedPass123!',
        })
        self.assertEqual(reset.status_code, 302)
        self.assertTrue(self.patient_user.check_password('ChangedPass123!'))

        reused = self.client.get(reset_path)
        self.assertEqual(reused.status_code, 302)
        self.assertIn('/auth/forgot-password', reused.location)

    @patch('app.routes.auth.send_password_reset_link', return_value=True)
    def test_password_reset_does_not_reveal_unknown_accounts(self, send_reset):
        response = self.client.post('/auth/forgot-password', data={
            'identifier': 'unknown@example.test',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'If that patient account can receive email', response.data)
        send_reset.assert_not_called()

    @patch('app.utils.email.urlopen')
    def test_brevo_email_transport_uses_https_api(self, open_url):
        from app.utils.email import send_email

        response = open_url.return_value.__enter__.return_value
        response.status = 201
        self.app.config.update(
            EMAIL_PROVIDER='brevo',
            BREVO_API_KEY='test-api-key',
            MAIL_DEFAULT_SENDER='ClinicConnect <verified@example.test>',
        )

        with self.app.app_context():
            delivered = send_email(
                'Reset password', 'patient@example.test', '<p>Reset</p>'
            )

        self.assertTrue(delivered)
        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.brevo.com/v3/smtp/email')
        self.assertEqual(request.headers['Api-key'], 'test-api-key')
        payload = json.loads(request.data.decode('utf-8'))
        self.assertEqual(payload['to'][0]['email'], 'patient@example.test')
        self.assertNotIn('test-api-key', request.data.decode('utf-8'))

    def test_api_cors_rejects_untrusted_origins(self):
        rejected = self.client.get('/api/health', headers={
            'Origin': 'https://attacker.example',
        })
        self.assertIsNone(rejected.headers.get('Access-Control-Allow-Origin'))

        allowed = self.client.get('/api/health', headers={
            'Origin': 'https://clinicconnect-enterprise.onrender.com',
        })
        self.assertEqual(
            allowed.headers.get('Access-Control-Allow-Origin'),
            'https://clinicconnect-enterprise.onrender.com',
        )

    def test_patient_api_cannot_list_all_patients(self):
        login = self.client.post('/api/auth/login', json={
            'identifier': 'patient@example.test', 'password': 'StrongPass123!'
        }).get_json()
        response = self.client.get('/api/patients', headers={
            'Authorization': f"Bearer {login['token']}"
        })
        self.assertEqual(response.status_code, 403)

    def test_booking_rejects_full_day_time_off(self):
        slot = (datetime.utcnow() + timedelta(days=3)).replace(hour=10, minute=0, second=0, microsecond=0)
        db.session.add(ClinicianTimeOff(
            clinician_id=self.clinician.id,
            start_date=slot.date(),
            end_date=slot.date(),
            full_day=True,
            status='approved',
        ))
        db.session.commit()
        self._session_as(self.patient_user)
        response = self.client.post('/appointments/book', data={
            'clinician_id': self.clinician.id,
            'appointment_date': slot.strftime('%Y-%m-%dT%H:%M'),
            'reason': 'Checkup',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Appointment.query.count(), 0)

    def test_partial_time_off_blocks_only_overlapping_slots(self):
        slot = (datetime.utcnow() + timedelta(days=4)).replace(hour=12, minute=0, second=0, microsecond=0)
        db.session.add(ClinicianTimeOff(
            clinician_id=self.clinician.id,
            start_date=slot.date(),
            end_date=slot.date(),
            start_time=slot.replace(hour=11).time(),
            end_time=slot.replace(hour=13).time(),
            full_day=False,
            status='approved',
        ))
        db.session.commit()
        self._session_as(self.patient_user)
        self.client.post('/appointments/book', data={
            'clinician_id': self.clinician.id,
            'appointment_date': slot.strftime('%Y-%m-%dT%H:%M'),
            'reason': 'Blocked',
        })
        self.assertEqual(Appointment.query.count(), 0)
        allowed = slot.replace(hour=14)
        response = self.client.post('/appointments/book', data={
            'clinician_id': self.clinician.id,
            'appointment_date': allowed.strftime('%Y-%m-%dT%H:%M'),
            'reason': 'Allowed',
        })
        self.assertIn('/payment/checkout/', response.location)
        self.assertEqual(Appointment.query.count(), 1)


if __name__ == '__main__':
    unittest.main()
