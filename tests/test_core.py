import unittest
from datetime import datetime, timedelta

from app import create_app
from app.extensions import db
from app.models import (Appointment, ClinicianProfile, ClinicianTimeOff,
                        PatientProfile, User)


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

    def test_inactive_clinician_cannot_login(self):
        self.clinician_user.is_active = False
        db.session.commit()
        response = self.client.post('/auth/clinician/login', data={
            'username': 'doctor', 'password': 'StrongPass123!'
        })
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as session:
            self.assertNotIn('user_id', session)

    def test_public_api_cannot_register_privileged_role(self):
        response = self.client.post('/api/auth/register', json={
            'email': 'new@example.test', 'phone': '5000',
            'password': 'StrongPass123!', 'full_name': 'New User', 'role': 'admin'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.find_by_identifier('new@example.test').role, 'patient')

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
