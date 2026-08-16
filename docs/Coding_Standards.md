# Coding Standards

## General Standards

- Follow PEP 8.
- Use meaningful variable and function names.
- Keep functions small and focused.
- Avoid duplicate code.
- Write modular code.
- Use environment variables for secrets.
- Never hardcode credentials.

---

## Folder Structure

Each module should follow this structure:

```
module/
├── routes.py
├── service.py
├── repository.py
└── validators.py
```

---

## Route Rules

Routes are responsible for:

- Receiving requests
- Validating input
- Calling services
- Returning responses

Routes must not contain business logic.

---

## Service Rules

Services are responsible for:

- Business logic
- Validation
- Transactions
- Coordination between repositories

Services must not directly render templates.

---

## Repository Rules

Repositories are responsible for:

- Database queries
- CRUD operations
- Returning model objects

Repositories must not contain business logic.

---

## Database Standards

- Every table must have a primary key.
- Use foreign keys where applicable.
- Avoid duplicate data.
- Prefer normalization.
- Include audit fields:
  - created_at
  - updated_at

---

## Security Standards

- Hash all passwords.
- Validate all user input.
- Use parameterized queries.
- Protect against CSRF.
- Implement role-based access control.
- Log important actions.

---

## Git Standards

- Write clear commit messages.
- Commit one logical change at a time.
- Never commit:
  - .env
  - venv/
  - __pycache__/
  - log files