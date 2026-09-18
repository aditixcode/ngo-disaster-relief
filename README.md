# NGO Disaster Relief Management System - Backend

A clean, modular REST API backend built using **FastAPI**, **PostgreSQL**, **SQLAlchemy**, and **Pydantic**, designed for disaster relief coordination, donation management, volunteer task tracking, and aid distribution.

---

## 1. Project Directory Layout

```
ngo-disaster-relief/
├── alembic/                      # Database migrations folder
│   ├── versions/                 # Migration scripts
│   │   ├── 0001_initial_create_users_and_disasters.py
│   │   ├── 0002_add_created_by_to_disasters.py
│   │   ├── 0003_add_volunteer_assignments_and_tasks.py
│   │   ├── 0004_add_donations.py
│   │   ├── 0005_add_inventory.py
│   │   ├── 0006_add_beneficiaries.py
│   │   ├── 0007_add_distribution_centers.py
│   │   └── 0008_add_resource_distributions.py
│   ├── env.py                    # Connects Alembic to app config & Base.metadata
│   └── script.py.mako            # Migration template
├── alembic.ini                   # Alembic configuration file
├── .env                          # Local environment variables (kept private)
├── .env.example                  # Template showing all environment variable schemas
├── .gitignore                    # Excludes .venv, secrets, cache from git
├── requirements.txt              # Pinned Python package dependencies
├── README.md                     # Documentation & setup instructions
│
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI app entry point (CORS, docs, routers)
│   │
│   ├── core/                     # Core system configuration & security
│   │   ├── __init__.py
│   │   ├── config.py             # Settings using Pydantic BaseSettings (.env loader)
│   │   ├── database.py           # Engine, SessionLocal, Base, get_db dependency
│   │   └── security.py           # Bcrypt password hashing & JWT encoding/decoding
│   │
│   ├── models/                   # SQLAlchemy ORM Models (PostgreSQL tables)
│   │   ├── __init__.py           # Re-exports all ORM models
│   │   ├── user.py               # User model & UserRole enum
│   │   ├── disaster.py           # Disaster model, DisasterStatus enum, & creator FK
│   │   ├── volunteer.py          # VolunteerAssignment & VolunteerTask models
│   │   ├── donation.py           # Donation model, DonationType & DonationStatus enums
│   │   ├── inventory.py          # InventoryItem model & InventoryStatus enum
│   │   ├── beneficiary.py        # Beneficiary model & vulnerability/status enums
│   │   ├── distribution_center.py# DistributionCenter model & CenterStatus enum
│   │   └── distribution.py       # ResourceDistribution model
│   │
│   ├── schemas/                  # Pydantic Schemas (Data Transfer Objects & validation)
│   │   ├── __init__.py           # Re-exports all schemas
│   │   ├── user.py               # User registration, login, and response DTOs
│   │   ├── disaster.py           # Disaster CRUD DTOs with date validation
│   │   ├── volunteer.py          # Assignment & Task schemas
│   │   ├── donation.py           # DonationCreate, DonationUpdate, DonationResponse
│   │   ├── inventory.py          # Inventory intake, status & stock schemas
│   │   ├── beneficiary.py        # Beneficiary demographic & verification schemas
│   │   ├── distribution_center.py# Distribution center CRUD & capacity schemas
│   │   ├── distribution.py       # ResourceDistribution schemas
│   │   └── report.py             # Disaster summary & operational report schemas
│   │
│   ├── services/                 # Business logic & Domain Services
│   │   ├── __init__.py
│   │   ├── inventory_service.py  # Distributable stock calculations
│   │   ├── beneficiary_service.py# Eligibility verification & duplicate check
│   │   ├── distribution_center_service.py # Center operational gating
│   │   ├── distribution_service.py# Atomic stock deduction & distribution
│   │   └── report_service.py     # Read-only SQL aggregation reports
│   │
│   └── api/                      # REST API routing
│       ├── __init__.py
│       ├── deps.py               # Dependencies (get_db, get_current_user, require_roles)
│       └── v1/                   # API Version 1
│           ├── __init__.py
│           ├── router.py         # Combines all v1 endpoint routers
│           └── endpoints/
│               ├── __init__.py
│               ├── health.py     # GET /api/v1/health monitoring endpoint
│               ├── auth.py       # Register, login, /me, & RBAC test endpoints
│               ├── disasters.py  # Full CRUD for disaster/event management
│               ├── volunteers.py # Volunteer deployment & task lifecycle endpoints
│               ├── donations.py  # Money and material donation management
│               ├── inventory.py  # Relief warehouse intake & stock tracking
│               ├── beneficiaries.py # Beneficiary registration & verification
│               ├── distribution_centers.py # Physical distribution hubs
│               ├── distributions.py # Resource distribution tracking
│               └── reports.py    # Read-only disaster summary & analytics reports
│
└── tests/                        # Automated Pytest Suite
    ├── __init__.py
    ├── conftest.py               # In-memory SQLite fixtures & TestClient override
    ├── test_health.py            # Unit tests for root & health endpoints
    ├── test_database.py          # Tests for DB models, roles, unique constraints
    ├── test_auth.py              # Tests for registration, login, JWT & RBAC
    ├── test_disasters.py         # Tests for disaster CRUD, date validation & RBAC
    ├── test_volunteers.py        # Tests for volunteer deployment & task management
    ├── test_donations.py         # Tests for money/material donations & status transitions
    ├── test_inventory.py         # Tests for relief inventory intake & stock rules
    ├── test_beneficiaries.py     # Tests for beneficiary demographics & eligibility
    ├── test_distribution_centers.py # Tests for distribution centers & operational states
    ├── test_distributions.py     # Tests for atomic resource distributions & multi-batch deduction
    └── test_reports.py           # Tests for read-only aggregation reports & privacy
```

---

## 2. Viva Concepts: Donation Management

### What is a Donation Resource?
A `Donation` represents aid contributed by a donor towards a specific disaster event. Our system models two distinct types of donations:
1. **MONEY**: Financial contributions.
   - Requires: `amount > 0`.
   - Material-specific fields (`item_name`, `quantity`, `unit`) are omitted/null.
2. **MATERIAL**: Physical goods (e.g. tarpaulins, first aid kits, dry rations).
   - Requires: `item_name` (non-empty string), `quantity > 0`, and `unit` (e.g. "boxes", "kg", "pallets").
   - `amount` is omitted/null.

### Database Relationships
* **Donation → User (`donor_id`)**: A foreign key to `users.id` identifying the donor who pledged or contributed the aid.
* **Donation → Disaster (`disaster_id`)**: A foreign key to `disasters.id` linking the donation to a specific active emergency relief effort.

### Donation Lifecycle & State Machine
Donations transition through distinct states:
```
         ┌───────────────┐
         │    PLEDGED    │  (Initial commitment by donor)
         └──┬─────────┬──┘
            │         │
            │         ▼
            │   ┌───────────┐
            │   │ CANCELLED │  (Donor or staff cancels the pledge)
            │   └───────────┘
            ▼
     ┌───────────┐
     │ RECEIVED  │  (Aid physically confirmed / funds deposited)
     └───────────┘  (Sets received_at = now())
```

#### State Transition Rules
- `PLEDGED → RECEIVED`: Allowed (sets `received_at` timestamp).
- `PLEDGED → CANCELLED`: Allowed.
- `RECEIVED → PLEDGED`: **Blocked (400 Bad Request)**. Once goods or funds are received, the status cannot revert to a pledge.
- `CANCELLED → RECEIVED`: **Blocked (400 Bad Request)**.
- `CANCELLED → PLEDGED`: **Blocked (400 Bad Request)**.
- **Donor Edit Lock**: Donors can only edit their donation details while it is in `PLEDGED` status. Once `RECEIVED` or `CANCELLED`, donors cannot alter the record.

### IDOR (Insecure Direct Object Reference) Protection
To prevent malicious donors from tampering with or viewing other donors' financial/material pledges:
* When a `DONOR` queries `GET /api/v1/donations`, the query is automatically scoped to `Donation.donor_id == current_user.id`.
* If a `DONOR` attempts to view (`GET /{id}`) or update (`PUT /{id}`) a donation owned by another donor, the API rejects it with **HTTP 403 Forbidden**.
* `DONOR` users cannot create a donation using another user's `donor_id` (returns **HTTP 403 Forbidden**).

---

## 3. Donation Endpoints & Permissions Matrix (Stage 6)

| Method | Endpoint | Allowed Roles | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/donations` | `DONOR`, `ADMIN`, `NGO_STAFF` | Pledge/create a money or material donation |
| `GET` | `/api/v1/donations` | `DONOR`, `ADMIN`, `NGO_STAFF` | List donations (scoped to caller if DONOR; filterable) |
| `GET` | `/api/v1/donations/{id}` | Owning `DONOR`, `ADMIN`, `NGO_STAFF` | Get donation details by ID |
| `PUT` | `/api/v1/donations/{id}` | Owning `DONOR`, `ADMIN`, `NGO_STAFF` | Edit donation details (Donor only while PLEDGED) |
| `PATCH`| `/api/v1/donations/{id}/status`| `ADMIN`, `NGO_STAFF` | Transition donation status (`PLEDGED → RECEIVED / CANCELLED`) |
| `DELETE`| `/api/v1/donations/{id}`| `ADMIN` only | Permanently delete donation record |

---

## 4. Example API Requests and Responses

### 1. Pledge a Money Donation (`POST /api/v1/donations`)
* **Headers**: `Authorization: Bearer <donor_token>`
* **Request**:
  ```json
  {
    "disaster_id": 1,
    "donation_type": "MONEY",
    "amount": 2500.0,
    "notes": "Emergency relief fund contribution"
  }
  ```
* **Response (`201 Created`)**:
  ```json
  {
    "id": 1,
    "donor_id": 3,
    "disaster_id": 1,
    "donation_type": "MONEY",
    "amount": 2500.0,
    "item_name": null,
    "quantity": null,
    "unit": null,
    "status": "PLEDGED",
    "notes": "Emergency relief fund contribution",
    "received_at": null,
    "created_at": "2026-09-18T10:45:00.123456Z",
    "updated_at": "2026-09-18T10:45:00.123456Z"
  }
  ```

### 2. Pledge a Material Donation (`POST /api/v1/donations`)
* **Headers**: `Authorization: Bearer <donor_token>`
* **Request**:
  ```json
  {
    "disaster_id": 1,
    "donation_type": "MATERIAL",
    "item_name": "Emergency Blankets",
    "quantity": 200.0,
    "unit": "boxes",
    "notes": "Arriving by cargo transport"
  }
  ```
* **Response (`201 Created`)**:
  ```json
  {
    "id": 2,
    "donor_id": 3,
    "disaster_id": 1,
    "donation_type": "MATERIAL",
    "amount": null,
    "item_name": "Emergency Blankets",
    "quantity": 200.0,
    "unit": "boxes",
    "status": "PLEDGED",
    "notes": "Arriving by cargo transport",
    "received_at": null,
    "created_at": "2026-09-18T10:46:00.123456Z",
    "updated_at": "2026-09-18T10:46:00.123456Z"
  }
  ```

### 3. Mark Donation as Received (`PATCH /api/v1/donations/{id}/status`)
* **Headers**: `Authorization: Bearer <staff_or_admin_token>`
* **Request**:
  ```json
  {
    "status": "RECEIVED"
  }
  ```
* **Response (`200 OK`)**:
  ```json
  {
    "id": 1,
    "status": "RECEIVED",
    "received_at": "2026-09-18T10:50:00.654321Z"
  }
  ```

---

## 5. How to Test Donations in Swagger UI (`/docs`)

1. Start development server:
   ```powershell
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
2. Open **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**.
3. Authenticate with the **Authorize 🔓** button as a `DONOR`.
4. Create a donation using `POST /api/v1/donations` with `donation_type: "MONEY"`, `amount: 1500.0`.
5. Verify `GET /api/v1/donations` lists your pledged donation.
6. Re-authenticate as `NGO_STAFF`.
7. Call `PATCH /api/v1/donations/{id}/status` with `{"status": "RECEIVED"}`. Verify `received_at` is populated.
8. Re-authenticate as the `DONOR` and attempt `PUT /api/v1/donations/{id}` to edit the received donation. Verify it returns **HTTP 400 Bad Request** because received donations are locked.

---

---

## 7. Stage 7: Relief Inventory Management

Stage 7 implements physical warehouse intake, stock inspection lifecycle, and distributable stock calculations.

### Inventory Lifecycle State Machine
```
[Physical Delivery] 
       │
       ▼
   RECEIVED  (Status on intake; received_at timestamp recorded; supplies under inspection; NOT distributable)
       │
       │  PATCH /api/v1/inventory/{id}/store (Inspection passed; stored_at recorded)
       ▼
    STORED   (Supplies verified in warehouse; ELIGIBLE FOR DISTRIBUTION)
       │
       │  Stage 10: Resource Distribution (atomic deduction with database locking)
       ▼
 DISTRIBUTED (Supplies handed over to verified beneficiaries)
```

### Critical Business Rules
1. **Intake (`RECEIVED`)**: Only `ADMIN` and `NGO_STAFF` can register incoming relief items. Quantity must be strictly positive (`> 0`), and strings cannot be empty or whitespace.
2. **Distributable Stock Calculation**:
   - `GET /api/v1/inventory/available?disaster_id=X&item_name=Rice&unit=kg`
   - Uses `app.services.inventory_service.get_available_quantity(db, disaster_id, item_name, unit)`.
   - **STRICT RULE**: Only items with `status == STORED` are counted. Items in `RECEIVED` status are completely excluded from available stock.
3. **State Transition Locks**:
   - `RECEIVED → STORED`: Permitted via `PATCH /store` or `PATCH /status`.
   - `STORED → RECEIVED`: Forbidden (HTTP 400 Bad Request). Reverting verified stock is rejected.
   - `STORED → DISTRIBUTED`: Reserved strictly for the Resource Distribution module (Stage 10). Arbitrary manual status modification is rejected.

### Inventory Endpoints Summary
| Method | Path | Required Role | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/inventory` | `ADMIN`, `NGO_STAFF` | Intake new physical goods into warehouse (`RECEIVED`) |
| `GET` | `/api/v1/inventory` | Authenticated | List inventory with filters (`disaster_id`, `status`, `item_name`) |
| `GET` | `/api/v1/inventory/available` | Authenticated | Calculate distributable stock (`STORED` only) |
| `GET` | `/api/v1/inventory/{id}` | Authenticated | Get inventory batch details |
| `PATCH` | `/api/v1/inventory/{id}/store` | `ADMIN`, `NGO_STAFF` | Mark verified supplies as stored (`RECEIVED → STORED`) |
| `PATCH` | `/api/v1/inventory/{id}/status` | `ADMIN`, `NGO_STAFF` | Lifecycle status transition with validation |

---

## 8. Stage 8: Beneficiary Management

Stage 8 implements beneficiary intake, demographic tracking, vulnerability categorization, verification lifecycle, and eligibility gating.

### What is a Beneficiary?
A **beneficiary** is an individual or household affected by a disaster event who is registered with the NGO to receive emergency relief resources (e.g. food rations, blankets, medical kits).

### Beneficiary-to-Disaster Relationship
Each beneficiary record is strictly associated with a specific `Disaster` via foreign key `disaster_id` (`ON DELETE CASCADE`). An individual can be registered under different disasters as new events occur, but duplicate registrations within the same disaster are prevented by a composite guard on `(disaster_id, name, contact_number)`.

### Registration Lifecycle State Machine
```
[Demographic Intake] 
          │
          ▼
       PENDING    (Initial status; recorded by ADMIN/STAFF; pending field inspection; is_eligible = False)
          │
          ├───────────────────────────────┐
          │ PATCH /status (VERIFIED)      │ PATCH /status (INACTIVE)
          ▼                               ▼
       VERIFIED                        INACTIVE
 (Vetted by staff; eligible       (Archived, relocated,
 for relief; is_eligible = True)   or duplicate claim)
          │                               ▲
          │ PATCH /status (INACTIVE)      │
          └───────────────────────────────┘
```

### Critical Business Rules
1. **Initial Status**: All beneficiaries start in `PENDING` status upon intake. Arbitrary initial status injection is disallowed.
2. **Eligibility Gating (`is_beneficiary_eligible`)**:
   - Only beneficiaries in `VERIFIED` status (`registration_status == VERIFIED`) can receive emergency relief items.
   - Beneficiaries in `PENDING` status (pending verification) and `INACTIVE` status are **ineligible**.
   - This service rule is located in `app.services.beneficiary_service.is_beneficiary_eligible()` and directly gates resource distribution in Stage 10.
3. **State Machine Locks**:
   - `PENDING → VERIFIED`: Allowed.
   - `PENDING → INACTIVE`: Allowed.
   - `VERIFIED → INACTIVE`: Allowed.
   - `VERIFIED → PENDING`: Forbidden (HTTP 400 Bad Request).
   - `INACTIVE → VERIFIED / PENDING`: Forbidden (HTTP 400 Bad Request - archived records cannot be reactivated).
4. **Duplicate Protection**:
   - Uniqueness is enforced on `(disaster_id, name, contact_number)`. Prevents accidental double-registration of the same person or household within the same disaster while permitting identical names in different disasters.
5. **Access Control**:
   - Intake, viewing, and updates are restricted to `ADMIN` and `NGO_STAFF`.
   - Record deletion is restricted strictly to `ADMIN`.
   - Volunteers and Donors have zero access to protect vulnerable individuals' privacy.

### Beneficiary Endpoints Summary
| Method | Path | Required Role | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/beneficiaries` | `ADMIN`, `NGO_STAFF` | Register a new beneficiary (`PENDING`) |
| `GET` | `/api/v1/beneficiaries` | `ADMIN`, `NGO_STAFF` | List beneficiaries with filters (`disaster_id`, `vulnerability_category`, `status`) |
| `GET` | `/api/v1/beneficiaries/{id}` | `ADMIN`, `NGO_STAFF` | Retrieve single beneficiary record |
| `PUT` | `/api/v1/beneficiaries/{id}` | `ADMIN`, `NGO_STAFF` | Update demographic & household information |
| `PATCH` | `/api/v1/beneficiaries/{id}/status` | `ADMIN`, `NGO_STAFF` | Update verification status with state machine guards |
| `DELETE` | `/api/v1/beneficiaries/{id}` | `ADMIN` only | Permanently delete a beneficiary record |

---

## 9. Stage 9: Distribution Center Management

Stage 9 implements distribution center facility registration, capacity specification, and operational availability management.

### What is a Distribution Center?
A **distribution center** is a physical ground dispatch station, relief camp depot, or warehouse staging hub where relief goods (food rations, medical supplies, water, blankets) are handed out to verified beneficiaries during a disaster event.

### Center-to-Disaster Relationship
Every distribution center belongs to a specific `Disaster` via foreign key `disaster_id` (`ON DELETE CASCADE`). Duplicate center names under the exact same disaster are disallowed by a composite unique constraint `uq_center_disaster_name` on `(disaster_id, name)`.

### Operational Status Lifecycle
```
             ┌─────────────────────────┐
             │       [POST /]          │
             ▼                         │
          ACTIVE ◄─────────────────────┤
      (Operational)                    │
        │        ▲                     │
        │        │                     │
        ▼        │                     │
       FULL ─────┤                     │
   (Capacity)    │                     │
        │        │                     │
        ▼        │                     │
     INACTIVE ───┘─────────────────────┘
 (Closed/Offline)
```

### Critical Business Rules
1. **Initial Status**: All newly registered centers automatically start with status **`ACTIVE`**.
2. **Operational Eligibility Rule (`is_center_eligible_for_distribution`)**:
   - Only **`ACTIVE`** centers are eligible to receive and disburse resources to beneficiaries.
   - Centers marked **`FULL`** (at capacity) or **`INACTIVE`** (closed, offline, or damaged) are **strictly ineligible**.
   - In Stage 10 (Resource Distribution), every dispatch request will verify `is_center_eligible_for_distribution(center)`. If not `ACTIVE`, the distribution request is rejected.
3. **Declared Capacity**:
   - `capacity` represents the maximum number of beneficiaries the facility is intended to process. Must be strictly positive (`> 0`).
4. **State Machine Transition Rules**:
   - `ACTIVE → FULL`: Facility reached throughput capacity.
   - `ACTIVE → INACTIVE`: Facility temporarily or permanently closed.
   - `FULL → ACTIVE`: Congestion cleared; facility ready for more dispatches.
   - `FULL → INACTIVE`: Facility closed while full.
   - `INACTIVE → ACTIVE`: Facility reopened.
   - `INACTIVE → FULL`: **Forbidden (HTTP 400 Bad Request)**. An inactive facility cannot leap directly to full capacity; it must be reopened as `ACTIVE` first.
5. **Access Control**:
   - Creating, viewing, listing, and updating centers is restricted to `ADMIN` and `NGO_STAFF`.
   - Center deletion is strictly restricted to **`ADMIN`** (Staff receive HTTP 403 Forbidden).
   - Volunteers and Donors have zero access.

### Distribution Center Endpoints Summary
| Method | Path | Required Role | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/distribution-centers` | `ADMIN`, `NGO_STAFF` | Register a new distribution facility (`ACTIVE`) |
| `GET` | `/api/v1/distribution-centers` | `ADMIN`, `NGO_STAFF` | List centers with filters (`disaster_id`, `status`) |
| `GET` | `/api/v1/distribution-centers/{id}` | `ADMIN`, `NGO_STAFF` | Retrieve single center details |
| `PUT` | `/api/v1/distribution-centers/{id}` | `ADMIN`, `NGO_STAFF` | Update facility details or declared capacity |
| `PATCH` | `/api/v1/distribution-centers/{id}/status` | `ADMIN`, `NGO_STAFF` | Update operational status (`ACTIVE`, `INACTIVE`, `FULL`) |
| `DELETE` | `/api/v1/distribution-centers/{id}` | `ADMIN` only | Permanently delete a distribution center |

---

## 10. Stage 10: Resource Distribution Tracking

Stage 10 completes the core operational loop of the NGO disaster-relief platform, linking inventory, beneficiaries, distribution centers, and staff dispatches into an atomic, audited transaction.

```
                  ┌──────────────────────────────┐
                  │    Disaster Relief Event     │
                  └──────────────┬───────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  Relief Storage  │   │   Beneficiary    │   │   Distribution   │
│   (STORED only)  │   │  (VERIFIED only) │   │  (ACTIVE center) │
└────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                │
                                ▼
               ┌─────────────────────────────────┐
               │    Atomic Resource Dispatch     │
               │   (Pessimistic Row Locking)     │
               │  - Batch balance decremented    │
               │  - STORED → DISTRIBUTED at 0.0  │
               │  - Multi-batch allocation       │
               │  - Immutable audit record logged│
               └─────────────────────────────────┘
```

### Critical Business Rules
1. **Disaster Alignment Guard**:
   - The beneficiary, the distribution center, and the inventory batch must all belong to the exact same `disaster_id`. Cross-disaster mismatches return **HTTP 400 Bad Request**.
2. **Beneficiary Eligibility Gating**:
   - Aid can only be distributed to beneficiaries in **`VERIFIED`** status (`is_beneficiary_eligible() == True`). Beneficiaries in `PENDING` (unverified claim) or `INACTIVE` (archived/closed) status are blocked with **HTTP 400 Bad Request**.
3. **Distribution Center Readiness Gating**:
   - Distributions may only occur from **`ACTIVE`** facilities (`is_center_eligible_for_distribution() == True`). Centers in `FULL` (congested/at capacity) or `INACTIVE` (offline/closed) status are blocked with **HTTP 400 Bad Request**.
4. **Inventory Readiness & Unit Verification**:
   - Only inventory batches in **`STORED`** status can be distributed. Items in `RECEIVED` status (awaiting inspection) or `DISTRIBUTED` status (depleted) are blocked with **HTTP 400 Bad Request**.
   - The requested unit of measurement must match the batch unit (e.g. attempting to disburse "kg" from a batch recorded in "boxes" returns **HTTP 400 Bad Request**).
5. **Multi-Batch Allocation & Atomic Deduction**:
   - When a distribution is requested, the system locks matching candidate `STORED` batches using `with_for_update()`.
   - The requested batch is deducted first. If depleted to `0.0`, its status moves to `DISTRIBUTED`.
   - If the requested batch does not have sufficient quantity, subsequent sibling `STORED` batches (same disaster, same item name, same unit) are consumed automatically.
6. **Overselling Protection**:
   - If the requested quantity exceeds the total available stock across all matching `STORED` batches, the transaction is rejected immediately with **HTTP 400 Bad Request** without altering any inventory balances.
7. **Immutability & Audit Trail**:
   - Distribution records serve as legal humanitarian dispatch logs. No `PUT`, `PATCH`, or `DELETE` endpoints are exposed. Records can only be created (`POST`) and viewed (`GET`).

### Resource Distribution Endpoints Summary
| Method | Path | Required Role | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/distributions` | `ADMIN`, `NGO_STAFF` | Execute atomic distribution to verified beneficiary |
| `GET` | `/api/v1/distributions` | `ADMIN`, `NGO_STAFF` | List distribution audit logs with multi-field filters |
| `GET` | `/api/v1/distributions/{id}` | `ADMIN`, `NGO_STAFF` | Retrieve single immutable distribution audit log |

---

## 11. Stage 11: Disaster-Relief Summary & Report APIs

Stage 11 introduces a high-performance, read-only analytics and aggregation layer. It exposes executive summaries and domain-specific reports across all 8 entity models without taking locks or altering transactional data.

```
Existing Database
       │
       ▼
Report Service (app/services/report_service.py)
       │
       ▼
SQL Aggregation Queries (COUNT, SUM, CASE, COALESCE, GROUP BY)
       │
       ▼
Pydantic Response Schemas (app/schemas/report.py)
       │
       ▼
GET /api/v1/reports/... (app/api/v1/endpoints/reports.py)
       │
       ▼
Swagger UI (/docs) / Frontend Analytics
```

### Critical Business Rules
1. **Read-Only Guarantee**:
   - All report endpoints use HTTP `GET`. Under no circumstances do reports modify inventory, alter beneficiary statuses, edit tasks, or insert distribution records.
2. **Access Control (Strict RBAC)**:
   - Reports contain aggregate operational metrics and demographic distributions. Access is restricted exclusively to **`ADMIN`** and **`NGO_STAFF`**.
   - `VOLUNTEER` and `DONOR` receive **HTTP 403 Forbidden**. Unauthenticated requests receive **HTTP 401 Unauthorized**.
3. **Disaster 404 Validation**:
   - Every report requires a `disaster_id`. The service validates that the disaster exists before running aggregations. If nonexistent, returns **HTTP 404 Not Found**.
4. **Empty Operations Resilience**:
   - Disasters with zero associated records return clean zero counts and empty arrays (`[]`), avoiding null-pointer crashes or 500 errors.
5. **Zero-Division Safe Metrics**:
   - In volunteer reports, task completion percentage is calculated safely: `(completed / total) * 100.0` if `total > 0` else `0.0`.
6. **Privacy by Design**:
   - Beneficiary reports return aggregate demographic and vulnerability numbers. All PII (names, contact numbers, street addresses) is strictly excluded from queries and responses.
7. **Database Aggregation Efficiency**:
   - Aggregations (`COUNT`, `SUM`, `CASE`) execute in the database engine rather than transferring large record sets into Python memory.

### Report Endpoints Summary
| Method | Path | Required Role | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/reports/disasters/{id}/summary` | `ADMIN`, `NGO_STAFF` | Unified operational summary across all domains |
| `GET` | `/api/v1/reports/disasters/{id}/inventory` | `ADMIN`, `NGO_STAFF` | Intake volume vs. available STORED stock per item |
| `GET` | `/api/v1/reports/disasters/{id}/distributions` | `ADMIN`, `NGO_STAFF` | Total disbursements, per-item volume, center activity |
| `GET` | `/api/v1/reports/disasters/{id}/volunteers` | `ADMIN`, `NGO_STAFF` | Volunteer deployments, task status, completion rate |
| `GET` | `/api/v1/reports/disasters/{id}/beneficiaries` | `ADMIN`, `NGO_STAFF` | Demographic aggregates & vulnerability distribution (No PII) |

---

## 12. Running Automated Tests

Run the complete test suite (**101 tests**):
```powershell
pytest -v
```

Tests cover:
- Health and Swagger endpoints
- Database models, constraints, and sessions
- Authentication, registration, login, and JWT validation
- Disaster CRUD, status filtering, and date validation
- Volunteer disaster deployment and task lifecycle
- Money and material donation creation and conditional validation
- IDOR security tests (donors cannot view or modify other donors' donations)
- Donation state machine transitions (`PLEDGED → RECEIVED / CANCELLED`) and locks
- Inventory intake, storage transition (`RECEIVED → STORED`), and available stock calculations
- Beneficiary intake, validation, duplicate protection, and eligibility verification
- Distribution center intake, validation, and unique name enforcement per disaster
- Distribution center operational status transitions (`ACTIVE`, `FULL`, `INACTIVE`) and transition rules
- Distribution center operational eligibility checks (`is_center_eligible_for_distribution()`)
- Resource distribution atomic deduction, lifecycle progression (`STORED → DISTRIBUTED`), multi-batch allocation, and overselling protection
- Read-only reporting and summary analytics across all domains, privacy protection, and zero-division handling
- Role permissions (Admin-only operations, Staff CRUD, Volunteer/Donor 403 blocks)


