# Database Design

## Database

MySQL

---

## Design Principles

- Normalize data to reduce duplication.
- Use foreign keys to maintain relationships.
- Use integer primary keys internally.
- Use business codes for display (e.g., PAT-LHR-000001).
- Store audit information for important records.
- Never permanently delete medical records.
- Prefer soft delete where applicable.

---

## Naming Conventions

### Tables

- Singular names
- Lowercase
- Snake_case

Examples:

- patient
- appointment
- prescription

---

### Columns

Use snake_case.

Examples:

- patient_id
- first_name
- created_at

---

## Standard Audit Columns

Every major table should include:

- created_at
- updated_at
- created_by
- updated_by

---

## Core Domains

- Organization
- Branch
- Users
- Roles
- Permissions
- Patients
- Patient Portal
- Appointments
- Consultations
- Prescriptions
- Billing
- Notifications
- Audit Logs

---

## Relationships

Organization
↓
Branch
↓
Users
↓
Patients
↓
Appointments
↓
Consultations
↓
Prescriptions
↓
Invoices
↓
Payments
---

# Table: organization

## Purpose

Stores the information of the organization that owns one or more clinic branches.

---

## Columns

| Column | Data Type | Constraints | Description |
|----------|-----------|-------------|-------------|
| organization_id | BIGINT | PRIMARY KEY, AUTO_INCREMENT | Internal unique identifier |
| organization_code | VARCHAR(20) | UNIQUE, NOT NULL | Organization code (e.g., CC) |
| organization_name | VARCHAR(150) | NOT NULL | Official organization name |
| registration_number | VARCHAR(50) | NULL | Business registration number |
| tax_number | VARCHAR(30) | NULL | NTN (optional) |
| email | VARCHAR(120) | NOT NULL | Official email |
| phone | VARCHAR(20) | NOT NULL | Primary contact number |
| website | VARCHAR(255) | NULL | Official website |
| logo_path | VARCHAR(255) | NULL | Organization logo |
| status | ENUM('Active','Inactive') | NOT NULL | Organization status |
| created_at | DATETIME | NOT NULL | Record creation timestamp |
| updated_at | DATETIME | NOT NULL | Last update timestamp |
| created_by | BIGINT | NULL | User who created the record |
| updated_by | BIGINT | NULL | User who last updated the record |

---

## Relationships

- One Organization can have many Branches.

Organization (1) → (Many) Branch

---

## Indexes

- PRIMARY KEY (organization_id)
- UNIQUE (organization_code)
- INDEX (organization_name)

---

## Business Rules

- Organization code must be unique.
- Organization name cannot be empty.
- Status defaults to Active.
- Organizations should not be deleted once created.
---

# Table: branch

## Purpose

Stores information about each clinic branch belonging to an organization.

---

## Columns

| Column | Data Type | Constraints | Description |
|----------|-----------|-------------|-------------|
| branch_id | BIGINT | PRIMARY KEY, AUTO_INCREMENT | Internal unique identifier |
| organization_id | BIGINT | FOREIGN KEY, NOT NULL | Parent organization |
| branch_code | VARCHAR(10) | UNIQUE, NOT NULL | Branch code (e.g., LHR01, ISB01) |
| branch_name | VARCHAR(100) | NOT NULL | Branch name |
| address | TEXT | NOT NULL | Full branch address |
| city | VARCHAR(50) | NOT NULL | City |
| province | ENUM('Punjab','Sindh','Khyber Pakhtunkhwa','Balochistan','Gilgit-Baltistan','Azad Jammu & Kashmir','Islamabad Capital Territory') | NOT NULL | Province or territory |
| postal_code | VARCHAR(15) | NULL | Postal code |
| phone | VARCHAR(20) | NOT NULL | Branch contact number |
| email | VARCHAR(120) | NULL | Branch email |
| timezone | VARCHAR(50) | NOT NULL | Default: Asia/Karachi |
| status | ENUM('Active','Inactive') | NOT NULL | Branch status |
| created_at | DATETIME | NOT NULL | Record creation timestamp |
| updated_at | DATETIME | NOT NULL | Last update timestamp |
| created_by | BIGINT | NULL | User who created the record |
| updated_by | BIGINT | NULL | User who last updated the record |

---

## Relationships

- One Organization can have many Branches.
- One Branch belongs to one Organization.

---

## Foreign Keys

organization_id → organization.organization_id

---

## Indexes

- PRIMARY KEY (branch_id)
- UNIQUE (branch_code)
- INDEX (organization_id)
- INDEX (city)

---

## Business Rules

- Every branch must belong to an organization.
- Branch code must be unique.
- Branch name cannot be empty.
- Default timezone is Asia/Karachi.
- Branches should not be permanently deleted.
---

# Table: branch_settings

## Purpose

Stores configurable settings specific to each branch.

---

## Columns

| Column | Data Type | Constraints | Description |
|----------|-----------|-------------|-------------|
| setting_id | BIGINT | PRIMARY KEY, AUTO_INCREMENT | Internal unique identifier |
| branch_id | BIGINT | FOREIGN KEY, UNIQUE, NOT NULL | Branch reference |
| consultation_fee | DECIMAL(10,2) | NOT NULL | Default consultation fee (PKR) |
| appointment_duration | INT | NOT NULL | Duration in minutes |
| online_booking_enabled | BOOLEAN | NOT NULL | Allow patient online booking |
| walk_in_enabled | BOOLEAN | NOT NULL | Allow walk-in patients |
| sms_enabled | BOOLEAN | NOT NULL | Enable SMS notifications |
| email_enabled | BOOLEAN | NOT NULL | Enable email notifications |
| max_daily_appointments | INT | NOT NULL | Maximum appointments per day |
| created_at | DATETIME | NOT NULL | Record creation timestamp |
| updated_at | DATETIME | NOT NULL | Last update timestamp |
| created_by | BIGINT | NULL | User who created the record |
| updated_by | BIGINT | NULL | User who last updated the record |

---

## Relationships

- One Branch has one Branch Settings record.

Branch (1) → (1) Branch Settings

---

## Foreign Keys

branch_id → branch.branch_id

---

## Indexes

- PRIMARY KEY (setting_id)
- UNIQUE (branch_id)

---

## Business Rules

- Every branch must have exactly one settings record.
- Consultation fee must be greater than or equal to zero.
- Appointment duration must be greater than zero.
- Maximum daily appointments must be greater than zero.