# AUDIT_FULL.md — Full System Audit (Catering Management module)

**Type:** Report only — no code was changed.
**Date:** 2026-08-16
**Scope:** `catering-mockup.html` (admin UI, 3,489 lines), `customer-portal.html` (public UI),
all 19 backend routers, RBAC + flow + booking-scoped factory, `SUBMISSION.md`,
`USER_INTERACTIONS.md`, and the earlier `UX_AUDIT.md` (repo root).
**Method:** static source review (full reads of both HTML files and every router), endpoint
inventory via grep, permission cross-check against `rbac.py`, plus the API-level smoke
verification performed in the previous session (32/32 review-gate checks, 85/85 RBAC smoke
checks, 0/38 legacy inquiries flagged).

Everything below is *reported*, not fixed.

---

## 0. System map

- **Admin frontend:** `/app` served from `catering-mockup.html` (main.py:66-69). Roles
  viewer / staff / manager / administrator, JWT bearer.
- **Customer frontend:** `/customer` served from `customer-portal.html` (main.py:71-74). No
  login; org resolved server-side; records addressed by `INQ-`/`QUO-`/`BK-` UUID references.
- **Backend:** FastAPI on 127.0.0.1:8001, single venv, ~115 routes across 19 routers
  (main.py:41-59). Two auth mechanisms coexist (see §2.B).
- **State machines:** inquiry `new→quoted→converted|closed`; quotation
  `draft→sent→accepted|rejected`; booking `pending→confirmed→in_progress→completed` (+
  `cancelled`); delivery `scheduled→in_transit→delivered` (+`cancelled`); bill
  `draft→sent→paid|void` with `overdue` computed at read time (never persisted).

### Endpoint inventory (confirmed by grep)

| Router | Prefix | Routes |
|---|---|---|
| auth_router | /auth | POST /login, GET /me |
| users | /users | GET "", POST "", PUT /{id}, POST /{id}/role-change/request-code, /{id}/deactivate, /{id}/deactivate/request-code, /{id}/reactivate, /{id}/reactivate/request-code, /{id}/reset-password, /{id}/reset-password/request-code |
| inquiries | /inquiries | GET "", POST "", GET /pending-review, GET /{id}, GET /{id}/detail, PUT /{id}, POST /{id}/approve-review, POST /{id}/reject-review, DELETE /{id} |
| quotations | /quotations | GET /from-inquiry/{id}, POST /from-inquiry/{id}, GET "", POST "", GET /{id}, GET /{id}/detail, POST /{id}/send, /{id}/accept, /{id}/reject, DELETE /{id} |
| bookings | /bookings | GET "", GET /{id}, GET /{id}/detail, POST /{id}/transition, POST /{id}/cancel |
| packages | /packages | GET "", POST "", GET /{id}, GET /{id}/detail, PUT /{id}, DELETE /{id} |
| menus | /menus | GET "", GET /foods, POST "", GET /{id}, PUT /{id}, DELETE /{id}, GET /{id}/items, POST /{id}/items, PUT /{id}/items/{item_id}, DELETE /{id}/items/{item_id} |
| guest_counts (factory) | /guest-counts | GET/POST "", GET/PUT/DELETE /{id} |
| food_requirements (factory) | /food-requirements | GET/POST "", GET/PUT/DELETE /{id} |
| payments (factory) | /payments | GET/POST "", GET/PUT/DELETE /{id} (+ after_write recomputes booking.payment_status) |
| staffing | /staff | GET "", POST "", GET /availability, GET /{id}, PUT /{id}, DELETE /{id} |
| staffing | /staff-assignments | GET/POST "", GET/PUT/DELETE /{id} |
| equipment | /equipment | GET/POST "", GET/PUT/DELETE /{id} |
| equipment | /equipment-assignments | GET/POST "", GET/PUT/DELETE /{id} |
| deliveries | /deliveries | GET/POST "", GET /{id}, PUT /{id}, DELETE /{id}, POST /{id}/advance, /{id}/cancel |
| billing | /billing | GET "", POST "", GET /{id}, PUT /{id}, DELETE /{id}, GET/POST /{id}/items, PUT/DELETE /{id}/items/{item_id}, POST /{id}/send, /{id}/mark-paid, /{id}/void |
| public_portal | /public | GET /packages, GET /packages/{id}, POST /inquiries, GET /inquiries/{reference}, POST /inquiries/{reference}/quotations/{qref}/accept, /reject |
| audit_log | /audit-log | GET "" |
| dashboard | /dashboard | GET /attention |

---

## 1. Part 1 — Working vs broken / incomplete / phantom actions

### 1.1 Working correctly (traced end to end)

| Flow | Trace | Notes |
|---|---|---|
| Customer submits inquiry | portal submit → `POST /public/inquiries` → validate selections (public_portal.py:228-312) → staffing availability (staffing.py:67-103) → `flag_note`/`pending_review` (public_portal.py:453-459) | Availability per role; near-term exempt (`REVIEW_EXEMPT_DAYS=7`, line 72) |
| Customer tracks status | `GET /public/inquiries/{reference}` returns inquiry + visible quotation (sent/accepted/rejected only, line 127-139) + booking |
| Customer accept quotation | `POST .../accept` — `with_for_update` row lock + `perform_accept` → exactly one booking, inquiry `converted` (public_portal.py:615-621) | Double-click → 409, no duplicate (verified) |
| Customer reject quotation | `POST .../reject` → quotation `rejected`, inquiry `closed` if no other open quotation |
| Staff triage / edit inquiry | Inquiries page; list excludes `pending_review` (inquiries.py:137); edit via PUT (307) |
| Draft quotation from inquiry | `POST /quotations/from-inquiry/{id}` prefills package + `suggested_price` (flow.py:40-43); inquiry → `quoted`; blocked for converted/closed/pending_review/rejected inquiries (quotations.py:279-284) |
| Send / approve / reject / delete quotation | send (431, draft-only), accept (463, `quotation:approve`, row-locked), reject (477), delete (490, draft/sent/rejected only) |
| Booking lifecycle | transition (bookings.py:156-191): `pending→confirmed` needs `booking:confirm`; onward needs `booking:update_progress`; cancel (194) resets payment_status to `unpaid` |
| Payment record/edit/delete | factory CRUD + `recompute_payment_status` (payments.py:15-34) keeps booking `payment_status` in sync |
| Review gate | `pending-review` list (202), approve (215), reject (246) — all `inquiry:update`; quotation creation blocked while pending/rejected. Verified 32/32 |
| Dashboard attention | `_build_groups` (dashboard.py:53-415) + role filtering (439-444): non-manager drops manager groups, viewer drops staff group + read-only. 8 groups confirmed |
| Users & roles | `require_role("administrator")` everywhere; step-up code REQUIRED for role change / deactivate / reactivate / reset-password (users.py:172-177, 219, 255, 291); self-role-change and self-deactivate blocked (167-171, 214-218) |
| Billing | draft→send→mark-paid/void, guarded status transitions (billing.py:386-443); line items CRUD |

### 1.2 Phantom features — permissions that exist in RBAC but have **no** endpoint and **no** UI action

These are "pre-wired" (rbac.py:130-135 comment) but some are also *advertised in the docs/UI*
as real, which is the problem:

| Permission | rbac.py | Referenced as a real feature in | Reality |
|---|---|---|---|
| `equipment:request` / `equipment:update_usage` / `equipment:approve` | 98-100 | ROLES_MATRIX "Equipment — view / request / usage", "Equipment — manage / approve" (mockup 1730-1731); USER_INTERACTIONS §6 "approve requests / Approval logged"; SUBMISSION.md "manage equipment" | equipment router exposes **CRUD only** (equipment.py:60-179). No request/approve/usage endpoint, no status field, no approval UI. |
| `payment:verify` | 119 | ROLES_MATRIX "Payments — update / verify" (1736); USER_INTERACTIONS §6 "Verify payments" | payments router is factory CRUD only; no verify endpoint/button. |
| `booking:update_prep` | 55 | ROLES_MATRIX "Update booking prep / progress" (1718) | No prep feature; transition only covers confirm/progress. |
| `delivery:advance` | 110 | ROLES_MATRIX "Deliveries — view / create / advance" (1733); USER_INTERACTIONS staff §5 | Endpoint exists but enforces **`delivery:update`** (deliveries.py:161), not `delivery:advance`. Same role today, but UI gates on `delivery:advance` (mockup 2834, 3109) while backend checks `delivery:update` — two different perms for one action. |
| `staff:assign` | 87 | USER_INTERACTIONS "Staff & assignments — view / create / assign" | Assignment creation requires `staff_assignment:create` (staffing.py:306); `staff:assign` never required. |
| `report:view` / `analytics:view` | 131-132 | ROLES_MATRIX "Analytics" (1739) | No module, no endpoint. |
| `settings:configure` / `system:restore` / `system:override` | 133-135 | ROLES_MATRIX "System settings / restore / override" (1742) | No endpoints. Users page gated client-side on `settings:configure` (mockup 349) but server ignores it (see §2.B). |

### 1.3 Broken or dead-end UI actions

| Action | Where | What happens |
|---|---|---|
| **Billing filter "Overdue"** | mockup filterOptions 2865 | Bills never persist `status='overdue'` (billing.py:59-63 computes it at read time *after* filtering at 87). `?status=overdue` → `apply_status` filters the DB column first → **always zero rows**. The filter is a dead end. (Same root cause as SUBMISSION.md #4.) |
| **Delivery status "Delayed"** | mockup filter 2817 and form select 2825 | Backend state machine has no `delayed` (advance map deliveries.py:167, cancel guard 200). Selecting it either 422s or persists a record that can never advance. USER_INTERACTIONS §8 "mark delayed" claims this feature. |
| **Quotation filter label "Approved"** | mockup 738 | Label maps to API value `accepted` — cosmetic, but the filter label and the status badge text diverge (`accepted` vs `approved`). |
| **Pending Review button from dashboard** | mockup 1186 | `goTo('pending-review'); setTimeout(..., 300)` then `openReviewModal(id)` reads `state.rows['pending-review']` (2087). If the list fetch is slower than 300 ms the modal opens against a stale/empty list. |
| **Own-role / self edits** | Users page | Server blocks self-role-change and self-deactivate (users.py:167-171, 214-218). Whether the row menu is disabled for the current user in the UI was not visible in the page renderer — verify the self-row isn't offering actions that will 400. |

### 1.4 Incomplete / inconsistent behaviors

1. **Billing and payments are two unlinked workflows** (SUBMISSION.md #5, confirmed). Marking a
   bill `paid` (billing.py:404-415) neither writes a payment row nor touches
   `booking.payment_status`. Result: a booking can be "paid in full" via bills yet still show
   `partial/unpaid` (payments.py recompute only runs on payment writes), and it stays in the
   dashboard **Completed — balance due** group (dashboard.py:340-377 uses `payment_summary`,
   flow.py:81-100). Cross-module contradiction.
2. **Menu / bill items "replaced not edited"** (SUBMISSION.md #10). The *item-level* PUT/DELETE
   endpoints now exist (menus.py:337/368, billing.py:298/340), so the limitation is partially
   addressed for new flows — but a bulk PUT on the parent still re-sends items. Stale doc
   claim; verify which path the mockup uses.
3. **Concurrency:** only quotation accept is server-row-locked (quotations.py:470,
   public_portal.py:615). Booking `transition` (bookings.py:156) and delivery
   advance/cancel have no lock/version guard — the UI's `state.saving` single-flight is the
   only protection; a double-submit past the UI could advance two steps.
4. **Two authorization mechanisms** (see §2.B): RBAC permission deps for 18 routers vs
   `require_role("administrator")` hard-coded in users.py. Behaviorally equivalent today.

---

## 2. Part 2 — Action triage

### CORE (must keep working; the revenue path)
- Inquiry create / edit / delete; quotation draft / edit / send / approve / reject / delete;
  booking transition + cancel; payment record / update / delete; customer portal
  submit / status / accept / reject; review-gate approve / reject.
- All CORE actions verified working (see §1.1; smoke-tested previously).

### SUPPORTING (nice-to-have depth; works, minor rough edges)
- Guest counts, food requirements (factory CRUD) — working.
- Deliveries create / update / advance / cancel / delete — working; **Delayed** status is not.
- Billing CRUD + send / mark-paid / void — working; **Overdue** is display-only.
- Staff & roster, staff/equipment assignments — working.
- Dashboard attention groups — working, role-filtered.
- Users & roles + step-up verification, Activity Log — working.

### QUESTIONABLE (dead perms, phantom docs, or dead-end UI)
- Equipment "request / usage / approve" (no endpoints — RBAC + docs only).
- Payment "verify" (no endpoint).
- Booking "prep" (no feature).
- Delivery **Delayed** status (UI option, no state machine).
- Bill **Overdue** filter (always empty).
- Reports, Analytics, System settings / restore / override (RBAC only).
- `staff:assign` (never required by an endpoint).
- Menu-level bulk item replace (item-level edit now available).

---

## 3. Part 3 — UI rough edges (newer modules only)

Using the UX_AUDIT.md 8 categories, scoped to Pending Review, Users & Roles, Activity Log,
dashboard attention, and the package-builder redesign:

1. **Feedback after actions** — approve/reject review, bill send/mark-paid/void, delivery
   advance/cancel, and user actions all toast a confirmation (good). Gap: quotation *send*
   toast is generic; no explicit "customer can now see it" hint.
2. **Error message quality** — 422s are unwrapped nicely client-side (apiFetch, mockup
   405-418). Gap: the step-up verification modal has no inline resend/cooldown message; the
   429 "try again in Ns" surfaces only in the toast.
3. **Required-field clarity** — module forms mark `*` (mockup 2961) and block save with a
   toast (3048). Gap: customer portal staffing/requirements sections don't indicate optionality.
4. **Label clarity** — quotation filter "Approved" vs stored "accepted"; delivery "Delayed";
   bill "Overdue" as a filter (all dead-ends, §1.3). Inconsistent terminology: booking tab
   labels vs status names.
5. **Consistency** — equipment assignments allow staff create/update (RBAC) while the
   equipment catalog is manager+; the dashboard "Missing staff / equipment" flags confirmed
   bookings with zero assignments, but staff *can* create equipment assignments while they
   **cannot** create staff assignments — inconsistent visibility of the "missing" flag.
6. **Dead ends** — Billing Overdue filter, Delivery Delayed, Equipment request/approve,
   Payment verify, Booking prep (all §1.2/1.3).
7. **Mobile/responsive** — module pages have desktop-table ↔ mobile-card + drawer
   (mockup 3145-3167); pending-review and users pages also have card fallbacks. Not tested on
   physical phones (SUBMISSION.md #7).
8. **Loading states** — list pages show loading rows + error state (mockup 3140-3142).
   Gap: the dashboard "Review" deep-link (1186) races the list fetch (§1.3).

---

## 4. Cross-module contradictions & dead code summary

- **Phantom permissions (RBAC-only):** `report:view`, `analytics:view`,
  `settings:configure`, `system:restore`, `system:override`, `booking:update_prep`,
  `equipment:request`, `equipment:update_usage`, `equipment:approve`, `payment:verify`,
  `staff:assign`, `delivery:advance` (perm never checked by its own endpoint).
- **Doc claims exceeding implementation:** USER_INTERACTIONS.md §6 (equipment approve,
  payment verify), §8 (mark delayed); ROLES_MATRIX rows 1718, 1731, 1736, 1739, 1742.
- **Stale SUBMISSION.md claim:** limitation #10 ("items replaced, not edited") — item-level
  PUT/DELETE now exists; menu-level replace behavior should be re-verified.
- **Billing/payments split** is real and documented (#5); its side effect on the dashboard
  balance_due group is not called out in the docs.

## 5. Known limitations re-check (SUBMISSION.md)

All 11 items confirmed accurate as written, with the note on #10 above and the added detail
for #4/#5 in §1.4.

## 6. Risks

1. No automated tests / no CI (SUBMISSION.md #8) — the phantom-perm and dead-end-filter
   issues above shipped without detection.
2. Demo credentials + JWT secret not gitignored (#9) — .env protection still pending.
3. Booking/delivery transitions lack server-side concurrency guards (UI single-flight only).
4. `pending_review` auto-approval path trusts staff review of `flag_note`; near-term
   exemption means staffing shortfalls inside 7 days never reach the review queue.
