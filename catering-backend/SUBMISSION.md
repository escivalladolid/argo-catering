# Catering Module — Submission Packet

## Known Limitations

Honest list of what is incomplete, stubbed, or not yet persisted.

1. **No ARGO single sign-on.** The module runs its own `POST /auth/login` and issues its
   own JWTs. A token handed off from the parent ARGO platform is anticipated by the code
   comments but no SSO/token-exchange endpoint exists yet. The module will not open "with
   no second login" from ARGO today.
2. **Not deployed.** The server binds `127.0.0.1` only; CORS is restricted to
   `127.0.0.1:8001` / `localhost:8001`. It is not reachable from another device and there
   is no production URL. No GitLab repository has been created, so there is no remote.
3. **Two-browser-tab consistency is not handled.** The frontend reloads data only on login
   and page navigation. If the same booking is open in two tabs, one tab does not
   auto-refresh when the other tab changes data. There is no polling, WebSocket, or
   `storage`-event listener. Backend-side, only quotation acceptance takes a row lock
   (`SELECT … FOR UPDATE`); other writes are last-write-wins with no optimistic-locking /
   conflict detection.
4. **Overdue bill status is display-only.** When listing bills, overdue flags are computed
   in memory for the response but are **not persisted**; the stored status stays `sent`
   until someone acts on it.
5. **Billing and payments are not linked.** Marking a bill `paid` does not update the
   booking's `payment_status`, and recording a payment does not update any bill. They are
   two independent workflows that both exist in the database.
6. **User management is a lightweight local module.** The **Users & Roles** page
   (administrator-only) can create, edit, deactivate, reactivate, and reset passwords for
   users within the module's own `users` table, and login enforces an `is_active` gate.
   It does not federate with the parent ARGO identity platform: roles still come from the
   JWT claim issued by `POST /auth/login`, so a role change only takes effect on the
   user's next login. There is no "change your own password" screen yet (admin resets
   generate a temporary password instead).
7. **Frontend is a single-file mockup UI.** The module UI is a working, DB-backed UI, but
   it is not a compiled SPA (no build step, no automated UI test suite, no error-tracking).
   Responsiveness has been exercised at desktop/tablet/mobile widths with headless Chrome
   (no horizontal overflow, correct table↔card swap and drawer/menu behaviour), but it has
   not been manually tested on physical phones. The customer portal (`/customer`) is a
   separate single-file page with no toggle and no login.
8. **No automated tests committed.** Verification so far was done with throwaway Node
   harnesses (API-level checks) that are not part of the repository. There is no CI.
9. **Seed data and secrets in plain view (demo only).** Demo passwords are hardcoded in
   `seed.py` and on the login screen. The JWT secret and DB password live in `.env`,
   which has no `.gitignore` protection (no git repository exists yet). Before pushing to
   GitLab: add `.env` to `.gitignore`, rotate the secret, and never commit real
   credentials.
10. **Menu / bill item edits use bulk replace in the UI, but item-level endpoints exist.**
    The mockup edit forms send all items on save (soft-delete + re-insert), so IDs change
    on every update. However, the backend also exposes item-level `PUT` and `DELETE`
    endpoints (`/menus/{menu_id}/items/{item_id}`, `/bills/{bill_id}/items/{item_id}`) that
    update or remove individual items without affecting siblings. These endpoints are not yet
    wired into the mockup's save flow.
11. **Payment/bill edge validations are basic.** Negative amounts and empty bill items are
    validated, but there is no partial-credit handling, no rounding policy for split
    payments, and duplicate bill numbers are only avoided by retry-random generation.

## Test steps

For a non-technical reviewer. You need a computer on the same network as the server
(local demo: same machine), the server running, and the database seeded.

1. **Access ARGO / open the module.** Open `http://127.0.0.1:8001/app` in Chrome. You
   should see the **Welcome back** sign-in screen with four demo buttons. Click
   **Manager** (or sign in with `manager@example.com` / `manager123`).
2. **Open the module/admin route.** After sign-in you land on the **Dashboard**. Use the
   left menu to open **Inquiries**. You should see any existing inquiries.
3. **Create a record (inquiry).** Click **New inquiry**, fill in Customer name, Contact
   (e.g. `0917 000 0001`), a future Event date, Guest count, and click **Save**. The new
   inquiry appears in the list with status **New**.
4. **Complete the related workflow.** From the inquiry, create a **Quotation** (set a
   price), click **Send** to mark it sent, then **Approve**. A **Booking** is created
   automatically with status **Pending**. Open the booking, then use **Advance** to move
   it to Confirmed / In progress / Completed, and optionally add a payment or bill in the
   booking's Payments / Billing tabs.
5. **Verify the record and status in the module portal.** Go back to **Inquiries** — the
   inquiry now shows **Converted**; **Quotations** shows the quotation as **Accepted**;
   **Bookings** shows the booking with its latest status and the recorded amount.
6. **Verify in the customer portal.** Open `http://127.0.0.1:8001/customer` in another
   tab — no login is required and the page loads immediately. Use **Check Status** with
   the `INQ-…` reference you copied when submitting the inquiry: the inquiry appears with
   its current status. Before the quotation is sent the customer sees no quotation; once
   the module sends it, the customer sees the quotation (amount, valid-until) and can
   **Accept** or **Decline** (a confirmation dialog asks first). Accepting creates the
   booking and the status screen then shows the `BK-…` booking reference with status
   **Pending** and payment **Unpaid**. The same change is immediately visible in the
   module portal at `/app`. A declined quotation closes the inquiry (status **Closed**);
   accepting an already-accepted quotation returns an error and never creates a second
   booking.
7. **Review the Activity Log.** Sign in as **Manager** (or Administrator) and open
   **Activity Log** in the left menu. Every create/update/delete, status change, payment,
   bill, delivery, and user-management action is listed newest-first with the actor, the
   affected entity, and a summary. Use the entity filter, the from/to date pickers, or
   the search box to narrow the list.
8. **Manage users (administrator only).** Sign out and sign in as
   `escivalladolid@gmail.com` / `admin123`. Open **Users & Roles** — the **Users** tab lists the
   seeded accounts. Click **New user**, enter an email, name, and role, and **Create
   user**: the generated temporary password is shown once (copy it, then sign out and
   sign in with that email + temporary password to confirm). Back as admin, use the row
   actions to **Edit** the role, **Reset password** (new temporary password shown once),
   and **Deactivate** — the deactivated account can no longer sign in (403) until you
   **Reactivate** it. The **Roles & permissions** tab shows the read-only permission
   matrix per role. Every one of these actions is recorded in the Activity Log under the
   `User` entity type.

## Mandatory submission block

- **PROJECT:** Capstone — Mobile Quiz System (Catering Management module of the ARGO platform) — *intern full name TBD*
- **INTERN:** *[Your full name / ID]*
- **MODULE:** Catering Management (Catering)
- **URLs:**
  - Module UI (admin): `http://127.0.0.1:8001/app`
  - Public / customer portal: `http://127.0.0.1:8001/customer`
  - API: `http://127.0.0.1:8001`
  - API docs: `http://127.0.0.1:8001/docs`
  - Public API (no auth): `POST /public/inquiries`, `GET /public/inquiries/{reference}`,
    `POST /public/inquiries/{reference}/quotations/{quotation_reference}/accept`,
    `POST /public/inquiries/{reference}/quotations/{quotation_reference}/reject`
  - Audit log (Bearer, `audit:view`): `GET /audit-log?entity_type=&from_date=&to_date=&search=`
  - Users (Bearer, administrator only): `GET /users`, `POST /users`,
    `PUT /users/{id}`, `POST /users/{id}/deactivate`, `POST /users/{id}/reactivate`,
    `POST /users/{id}/reset-password`
- **AUTHENTICATION:** Bearer JWT (HS256). Claims used: `sub` (user), `role`
  (viewer/staff/manager/administrator), `org` (organization). Issuer `catering-api`,
  audience `catering-app`, expiry 24 h. Tokens issued by `POST /auth/login`. The customer
  portal uses no authentication; the organization is resolved server-side
  (`PUBLIC_ORGANIZATION_ID` setting, falling back to the single seeded organization) and
  records are addressed by non-guessable `INQ-`/`QUO-`/`BK-` UUID references, so no
  internal route is ever exposed to anonymous callers. ARGO single-sign-on: *not
  implemented — see Known Limitations #1*.
- **GITLAB REPOSITORY:** *[repository URL — not created yet]*
- **DEPLOYED VERSION:** *[not deployed — runs locally on 127.0.0.1:8001]*
- **KNOWN LIMITATIONS:** see *Known Limitations* above (no ARGO SSO; no deployment; no
  two-tab sync; overdue status display-only; billing/payments not linked; user
  management is module-local and does not federate with ARGO (module ships its own
  Users & Roles page + an Activity Log); single-file mockup UI; no committed automated
  tests; demo credentials/secrets not yet gitignored; menu/bill UI saves via bulk-replace
  (item-level API endpoints exist but aren't wired into the UI); basic payment/bill
  validation).
- **TEST STEPS:** see *Test steps* above (access ARGO → open module/admin route → create
  a record → open public/customer route → complete the related workflow → verify the
  record and status appear correctly in both portals).
