# ClinicConnect Enterprise

## Overview

ClinicConnect Enterprise is a Flask/PostgreSQL clinic-management and electronic health-record Final Year Project. It connects patient, clinician, and administrator workflows without claiming to be a certified production medical platform.

## Problem Statement and Objectives

Small clinics often keep scheduling, consultations, clinical notes, prescriptions, and operational records in disconnected systems. ClinicConnect demonstrates one understandable, role-protected workflow from appointment request through longitudinal history. Its objectives are reliable scheduling, controlled record access, traceable operations, and an examiner-friendly video-consultation demonstration.

## Features and User Roles

- **Patients:** clinician discovery, real availability, in-person/video requests, demo deposits, video rooms, history, prescriptions, and completed-appointment reviews.
- **Clinicians:** assigned patients, schedules, availability/time off, secure messages/video, visit notes, prescriptions, and valid status transitions.
- **Administrators:** clinician/patient management, appointment oversight, real database statistics, guest intake verification, and filtered audit activity.
- **Public assistant:** bilingual general product guidance, emergency escalation, and privacy-conscious first-appointment intake. It does not diagnose or read EHR records.

## Technology Stack

Python/Flask, SQLAlchemy, PostgreSQL, Jinja, Bootstrap/CSS/JavaScript, Gunicorn, Fernet field encryption, Werkzeug password hashing, and Jitsi Meet for browser-based WebRTC calls.

## System Architecture

```text
Browser -> Flask routes + authentication/CSRF
        -> server-side role and object authorization
        -> scheduling/clinical rules -> SQLAlchemy -> PostgreSQL

Authorized patient browser --\
                              Jitsi Meet (WebRTC media/signaling)
Authorized clinician browser-/
```

Flask remains the authority for room eligibility. Jitsi receives no database credentials and the application stores no media. See [System Architecture](docs/System_Architecture.md).

## Database Overview

User 1:0/1 Patient/Clinician profile; Patient and Clinician 1:many Appointments; Appointment 0/1:1 VideoConsultation; Appointment 0/1:1 Visit; Visit 1:many Prescriptions; completed Appointment 0/1:1 DoctorReview. Availability, time off, payments, encrypted messages, guest requests, and audit logs support that lifecycle. See [Database Design](docs/Database_Design.md).

## Appointment Scheduling Logic

One availability engine applies weekly working hours, approved time off, duration, existing active appointments, and future-time validation to both visit types. Booking locks the clinician row, rechecks inside the transaction, and migration `006` adds a partial unique exact-slot index. Requests start `pending`; only permitted transitions are accepted.

## Video Consultation Architecture

A booking must explicitly be `video`. An authenticated assigned patient or clinician enters through an unpredictable token, but the token never replaces server authorization. Flask checks type, status, ownership, and a configurable join window before activating the VideoConsultation. The page performs local camera/microphone preflight and loads Jitsi only after Enter.

Jitsi is a maintainable WebRTC integration suitable for this FYP and supplies signaling plus deployed NAT traversal/media infrastructure. Native WebRTC would need a separate signaling service; STUN alone fails on some restrictive NATs, so a controlled production deployment needs contracted/private infrastructure with TURN and a suitable privacy policy.

## Security Measures

- Passwords are one-way hashed; profile contact fields and consultation messages are Fernet-encrypted.
- Secrets and credentials come only from environment configuration.
- Secure/HttpOnly/SameSite cookies, CSRF, rate limits, security headers, and restricted CORS are centralized.
- Sensitive routes enforce roles and object ownership server-side; public self-registration is disabled.
- Audits exclude passwords, tokens, message bodies, and full medical notes.
- Never rotate `ENCRYPTION_KEY` without a tested re-encryption plan and backup.

## Installation, Database Setup, and Local Run

1. `python -m venv venv`, then activate `venv\Scripts\activate` on Windows.
2. `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env`, replace placeholders, and generate a Fernet key with `Fernet.generate_key()`.
4. Create PostgreSQL and apply `migrations/001...007` in order.
5. Provision users explicitly and run `python run.py`.

Startup intentionally does not create tables or bootstrap an administrator. Back up production before migrations; project migrations are additive and do not intentionally delete clinical data.

## Environment Variables

Production requires `DATABASE_URL`, `SECRET_KEY`, `ENCRYPTION_KEY`, `WTF_CSRF_SECRET_KEY`, and `JWT_SECRET_KEY`. Video policy uses `VIDEO_CONSULTATION_BASE_URL`, `VIDEO_JOIN_EARLY_MINUTES`, and `VIDEO_JOIN_GRACE_MINUTES`. Email, Redis, CORS, session, and audit settings are in `.env.example`. Never commit real values.

## Running Tests

Run `python -m unittest discover -s tests -v`. Tests use isolated SQLite and cover authentication/RBAC, scheduling/time off/conflicts, encrypted intake, payments, consultations, history, reviews, auditing, and security behavior.

## Demo Accounts and Data

Use fictional records only. No production credentials are committed. Provision separate demo admin, clinician, and patient accounts plus a same-day confirmed video appointment; store credentials outside Git.

## Deployment

Render uses `render.yaml`, `Procfile`, `wsgi.py`, and Gunicorn. HTTPS is mandatory for browser media. Apply migrations through `007_add_forced_password_change.sql` before this release. The free deployment uses one worker with local sessions/rate limits; use Redis before scaling. Brevo HTTPS email works where SMTP egress is blocked. See [Deployment](docs/Deployment.md).

Privileged password recovery is deliberately separated: verified clinicians may request an email reset, or an authenticated administrator may issue a temporary password that must be replaced at next login. Administrators have no public email-reset path. A system owner with trusted shell access can run `flask recover-admin`, which prompts interactively for the username and new password and records the recovery in the audit log.

## Project Structure

`app/models` entities; `app/routes` blueprints; `app/utils` shared rules; `app/templates` role UI; `app/static` assets; `migrations` additive SQL; `tests` automated flows; `docs` engineering documentation.

## Known Limitations

- Public Jitsi is suitable for an academic demo, not a contractual healthcare deployment; quality depends on networks/provider availability.
- No recording, transcription, insurance, interoperability, or native mobile app.
- Payment is a demo recorder and never collects real card details.
- Filesystem sessions and in-memory rate limits require Redis before scaling.
- The assistant offers general guidance only, not diagnosis.

## FYP Demonstration Flow

Patient login -> choose clinician/video slot -> request/show status -> demo deposit -> clinician login -> scheduled room/device preflight -> linked visit/prescription -> complete -> patient history/prescription -> eligible review -> admin statistics/audit trail.

## Technical Justifications and Future Improvements

Flask keeps architecture explainable; PostgreSQL supplies transactional integrity; server authorization protects manipulated URLs; one availability engine prevents divergent schedules; video attaches to appointments so consultation, visit, prescription, history, and review form one traceable chain. Future work: private managed video/TURN, Redis, indexed keyed hashes for encrypted identifier lookup, FHIR export, and a PCI-compliant payment provider.
