# Requirements and Scope

This document describes the implemented ClinicConnect Enterprise v3.0 FYP scope. Items under Future Work are not claimed as production features.

## Functional requirements

### Authentication and security

- Admin, clinician, and patient login/logout
- Role-based route protection and inactive-account enforcement
- Hashed passwords and encrypted sensitive profile fields
- Single-use patient password-reset links delivered by email
- CSRF protection, secure production cookies, rate limiting, and security headers

### Administration

- Dashboard totals for patients, clinicians, appointments, and recorded revenue
- Create, view, edit, activate, and deactivate clinicians
- View and search patients and their retained history
- View appointments and audit logs

### Clinician portal

- Dashboard and relevant patient list/folders
- Create patient accounts through an authorized workflow
- Record visits, diagnoses, treatment plans, and prescriptions
- View appointments and update supported statuses
- Configure weekly working hours and availability
- Record full-day or partial-day time off

### Patient portal

- Dashboard, appointments, medical history, and prescriptions
- Book an active, available clinician
- Cancel an eligible future appointment
- Record an explicitly labelled FYP demonstration payment

### Scheduling rules

- Reject inactive or unavailable clinicians
- Reject dates outside working days/hours
- Reject clinician time off and overlapping appointments
- Allow different clinicians to hold appointments at the same time
- Preserve cancelled and completed appointment history

### Operations

- PostgreSQL persistence and additive migrations
- Health endpoint with database connectivity status
- Brevo HTTPS transactional email on free Render hosting
- Manual custom-format PostgreSQL backup procedure

## Non-functional requirements

- Preserve EHR and appointment history
- Prevent cross-role and altered-ID access
- Keep secrets outside Git and application logs
- Provide responsive Bootstrap-based pages
- Start through the Flask application factory and Gunicorn
- Run focused automated regression tests without production data

## FYP limitations

- Payment is a demo record; no real card or bank gateway is connected.
- Filesystem sessions and in-memory rate limits require one Gunicorn worker.
- Encrypted-field compatibility search is application-level rather than indexed.
- Public self-registration is disabled; authorized staff create accounts.
- The placeholder chatbot is not presented as a clinical decision system.

## Future work

- Managed Redis and multiple workers
- Keyed lookup hashes for indexed encrypted-field searches
- Real payment integration with verified webhooks
- Multi-branch organizations and receptionist/accountant roles
- Laboratory, file-upload, SMS, reminder, and document-export workflows
- Expanded performance, accessibility, and browser automation testing
