# User Acceptance Testing Checklist

Use disposable demonstration records. Never place real patient information in screenshots or a public presentation.

## Pre-demo checks

- [ ] Render deployment is Live and `/api/health` is healthy.
- [ ] A current PostgreSQL backup exists outside the repository.
- [ ] One active demo account exists for each role.
- [ ] One clinician has working hours and is available.
- [ ] Browser tabs, terminal history, and screenshots contain no secrets.

## Admin scenario

- [ ] Log in through the Admin Login page.
- [ ] Confirm dashboard totals and revenue formatting.
- [ ] Create a clinician with required contact information.
- [ ] Edit and deactivate/reactivate the clinician.
- [ ] View patient details, appointments, and audit logs.
- [ ] Log out and confirm protected pages redirect to Admin Login.

## Clinician scenario

- [ ] Log in through the Clinician Login page.
- [ ] Configure availability and working hours.
- [ ] Add full-day or partial-day time off.
- [ ] Open an authorized patient folder.
- [ ] Record a visit, diagnosis, treatment plan, and prescription.
- [ ] Update an appointment status.
- [ ] Log out and confirm protected pages redirect to Clinician Login.

## Patient scenario

- [ ] Log in using the patient email or phone.
- [ ] View dashboard, medical history, and prescription.
- [ ] Book a valid future appointment.
- [ ] Demonstrate rejection of a conflict or time-off slot.
- [ ] Record the clearly labelled demo payment.
- [ ] Cancel an eligible future appointment.
- [ ] Request a password-reset email and use the link once.
- [ ] Log out and confirm protected pages redirect to Patient Login.

## Security checks

- [ ] Patient A cannot access Patient B by changing a URL ID.
- [ ] Clinician cannot alter another clinician's protected appointment.
- [ ] Cross-role dashboard requests are rejected or redirected.
- [ ] Public registration is unavailable.
- [ ] Reusing an expired/used reset link fails safely.
- [ ] No password, reset token, database URL, or API key appears in logs.

## Acceptance record

| Field | Value |
| --- | --- |
| Tester | |
| Date | |
| Git commit | |
| Render deployment | |
| Database health | |
| Automated tests | 18 passed |
| Overall result | PASS / PARTIAL / FAIL |
| Notes | |
