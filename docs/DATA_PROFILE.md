# FestOS Data Pack Profile (`docs/DATA_PROFILE.md`)

This document is the comprehensive data profile of all raw files in `data/raw/` for the FestOS system (EPINOIA 2026, IIM Indore). It provides derived headers, inferred data types, null counts, label variants, date/time formats, anomalies, and cross-file key relationships.

---

## 1. File Inventory and Summary

| File | Rows | Columns | Description |
|---|---:|---:|---|
| `participants.csv` | 2,836 | 13 | Core participant roster including contact, diet, gender, and travel timing |
| `registrations.csv` | 5,580 | 3 | Participant-to-event mappings with team assignments |
| `contingents.csv` | 38 | 6 | College contingents with declared strength, leader, and escort |
| `events.csv` | 31 | 8 | Event definitions, rounds, duration, requirements, volunteer needs |
| `venues.csv` | 9 | 5 | Campus venues, capacity, operating availability windows, indoor/outdoor |
| `core_team.csv` | 48 | 5 | Staff roster, roles, assigned shift times, contact phone |
| `hostels.csv` | 200 | 7 | On-campus hostel rooms, floor, gender allocation, bed capacity, accessibility |
| `external_stays.csv` | 6 | 6 | External accommodations, bed capacity, cost per night, distance, transport |
| `inventory_logistics.csv` | 72 | 5 | Event equipment inventory, quantities, current location, condition |
| `inventory_merch.csv` | 10 | 4 | Merchandise items (T-shirts, medals, lanyards, totes) with reserved quantities |
| `vendors.csv` | 14 | 8 | Food vendors, menus, declared dietary options, hygiene cert expiry, capacity |
| `README.txt` | - | - | Metadata on synthetic imperfections, dates, and handling rules |

---

## 2. Per-File Column Profiles

### 2.1 `participants.csv`
- **Total Rows:** 2,836
- **Derived Headers:** `participant_id`, `name`, `college`, `contingent_id`, `gender_as_given`, `age`, `contact`, `accessibility_needs`, `dietary_needs`, `arrival_datetime`, `departure_datetime`, `accommodation_requested`, `tshirt_size`

| Column | Inferred Type | Null Count | Null % | Top Variants / Samples |
|---|---|---:|---:|---|
| `participant_id` | String (`P\d{4}`) | 0 | 0.0% | `P0001` - `P2836` |
| `name` | String | 0 | 0.0% | Repeated across pool (e.g. Ishaan Nair, Nidhi Bose) |
| `college` | String | 0 | 0.0% | 38 distinct IIMs/Colleges (e.g., IIM Indore, IIM Ranchi) |
| `contingent_id` | String (`C\d{2}`) | 0 | 0.0% | `C01` - `C38` |
| `gender_as_given` | Categorical String | 417 | 14.7% | Female (831), Male (743), Prefer not to say (430), Non-binary (415), Blank (417) |
| `age` | Integer | 0 | 0.0% | 17 to 24; exactly 279 records are age 17 (minors) |
| `contact` | String | 0 | 0.0% | E.164 formatted (`+91-8480737211`); all 2,836 unique |
| `accessibility_needs` | Categorical String | 2,321 | 81.8% | Ground floor / no stairs (135), Near washroom (128), Visual assistance (128), Wheelchair access (124), Blank (2,321) |
| `dietary_needs` | Categorical String | 394 | 13.9% | Vegetarian (439), Non-vegetarian (414), Halal (411), Nut allergy (411), Gluten-free (387), Jain (380), Blank (394) |
| `arrival_datetime` | Datetime (`YYYY-MM-DD HH:MM`) | 0 | 0.0% | Discrete waves: 2026-10-29 08:00 to 2026-11-02 02:00 |
| `departure_datetime` | Datetime (`YYYY-MM-DD HH:MM`) | 0 | 0.0% | Discrete waves: 2026-10-31 06:00 to 2026-11-03 07:00 |
| `accommodation_requested` | Boolean String (`yes`/`no`) | 0 | 0.0% | `yes`: 2,144 (75.6%), `no`: 692 (24.4%) |
| `tshirt_size` | Categorical String | 0 | 0.0% | L (596), M (572), XL (569), S (563), XXL (536) |

**Anomalies:**
1. **Invalid Intervals:** Exactly 3 rows have arrival datetime occurring after departure datetime:
   - `P0037` (Meera Bose): Arrival `2026-11-02 02:00` > Departure `2026-10-31 20:00`
   - `P1189` (Ishaan Bose): Arrival `2026-11-02 02:00` > Departure `2026-11-01 18:00`
   - `P2034` (Tanvi Gupta): Arrival `2026-11-02 02:00` > Departure `2026-11-01 06:00`
2. **Minors (Safety Critical):** 279 participants are age 17; 220 of them have requested accommodation.
3. **Gender/Bed Mismatch:** 1,262 participants have non-binary, prefer not to say, or missing gender, yet campus hostels offer 0 gender-neutral rooms.
4. **Unmappable Accessibility Needs:** 256 participants request visual assistance (128) or proximity to washrooms (128), attributes not captured in `hostels.csv`.

---

### 2.2 `registrations.csv`
- **Total Rows:** 5,580
- **Derived Headers:** `participant_id`, `event_id`, `team_id`

| Column | Inferred Type | Null Count | Null % | Notes |
|---|---|---:|---:|---|
| `participant_id` | String (`P\d{4}`) | 0 | 0.0% | Foreign Key -> `participants.participant_id` |
| `event_id` | String (`E\d{2}`) | 0 | 0.0% | Foreign Key -> `events.event_id` |
| `team_id` | String | 3,613 | 64.7% | Team grouping identifier (e.g., `T22-C02-0`) |

**Anomalies:**
1. **Team Event Missing Team IDs:** Exactly 1,810 registrations belong to the 10 team events (`solo_team == 'team'`), and **100% of these 1,810 registrations have a completely blank `team_id`**.
2. **Solo Registrations with Team IDs:** 1,967 registrations for solo events have a populated `team_id` string.
3. **Referential Integrity:** 100% valid referential integrity; 0 unknown participants, 0 unknown events.

---

### 2.3 `contingents.csv`
- **Total Rows:** 38
- **Derived Headers:** `college`, `contingent_id`, `leader`, `escort`, `strength_declared`, `preferences`

| Column | Inferred Type | Null Count | Null % | Notes |
|---|---|---:|---:|---|
| `college` | String | 0 | 0.0% | Unique college names |
| `contingent_id` | String (`C\d{2}`) | 0 | 0.0% | `C01` - `C38` |
| `leader` | String | 0 | 0.0% | Contingent leader full name |
| `escort` | String | 0 | 0.0% | Contingent escort full name |
| `strength_declared` | Integer | 0 | 0.0% | Total declared: 2,842 (range 6 to 120) |
| `preferences` | String | 0 | 0.0% | e.g. "no preference", "female rooms close to exit" |

**Anomalies:**
1. **Declared vs Actual Headcount:** Declared strength is 2,842, while actual participant count is 2,836 (net -6 difference).
2. **7 Contingents with Discrepancies:**
   - `C05`: declared 107, actual 99 (difference: -8)
   - `C18`: declared 19, actual 14 (difference: -5)
   - `C32`: declared 43, actual 36 (difference: -7)
   - `C27`: declared 45, actual 52 (difference: +7)
   - `C09`: declared 79, actual 84 (difference: +5)
   - `C02`: declared 101, actual 102 (difference: +1)
   - `C03`: declared 116, actual 117 (difference: +1)
3. **Missing Leaders and Escorts:**
   - Only 3 of 38 leaders match names in their own contingent: C05 (Ishaan Nair), C12 (Saanvi Sharma), C22 (Ananya Iyer).
   - Only 3 of 38 escorts match names in their own contingent: C07 (Shreya Sharma), C24 (Riya Patel), C30 (Vansh Nair).
   - ~70 leaders/escorts are unrepresented in the participant file.

---

### 2.4 `events.csv`
- **Total Rows:** 31
- **Derived Headers:** `event_id`, `event_name`, `type`, `rounds`, `duration_minutes`, `venue_requirements`, `equipment_needs`, `volunteers_needed`

| Column | Inferred Type | Null Count | Null % | Notes |
|---|---|---:|---:|---|
| `event_id` | String (`E\d{2}`) | 0 | 0.0% | `E01` - `E31` |
| `event_name` | String | 0 | 0.0% | Unique event names |
| `type` | Categorical String | 0 | 0.0% | `solo` (21), `team` (10) |
| `rounds` | String Pipeline | 0 | 0.0% | `prelims\|semis\|finals` (16), `prelims\|finals` (11), `single` (4) |
| `duration_minutes` | Integer | 0 | 0.0% | Range 45 to 120 minutes |
| `venue_requirements` | Semicolon List | 0 | 0.0% | audio; seating (9), open ground (6), power; tables (5), etc. |
| `equipment_needs` | Semicolon List | 0 | 0.0% | barricades; tables (11), no special equipment (9), etc. |
| `volunteers_needed` | Integer | 0 | 0.0% | Range 2 to 12 volunteers |

**Anomalies:**
1. **No Scheduling Timestamps:** Source events lack start and end times. Schedules must be generated and labelled `ASSUMED`.
2. **No Venue Assignments:** Source events do not map to venues.
3. **No Judges:** No judge profiles or numbers are provided in raw data.

---

### 2.5 `venues.csv`
- **Total Rows:** 9
- **Derived Headers:** `venue_id`, `venue_name`, `capacity`, `availability_windows`, `indoor_outdoor`

| Column | Inferred Type | Null Count | Null % | Notes |
|---|---|---:|---:|---|
| `venue_id` | String (`V\d{2}`) | 0 | 0.0% | `V01` - `V09` |
| `venue_name` | String | 0 | 0.0% | Main Stage, LT-1, LT-2, Audi-1, Sports Complex, etc. |
| `capacity` | Integer | 0 | 0.0% | 60 to 250 |
| `availability_windows` | Semicolon Time Ranges | 0 | 0.0% | `2026-10-30 08:00-22:00;2026-10-31 08:00-22:00;2026-11-01 08:00-20:00` |
| `indoor_outdoor` | Categorical String | 0 | 0.0% | `indoor` (7), `outdoor` (2) |

---

### 2.6 `core_team.csv`
- **Total Rows:** 48
- **Derived Headers:** `member_id`, `name`, `role`, `shift`, `phone`

| Column | Inferred Type | Null Count | Null % | Notes |
|---|---|---:|---:|---|
| `member_id` | String (`ST\d{2}`) | 0 | 0.0% | `ST01` - `ST48` |
| `name` | String | 0 | 0.0% | Staff member name |
| `role` | String | 0 | 0.0% | Logistics, Registration Desk, Stage Management, etc. |
| `shift` | Time Range (`HH:MM-HH:MM`) | 0 | 0.0% | `22:00-06:00` (16), `06:00-14:00` (16), `14:00-22:00` (16) |
| `phone` | String | 0 | 0.0% | E.164 phone numbers; all 48 unique |

**Anomalies:**
- 469 participant rows share a name with core team members due to the synthetic small name pool; phone numbers confirm distinct individuals.

---

### 2.7 `hostels.csv`
- **Total Rows:** 200
- **Derived Headers:** `room_id`, `block`, `floor`, `gender`, `capacity`, `accessibility`, `status`

| Column | Inferred Type | Null Count | Null % | Notes |
|---|---|---:|---:|---|
| `room_id` | String | 0 | 0.0% | `B1-0-01` to `G2-3-10` |
| `block` | String | 0 | 0.0% | B1, B2, B3 (boys), G1, G2 (girls) — 40 rooms each |
| `floor` | Integer | 0 | 0.0% | 0 (Ground), 1, 2, 3 — 50 rooms each |
| `gender` | Categorical String | 0 | 0.0% | `boys`: 120 rooms (426 beds), `girls`: 80 rooms (284 beds) |
| `capacity` | Integer | 0 | 0.0% | 2 (4 rooms), 3 (82 rooms), 4 (114 rooms); Total beds = 710 |
| `accessibility` | Categorical String | 0 | 0.0% | `yes`: 10 rooms (26 beds, all on floor 0), `no`: 190 rooms |
| `status` | String | 0 | 0.0% | All 200 rooms `available` |

---

### 2.8 `external_stays.csv`
- **Total Rows:** 6
- **Derived Headers:** `property_id`, `property_name`, `beds`, `cost_per_bed_per_night`, `distance_km`, `transport_availability`

| Column | Inferred Type | Null Count | Null % | Notes |
|---|---|---:|---:|---|
| `property_id` | String (`EXT\d{2}`) | 0 | 0.0% | `EXT01` - `EXT06` |
| `property_name` | String | 0 | 0.0% | Campus Guest House, Shakti Lodge, Lakeview Hotel, etc. |
| `beds` | Integer | 0 | 0.0% | 80 to 180; Total beds = 740 |
| `cost_per_bed_per_night` | Float / Int | 0 | 0.0% | ₹750 to ₹2,200 |
| `distance_km` | Float / Int | 0 | 0.0% | 1 to 9 km |
| `transport_availability` | Categorical String | 0 | 0.0% | `yes`: 5 properties (600 beds), `limited`: EXT03 (140 beds) |

**Anomalies:**
- EXT03 (Lakeview Hotel) has `limited` transport; policy prohibits assigning minors or late-night arrivals there.
- No accessibility or gender suitability information is provided.

---

### 2.9 `inventory_logistics.csv`
- **Total Rows:** 72
- **Derived Headers:** `item_id`, `item`, `quantity`, `location`, `condition`

| Column | Inferred Type | Null Count | Null % | Notes |
|---|---|---:|---:|---|
| `item_id` | String (`L\d{2}-\d`) | 0 | 0.0% | `L00-1` to `L17-4` |
| `item` | String | 0 | 0.0% | mic, speaker, mixer, extension cord, projector, etc. |
| `quantity` | Integer | 0 | 0.0% | 5 to 33 per line item |
| `location` | String | 0 | 0.0% | Main Stage (16), Sports Complex (17), Registration Desk (14), Van 1 (13), Store Room A (12) |
| `condition` | Categorical String | 0 | 0.0% | `good` (35), `under repair` (22), `needs check` (15) |

**Anomalies:**
- 37 items (51.4%) are in `under repair` or `needs check` condition and cannot be considered available for immediate deployment without inspection.

---

### 2.10 `inventory_merch.csv`
- **Total Rows:** 10
- **Derived Headers:** `item`, `size`, `quantity`, `reserved_quantity`

| Column | Inferred Type | Null Count | Null % | Notes |
|---|---|---:|---:|---|
| `item` | String | 0 | 0.0% | T-shirt (5 sizes), winner medal (2), lanyard (2), tote (1) |
| `size` | String / Null | 0 | 0.0% | S, M, L, XL, XXL for T-shirt; blank string for others |
| `quantity` | Integer | 0 | 0.0% | Total stock counts |
| `reserved_quantity` | Integer | 0 | 0.0% | Holds reserved for VIPs/winners |

---

### 2.11 `vendors.csv`
- **Total Rows:** 14
- **Derived Headers:** `vendor_id`, `vendor_name`, `menu`, `dietary_options`, `hygiene_certificate_expiry`, `hours`, `capacity`, `payment_terms`

| Column | Inferred Type | Null Count | Null % | Notes |
|---|---|---:|---:|---|
| `vendor_id` | String (`VND\d{2}`) | 0 | 0.0% | `VND01` - `VND14` |
| `vendor_name` | String | 0 | 0.0% | Vendor A through Vendor N |
| `menu` | String | 0 | 0.0% | North Indian, South Indian, Jain thali, Chaat, etc. |
| `dietary_options` | Semicolon List | 0 | 0.0% | e.g., `vegetarian;jain`, `non-vegetarian;halal` |
| `hygiene_certificate_expiry`| Date (`YYYY-MM-DD`) | 0 | 0.0% | 2026-09-29 (4), 2026-10-31 (4), 2026-11-10 (1), 2027-10-29 (5) |
| `hours` | Time Range (`HH:MM-HH:MM`) | 0 | 0.0% | `07:00-23:00` (11), `10:00-16:00` (3) |
| `capacity` | Integer | 0 | 0.0% | 180 to 450 meals per slot |
| `payment_terms` | String | 0 | 0.0% | 50% advance; balance actuals (7), minimum guarantee (4), per item sold (3) |

**Anomalies:**
1. **Hygiene Certificate Expiry:**
   - 4 vendors expired prior to fest (`2026-09-29`): VND05, VND08, VND11, VND13.
   - 4 vendors expire mid-fest (`2026-10-31`): VND01, VND02, VND04, VND07.
2. **Menu vs Dietary Tag Mismatch:**
   - VND09 (Vendor I): Menu is `Jain thali`, but `dietary_options` is only `vegetarian` (missing `jain`).
   - VND13 (Vendor M): Menu is `Sandwiches`, but `dietary_options` declared `vegetarian;jain`.

---

## 3. Cross-File Key Relationships & Entity Graph

```text
contingents.csv (contingent_id)
      ^
      | (1 : N)
participants.csv (participant_id) <-----+
      ^                                 | (1 : N)
      | (1 : N)                         |
registrations.csv (participant_id, event_id)
      |
      v (N : 1)
events.csv (event_id)
      |
      +----[Assumed / Generated Schedule]----> venues.csv (venue_id)

hostels.csv (room_id: B1-0-01, 710 beds) <---+
                                             +--- [StayAssignment Plan A/B/C]
external_stays.csv (property_id, 740 beds) <-+

inventory_logistics.csv (item_id: L00-1) ---> Inventory Location / Movements
inventory_merch.csv (item: T-shirt, medal) ---> MerchClaim Ledger
vendors.csv (vendor_id) ---> MealSlot / VendorAssignment
core_team.csv (member_id: ST01) ---> Staff / Shifts
```

---

## 4. Reconciliation Baseline & Spec Reference Numbers

| Spec Metric | Spec Reference | Actual Pack Value | Verified Status |
|---|---:|---:|---|
| Raw Participant Records | 2,836 | 2,836 | Exact match |
| Declared Contingent Strength | 2,842 | 2,842 | Exact match (-6 discrepancy) |
| Narrative Expected Count | 2,400 | 2,400 (assumption) | Explained via gap analysis (+436) |
| Invalid Arrival/Departure Intervals | 3 | 3 | Exact match (P0037, P1189, P2034) |
| Contingent Count | 38 | 38 | Exact match |
| Contingents with Discrepancies | 7 | 7 | Exact match (C02, C03, C05, C09, C18, C27, C32) |
| Leaders in Participant Roster | 3 of 38 | 3 of 38 | Exact match (C05, C12, C22) |
| Escorts in Participant Roster | 3 of 38 | 3 of 38 | Exact match (C07, C24, C30) |
| Total Registrations | 5,580 | 5,580 | Exact match |
| Team Regs Missing Team ID | 1,810 | 1,810 | Exact match (all 10 team events) |
| Total Events | 31 | 31 | Exact match |
| Total Venues | 9 | 9 | Exact match |
| Campus Hostel Beds | 710 | 710 | Exact match |
| External Stay Beds | 740 | 740 | Exact match |
| Total Accommodation Beds | 1,450 | 1,450 | Exact match |
| Participants Requesting Housing | 2,144 | 2,144 | Exact match |
| Minors (Age 17) | 279 | 279 | Exact match |
| Minors Requesting Housing | 220 | 220 | Exact match |
| Core Team Members | 48 | 48 | Exact match |
| Vendors | 14 | 14 | Exact match |
| Expired / Expiring Hygiene Certs | 8 | 8 | Exact match |
