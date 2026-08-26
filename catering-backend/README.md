# Catering Management System — ARGO Module

## Project overview

The Catering Management System is the **Catering module** of the ARGO platform. It lets a
catering business log customer inquiries, price and send quotations, convert accepted
quotations into bookings, and manage everything that happens around a booking:

- guest counts, food requirements, staff assignments, equipment assignments
- deliveries, payments, and billing

The backend is a FastAPI (Python) JSON API backed by PostgreSQL, secured with role-based
access control (RBAC) that trusts the signed JWT (user, role, organization). The frontend
is a single-file Material-Design-3-style web app served by the same API. A separate
**public customer portal** (`/customer`, no login) lets customers submit inquiries and
check/accept/reject their quotations end-to-end.

> Note: there is **no AGENTS.md** in this repository. This README describes only what is
> actually implemented in the code right now.

## Technologies used

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Web framework | FastAPI 0.141, Uvicorn |
| ORM / database | SQLAlchemy 2.0, PostgreSQL |
| Migrations | Alembic (9 revisions, current head `catering_008`) |
| Auth | JWT (python-jose, HS256), bcrypt (passlib) |
| Validation | Pydantic 2 |
| Frontend | Single-file HTML/CSS/JS (`catering-mockup.html`), Bootstrap Icons |
| Passwords | bcrypt-hashed demo accounts via `seed.py` |

## Setup instructions

Prerequisites: Python 3.11, PostgreSQL running locally.

1. Create the database:

   ```sql
   CREATE DATABASE catering_db;
   ```

2. Configure the environment — copy/adjust `.env`:

   ```
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/catering_db
   JWT_SECRET_KEY=<random string of at least 32 characters>
   JWT_ALGORITHM=HS256
   JWT_EXPIRATION_MINUTES=1440
   JWT_ISSUER=catering-api
   JWT_AUDIENCE=catering-app
   ```

3. Install dependencies and apply migrations:

   ```
   venv\Scripts\python -m pip install -r requirements.txt
   venv\Scripts\python -m alembic upgrade head
   ```

4. Seed the demo organization, users, and reference data:

   ```
   venv\Scripts\python seed.py
   ```

5. Start the server:

   ```
   venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
   ```

6. Open the module UI at `http://127.0.0.1:8001/app`, the public customer portal at
   `http://127.0.0.1:8001/customer`, and the API docs at `http://127.0.0.1:8001/docs`.

Demo accounts (all `@example.com`): `admin` / `manager` / `staff` / `viewer`, passwords
`admin123` / `manager123` / `staff123` / `viewer123`.

## ARGO authentication expectations

- The API issues and accepts **Bearer JWTs** (HS256, signed with `JWT_SECRET_KEY`).
- Every protected endpoint requires an `Authorization: Bearer <token>` header.
- The token carries three claims used for authorization: `sub` (user id), `role`
  (`viewer` / `staff` / `manager` / `administrator`), and `org` (organization / tenant id).
- **Organization and role are taken from the signed token, never from the client.**
- Issuer (`catering-api`) and audience (`catering-app`) are verified on every request.
- A missing token returns `403 Not authenticated`; a tampered/expired/invalid token returns
  `401 Invalid token`.
- The parent ARGO platform is **not yet integrated**: the module currently issues its own
  tokens via `POST /auth/login`. The code is structured so a future ARGO-issued token can be
  validated the same way (it will just supply `role` and `org` claims).

## Routes list

### Public (no auth)
| Method | Path | Purpose |
|---|---|---|
| GET | `/` | API banner |
| GET | `/app` | Serves the module web app |
| GET | `/customer` | Serves the public customer portal (no login) |
| POST | `/auth/login` | Exchange email+password for a JWT |
| POST | `/public/inquiries` | Customer submits an inquiry |
| GET | `/public/inquiries/{reference}` | Customer checks inquiry/quotation/booking status |
| POST | `/public/inquiries/{reference}/quotations/{quotation_reference}/accept` | Customer accepts a quotation → creates booking |
| POST | `/public/inquiries/{reference}/quotations/{quotation_reference}/reject` | Customer declines a quotation |

The customer portal resolves the organization server-side (`PUBLIC_ORGANIZATION_ID`
setting in `app/config.py`, falling back to the single seeded organization), addresses
records only by non-guessable `INQ-`/`QUO-`/`BK-` UUID references, and never exposes
internal IDs, audit columns, or staff/billing data. Draft quotations are hidden from
customers until sent. Internal `/app` routes remain JWT/RBAC-protected.

### Authenticated
| Method | Path | Purpose |
|---|---|---|
| GET | `/auth/me` | Current user + permission list |
| GET/POST/PUT/DELETE | `/inquiries/…` | Customer inquiries |
| GET/POST/PUT/DELETE | `/quotations/…` | Quotations |
| POST | `/quotations/{id}/send` | Mark quotation sent |
| POST | `/quotations/{id}/accept` | Accept → creates booking |
| POST | `/quotations/{id}/reject` | Reject quotation |
| GET/POST | `/bookings/…` | Bookings |
| POST | `/bookings/{id}/transition` | pending→confirmed→in_progress→completed |
| POST | `/bookings/{id}/cancel` | Cancel booking |
| GET/POST/PUT/DELETE | `/packages/…` | Catering packages |
| GET/POST/PUT/DELETE | `/menus/…`, `/menus/{id}/items/…` | Menus + menu items |
| GET/POST/PUT/DELETE | `/guest-counts/…` | Guest counts per booking |
| GET/POST/PUT/DELETE | `/food-requirements/…` | Dietary requirements per booking |
| GET/POST/PUT/DELETE | `/staff/…` | Staff members |
| GET/POST/PUT/DELETE | `/staff-assignments/…` | Staff → booking assignments |
| GET/POST/PUT/DELETE | `/equipment/…` | Equipment |
| GET/POST/PUT/DELETE | `/equipment-assignments/…` | Equipment → booking assignments |
| GET/POST/PUT/DELETE | `/deliveries/…` | Deliveries |
| POST | `/deliveries/{id}/advance`, `/cancel` | Delivery status changes |
| GET/POST/PUT/DELETE | `/payments/…` | Payments (recompute booking payment status) |
| GET/POST/PUT/DELETE | `/billing/…`, `/billing/{id}/items/…` | Bills + bill items |
| POST | `/billing/{id}/send`, `/mark-paid`, `/void` | Bill status changes |

Full interactive list: `http://127.0.0.1:8001/docs`.

## Test steps

See **SUBMISSION.md** → *Test steps* for a reviewer-oriented walkthrough that matches the
required sequence (access ARGO → module/admin route → create a record → public/customer
route → complete workflow → verify in both portals).
