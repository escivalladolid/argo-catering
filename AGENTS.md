# AGENTS.md — Catering Management System

## Project layout
- `catering-backend/` — FastAPI + SQLAlchemy + PostgreSQL (`catering_db` at `postgresql://postgres:postgres@localhost:5432/catering_db`)
  - `catering-mockup.html` — admin portal (single file, lives INSIDE catering-backend/)
  - `customer-portal.html` — customer portal (single file)
- API base: `http://127.0.0.1:8001` (root-level routers, no `/api` prefix)
- Admin login for tests: `escivalladolid@gmail.com` / `admin123`
- venv python: `catering-backend\venv\Scripts\python.exe`

## Running the server
```powershell
# from catering-backend/ — NO --reload flag
Start-Process -FilePath ".\venv\Scripts\python.exe" `
  -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8001" `
  -WorkingDirectory "C:\xampp\htdocs\Capstone-Mobile-Quiz-System\catering-backend" `
  -WindowStyle Hidden `
  -RedirectStandardOutput "$env:TEMP\opencode\uvicorn_out.log" `
  -RedirectStandardError "$env:TEMP\opencode\uvicorn_err.log"
```
- Kill and start MUST be separate shell-tool commands; killing all python.exe breaks the tool session.
- After a kill command, the immediately following Start-Process command may report a spurious `ChildProcess.kill` error — the process still starts. Verify with `GET /openapi.json`.

## Conventions
- Migrations: numbered `alembic/versions/catering_XXX_*.py`, revision ids `catering_XXX`. Run with `& .\venv\Scripts\python.exe -m alembic upgrade head`.
- Public status endpoint response has TOP-LEVEL keys `inquiry`, `quotation`, `booking` — quotation is NOT nested inside inquiry.
- Customer-facing write endpoints on the portal are gated by the per-inquiry access token passed as a QUERY param (`?token=...`). Billing/payment endpoints use a separate OTP-based billing JWT instead.
- Manual response construction drops new schema fields silently — when adding fields to an Out model, grep for manual constructor calls.
- `CateringInquiryItem.kind` is constrained: 'default' | 'custom' | 'included' | 'addon'.
- Shared pricing lives in `app/flow.py`: `_price_catalog_ids()` is the single source of catalog item pricing (per_guest × guests, flat × qty). Used by custom-mode totals, premade add-ons, submit-time totals, quotation breakdowns, and the accept-time equipment copy.
- Dishes never need copying into bookings: booking detail and the customer status page read `inquiry.items` through the linked inquiry/quotation live.

## Environment notes
- Windows PowerShell 5.1; `rg` NOT installed (use Grep tool); git NOT installed.
- AGENTS.md did not exist until 2026-08-23 — keep it updated when conventions change.

## Feature history snapshot (2026-08-23)
- Premade-package add-ons (`addon_catalog_ids`, stored as kind='addon' inquiry items) + `requested_service_style` override; accept-time pass copies customer equipment picks into `catering_equipment_assignments`; staff picks are informational only.
- Proof-of-payment upload exists but `/uploads` has NO StaticFiles mount yet (URLs 404) and the admin portal has no proof viewer.
