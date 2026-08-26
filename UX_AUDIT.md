# UX Self-Audit — ARGO Catering UI

**Scope:** `catering-backend/catering-mockup.html` (admin console, 2,744 lines) and `catering-backend/customer-portal.html` (customer portal, 1,373 lines).

**Method:** Full source read of both files; every form, modal, status/action button, toast, and error path inspected. Findings are grouped by the 8 requested categories. Each item lists **file · function/element · issue · suggested fix**.

**Status:** Report only. Nothing has been changed.

---

## 1. Feedback after actions

- [ ] **Admin · `renderToasts()` (catering-mockup.html:852-854)** — Every toast renders a green `bi-check-circle` icon, including errors and validation failures (`showToast('Error loading data: …')`, `showToast(err.message)`, `showToast('Customer name is required')`). A failure looks like a success. Suggested fix: add an `isError` flag to `showToast`, render a red icon (e.g. `bi-x-circle`) and error styling for failures, mirroring the customer portal's toast (customer-portal.html:1348-1355).
- [ ] **Admin · `openBooking()` (catering-mockup.html:1184-1189)** — The `/bookings/{id}/detail` fetch swallows errors with `.catch(()=>{})`. If the detail call fails, the detail page silently renders stale/list-level data with no notice. Suggested fix: show an error toast or inline banner ("Could not load full booking details") and keep the page usable.
- [ ] **Admin · `ensureBookingPayments()` / `ensureBookingBills()` (catering-mockup.html:2678-2684, 2691-2697)** — On fetch failure the state is set to `[]` and the UI renders "No payments recorded for this booking yet." / "No bills for this booking yet." — a load failure is indistinguishable from a legitimately empty list. Suggested fix: track a per-booking error flag and render "Could not load payments — try again" instead of the empty message.
- [ ] **Admin · `sendQuo()` / `sendBill()` (catering-mockup.html:1005-1008, 2652-2653)** — Irreversible-ish "send to customer" actions fire with no confirmation and no button-level progress state; only a post-success toast. Suggested fix: add a confirm dialog for sends and/or disable the row while sending.
- [ ] **Admin · `runSave()` (catering-mockup.html:1450-1460)** — Save buttons are disabled while saving but the label never changes (no "Saving…"). The confirm dialog (`runConfirm`) shows "Working…", so save feels inconsistent with it. Suggested fix: add a spinner/`Saving…` label on the primary save button.
- [ ] **Admin · bookings "New" button (catering-mockup.html:1152, 1167)** — Clicking the disabled-looking primary "New" button fires a green-check toast "Bookings are created by approving a quotation". Informational text is dressed up as a success event. Suggested fix: use a plain info toast or an inline helper text near the header.
- [ ] **Customer · `copyReference()` (customer-portal.html:1020-1027)** — The clipboard `catch` also shows "Reference copied" even when the clipboard write failed. Suggested fix: show "Copy failed — select the text manually" on failure.
- [ ] **Customer · accept/decline (customer-portal.html:1286-1345)** — Good: spinner on button + progress toast + status refresh. Positive pattern to preserve.

## 2. Error message quality

- [ ] **Admin · `apiFetch()` 422 handling (catering-mockup.html:397-407)** — Validation errors surface raw backend field names (e.g. `shift_start: Input should be a valid datetime`, `guest_count: …`). Field names are snake_case and technical. Suggested fix: map error `loc` to the field's user-facing label (the `MODULES[key].fields[].label` is already available in save paths) and use friendly copy.
- [ ] **Admin · `apiFetch()` generic errors (catering-mockup.html:406)** — Non-422 failures throw `err.detail || 'Request failed'`. Browser-level network failures surface as raw "Failed to fetch". Suggested fix: translate network errors to "Unable to connect to the server. Please check your connection and try again.", like the customer portal's `friendlyError()` (customer-portal.html:519-545).
- [ ] **Admin · `fetchList()` (catering-mockup.html:741-743)** — On a load error, the toast appears but the list then renders the empty/zero state ("No inquiries match your search." / "No … yet"), which looks like a legitimate empty result, not a failure. Suggested fix: keep a per-list error state and render "Could not load — retry" instead of the empty message.
- [ ] **Admin · validation toasts (catering-mockup.html:2337-2340, 1477-1481, 1568-1570, 2516-2517, 2616-2620, 1831-1843)** — Required-field failures are shown only as a toast with no field highlighting or anchor scroll; on long modals (package builder, bill) the user must hunt for the offending field. Suggested fix: highlight the offending field and/or scroll it into view (the customer portal's `.invalid` class is the existing pattern to reuse).
- [ ] **Customer · `friendlyError()` (customer-portal.html:519-545)** — Good coverage of 404/409/400/422. Keep. Minor: 422 "Please check the highlighted fields." is a promise, but the portal only highlights fields on the inquiry form — on other flows no field is highlighted.
- [ ] **Customer · `loadPackages()` / `renderHomePackages()` (customer-portal.html:606-618, 634-642)** — Network failure silently yields an empty package list; the package section and picker just disappear or hide with no explanation. Suggested fix: show a muted "Packages could not be loaded" notice with a retry link.

## 3. Required vs. optional clarity

- [ ] **Admin · inquiry modal (catering-mockup.html:1355-1371)** — Name, Contact, Event date, Guests are required (enforced in `saveInquiry`, 1477-1481) but only "Event address" shows a red `*`. Inconsistent with the module engine, which marks every required field (moduleFieldHtml:2253). Suggested fix: mark all four required fields.
- [ ] **Admin · quotation modal (catering-mockup.html:1382-1390)** — No field shows a required mark though inquiry, guest count, and total price are required (`saveQuotation`, 1568-1570). Suggested fix: add `*` to the three required labels.
- [ ] **Admin · bill modal (catering-mockup.html:2552-2567)** — Booking and "at least one line item" are required but no field is marked. Suggested fix: mark Booking with `*` and note the line-item requirement inline.
- [ ] **Admin · menu modal (catering-mockup.html:2474-2483)** — "Menu name" is required (`saveMenu`, 2516) but unmarked. Suggested fix: add `*`.
- [ ] **Admin · package modal (catering-mockup.html:1657-1672)** — Name and Base price are required (`savePackage`, 1831-1832) but unmarked. Suggested fix: add `*`.
- [ ] **Admin · module engine (catering-mockup.html:2253)** — Good: red `*` on all `required:true` fields. Positive pattern to keep; apply it to the hand-built modals above.
- [ ] **Customer · inquiry form (customer-portal.html:324, 329-374)** — Good: required fields have `*` and the intro explains it; optional fields are labelled "(optional)". Positive pattern to keep.

## 4. Label clarity

- [ ] **Admin · module fields (catering-mockup.html:2074-2244)** — Labels are generally clear ("Scheduled at", "Delivery address", "Amount (₱)", "Quantity on hand"). Minor: optional `notes`/`shift_end`/`contact_name`/`contact_phone`/`reference` have no "(optional)" marker, so an admin cannot tell optional from required at a glance — acceptable given the `*` convention, but inconsistent with the customer portal's explicit "(optional)" hints. Suggested fix (optional): append "(optional)" to non-required fields in the module engine.
- [ ] **Customer · `buildAddressBlock()` (customer-portal.html:563-570)** — Address rendering is clear (address + venue/floor/room + "Near landmark" + instructions). Positive pattern to keep.
- [ ] **Customer · payment card (customer-portal.html:1187-1197)** — Shows Total / Amount paid / Remaining balance clearly. Positive pattern to keep.

## 5. Consistency

- [ ] **Admin · required-marker inconsistency** — Hand-built modals (inquiry, quotation, bill, menu, package) vs the module engine disagree on `*` usage (see section 3). Suggested fix: adopt the module engine convention everywhere.
- [ ] **Admin · validation UX inconsistency** — The module engine (`saveModule`) and hand-built forms all validate via toast only; the customer portal uses `.invalid` red borders (customer-portal.html:101, 599). Within the admin there is no field-level error indication anywhere. Suggested fix: unify on the `.invalid` pattern (or at least highlight the first offending field).
- [ ] **Admin · confirmation inconsistency** — Deletes, cancels, advances, approves, rejects, delivery/bill actions use `confirmDialog`, but `sendQuo`/`sendBill` do not. Suggested fix: decide one policy for "sends" and apply it consistently.
- [ ] **Admin · toast duration 2.6s (catering-mockup.html:850) vs customer 3.2s (customer-portal.html:1354)** — Minor timing mismatch. Suggested fix: pick one duration.
- [ ] **Admin · sortable columns** — In inquiries only name/guests are sortable; "Event date" is plain; bookings has similar mixed headers. Not a bug, but inconsistent affordance (sort icons on some headers, none on others). Suggested fix: either make all columns sortable or none.
- [ ] **Customer · status display for draft/in-review quotations (customer-portal.html:1124-1135)** — When a quotation exists in `draft`/`sent`, the timeline renders step "Quotation accepted" as `current` even when the customer has no accept/decline buttons yet (draft). "Quotation available" is also marked `done` for a draft. This reads as a status lie and is confusing. Suggested fix: only mark "Quotation available" done for `sent`; render a distinct "Quotation in preparation" current step for drafts.
- [ ] **Customer · timeline wording** — The "Booking confirmed / Awaiting quotation acceptance" step is shown even while the inquiry is still `new` (customer-portal.html:1136-1139). Suggested fix: gate that step on a quotation being sent or keep it muted.

## 6. Dead ends

- [ ] **Admin · mobile module cards are view-only (catering-mockup.html:2073, 2093, 2113, 2140, 2161, 2179, 2197, 2217, 2236)** — On mobile, guest counts, food requirements, deliveries, payments, billing, staff, staff-assignments, equipment, and equipment-assignments cards render only a View button; the view modal offers only Close. There is no path to Edit/Delete/Send/Advance/Mark-paid on mobile for these records. Suggested fix: add contextual action buttons to mobile cards (mirroring what desktop kebab menus offer), or add a trailing kebab on each card.
- [ ] **Admin · inquiries mobile card (catering-mockup.html:1095)** — Same issue: View only; Edit/Delete unreachable on mobile.
- [ ] **Admin · booking "History" tab (catering-mockup.html:1253)** — Exists in the tab bar but only ever says "Status history is not tracked in v1." Suggested fix: either implement a minimal history feed or remove the tab until then.
- [ ] **Admin · "Users & Roles" page/modal (catering-mockup.html:1309-1323, 1397-1398)** — Reachable in nav but is a static "out of scope" placeholder. At least it is transparent; flagging because it is a navigable dead end. Suggested fix: hide it from nav for non-config roles or keep it clearly labelled "coming soon".
- [ ] **Customer · quotation with no action available** — When a quotation exists but is not actionable (`draft`, or `accepted`/`rejected` with no booking), the card shows status text but no next step ("contact us" or an explanation). Suggested fix: add a muted "If you have questions, contact our team" line whenever no action button renders.
- [ ] **Customer · payment next-steps (customer-portal.html:1177-1201)** — A booking with a non-zero balance shows amounts but no "how to pay" guidance. Suggested fix: add a short "You'll be contacted regarding payment" note or a payment method list.
- [ ] **Customer · unknown reference (customer-portal.html:1056-1059)** — Error copy is good but offers no recovery path (e.g., re-submit or contact). Suggested fix: add a "Submit a new inquiry" link under the error.

## 7. Mobile / responsive issues

- [ ] **Admin · `.field-row` (catering-mockup.html:182)** — `display:flex` with no wrap and no mobile stacking. On narrow screens the inquiry modal's Date/Time/Guests and Venue/Floor/Room rows (1364-1368) and similar multi-field rows get cramped/overflow. Suggested fix: add `flex-wrap:wrap` and/or stack `.field-row` to one column under a mobile breakpoint (the customer portal already does this for `.form-grid` at ≤820px).
- [ ] **Admin · modal width/height on mobile (catering-mockup.html:174, 178)** — Modal is 90% wide with `max-height:52vh` body scroll; long builders (package/menu/bill) are usable but the header/footer pin while content scrolls, and there's no full-screen treatment on small screens. Suggested fix: make the modal full-height on mobile with a sticky footer so Save/Cancel are always visible.
- [ ] **Admin · staff/equipment pick lists (catering-mockup.html:184, 2054)** — Fixed `max-height:180px` with per-item quantity inputs on the right; on very narrow screens the qty input + name + "(×N on hand)" can overflow one line. Suggested fix: allow the quantity input to wrap below the label.
- [ ] **Admin · module pages on mobile** — Filter bar is rendered inline (pageModule:2411) but search input may shrink; acceptable, but verify the filter dropdown doesn't overflow on ~320px widths.
- [ ] **Customer · overall responsive behavior (customer-portal.html:226-237)** — Good: form-grid, pkg-pick, status-summary, detail-list collapse to one column at ≤820px; staff-grid goes 2-up at ≤560px; nav → hamburger. Positive pattern to keep.
- [ ] **Customer · `lookup-row` (customer-portal.html:163-164, 445-448)** — Input + button on one line; at very narrow widths the button may wrap awkwardly. Minor: add `flex-wrap:wrap`.

## 8. Loading / waiting states

- [ ] **Admin · initial `loadAllData()` (catering-mockup.html:643-701)** — No global loading indicator: after login, the canvas renders empty until the batch fetch resolves, and a slow/failing batch just shows a toast on a blank page. Suggested fix: show a full-canvas "Loading…" state on first load and a retry affordance on failure.
- [ ] **Admin · `openBooking()` detail fetch (catering-mockup.html:1184-1189)** — No "Refreshing…" indicator while `/bookings/{id}/detail` loads; the page silently upgrades. Suggested fix: a lightweight inline loading note on the detail sections.
- [ ] **Admin · `quotePrefill()` (catering-mockup.html:1521-1559)** — No loading state while inquiry details fetch; the info box pops in. Suggested fix: show "Loading inquiry details…" in `#quote-prefill-info`.
- [ ] **Admin · good loading states to keep** — `openInquiryView` (1404-1406), `openPackageModal` (1786-1788), `openBillModal` view (2542-2545), `billViewItems` (2630), `bookingPaymentsHtml`/`bookingBillsHtml` (2673, 2686), and the list "Loading…" row (`listLoadingRow`, 760) all provide feedback. Positive patterns.
- [ ] **Admin · login (catering-mockup.html:441-463)** — Good: button shows "Signing in…" spinner. Keep.
- [ ] **Customer · `checkStatus()` (customer-portal.html:1049-1077)** — Button disables but shows no progress state; a slow lookup looks frozen. Suggested fix: swap the label to a spinner while checking, matching `runAccept`.
- [ ] **Customer · good loading states to keep** — Submit button spinner (989), "Loading available packages…" (378), accept/decline spinners (1292-1293, 1323-1324).
- [ ] **Admin · confirm dialog (catering-mockup.html:946-953)** — Good: "Working…" on confirm. Keep.
- [ ] **Admin · save buttons (catering-mockup.html:1450-1460)** — Disabled but no label change (see also section 1). Suggested fix: spinner/"Saving…" on the primary button.

---

## Quick summary of the highest-impact items

1. **Error toasts look like successes** (green check on every admin toast).
2. **Mobile admin module pages are view-only** — Edit/Delete/Send/Advance unreachable on mobile.
3. **Required markers are missing** across the hand-built admin modals (inquiry, quotation, bill, menu, package).
4. **`.field-row` doesn't stack on mobile** — cramped multi-field rows in admin modals.
5. **Load failures masquerade as empty states** (`fetchList`, booking payments/bills, package loaders).
6. **Customer quotation timeline can mislabel draft/sent status** as "accepted/current".
7. **No initial-loading indicator** in the admin app; save buttons don't show progress.
8. **`openBooking()` swallows detail errors silently**.
