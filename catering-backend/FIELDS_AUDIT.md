# Customer Portal Fields Audit

Audit of every customer-facing input in `customer-portal.html` against downstream
usage in the backend and admin mockup.

**Date:** 2026-08-16
**Scope:** Inquiry form fields, their storage, and where they surface to staff/manager/admin.

---

## Summary of Findings

### Most Actionable Findings

| Priority | Finding | Detail |
|----------|---------|--------|
| **HIGH** | `event_type` is missing from the customer form | Admin detail view shows it, admin edit form can set it, backend stores it — but the customer never gets to fill it in. Staff must call/message the customer or leave it blank. |
| **MEDIUM** | `guest_count` has no upper-bound validation | Customer can submit 99,999 guests and the backend accepts it. No `max` attribute on the HTML input, no backend cap beyond `ge=1`. Staff have to follow up to correct obvious typos. |
| **MEDIUM** | `customer_contact` has no format validation | Accepts any string ≥ 1 char. Customer could type "hello" and it passes. Backend has no regex check. |
| **LOW** | Location sub-fields could optionally consolidate | `floor`, `room_hall`, and `landmark` are rarely all used together. A single "Additional location details" textarea would reduce 3 fields to 1 without losing info (all concat into `event_location` on booking anyway). Current separate fields are defensible for large-venue use cases. |

### No Removals Needed

Every field in the form is used downstream. No field is pure friction with zero payoff.

---

## Full Field Table

| # | Form Field | DB Column | Used Downstream? | Required/Optional (Correct?) | Overlaps With | Recommendation |
|---|-----------|-----------|-------------------|------------------------------|---------------|----------------|
| 1 | **Full name** | `customer_name` | **Yes** — Admin inquiry list (name column), inquiry detail, quotation prefill, booking list, dashboard event labels, payments search, customer status view | Required — Correct. Staff need customer identity to communicate and build quotation. | None | **KEEP AS-IS** |
| 2 | **Contact number** | `customer_contact` | **Yes** — Admin inquiry detail ("Contact"), quotation prefill, staff use it to phone/message customer | Required — Correct. Essential for follow-up. | None | **KEEP AS-IS** (but add format hint or regex: `09XX XXX XXXX`) |
| 3 | **Event date** | `event_date` | **Yes** — Admin inquiry list/detail, quotation prefill, booking detail, staffing availability check, near-term review exemption, delivery scheduling, equipment scheduling | Required — Correct. Drives all scheduling. | None | **KEEP AS-IS** |
| 4 | **Estimated guests** | `guest_count` | **Yes** — Admin inquiry list ("Guests"), inquiry detail, quotation prefill, quotation pricing calculation, booking detail, package `suggested_price()` | Required — Correct. Core pricing input. | None | **KEEP AS-IS** (but add `max="5000"` and a hint "Maximum 5,000 guests") |
| 5 | **Event time** | `event_time` | **Yes** — Admin inquiry detail (appended to date), quotation prefill, booking detail, delivery `scheduled_at` prefill, equipment scheduling window | Optional — **Borderline.** Delivery and equipment scheduling use `bookingEventDatetime()` which falls back to event_date alone if time is null. But having it improves accuracy. | None | **KEEP AS-IS** (optional is fine; scheduling degrades gracefully without it) |
| 6 | **Event address** | `event_address` | **Yes** — Admin inquiry list (searchable), inquiry detail, quotation prefill, booking creation (becomes first line of `event_location`), dashboard event labels, bookings search, delivery address prefill | Required — Correct. Without it, no delivery or event location is possible. | Partial overlap with venue_name/floor/room/landmark/instructions (all location-related) but captures the street address specifically — distinct info. | **KEEP AS-IS** |
| 7 | **Venue name** | `venue_name` | **Yes** — Admin inquiry detail ("Venue"), quotation prefill, booking creation (`format_event_location` → "Venue: {name}"), customer status view address block | Optional — Correct. Many events use public spaces or homes with no named venue. | Overlaps location-wise with event_address (both identify where), but captures building/establishment name — distinct. | **KEEP AS-IS** |
| 8 | **Floor** | `location_floor` | **Yes** — Admin inquiry detail ("Floor"), quotation prefill, booking creation (`format_event_location` → "Floor: {floor}"), customer status view | Optional — Correct. Only relevant for multi-story venues. | Overlaps location-wise; part of the address block. | **KEEP AS-IS** |
| 9 | **Room / function hall** | `room_hall` | **Yes** — Admin inquiry detail ("Room / function hall"), quotation prefill, booking creation (`format_event_location` → "Room / function hall: {room}"), customer status view | Optional — Correct. Only relevant for venues with multiple bookable spaces. | Overlaps location-wise; part of the address block. | **KEEP AS-IS** |
| 10 | **Landmark** | `landmark` | **Yes** — Admin inquiry detail ("Landmark"), quotation prefill, booking creation (`format_event_location` → "Near: {landmark}"), customer status view | Optional — Correct. Helps drivers/delivery find the location. | Overlaps location-wise; part of the address block. | **KEEP AS-IS** |
| 11 | **Delivery / location instructions** | `delivery_instructions` | **Yes** — Admin inquiry detail (separate callout box), quotation prefill, booking creation (`format_event_location`), customer status view | Optional — Correct. Not every event needs special instructions. | Overlaps location-wise but captures procedural info (which entrance, setup area) — distinct from physical location. | **KEEP AS-IS** |
| 12 | **Additional details** | `notes` | **Yes** — Admin inquiry detail ("Notes"), quotation prefill, booking detail, customer status view, admin edit form | Optional — Correct. Catch-all for dietary themes, décor, schedule notes, etc. | None (intentionally catch-all) | **KEEP AS-IS** |
| 13 | **Choose a package** | `catering_package_id` | **Yes** — Admin inquiry detail, quotation prefill (package name, pricing method, base price, suggested total), quotation creation (pricing), booking detail, menu tab | Optional — Correct. "Custom quotation" is a valid path. | None | **KEEP AS-IS** |
| 14 | **Package mode** | `package_mode` | **Yes** — Admin inquiry detail ("Selection mode"), quotation prefill, booking detail menu tab | Optional — Only relevant when package selected. Auto-set to "default" if package picked without explicit choice. | None | **KEEP AS-IS** |
| 15 | **Package items** | `items` (inquiry_items) | **Yes** — Admin inquiry detail (dish table with name/group/kind/qty), quotation prefill, booking detail menu tab, customer status "Your selection" | Optional — Only relevant when package selected. | None | **KEEP AS-IS** |
| 16 | **Food requirements** | `food_requirements_json` | **Yes** — Admin inquiry detail (type/description/guests table), quotation prefill, booking detail, customer status "Your selection" | Optional — Correct. Not all events have dietary needs. Backend requires `description` ≥ 1 char when present (prevents empty rows). | None | **KEEP AS-IS** |
| 17 | **Staffing: Waiters** | `waiter_count` | **Yes** — Admin inquiry detail (chip), quotation prefill, booking detail (with availability), staffing availability check, review flow | Optional — Correct. Defaults to 0. | None (part of staffing group) | **KEEP AS-IS** |
| 18 | **Staffing: Bartenders** | `bartender_count` | **Yes** — Same as waiters | Optional — Correct. | None | **KEEP AS-IS** |
| 19 | **Staffing: Chefs** | `chef_count` | **Yes** — Same as waiters | Optional — Correct. | None | **KEEP AS-IS** |
| 20 | **Staffing: Kitchen staff** | `kitchen_staff_count` | **Yes** — Same as waiters | Optional — Correct. | None | **KEEP AS-IS** |
| 21 | **Staffing: Support crew** | `support_crew_count` | **Yes** — Same as waiters | Optional — Correct. | None | **KEEP AS-IS** |

---

## Analysis by Question

### Q1: Is it actually used downstream?

**All 21 fields are used downstream.** Every field stored by the customer form appears in at least one admin-side view:

- **Inquiry detail** (`openInquiryView`): Shows all fields — customer, contact, event date/time, event type, guests, event address, venue, floor, room/hall, landmark, status, delivery instructions, package, selection mode, flag note, dishes, food requirements, staffing, notes.
- **Quotation prefill** (`quotePrefill`): Shows customer name, contact, date/time, event type, address, venue, floor, room, landmark, delivery instructions, guests, package info, pricing, food requirements, items, staffing, notes.
- **Booking detail** (`pageBookingDetail`): Shows event location (concatenated from all address fields), event date/time, guests, package. Menu tab shows package_mode, items, food requirements, staffing.
- **Dashboard**: Uses `event_location` (concatenated) for event labels.
- **Deliveries**: Prefills delivery address from `event_location`.
- **Equipment scheduling**: Uses event date/time for availability windows.

**No field is stored and never surfaced.** Zero pure-friction fields.

### Q2: Is required/optional set correctly?

| Field | Current | Verdict | Reason |
|-------|---------|---------|--------|
| customer_name | Required | **Correct** | Staff need to know who the customer is |
| customer_contact | Required | **Correct** | Staff must be able to reach the customer |
| event_date | Required | **Correct** | Drives all scheduling and pricing |
| guest_count | Required | **Correct** | Core pricing input |
| event_address | Required | **Correct** | Without it, no delivery or location is possible |
| event_time | Optional | **Correct** | Scheduling works without it (degrades gracefully) |
| venue_name | Optional | **Correct** | Many events at homes/public spaces |
| location_floor | Optional | **Correct** | Only multi-story venues |
| room_hall | Optional | **Correct** | Only multi-space venues |
| landmark | Optional | **Correct** | Nice-to-have for navigation |
| delivery_instructions | Optional | **Correct** | Not every event needs special access |
| notes | Optional | **Correct** | Catch-all |
| Package/mode/items | Optional | **Correct** | Custom quotation without package is valid |
| Food requirements | Optional | **Correct** | Not all events have dietary needs |
| Staffing (all 5) | Optional | **Correct** | Defaults to 0; staff can recommend later |

**No required/optional mismatches found.** All required fields have concrete downstream reasons. All optional fields would not cause staff problems if left blank.

### Q3: Does it overlap with another field?

The six address-related fields (`event_address`, `venue_name`, `location_floor`, `room_hall`, `landmark`, `delivery_instructions`) all answer "where is the event?" and are concatenated into a single `event_location` string on booking creation via `format_event_location()` in `app/flow.py:56`.

**However, they are NOT redundant:**

1. **Admin inquiry detail shows them separately** (lines 2078-2082 of mockup), and staff edit them individually.
2. **Each captures genuinely distinct information:**
   - `event_address` = street address (where on the map)
   - `venue_name` = building/establishment name
   - `location_floor` = which floor
   - `room_hall` = which room/function hall
   - `landmark` = nearby reference point for navigation
   - `delivery_instructions` = procedural access info (which entrance, setup area)
3. **Delivery address prefill** uses the concatenated `event_location` — separate fields give delivery staff more detail than a single blob.
4. **The concatenation is lossless** — each field maps to a labeled line ("Venue:", "Floor:", "Near:", etc.).

**Verdict: No consolidation needed.** The 6 fields are location-related but each captures a distinct, non-redundant piece of information. Merging them into a single "Additional location details" textarea would lose the labeled structure that makes the concatenated `event_location` useful for delivery staff.

### Q4: Is anything genuinely missing?

**Yes — one clear gap:**

| Missing Field | Evidence |
|---------------|----------|
| **`event_type`** | The `CateringInquiry` model has `event_type: String(50)`. The `CateringInquiryUpdate` schema supports it. The admin inquiry detail shows it (line 2076: `['Event type',d.event_type?titleCase(d.event_type):'—']`). The admin edit form does NOT include it for the customer to fill, but staff can set it via the inquiry update API. The customer form never asks for it. **Staff must call/message the customer or leave it blank.** This is the clearest signal of a missing field. |

**`flag_note` is NOT missing** — it's set automatically by the backend based on staffing shortfall warnings and selection validation (line 483 of `public_portal.py`). It's not something the customer should fill in; it's a system-generated internal flag.

### Q5: Is the label/help text precise enough?

| Field | Label | Issue | Severity |
|-------|-------|-------|----------|
| `f-guests` | "Estimated guests" | No guidance on min/max. Backend rejects < 1 but accepts 99,999. Placeholder says "e.g. 80" but no hint about realistic range. | Medium |
| `f-contact` | "Contact number" | No format hint. Placeholder says "e.g. 0917 000 0001" which helps, but backend accepts any string ≥ 1 char (e.g. "abc" passes). | Medium |
| `f-address` | "Event address" | Good. Placeholder gives concrete example. Required badge is clear. | None |
| `f-venue` | "Venue name" | Good. Clear label and placeholder. | None |
| `f-floor` | "Floor" | Good. Clear and specific. | None |
| `f-room` | "Room / function hall" | Good. Clear label. | None |
| `f-landmark` | "Landmark" | Good. Placeholder "e.g. Near Ayala Triangle" is helpful. | None |
| `f-instructions` | "Delivery / location instructions" | Good. Placeholder gives concrete examples. | None |
| `f-notes` | "Additional details" | Slightly vague. Placeholder ("Dietary preferences, menu ideas, theme, or anything else...") helps but the label could be more specific. | Low |

---

## Q5+ Bonus: Admin-Side Edits of Fields the Customer Form Doesn't Ask For

**One field exists:**

| Admin Editable Field | Customer Form Asks? | Admin Detail Shows? | Admin Edit Form Includes? |
|----------------------|---------------------|---------------------|---------------------------|
| `event_type` | **No** | **Yes** (line 2076) | **Yes** (in `CateringInquiryUpdate` schema, line 665) |

This is the clearest signal of a missing customer-side field. The backend stores it, the admin displays and can edit it, but the customer form never asks for it.

**All other fields** the admin can edit are also asked for in the customer form — no other gaps found.

---

## Appendix: Field Trace Reference

| Field | Stored In | Admin List | Admin Detail | Quotation Prefill | Booking | Customer Status | Dashboard | Delivery Prefill |
|-------|-----------|------------|--------------|-------------------|---------|-----------------|-----------|------------------|
| customer_name | inquiry | name col | ✓ | ✓ | ✓ (via inquiry) | ✓ | event label | — |
| customer_contact | inquiry | source col | ✓ | ✓ | — | — | — | — |
| event_date | inquiry | ✓ | ✓ | ✓ | ✓ | ✓ | event label | — |
| event_time | inquiry | — | ✓ (with date) | ✓ (with date) | ✓ (with date) | ✓ (with date) | — | ✓ (fallback) |
| event_type | inquiry | event col | ✓ | ✓ | ✓ | — | — | — |
| event_address | inquiry | — | ✓ | ✓ | → event_location | ✓ (address block) | event label | ✓ (prefill) |
| venue_name | inquiry | — | ✓ | ✓ | → event_location | ✓ (address block) | — | → event_location |
| location_floor | inquiry | — | ✓ | ✓ | → event_location | ✓ (address block) | — | → event_location |
| room_hall | inquiry | — | ✓ | ✓ | → event_location | ✓ (address block) | — | → event_location |
| landmark | inquiry | — | ✓ | ✓ | → event_location | ✓ (address block) | — | → event_location |
| delivery_instructions | inquiry | — | ✓ (callout) | ✓ | → event_location | ✓ (address block) | — | → event_location |
| guest_count | inquiry | guests col | ✓ | ✓ | ✓ | ✓ | — | — |
| catering_package_id | inquiry | — | ✓ | ✓ | ✓ (via quotation) | ✓ (package name) | — | — |
| package_mode | inquiry | — | ✓ | ✓ | ✓ (menu tab) | ✓ | — | — |
| items | inquiry_items | — | ✓ (dish table) | ✓ | ✓ (menu tab) | ✓ (selection) | — | — |
| food_requirements | inquiry (JSON) | — | ✓ (req table) | ✓ | ✓ (menu tab) | ✓ (selection) | — | — |
| waiter_count | inquiry | — | ✓ (chip) | ✓ | ✓ (with avail) | ✓ (selection) | — | — |
| bartender_count | inquiry | — | ✓ (chip) | ✓ | ✓ (with avail) | ✓ (selection) | — | — |
| chef_count | inquiry | — | ✓ (chip) | ✓ | ✓ (with avail) | ✓ (selection) | — | — |
| kitchen_staff_count | inquiry | — | ✓ (chip) | ✓ | ✓ (with avail) | ✓ (selection) | — | — |
| support_crew_count | inquiry | — | ✓ (chip) | ✓ | ✓ (with avail) | ✓ (selection) | — | — |
| notes | inquiry | — | ✓ | ✓ | ✓ (menu tab) | ✓ | — | — |
| flag_note | inquiry (auto) | — | ✓ (callout) | — | — | — | — | — |
