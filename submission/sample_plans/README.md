# FestOS Sample Plans & Verification Reports (`submission/sample_plans/`)

> **Festival:** Aarohan (EPINOIA 2026, IIM Indore)  
> **Deliverable:** Mandatory sample accommodation, scheduling, inventory plans, reconciliation, and data quality reports generated from the benchmark data pack.  
> **Generation Command:** `PYTHONPATH=backend python3 scripts/generate_sample_plans.py`  
> **Commit Hash:** `a10fb16fbca6f8ce887137107d6b7b301c9d626e`  
> **Generated Timestamp:** `2026-10-31T00:18:45+00:00`

---

## 1. Inventory of Generated Artifacts

| Artifact | File Name | Size | Scope & Operational Description |
|---|---|---:|---|
| **Accommodation Plan A** | [`accommodation_plan_A.csv`](accommodation_plan_A.csv) | ~360 KB | **Cohesion-First Plan:** Prioritizes university contingent unity by reserving contiguous hostel blocks; places overflow contingents together in external hotels (+₹42,500 cost). |
| **Accommodation Plan B** | [`accommodation_plan_B.csv`](accommodation_plan_B.csv) | ~356 KB | **Cost-First Plan:** Minimizes off-campus commercial lodging spend (+₹21,000) by packing all vacant on-campus beds first, accepting split contingents. |
| **Accommodation Plan C** | [`accommodation_plan_C.csv`](accommodation_plan_C.csv) | ~361 KB | **Balanced Plan:** Mathematical multi-objective compromise (50% cohesion, 30% cost, 20% shuttle proximity) balancing togetherness with budget. |
| **Provisional Schedule Plan** | [`schedule_plan.csv`](schedule_plan.csv) | ~19 KB | **Event Sessions Schedule:** Assigned venues, heats, volunteer needs, and equipment requisitions across all 31 festival events (marked `ASSUMED`). |
| **Logistics & Inventory Plan** | [`inventory_plan.csv`](inventory_plan.csv) | ~7 KB | **Equipment Allocation Ledger:** Stage-by-stage distribution of sound consoles, projectors, microphones, and safety equipment with condition tracking. |
| **Reconciliation Report** | [`reconciliation_report.csv`](reconciliation_report.csv) | ~1 KB | **Golden Headcount Waterfall:** Full variance reconciliation accounting for 2,836 raw roster records vs. 2,842 declared strength vs. 2,400 narrative prospectus. |
| **Data Quality Audit** | [`data_quality_report.csv`](data_quality_report.csv) | ~90 KB | **Data Hygiene & Unknowns Audit:** Itemized log of quarantined malformed records, missing dietary/gender fields, and field verification action items. |

---

## 2. Schema Dictionaries

### 2.1 Accommodation Plans (`accommodation_plan_A.csv`, `B.csv`, `C.csv`)
- `participant_id`: Canonical participant identifier (`P0001` - `P2836`).
- `name`: Participant full name.
- `contingent_id`: University/College contingent code (`C01` - `C38`).
- `college`: Full institution name.
- `gender`: Recorded or verified gender (`Male`, `Female`, `Non-binary`, `UNKNOWN`).
- `assigned_location`: Hostel block or external hotel name (e.g., `Hostel A`, `Campus Guest House`, `Lakeview Hotel`).
- `room_number`: Room identifier.
- `bed_number`: Assigned bed slot.
- `property_type`: `ON_CAMPUS` vs. `EXTERNAL_HOTEL`.
- `cost_per_night_inr`: Nightly room rate (₹0 for on-campus, ₹750–₹2,200 for external).
- `distance_km`: Distance to central fest venue.
- `accessibility_flag`: Wheelchair or ground-floor accommodation compliance.

### 2.2 Schedule Plan (`schedule_plan.csv`)
- `session_id`: Unique event session identifier.
- `event_id`: Event code (`E01` - `E31`).
- `event_name`: Full competition title.
- `round_number`: Competition round (`1` prelim, `2` semifinal, `3` final).
- `heat_number`: Heat or track sequence.
- `assigned_venue_id`: Allocated venue (`V01` - `V09`).
- `assigned_venue_name`: Name of stage or auditorium.
- `start_at`: Session start timestamp (UTC).
- `end_at`: Session end timestamp (UTC).
- `entrants_count`: Scheduled participants or teams.
- `volunteers_required`: Volunteer staff needed for room control and scoring.
- `equipment_required`: Equipment SKUs reserved for this stage.
- `status`: Lifecycle state (`PROVISIONAL`, `SCHEDULED`, `COMPLETED`, `CANCELLED`).

### 2.3 Inventory Plan (`inventory_plan.csv`)
- `item_id`: Unique equipment asset tag.
- `sku`: Inventory stock-keeping unit.
- `name`: Equipment asset title.
- `category`: Category (`AUDIO_VISUAL`, `LIGHTING`, `STAGE_RIGGING`, `MERCHANDISE`, `SAFETY`).
- `allocated_venue_id`: Venue where asset is currently deployed.
- `total_quantity`: Total owned/rented units.
- `available_quantity`: Idle units in Central Store.
- `issued_quantity`: Units actively deployed at venues.
- `maintenance_quantity`: Units under repair or inspection.
- `status`: Physical asset condition (`AVAILABLE`, `IN_USE`, `MAINTENANCE`, `DAMAGED`).

### 2.4 Reconciliation Report (`reconciliation_report.csv`)
- `metric`: Operational counter description.
- `count`: Numeric total.
- `category`: Classification (`Input`, `Target`, `Data Quality`, `Operations`, `Variance`).
- `explanation`: Audit rationale explaining variances honestly.
