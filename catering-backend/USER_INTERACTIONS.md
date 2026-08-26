# User Interactions — How Staff, Manager, and Admin Handle a Customer

**Module:** Catering Management (ARGO platform) · **App UI:** `http://127.0.0.1:8001/app`
**Customer portal:** `http://127.0.0.1:8001/customer` (no login) · **API:** `http://127.0.0.1:8001/docs`

This document walks through, step by step, how the three working roles — **Staff**, **Manager**,
and **Administrator** — handle a customer from first contact to final payment. It mirrors the
actual permissions in `app/rbac.py`, the status rules in the routers, and the buttons the UI
shows for each role in `catering-mockup.html`.

---

## 1. Roles at a glance

| Role | Who they are | Typical job | Login |
|---|---|---|---|
| **Staff** | Frontline coordinators | Triage inquiries, draft & send quotations, run the event (prep → in progress → completed), schedule deliveries, record payments, build bills | `staff@example.com` / `staff123` |
| **Manager** | Operations lead | Approves quotations, confirms & cancels bookings, owns staffing/equipment assignments, sends/marks-paid/voids bills, reviews the Activity Log | `manager@example.com` / `manager123` |
| **Administrator** | System owner | Everything a manager can do, plus package/menu catalogs, deleting staff, and the Users & Roles page (create/edit/deactivate/reset-password) | `escivalladolid@gmail.com` / `admin123` |
| Viewer (reference) | Read-only | Can see dashboard/inquiries/quotations/bookings/packages/menus | `viewer@example.com` / `viewer123` |

**The customer** never logs in. They use the public portal at `/customer`, addressing their
records only by the non-guessable references they are given (`INQ-…`, `QUO-…`, `BK-…`).

### What each role can do (permission summary)

| Capability | Viewer | Staff | Manager | Administrator |
|---|---|---|---|---|
| Dashboard | ✔ | ✔ | ✔ | ✔ |
| Inquiries — create / update | – | ✔ | ✔ | ✔ |
| Inquiries — delete | – | – | ✔ | ✔ |
| Quotations — create / update / send | – | ✔ | ✔ | ✔ |
| Quotations — approve (accept) / reject / delete | – | – | ✔ | ✔ |
| Bookings — confirm (pending→confirmed) | – | – | ✔ | ✔ |
| Bookings — advance (confirmed→in progress→completed) | – | ✔ | ✔ | ✔ |
| Bookings — cancel | – | – | ✔ | ✔ |
| Guest counts / food requirements — create / update | – | ✔ | ✔ | ✔ |
| Staff & assignments — view / create / assign | – | – | ✔ | ✔ |
| Staff — delete | – | – | – | ✔ |
| Equipment — view | – | ✔ | ✔ | ✔ |
| Equipment — manage | – | – | ✔ | ✔ |
| Deliveries — create / update / advance / cancel | – | ✔ | ✔ | ✔ |
| Deliveries — delete | – | – | ✔ | ✔ |
| Payments — record | – | ✔ | ✔ | ✔ |
| Payments — update / delete | – | – | ✔ | ✔ |
| Bills — create / update | – | ✔ | ✔ | ✔ |
| Bills — send / mark paid / void / delete | – | – | ✔ | ✔ |
| Packages & menus — create / update / delete | – | – | – | ✔ |
| Activity Log (audit) | – | – | ✔ | ✔ |
| Users & Roles (user management) | – | – | – | ✔ |

---

## 2. The customer journey (end to end)

```
Customer                        Staff                      Manager / Admin
────────                        ─────                      ────────────────
1. Submits inquiry       ──►   2. Triage (New)
                              3. Drafts quotation  (inquiry → Quoted)
                              4. Sends quotation   (quotation → Sent)
                                         │
Customer 5. Accepts/Declines ──►   6a. Accept → Booking created (Pending), inquiry → Converted
  via portal (or call)               6b. Decline → quotation Rejected, inquiry → Closed
                                         │
                              7. Manager Confirms booking (Confirmed)
                              8. Staff advances event  (In progress → Completed)
                              9. Staff/Manager schedule delivery & advance (Scheduled →
                                 In transit → Delivered); Manager assigns staff & equipment
                             10. Staff records payments; Manager sends bill, marks paid/voids
```

The canonical happy path in detail is in **Section 4**. Sections 5–7 then repeat it from each
role's point of view, showing exactly which buttons they see and which rules the system enforces.

---

## 3. Status rules (what the backend enforces)

These are the state machines from the models and routers. Everything below is enforced
server-side; the UI only shows the actions the current role is allowed to take.

**Inquiry:** `new → quoted → converted` (booked) or `new → quoted → closed` (declined).
`quoted` is set automatically when a draft quotation is created. Deleted inquiries also soft-delete
their quotations.

**Quotation:** `draft → sent → accepted | rejected`. Accept is only allowed when
`draft` or `sent` and not expired (`valid_until`); it creates **exactly one** booking and marks the
inquiry `converted`. Reject closes the inquiry unless another quotation is still open.
Delete is only allowed for `draft` / `sent` / `rejected`.

**Booking:** `pending → confirmed → in_progress → completed`, or `pending/confirmed/in_progress
→ cancelled`. Cancelling resets `payment_status` to `unpaid`. A completed or cancelled booking
cannot be cancelled again.

**Delivery:** `scheduled → in_transit → delivered`, or `scheduled/in_transit/delayed → cancelled`.
A delivery can also be set to `delayed` (via create or update) when a problem is encountered
en route; from `delayed`, **Advance** returns it to `in_transit` (retry), or **Cancel** discards it.
`delivered` and `cancelled` are terminal — cannot be advanced or cancelled further.

**Bill:** `draft → sent → paid`, with `overdue` computed in display and `void` for cancelled bills.

**Payment methods:** cash, bank_transfer, card, gcash, check, other.

**Staff member roles:** chef, server, crew, supervisor, driver, bartender, kitchen_staff, support.
**Guest-count types:** estimated, guaranteed, actual.
**Food-requirement types:** vegetarian, vegan, halal, gluten_free, allergy, other.

---

## 4. Step-by-step walkthrough (canonical happy path)

### Step 1 — Customer submits an inquiry (public portal, no login)

1. Customer opens `http://127.0.0.1:8001/customer`.
2. They pick an active package (or submit without one), enter name, contact, event date/time,
   address details, guest count, food requirements, and optionally staffing numbers.
3. They hit **Submit**. The backend validates the selections (only dishes that exist on the
   package; unavailable dishes are rejected in custom mode or flagged in default mode).
4. The system stores the inquiry as `new` and returns a reference **`INQ-<uuid>`** that the
   customer keeps to check status later.
5. If a requested dish is unavailable, or the staffing request exceeds what is available on that
   date, the backend writes an internal `flag_note` on the inquiry — the first thing staff sees.

### Step 2 — Staff triage (Inquiries page)

1. Staff signs in at `/app` (email + password, JWT issued).
2. **Inquiries** list shows the new inquiry with status **New**. The red flag icon/note (if any)
   tells staff the customer picked an unavailable dish or asked for more staff than is free.
3. Staff opens the inquiry (View) to read customer details, package, items, requirements,
   requested staffing, and the flag note.
4. If details are wrong or incomplete, staff uses **Edit** to correct them (name, contact, date,
   guests, address, items, staffing). Viewer-level and non-authorized roles never see Edit/Delete.

### Step 3 — Staff drafts a quotation (Quotations page)

1. From the inquiry, staff clicks **New quotation** (or *New quotation* on the Quotations page).
2. The form prefills from the inquiry (guest count, package, suggested price via
   `base_price × guests` or fixed). Staff sets the total price and `valid_until` date.
3. **Save** creates the quotation in `draft` status. The inquiry automatically flips to
   **Quoted**.
4. Staff can re-open and **Edit** the draft as many times as needed; the customer still sees
   nothing yet.

### Step 4 — Staff sends the quotation (quotation → Sent)

1. Staff clicks **Send** on the draft quotation (a confirmation/feedback toast appears).
2. Status becomes **Sent**. From now on the customer can see the quotation on the portal:
   amount, valid-until, package, items, and **Accept / Decline** buttons.
3. Draft quotations were hidden from the customer until this moment.

### Step 5 — Customer decides (portal)

- **Accept:** the backend creates a **Booking** (`pending`, `payment_status=unpaid`), flips the
  quotation to `accepted` and the inquiry to `converted`, then returns a **`BK-<uuid>`** reference.
- **Decline:** the quotation becomes `rejected`; if no other quotation is open the inquiry closes
  (`closed`).
- Staff can also hear back by phone and record the outcome themselves — see the manager step below.

### Step 6 — Manager approves / confirms the booking

1. Manager opens **Quotations** and sees the sent quotation with the **Approve** (accept) and
   **Reject** actions — these are manager+ only; staff cannot accept.
2. **Approve** creates the booking (identical logic to the customer portal — the booking is
   always created by the backend exactly once; a second accept is rejected with a conflict).
3. On **Bookings**, the manager sees the booking **Pending** and clicks **Confirm**.
   (Pending→Confirmed requires `booking:confirm`, manager+ only.)

### Step 7 — Staff runs the event

1. On the event day the booking shows **Confirmed**. Staff opens the booking and clicks
   **Advance** to move it to **In progress**, then again to **Completed**.
   (Confirmed→In progress→Completed requires `booking:update_progress`, which staff holds.)

### Step 8 — Manager assigns staff and equipment

1. On the booking **Details** tab, the manager sees the staffing requested by the inquiry, the
   staffing available that day, and a **staffing shortfall warning** if numbers don't add up.
2. In **Staff & Assignments** the manager adds staff members, then assigns them to the booking
   with shift start/end and role. Equipment assignments are made the same way.
3. (Staff cannot even open the Staff page — no `staff:view`; and can only create/update
   *equipment assignments*, not the equipment catalog itself.)

### Step 9 — Staff schedules and advances the delivery

1. On the booking's Deliveries tab (or the Deliveries page), staff creates a delivery with
   scheduled time, address, and contact.
2. Status starts `scheduled`. On dispatch day staff clicks **Advance** → **In transit**, then
   on arrival **Advance** → **Delivered**. If a problem is encountered en route, staff clicks
   **Delay** to set status to `delayed`; from there, **Advance** retries (`delayed → in_transit`)
   or **Cancel** discards the delivery. **Cancel** is also available from `scheduled` or
   `in_transit`. Once `delivered` or `cancelled`, no further actions are possible.

### Step 10 — Payments and billing

1. When the customer pays, staff opens the booking's **Payments** tab and clicks
   **Record payment** (amount, method cash/gcash/card/etc., reference, notes). The booking's
   "Amount paid / Remaining balance" updates automatically.
2. Staff creates the bill on the **Billing** tab with line items; the bill starts `draft`.
3. Only the manager can **Send** the bill, **Mark paid**, or **Void** it.
4. Every payment and bill action is written to the Activity Log with the actor, entity, and summary.

### Step 11 — Everyone can verify

- **Manager/Admin:** open **Activity Log** to see the full trail (who did what, when), filtered by
  entity, date range, or search.
- **Customer:** re-open `/customer` → **Check Status** with their `INQ-…` reference to see the
  inquiry, the accepted quotation, and the booking reference with status **Pending/Confirmed/
  In progress/Completed** and payment **Unpaid/Paid**.

---

## 5. Staff interactions in detail

Staff are the hands of the operation. They never approve quotations, confirm bookings, manage the
staff roster, delete things, or see the Activity Log.

| Interaction | What staff does on screen | System behavior |
|---|---|---|
| Log in | Email + password on `/app` | JWT issued; role `staff`; nav shows only permitted pages |
| New inquiry (phone/walk-in) | Inquiries → **New inquiry**, fill customer/event/guests | Inquiry saved as `new` |
| Triage flagged inquiry | Open inquiry, read `flag_note` (unavailable dish, staffing shortfall) | Staff decides to call customer / adjust |
| Correct details | Inquiries → **Edit** | Inquiry updated; audit row `inquiry updated` |
| Draft quotation | Quotations → **New quotation** (prefilled) or from inquiry | Quotation `draft`; inquiry → `quoted` |
| Re-quote | Edit draft quotation | Re-save, stays `draft` |
| Send quotation | **Send** on the draft | Quotation `sent`; customer portal unlocks Accept/Decline |
| Guest count updates | Booking → guest counts module (create/update estimated/guaranteed/actual) | New count row logged |
| Food requirements | Booking → food requirements module (create/update) | Rows for vegetarian/vegan/halal/allergy/etc. |
| Equipment request | Booking → equipment assignments (create/update) | Assignment logged; manager handles the catalog |
| Advance event status | Booking → **Advance** (confirmed→in progress→completed) | Requires `booking:update_progress` |
| Create delivery | Booking deliveries / Deliveries → **New** | Delivery `scheduled` |
| Dispatch / arrive | Delivery **Advance** → `in_transit` → `delivered` | Requires `delivery:advance` |
| Delay delivery | Delivery **Delay** → `delayed` | Requires `delivery:delay`; allows retry or cancel later |
| Cancel delivery | Delivery **Cancel** | Only if not `delivered`/`cancelled`; requires `delivery:cancel` |
| Record payment | Booking → Payments → **Record payment** | Payment row; balance recomputed |
| Build a bill | Booking → Billing → **Create bill** (line items) | Bill `draft` |
| What staff **cannot** do | Approve/reject/delete quotations, confirm/cancel bookings, view staff roster, manage equipment catalog, send/mark-paid/void bills, delete deliveries, open Activity Log or Users | Backend returns `403` if forced |

---

## 6. Manager interactions in detail

Managers do everything staff do, plus the decision points and money actions. Staff does the
legwork; the manager keeps control.

| Interaction | What manager does on screen | System behavior |
|---|---|---|
| Everything staff can do | Same screens as Section 5 | – |
| Approve a quotation | Quotations → **Approve** (or Reject) | Booking created (`pending`), quotation `accepted`, inquiry `converted`; or quotation `rejected`/inquiry `closed` |
| Confirm booking | Bookings → **Confirm** on a `pending` booking | Status `confirmed` (needs `booking:confirm`) |
| Cancel booking | Bookings → **Cancel** (not on completed/cancelled) | Status `cancelled`, `payment_status` reset to unpaid |
| Manage staff roster | Staff & Assignments → add staff members, then **assign** to a booking with shifts | Staff member + assignment rows; shortfall warning shown on booking detail |
| Manage equipment | Equipment → create/update/delete | Catalog changes affect assignment availability |
| Delete data | Delete inquiry / quotation / delivery / payment / bill (guarded by status rules) | Soft delete + audit row |
| Update / delete payments | Payments → update/delete a payment | Payment rows corrected; balance recomputed |
| Money: send bill | Billing → **Send** | Bill `draft → sent` |
| Money: collect | Billing → **Mark paid** | Bill `sent → paid` |
| Money: write off | Billing → **Void** | Bill `void` |
| Oversight | Activity Log → filter by entity/date/search | Read-only `audit:view`; newest first |
| What manager **cannot** do | Create/update/delete packages & menus, delete staff members, manage user accounts | Admin-only permissions |

---

## 7. Administrator interactions in detail

The administrator is the catalog and account owner. They hold every manager permission plus the
configuration surface.

| Interaction | What admin does on screen | System behavior |
|---|---|---|
| Everything manager can do | Same screens as Sections 5–6 | – |
| Manage packages | Packages → **New package** (name, base price, per-guest/fixed, included/default/option items, customization groups) | Catalog drives the customer portal and quotation prefill |
| Manage menus & items | Menus & Items → create/edit/delete menus and dishes | Dishes feed packages; inactive items block custom selection |
| Delete staff member | Staff & Assignments → **Delete** (deactivate) a staff member | `staff:delete` (admin only) |
| Manage users | Users & Roles → **New user** (email, name, role) | Temporary password shown once; user can then log in |
| Change a role | Users & Roles → **Edit** role | Role claim updates on that user's next login |
| Reset a password | Users & Roles → **Reset password** | New temporary password shown once (email verification used for sensitive actions) |
| Deactivate / reactivate | Users & Roles → **Deactivate** / **Reactivate** | Deactivated account can no longer sign in (`403`) until reactivated |
| Review permissions | Users & Roles → **Roles & permissions** tab | Read-only matrix per role |
| Config / system | (pre-wired hooks) settings, restore, override | Not yet exposed as screens — reserved perms exist in RBAC |
| What admin **cannot** do | Login as the customer, or act on a customer's behalf inside the portal | Customer actions stay on `/customer` |

---

## 8. Edge cases and how each role handles them

| Situation | Who handles it | What happens |
|---|---|---|
| Customer calls instead of using the portal | Staff | Staff creates the inquiry manually (Step 2), then quotes and sends; customer decides over the phone, staff records the outcome via the manager's Approve/Reject |
| Unavailable dish selected | Customer (portal) + Staff | Custom mode rejects it outright; default mode writes a `flag_note` warning staff must review |
| Staffing shortfall on the event date | Customer (portal) + Staff/Manager | `flag_note` + a red warning box on the booking detail; manager rebalances assignments or re-roles staff |
| Quotation expired (`valid_until` passed) | Manager | Accept is refused server-side; manager drafts a new quotation |
| Customer double-clicks Accept | System | Second accept returns `409` (booking already exists); no duplicate booking |
| Customer declines | Manager | Quotation `rejected`; inquiry `closed` if no other open quotation |
| Booking must be called off | Manager | **Cancel booking** — but never once `completed`/`cancelled`; payment resets to unpaid |
| Delivery runs late / falls through | Staff | Delivery **Cancel** (if not delivered) or mark delayed; audit trail shows who |
| Customer disputes a payment | Manager | Update / delete the payment row; balances recompute automatically |
| Bill never sent | Manager | Bills sit in `draft`; only the manager can **Send** |
| Customer never pays | Manager | Bill shows `overdue` (computed in display); manager follows up and can void |
| Wrong package on the portal | Administrator | Deactivate the package; it disappears from the public catalog immediately |
| A staff member leaves | Administrator | **Deactivate** the user; sign-in is blocked (`403`) until reactivated |
| Need to prove who did what | Manager/Admin | Activity Log — entity filter, date range, search, actor, summary |

---

## 9. What the customer actually sees (for the role-aware view)

The portal only exposes customer-safe data — no internal IDs, no audit columns, no staff,
payments, or billing numbers:

1. **Submit inquiry** → gets `INQ-<uuid>`.
2. **Check status** with that reference → inquiry details; the quotation appears **only after
   staff sends it** (drafts stay hidden), with Accept/Decline.
3. After acceptance → booking reference `BK-<uuid>`, status **Pending** and payment **Unpaid**,
   plus the amount paid / remaining balance.
4. After a decline → quotation `Rejected` and, if nothing else is open, the inquiry `Closed`.

A staff, manager, or admin never touches these references directly; they work on the internal
screens, and both portals show the same record state immediately because they share one database.

---

## 10. Quick test script per role

1. **Staff** — sign in, create an inquiry, draft + send a quotation, record a payment, create a
   delivery and advance it. Confirm you *cannot* see Approve on the quotation, the Staff page,
   the Activity Log, or the Billing Send/Mark-paid buttons.
2. **Manager** — approve that quotation (booking appears), confirm the booking, assign staff,
   send the bill, mark it paid, and review the Activity Log entries created by every action above.
3. **Administrator** — create a package and a menu, delete a staff member, create a new user and
   verify the temporary password lets them sign in, then deactivate them.
4. **Customer** — submit an inquiry in `/customer`, wait for the quotation to be sent, then accept
   it and verify the booking reference and status match what the admin portal shows.

---

## 11. Role-aware "Needs attention" dashboard

The Dashboard now surfaces a **Needs attention** section under the KPI cards, backed by
`GET /dashboard/attention` (`app/routers/dashboard.py`). Groups are computed server-side, scoped
to the caller's organization, and filtered by the caller's role:

**Everyone (Staff, Manager, Administrator, Viewer):**

| Group | Rule |
|---|---|
| Needs a quotation | Inquiries in `new` waiting for a quotation (shown immediately, oldest first) |
| Awaiting customer response | Quotations in `sent`, ordered by `valid_until` |
| Happening soon | Confirmed / in-progress bookings whose event date falls within the next 48h |
| Deliveries needing action | Scheduled / in-transit / delayed deliveries due within the next 48h |

**Manager & Administrator only** (in addition to the four above):

| Group | Rule |
|---|---|
| Pending review | Customer inquiries flagged for staffing review |
| Pending approval | Sent quotations still waiting for manager sign-off |
| Missing staff / equipment | Confirmed / in-progress bookings with zero staff *or* equipment assignments |
| Completed — balance due | Completed bookings whose payments don't cover the total |
| Overdue bills | Sent bills past their due date (same rule as the Billing module's display) |
| Payments awaiting verification | Customer proof-of-payment uploads that need admin verification (`verified=False`, `proof_url` set) |
| Requirements overdue/due | Pre-event checklist tasks past their due date or due within 7 days, across all bookings |

**Viewer** sees the shared groups but **read-only**: the backend marks every group
`actionable=false` and the frontend hides the View/Open action buttons.

Clicking an item navigates to the right place: **Open** → booking detail, **View** → inquiry /
quotation / delivery / bill as appropriate. A group with no items is hidden; when nothing at all
needs attention the section shows an "All clear" message.

### Notification bar

The Dashboard shows a **notification bar** above the KPI cards when either:
- Payment verifications are pending, or
- Booking requirements are overdue/due

Format: `<b>5</b> payments awaiting verification | <b>2</b> requirements overdue/due`

Clicking the payment count jumps to the Payments page; clicking the requirements count jumps
to the Requirements page. The Dashboard nav badge also shows the combined count.

> **Note (workaround):** bill "overdue" is not persisted anywhere (see SUBMISSION.md, known
> limitation #4). The dashboard therefore recomputes it the same way Billing does — a `sent` bill
> whose `due_date` has passed is reported as overdue.

---

## 12. Pre-event checklist (Booking Requirements)

When a quotation is accepted and a booking is created, the system auto-generates a **pre-event
task checklist** (stored in `booking_requirements`). These are the things staff must arrange
before the event day.

### Auto-generated requirements

| Category | Trigger | Example | Due date |
|---|---|---|---|
| Venue | Inquiry has `venue_name` or `selected_venue_id` | "Confirm venue reservation: Garden Function Hall" | Event date − 14 days |
| Equipment | Customer equipment add-on picks | "Reserve 2× Buffet Table" | Event date − 7 days |
| Equipment | Package derived ratios (chafing dishes, tables, place settings) | "Prepare 3× chafing dishes" | Event date − 7 days |
| Other | Manual additions | "Book sound system" | User-defined |

Due dates are clamped to today if the computed date would be in the past.

### Booking detail — Checklist tab

The admin sees a checklist grouped by category (Venue / Equipment / Other) with:
- **Progress bar**: "3/7 tasks completed"
- **Editable due date** per row (change saves immediately)
- **"Mark done" button** per row (sets `completed_by` + `completed_at`)
- **Add form**: description + category select + due date → manual requirement
- **Status badges**: Pending (amber), Overdue (rose), Done (green)

### Requirements page (admin nav)

A cross-booking view of all requirements across every booking, filterable by:
- Overdue (past due date)
- Due this week (within 7 days)
- All pending
- Done
- All

Sorted by due date (soonest/most-overdue first). Click any row to jump to the booking.

### Overdue flip

On every dashboard load and requirements page load, the system automatically flips any
`pending` requirement whose `due_date` has passed to `overdue`. This is a cheap UPDATE, not
a background job.

---

## 13. Payment verification workflow

When a customer uploads a proof of payment through the portal:
1. The payment record is created with `proof_url` set and `verification_status='pending'`.
2. The **Dashboard notification bar** shows the count: "N payments awaiting verification".
3. The **Payments awaiting verification** attention group lists each payment with amount
   and upload timestamp.
4. An admin/manager reviews the proof directly on the **Payments** page:

### Payments page UI (admin)
- **Proof column**: thumbnail of uploaded proof (click to open full-size in new tab).
- **Status column**: badge — Pending (amber), Approved (green), Rejected (rose).
- **Verify button**: appears on pending payments only (requires `payment:update` permission).

### Verify modal
When the manager clicks **Verify** on a pending payment:
1. Modal shows the proof image (or "No proof uploaded").
2. **Editable fields**: Amount (₱), Method, Reference number, Notes.
3. **Rejection reason** field (optional, only used when rejecting).
4. **Approve** button → saves edits + sets `verification_status='approved'`.
5. **Reject** button → sets `verification_status='rejected'`, records rejection reason.

### Proof upload
- Customer uploads via billing portal (multipart form, JPG/PNG/PDF, 5MB max).
- Files saved to `uploads/payment_proofs/{payment_id}.ext`.
- `/uploads` mounted as StaticFiles — proof URLs resolve correctly.

### Payment status flow
`pending` → `approved` (manager approves) or `rejected` (manager rejects).
Only `pending` payments show the Verify button.

---

## 14. Complete admin flow — day by day

### Day 0: Customer submits inquiry

1. Customer opens `/customer`, picks Basic/Standard/Premium, fills details, submits.
2. **Dashboard** shows: "Needs a quotation" group gains 1 item (the new inquiry).
3. **Notification bar** appears if payments or requirements also need attention.

### Day 1: Staff triages

1. Staff logs in → **Inquiries** page → sees inquiry with status **New**.
2. Opens inquiry, reads details, checks for flag notes (unavailable items, staffing shortfall).
3. Edits if needed (wrong date, missing address, etc.).

### Day 2: Staff drafts + sends quotation

1. **Quotations** → New quotation (prefilled from inquiry).
2. Sets price, validity, saves → status **Draft**. Inquiry flips to **Quoted**.
3. Reviews, then clicks **Send** → status **Sent**. Customer receives email with Accept/Decline link.

### Day 2–5: Customer decides

- **Accepts** → Booking created (**Pending**, payment_status **Unpaid**). Quotation **Accepted**. Inquiry **Converted**. Booking requirements auto-generated. Equipment picks auto-copied. Dashboard updates.
- **Declines** → Quotation **Rejected**. If no other open quotation, inquiry **Closed**.

### Day 5: Manager confirms booking

1. **Bookings** → sees booking **Pending**.
2. Clicks **Confirm** → system checks: at least one payment exists? If not, blocks: "At least one payment is required before confirmation."
3. Payment recorded → Confirm succeeds → status **Confirmed**. Confirmation email sent.

### Day 5–10: Pre-event preparation

1. **Checklist tab** on booking: auto-generated requirements appear. Manager completes items:
   - Marks "Confirm venue" done.
   - Marks "Reserve chafing dishes" done.
   - Adds manual requirement "Book sound system".
2. **Staff & Assignments** → assigns server, chef, supervisor (supervisor auto-sets coordinator).
3. **Equipment** → assigns specific equipment to booking.
4. **Deliveries** → creates delivery, sets time/address.
5. Dashboard notification bar: requirements count decreases as items are completed.

### Day 10: Event day

1. **Advance** booking: Confirmed → **In Progress**.
2. Delivery: **Advance** → **In Transit** → **Delivered** (or **Delay** → `delayed` → retry/cancel).
3. Staff records any on-site adjustments.

### Day 11: Event complete

1. **Advance** booking: In Progress → **Completed**.
2. **Billing** → creates bill with line items (Draft).
3. Manager **Sends** bill → **Sent**. Customer receives email.

### Day 12–15: Payment collection

1. Customer pays (cash/GCash/bank transfer). Staff **Records payment**.
2. Customer uploads proof of payment → payment status **pending**, notification bar updates.
3. Manager clicks **Verify** on the Payments page → reviews proof + edits details if needed → Approves.
4. Manager **Marks bill paid** → **Paid**. Payment status recomputed to **Paid**.
5. Dashboard: all groups clear. "All clear — nothing needs your attention."

### Delivery edge case: delay

1. Delivery is `in_transit` but the driver hits traffic / vehicle issue.
2. Staff clicks **Delay** → status changes to `delayed`.
3. Later, if the issue resolves: **Advance** → `delayed → in_transit` (retry the trip).
4. If the delivery cannot proceed at all: **Cancel** → `delayed → cancelled` (cancel is allowed from `delayed`).
5. Alternatively, staff can **Cancel** directly from `in_transit` without going through `delayed`,
   then create a new delivery for the rescheduled time.

