# Patient Discharge Planning Coordination Portal with Interdepartmental Communication Logs

A full-stack, database-backed hospital patient discharge coordination web application designed for healthcare facilities to streamline inpatient discharge planning, interdepartmental clearances (Nursing, Pharmacy, Diagnostic Laboratory), auditable clinical communication, patient financial statements, and post-discharge continuity of care.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/K-NAVEENA/patient-discharge-portal)

- **Live URL on Render:** [https://patient-discharge-portal.onrender.com](https://patient-discharge-portal.onrender.com)
- **1-Click Deploy on Render:** [Deploy to Render](https://render.com/deploy?repo=https://github.com/K-NAVEENA/patient-discharge-portal)

---

## 1. Technology Stack

- **Backend:** Python 3.10+ / Flask 3.x
- **ORM & Database Connectivity:** Flask-SQLAlchemy 3.x with PyMySQL
- **Database:** MySQL 8.0+ (with native UTF8mb4 schema and ACID transactions)
- **Frontend:** HTML5, CSS3 (Medical Portal UI Theme), Vanilla JavaScript (with real-time notification polling & async APIs)
- **Testing:** Pytest (17 comprehensive unit & integration tests)

---

## 2. Architecture & Modules

```
patient-discharge-portal/
│
├── app.py                     # Flask application factory, CLI commands, context processors
├── config.py                  # Database, session security, and hospital billing configuration
├── requirements.txt           # Python dependency specifications
├── .env.example               # Environment variables template
├── README.md                  # Complete documentation and setup manual
│
├── models/                    # SQLAlchemy Database Models
│   ├── __init__.py            # Model registry & exports
│   ├── user.py                # User credentials, roles, approval status, password hashing
│   ├── patient.py             # Patient demographics, age calculation, clinical relationships
│   ├── room.py                # Room inventory, wards, daily rates, occupancy state
│   ├── admission.py           # Inpatient admission records and status lifecycle
│   ├── discharge.py           # Multi-department discharge coordination records
│   ├── task.py                # Departmental tasks (Nursing, Pharmacy, Laboratory)
│   ├── communication.py       # Persistent, auditable interdepartmental communication logs
│   ├── notification.py        # Role-based system alerts & notifications
│   ├── billing.py             # Itemized billing statements, room charges, and payments
│   └── audit.py               # Compliance audit trail for administrative actions
│
├── routes/                    # Modular Route Blueprints
│   ├── __init__.py            # Blueprint registry
│   ├── auth.py                # Authentication, registration, first-login password change
│   ├── admin.py               # Admin dashboard, patient admissions, rooms, staff approvals
│   ├── doctor.py              # Doctor dashboard, clinical discharge assessment & initiation
│   ├── nurse.py               # Nurse dashboard, ward care, discharge checklists
│   ├── pharmacy.py            # Pharmacy dashboard, prescription reconciliation, medication dispensing
│   ├── laboratory.py          # Laboratory dashboard, diagnostic test clearance & sign-offs
│   ├── patient.py             # Patient portal, stay progress, care instructions, bills
│   ├── communication.py       # Interdepartmental message dispatch & acknowledgements
│   ├── notifications.py       # Notification feed & asynchronous polling endpoint
│   └── billing.py             # Billing ledger, charges, payments, and discounts
│
├── services/                  # Business Logic Layer
│   ├── __init__.py            # Services package init
│   ├── discharge_service.py   # Centralized discharge readiness engine & final discharge workflow
│   ├── billing_service.py     # Room charges sync, payment entries, ledger recalculations
│   └── notification_service.py# Notification dispatcher by role and department
│
├── templates/                 # Jinja2 Templates (All 6 Dashboards & Clinical Views)
│   ├── base.html              # Responsive layout with medical theme, sidebar, & topbar
│   ├── login.html             # Secure login with synthetic credential helper
│   ├── register.html          # Staff registration with department & role pickers
│   ├── change_password.html   # Forced password change for initial temporary credentials
│   ├── admin_dashboard.html   # 8-metric hospital operations center & discharge pipeline
│   ├── patients_list.html     # Patient directory with keyword & date range filters
│   ├── admit_patient.html     # Inpatient admission, room allocation, staff assignment
│   ├── patient_details.html   # Clinical patient record & portal activation
│   ├── edit_patient.html      # Demographic edit form
│   ├── patient_history.html   # Preserved multi-admission history for returning patients
│   ├── rooms.html             # Room inventory & real-time occupancy management
│   ├── staff_approvals.html   # Staff registration verification & account activation
│   ├── discharge_details.html # Administrative final discharge execution & clearance review
│   ├── doctor_dashboard.html  # Physician assigned inpatient roster & status queue
│   ├── doctor_patient_detail.html # Clinical discharge initiation & department selector
│   ├── nurse_dashboard.html   # Ward care roster & nursing tasks
│   ├── nurse_discharge_detail.html # Nursing discharge checklist & protocol updates
│   ├── pharmacy_dashboard.html # Pharmacy queue & dispensing worklist
│   ├── pharmacy_discharge_detail.html # Medication reconciliation & pharmacy billing
│   ├── laboratory_dashboard.html # Diagnostics queue awaiting sign-off
│   ├── laboratory_discharge_detail.html # Lab report sign-off & investigation billing
│   ├── patient_dashboard.html # Patient personal health dashboard, progress timeline, bill
│   ├── notifications.html     # Notification center
│   ├── billing.html           # Itemized billing statement, payment posting, discounts
│   └── error.html             # Friendly error page for 403, 404, 500 status codes
│
├── static/
│   ├── css/style.css          # Medical hospital stylesheet (light palette, responsive)
│   └── js/app.js              # Client-side notification poller, modals, dynamic forms
│
├── database/
│   ├── schema.sql             # Native MySQL 8.0 DDL database schema
│   └── seed.py                # Synthetic demo dataset initialization script
│
└── tests/                     # Automated Test Suite (17 Tests)
    ├── conftest.py            # Test configuration, in-memory DB, client fixtures
    ├── test_auth.py           # Authentication, RBAC, pending approvals tests
    ├── test_discharge.py      # Discharge initiation, task completion, readiness tests
    ├── test_billing.py        # Room charges, itemized additions, payment calculations
    ├── test_portal.py         # Patient privacy and boundary isolation tests
    └── test_workflows.py      # End-to-end approvals, searching, logs, and history tests
```

---

## 3. The Six Portal Dashboards

1. **Admin Dashboard (`/admin/dashboard`):**
   - 8 live statistical metrics: Total Admitted, Discharge In Progress, Awaiting Departmental Clearance, Ready for Final Discharge, Total Discharged, Pending Staff Approvals, Room Occupancy Rate (%), and Outstanding Billing Ledger.
   - Comprehensive discharge pipeline overview.
   - Quick action bar: Patient Admission, Room Management, Staff Approvals, Patient Directory.
   - Final Discharge Management: Revalidates all clearances before releasing rooms.

2. **Doctor Dashboard (`/doctor/dashboard`):**
   - Roster of inpatients assigned to the logged-in physician.
   - Clinical discharge decision interface: records clinical readiness, follow-up instructions, and dynamically specifies required departments (Nursing, Pharmacy, Laboratory).
   - Real-time departmental progress tracker and communication logs.

3. **Nurse Dashboard (`/nurse/dashboard`):**
   - Patients assigned to ward care.
   - Discharge checklists: Vitals & Clinical Assessment, Care Discontinuation (IV lines, catheters), Home Care Education, Belongings Return.
   - Protocol status updates (`Pending`, `In Progress`, `Completed`, `Blocked` with mandatory reason).

4. **Pharmacy Dashboard (`/pharmacy/dashboard`):**
   - Inpatients requiring pharmacy clearance.
   - Medication reconciliation, prescription verification, packaging, dispensing sign-off.
   - Add discharge prescription medications directly to the patient's billing ledger.
   - Blocked tasks alert doctors and administrators.

5. **Laboratory Dashboard (`/laboratory/dashboard`):**
   - Inpatients requiring diagnostic laboratory sign-off (created only when ordered by the doctor).
   - Pathology and bloodwork results verification.
   - Add laboratory investigation charges to the patient's billing statement.

6. **Patient Dashboard (`/patient/dashboard`):**
   - Secure patient-accessible view of their current admission.
   - Visual 4-stage progress timeline (Admitted &rarr; Doctor Decision &rarr; Department Clearances &rarr; Final Discharge).
   - Status indicators for Nursing, Pharmacy, and Diagnostics.
   - Physician discharge instructions and care guidelines.
   - Transparent, itemized billing statement with payments and balance due.
   - Strictly isolated: no internal staff communications or other patients' data visible.

---

## 4. Installation & Setup Instructions

### Step 1: Clone or Navigate to the Project Folder
```bash
cd patient_dischargePortal
```

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Edit `.env` with your MySQL database credentials:
```ini
SECRET_KEY=hospital_secure_key_84920491823901
DATABASE_URL=mysql+pymysql://root:your_mysql_password@localhost:3306/patient_discharge_db
FLASK_ENV=development
```

### Step 4: MySQL Database Initialization

Option A: Run the raw SQL schema in MySQL:
```bash
mysql -u root -p < database/schema.sql
```

Option B: Use Flask CLI commands:
```bash
flask init-db
```

### Step 5: Create Initial Administrator Account
Run the interactive CLI command to securely create your administrator account:
```bash
flask create-admin
```
*(You will be prompted for username, email, full name, and password.)*

### Step 6: Populate Synthetic Demonstration Data
To seed realistic hospital records (doctors, nurses, pharmacists, lab techs, rooms, inpatients at various stages of discharge, pending staff applications, and billing ledgers):
```bash
flask seed-db
```

---

## 5. Running the Application

Start the Flask development server:
```bash
python app.py
```
Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 6. Pre-Configured Demo Accounts (From `flask seed-db`)

| Role | Username | Password | Purpose / Focus |
|---|---|---|---|
| **Administrator** | `admin` | `Admin@123` | Hospital operations, admissions, rooms, approvals, final discharge |
| **Cardiologist** | `dr_smith` | `Doctor@123` | Assigned to Eleanor Vance (cardiac discharge in progress) |
| **Internist** | `dr_chen` | `Doctor@123` | Assigned to Marcus Brody (ready for final discharge) & Sophia Patel |
| **Registered Nurse** | `nurse_emma` | `Nurse@123` | Inpatient Ward A nurse, discharge checklists |
| **ICU Nurse** | `nurse_david` | `Nurse@123` | Post-surgical recovery nurse |
| **Pharmacist** | `pharm_lisa` | `Pharm@123` | Pharmacy queue, medication dispensing & billing |
| **Lab Technologist** | `lab_robert` | `Lab@123` | Diagnostics review & test sign-off |
| **Patient** | `eleanor_vance` | `Patient@123` | Patient portal, stay progress & billing statement |
| **Pending Staff** | `nurse_kevin` | `Nurse@123` | Demonstrates administrator approval/rejection workflow |

---

## 7. Running the Automated Test Suite

Run all 17 automated tests covering authentication, RBAC, clinical workflows, readiness calculations, room occupancy locks, billing, and patient privacy:

```bash
python -m pytest -v
```

**Test Summary:**
- `tests/test_auth.py`: Login/logout, staff registration approval status, RBAC enforcement.
- `tests/test_discharge.py`: Patient admission, double-room occupancy prevention, discharge initiation, readiness validation, premature finalization prevention, room release.
- `tests/test_billing.py`: Room charge duration calculations, itemized billing additions, payment posting, balance recalculation.
- `tests/test_portal.py`: Patient privacy boundaries and restricted access.
- `tests/test_workflows.py`: Staff approval lifecycle, search and date filters, interdepartmental communication logs, returning patient history preservation.

---

## 8. Key Workflow Features & Security Highlights

- **Anti-Double-Occupancy Guarantee:** Database checks and transactional locks ensure a room cannot be allocated to a second patient while occupied. Rooms are released upon formal final discharge.
- **Centralized Discharge Readiness Engine:** Readiness is computed server-side in Python. Discharge cannot be finalized if any required task remains pending, in progress, or blocked.
- **Auditable Interdepartmental Communication:** Every message is timestamped with the sender's identity and department, linked directly to the patient's admission.
- **Patient Privacy by Design:** Patients can only view their own admission, timeline, instructions, and billing statement. Internal clinical chats and other patient records are strictly excluded.
- **Separation of Clinical and Financial Clearance:** Financial balances do not arbitrarily block clinical clearance, following modern healthcare compliance standards.
