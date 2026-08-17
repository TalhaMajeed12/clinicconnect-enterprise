# ClinicConnect Enterprise

ClinicConnect Enterprise is a Flask/PostgreSQL clinic-management and EHR Final Year Project with separate admin, clinician, and patient portals.

## Local setup

1. Create and activate a virtual environment:
   `python -m venv venv` then `venv\Scripts\activate` on Windows.
2. Install dependencies: `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and replace every placeholder. Keep PostgreSQL in `DATABASE_URL`; generate a Fernet key with `Fernet.generate_key()` for `ENCRYPTION_KEY`. Once encrypted data exists, keep that key unchanged.
4. Apply the project schema using the approved database initialization/migration workflow. Never run initialization against production without reviewing the target database.
5. Start locally with `python run.py`.

The app does not create tables or bootstrap an administrator during startup. This avoids hidden production writes. Administrator credentials must be provisioned explicitly and must never use a shared default password.

## Roles and core flows

- Admin: dashboard metrics, patient/clinician records, appointments, soft activation/deactivation, and audit logs.
- Clinician: dashboard, patients, visits, prescriptions, appointments, availability, and time off.
- Patient: login, dashboard, history/prescriptions, booking, cancellation, and demo payment records. Public self-registration is disabled by default.
- Clinical support assistant: authenticated appointment/account guidance, medication-safety prompts, and emergency escalation without diagnosis or EHR access.

Sensitive profile fields are encrypted. The current compatibility lookup decrypts and compares identifiers in application code because Fernet ciphertext is randomized. A future migration should add normalized keyed lookup hashes for indexed search.

## Tests

Run: `python -m unittest discover -s tests -v`.

Tests use an isolated in-memory SQLite database and do not touch PostgreSQL.

## Render deployment

`render.yaml`, `Procfile`, `wsgi.py`, and `gunicorn.conf.py` define deployment. Configure `DATABASE_URL`, `ENCRYPTION_KEY`, and all required secrets in Render. Free-tier production email uses Brevo's HTTPS API because SMTP egress is unavailable. The production configuration uses one Gunicorn worker because filesystem sessions are not shared; configure Redis before scaling workers.

See [Deployment](docs/Deployment.md), [Architecture](docs/System_Architecture.md), and [Testing](docs/Testing.md) for operational details.

The payment screen is explicitly an FYP demo recorder. It does not contact or claim success from an external payment provider.
