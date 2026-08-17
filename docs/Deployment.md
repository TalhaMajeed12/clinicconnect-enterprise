# Deployment

ClinicConnect is deployed as a Python web service on Render with Gunicorn and PostgreSQL. The repository's `render.yaml`, `wsgi.py`, and `gunicorn.conf.py` are the production entry points.

## Required Render variables

- `FLASK_CONFIG=production`
- `DATABASE_URL`: Render PostgreSQL connection URL
- `SECRET_KEY`: long random value
- `ENCRYPTION_KEY`: stable Fernet key; never rotate without re-encrypting data
- `JWT_SECRET_KEY`: long random value
- `WTF_CSRF_SECRET_KEY`: long random value
- `SESSION_COOKIE_SECURE=True`
- `WTF_CSRF_ENABLED=True`
- `RATELIMIT_ENABLED=True`
- `CORS_ALLOWED_ORIGINS`: deployed application origin

Never paste these values into source files, documentation, logs, or Git.

## Transactional email on the free tier

Render free web services block outbound SMTP. Production therefore uses the Brevo HTTPS API:

- `EMAIL_PROVIDER=brevo`
- `BREVO_API_KEY`: Brevo v3 API key
- `MAIL_DEFAULT_SENDER`: a sender verified in Brevo

SMTP variables remain available for local development. Do not use an SMTP key as `BREVO_API_KEY`.

## Database migrations

Review the target database and create a backup before applying SQL manually:

```powershell
psql "$env:DATABASE_URL" --file="migrations/001_add_clinician_time_off.sql"
psql "$env:DATABASE_URL" --file="migrations/002_add_password_reset_tokens.sql"
psql "$env:DATABASE_URL" --file="migrations/003_add_audit_archiving.sql"
```

The migrations are additive. Never initialize or reset an existing production database to resolve migration errors.

Apply migration 003 before deploying the matching application commit. In the admin Activity Records page, archive operational audit entries older than 7, 30, or 90 days. Archiving never deletes records and does not affect appointments, visits, prescriptions, payments, or patient history.

## Backup and verification

Free Render PostgreSQL does not provide downloadable managed backups. Create a custom-format backup from a trusted workstation:

```powershell
pg_dump --format=custom --no-owner --no-privileges --file="clinicconnect.dump" "$env:DATABASE_URL"
pg_restore --list "clinicconnect.dump"
```

Store backups outside the repository and test restoration into a disposable database before relying on them.

## Production check

1. Confirm the deployment uses the expected Git commit.
2. Open `/api/health` and require `status=healthy` and `database=connected`.
3. Test one login for each role.
4. Test booking, a clinical visit, patient history, and password recovery.
5. Review Render and Brevo logs without exposing secrets or patient data.

The current free deployment uses one Gunicorn worker because filesystem-backed sessions and in-memory rate limiting are process-local. Configure a managed Redis URL before scaling to multiple workers.
