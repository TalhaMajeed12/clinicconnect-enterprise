# ClinicConnect Enterprise

ClinicConnect Enterprise is a university Final Year Project demonstrating a clinic-management and Electronic Health Record workflow for private clinics. The current application supports three roles: administrator, clinician, and patient.

## Implemented scope

- Role-specific authentication, authorization, logout, and inactive accounts
- Administrator dashboards, clinician management, patient records, appointments, revenue summaries, and audit logs
- Clinician patient folders, visits, prescriptions, appointments, availability, and full-day or partial-day time off
- Patient dashboard, medical history, prescriptions, appointment booking and cancellation, and clearly labelled demo payment records
- Conflict-aware scheduling using clinician hours, availability, and time off
- Secure, single-use password reset links delivered by an HTTPS email API
- Health and protected JSON API endpoints
- Multi-field patient search with stable patient numbers for duplicate-name disambiguation
- Authenticated safety-first clinical support chatbot with emergency escalation

## Technology stack

- Python 3 and Flask
- SQLAlchemy and PostgreSQL
- Flask-Login, Flask-WTF/CSRF, Flask-Limiter, and Flask-Session
- Jinja templates, Bootstrap 5, CSS, and JavaScript
- Gunicorn and Render
- Optional Redis for shared sessions and rate limiting
- Brevo HTTPS API for production transactional email

## Data and security

Profile fields such as email, phone, and name are encrypted with Fernet. The `ENCRYPTION_KEY` must remain stable for the lifetime of existing encrypted data. Passwords are hashed, roles are enforced on server routes, sensitive forms use CSRF protection, and production responses include security headers.

Medical history is retained. Clinicians are deactivated rather than hard-deleted when historical relationships exist. The payment module is an FYP demo recorder and does not process real cards or bank transfers.

## Current version

Version 3.0.0
