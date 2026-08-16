# API Design

## API Style

ClinicConnect follows RESTful API principles.

---

## Base URL

/api/v1

---

## Response Format

### Success

```json
{
  "success": true,
  "message": "Operation completed successfully.",
  "data": {}
}
```

### Error

```json
{
  "success": false,
  "message": "Error description.",
  "errors": []
}
```

---

## HTTP Methods

- GET - Retrieve data
- POST - Create data
- PUT - Update existing data
- PATCH - Partial update
- DELETE - Soft delete where applicable

---

## Authentication

Protected endpoints require authentication.

Authorization is based on user roles.

---

## API Versioning

Current Version:

v1

Future versions:

v2

v3

---

## Endpoint Naming

Use plural nouns.

Examples:

/patients

/appointments

/prescriptions

/users

/branches

---

## General Rules

- Return proper HTTP status codes.
- Validate all request data.
- Return JSON responses.
- Keep endpoints consistent.
- Do not expose internal database IDs unnecessarily.