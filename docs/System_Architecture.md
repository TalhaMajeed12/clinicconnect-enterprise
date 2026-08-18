# System Architecture

ClinicConnect uses a conventional Flask application-factory architecture. It is kept intentionally compact for an FYP: routes coordinate validation and business rules, SQLAlchemy models manage persistence, and Jinja templates render the UI.

```text
Browser / API client
        |
Gunicorn + Flask application factory
        |
Blueprint routes and authorization helpers
        |
SQLAlchemy models and transactions
        |
PostgreSQL
```

## Application structure

- `app/__init__.py`: application factory, extension initialization, headers, logging, and blueprint registration
- `app/config.py`: development, testing, and production configuration
- `app/extensions.py`: shared Flask extension instances
- `app/models/`: users, profiles, appointments, visits, prescriptions, payments, audit records, time off, and password reset tokens
- `app/routes/`: role portals, appointments, payment, and API endpoints
- `app/templates/`: role-specific Jinja/Bootstrap views
- `app/utils/`: authorization, translations, OTP, and transactional email
- `migrations/`: reviewed additive SQL migrations
- `tests/`: focused critical-flow tests

## Production services

- Render web service runs Gunicorn
- Render PostgreSQL stores application and EHR data
- Brevo sends transactional email over HTTPS
- Redis is optional; when absent, the single-worker deployment uses filesystem sessions and in-memory rate limiting

The application does not initialize tables or create administrators at startup. This prevents hidden writes and protects existing production data.
# Integrated Video Consultation (2026 update)

Video is an appointment capability, not a separate record silo. Flask verifies the authenticated user, appointment ownership, `video` type, permitted status, and centralized time window before rendering an unpredictable token room. The browser then performs a local `getUserMedia()` preflight and embeds Jitsi Meet. Jitsi supplies WebRTC signaling and NAT traversal; ClinicConnect stores only lifecycle timestamps and encrypted text messages, never audio/video. A regulated deployment should replace the public service with contracted or self-hosted infrastructure including TURN.
