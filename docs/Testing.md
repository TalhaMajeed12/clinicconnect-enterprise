# Testing

The focused automated suite covers the application's critical security and workflow boundaries. It uses an in-memory SQLite database and does not access production PostgreSQL or send real email.

## Run the suite

From the repository root with the virtual environment active:

```powershell
python -m unittest discover -s tests -v
```

The current suite covers:

- Encrypted identifier login and role-specific logout
- Inactive clinician access
- Cross-role dashboard protection
- Disabled public registration
- Admin clinician validation
- Patient privacy and appointment ownership
- Booking conflicts and clinician time off
- CSRF-protected appointment status updates
- Demo checkout/payment recording
- Single-use, non-enumerating password recovery
- Brevo HTTPS transport without real network delivery
- Restricted API CORS and HTTP security headers

## Manual production smoke test

After deploying, verify:

1. `/api/health` reports a connected database.
2. Admin, clinician, and patient logins reach the correct dashboard.
3. An active clinician can be selected for a valid appointment slot.
4. Time off and conflicting slots are rejected.
5. A clinician can record a visit and prescription visible to that patient.
6. Appointment status and demo payment records update correctly.
7. A known patient receives one password-reset email and the link is single-use.
8. Cross-role and altered-ID requests are rejected.

Never run destructive fixtures or database initialization against production.
