# FestOS – Complete Consolidated Problem Analysis, Features, Requirements & Innovation Blueprint

**Event:** Aarohan – Inter-College Festival  
**Challenge:** EPINOIA 2026, IIM Indore  
**Project:** FestOS (Festival Operations System)  
**Context:** Consolidated from the official problem statement, Claude conversation, planning-engine script, findings report, summary JSON, and generated CSV outputs.

> **How to use this document:** Copy the entire Markdown content into another chat or project document. The headings, tables, numbered lists, code blocks, flowcharts, and diagrams are deliberately written in Markdown so their structure is preserved.

---

# 1. Project Overview and Core Objective

## 1.1 What is FestOS?

FestOS is an intelligent, unified Festival Operations Management and Decision-Support Platform designed to manage the complete operational ecosystem of a large inter-college festival.

The festival currently operates through disconnected spreadsheets, forms, phone calls, and messaging groups.

The primary problem is not simply a lack of information. The real problem is that information is fragmented across departments, and organizers cannot understand how one operational change affects other departments.

For example:

A delayed bus can affect participant check-in, accommodation readiness, food requirements, merchandise distribution, and event attendance.

Similarly, a hostel closure can affect room allocation, participant safety, transportation, contingent distribution, and the festival budget.

FestOS must bring all these operations into one connected system.

It should help organizers:

- Verify and reconcile operational information.
- Manage participants and contingents.
- Allocate accommodation under multiple constraints.
- Schedule events and resources.
- Track logistics and merchandise.
- Manage food vendors and dietary requirements.
- Manage staff and volunteers.
- Detect operational conflicts.
- Simulate disruptions.
- Recommend alternative solutions.
- Understand the downstream consequences of changes.
- Record why important decisions were made.

**Central design philosophy:**

> Every operational change must make its downstream consequences visible.

FestOS must be a decision-support and operational command centre, not merely a registration website or a CRUD-based management portal.

# 2. Festival Scale and Operational Context

The system must handle the following scale:

| Entity | Quantity |
|---|---:|
| Expected participants in original narrative | Approximately 2,400 |
| Raw participant records | 2,836 |
| Contingents / colleges | 38 |
| Events | 31 |
| Venues | 9 |
| Food vendors | 14 |
| Core team members | 48 |
| On-campus hostel rooms | 200 |
| On-campus beds | 710 |
| External properties | 6 |
| External beds | 740 |
| Total accommodation capacity | 1,450 |
| Event registrations | 5,580 |
| Contingent size range | 6–140 participants |

Additional operating conditions:

- Participants arrive across five days, although the festival itself is three days.
- Participants may register for multiple solo and team events.
- Contingents arrive at different times.
- Accommodation demand varies by arrival and departure dates.
- Staff and organizers work in different shifts.
- Rooms require cleaning before reuse.
- External properties have additional costs and transportation considerations.
- Inventory and equipment move between locations.
- Vendors have different operating hours, service capacities, and compliance conditions.

# 3. Complete List of Problems Identified

## 3.1 Fragmented operational information

Different festival departments maintain separate information.

There is no centralized source of truth connecting participants, accommodation, events, inventory, vendors, and staff.

**Problem:** One department changes information without knowing the consequences for another department.

**Required solution:** A unified operational database and connected modules.

## 3.2 Participant data inconsistencies

The participant dataset contains:

- Duplicate-looking records.
- Repeated names.
- Inconsistent labels.
- Missing gender information.
- Missing dietary information.
- Invalid arrival/departure intervals.
- Contingent strength mismatches.
- Missing leader and escort records.
- Uncertain participant status.

**Required solution:** Data validation, deduplication, reconciliation, verification, and an uncertainty-management system.

## 3.3 Accommodation shortages

There are 1,450 total beds, but peak simultaneous demand is 1,601.

The hostel capacity is not sufficient for everyone requesting accommodation during the peak period.

**Problem:** The system must allocate scarce resources while respecting accessibility, privacy, gender accommodation preferences, group cohesion, room capacity, cleaning, transportation, budget, and safety.

## 3.4 Gender and privacy accommodation challenges

On-campus accommodation consists of boys' and girls' blocks.

There are no gender-neutral rooms.

A substantial number of participants have non-binary, prefer-not-to-say, or blank gender values.

**Problem:** They cannot automatically be allocated to gendered housing.

The system needs explicit housing preferences and appropriate single-room or gender-neutral alternatives.

## 3.5 Accessibility accommodation shortages

There are only 10 accessible rooms containing 26 beds.

Peak demand includes:

- 72 wheelchair-accessibility requests.
- 80 ground-floor requirements.

External properties do not contain verified accessibility information.

**Problem:** Participants with hard accessibility needs cannot simply be moved into external accommodation without verifying suitability.

## 3.6 Contingent fragmentation

Contingents contain between 6 and 140 members.

Room availability may force one contingent to occupy multiple hostels, properties, floors, or buildings.

**Problem:** Unnecessary splitting makes group management difficult and affects coordination.

## 3.7 External accommodation cost

External accommodation increases expenditure.

The system needs to balance:

- Accommodation cost.
- Contingent cohesion.
- Travel time.
- Event schedules.
- Transport availability.
- Safety.
- Room availability.

There is no predefined external accommodation budget in the supplied dataset.

## 3.8 Event scheduling conflicts

Participants, teams, judges, volunteers, venues, and equipment may be required in multiple places simultaneously.

Events also need:

- Setup time.
- Teardown time.
- Travel time.
- Round dependencies.
- Result declaration buffers.
- Capacity validation.

## 3.9 Incomplete event information

The actual dataset does not provide event start times or venue assignments.

Venue feature tags are also missing.

Judge information is entirely absent.

**Problem:** A complete schedule cannot be derived directly from the imported data. Assumptions and generated schedules must be clearly identified.

## 3.10 Logistics and inventory uncertainty

Inventory quantities alone are insufficient.

Stock can be:

- Available.
- Reserved.
- In transit.
- Damaged.
- Under repair.
- Awaiting return.

The system must understand where an item is and when it will actually be available.

## 3.11 Merchandise shortages and duplicate claims

Several merchandise categories have insufficient stock.

The system must also prevent the same participant from receiving the same entitled merchandise more than once.

## 3.12 Vendor compliance and food coverage problems

Different vendors have different:

- Dietary coverage.
- Hygiene certificate validity.
- Capacity.
- Service hours.
- Payment terms.
- Menus.

Some menus conflict with their declared dietary labels.

Certain dietary requirements have no compliant vendor.

## 3.13 Staff and volunteer shortages

The festival has 48 core team members, but different events require more volunteers than are available during certain time windows.

**Problem:** Multiple simultaneous events can create staffing shortages even when the total number of staff appears sufficient.

## 3.14 Safety and transportation gaps

There is no transportation dataset.

However, external properties, late-night arrivals, minors, and event schedules create transportation and safety requirements.

**Problem:** Accommodation can be technically assigned but practically unsafe or unreachable.

## 3.15 Security and privacy

Contact, medical, accessibility, and accommodation information is sensitive.

Different organizers require different access privileges.

The platform must prevent unnecessary access and record important administrative activity.

## 3.16 No centralized incident management

A disruption should not require organizers to manually contact every department.

The system needs a mechanism to identify affected entities and propose coordinated solutions.

# 4. Actual Dataset Findings – Important Problems Discovered

The following figures come from the planning-engine analysis and uploaded output files. They are findings from the supplied data and Claude's prototype, not universal assumptions.

## 4.1 Participant reconciliation

| Metric | Actual value |
|---|---:|
| Participant records | 2,836 |
| Contingent declared strength | 2,842 |
| Narrative expected count | 2,400 |
| Difference between narrative and raw data | 436 |
| Difference between declared strength and raw records | 6 |
| Invalid arrival/departure intervals | 3 |
| Likely duplicate pairs | 7 |
| Possible duplicate pairs | 305 |

All contact numbers were unique, and participant names repeated because the dataset used a relatively small name pool.

Therefore, automatic deletion or merging of duplicate-looking records would be dangerous.

**Required feature:** Duplicate Reconciliation Workbench with confidence scoring, manual verification, merge history, and undo.

### Contingent discrepancies

Seven contingents have differences between declared and actual participant counts:

| Contingent | Difference |
|---|---:|
| C05 | -8 |
| C18 | -5 |
| C32 | -7 |
| C27 | +7 |
| C09 | +5 |
| C02 | +1 |
| C03 | +1 |

Only 3 of 38 contingent leaders and 3 of 38 escorts were found in the participant records.

Approximately 70 leader/escort records may therefore be missing from the participant dataset.

These roles must be reconciled before the accommodation demand can be considered complete.

### Additional participant data findings

| Issue | Count |
|---|---:|
| Gender blank | 417 |
| Prefer not to say | 430 |
| Non-binary | 415 |
| Dietary information blank | 394 |
| Participants aged 17 | 279 |
| 17-year-olds requesting accommodation | 220 |
| Unmappable accessibility requirements | 256 |
| Invalid arrival/departure intervals | 3 |

Gender and dietary blanks must remain UNKNOWN.

The 256 unmappable accessibility records concern requirements such as proximity to washrooms and visual assistance, for which the current room dataset does not provide sufficient information.

**Required features:** Unknown Data Queue, Participant Verification, Accessibility Verification, and Contingent Reconciliation.

## 4.2 Accommodation findings

| Metric | Value |
|---|---:|
| Participants requesting accommodation | 2,144 |
| Records included in generated plans | 2,141 |
| On-campus beds | 710 |
| External beds | 740 |
| Total beds | 1,450 |
| Peak simultaneous demand | 1,601 |
| Peak date and time | 30 October 2026, 6 PM |

The 3-record difference between requests and plan output is because records with invalid arrival/departure intervals were excluded.

### Generated accommodation results

| Metric | Cohesion-first | Cost-first |
|---|---:|---:|
| Allocated on campus | 861 | 861 |
| Allocated externally | 920 | 920 |
| Unplaced | 360 | 360 |
| External accommodation cost | ₹33,15,700 | ₹33,19,250 |
| Contingents split | 36 | 36 |
| Minors in external stays | 71 | 71 |

The difference between the two cost strategies is just ₹3,550.

The 360 unplaced cases are classified as:

- 109 hard accessibility/ground-floor cases.
- 129 without a suitable bed under the transport restrictions.
- 122 with no available eligible property.

The 241 unplaced participants with unconfirmed gender are a cross-cutting classification, not an additional disjoint group.

### Accessibility problems

- Only 10 accessible rooms exist.
- Accessible capacity is 26 beds.
- Wheelchair demand reaches 72 at peak.
- Ground-floor demand reaches 80 at peak.
- External properties lack verified accessibility information.

### Gender accommodation problems

At peak:

- 474 female participants.
- 417 male participants.
- 710 non-binary / prefer-not-to-say / blank participants.

On-campus accommodation contains:

- 236 girls' beds.
- 474 boys' beds.
- No gender-neutral beds.

This creates a significant eligibility and capacity mismatch.

### Minor safety

- 279 participants are aged 17.
- 220 of them request accommodation.
- 71 minors are allocated to external properties.
- All 71 require guardian/escort approval according to the generated plan.

### Additional observations

- 36 out of 38 contingents are split.
- External placements use six properties.
- 0 gender-block violations were reported in the generated output.
- 0 wheelchair/ground-floor violations were reported.
- No room or external property exceeded its modeled capacity at an arrival instant.
- No minors or late-night arrivals were allocated to the limited-transport property.

**Important:** These are results of Claude's prototype and its stated assumptions, not proof that all privacy, accessibility, and real-world safety requirements have been fully verified.

## 4.3 Scheduling findings

| Metric | Value |
|---|---:|
| Events in dataset | 31 |
| Venues | 9 |
| Registrations | 5,580 |
| Generated sessions | 172 |
| Registrations without prelim slot | 987 |
| Unplaced semi/final sessions | 28 |
| Venue overlaps detected | 0 |
| Team registrations missing team IDs | 1,810 |

The schedule is only a prototype.

It successfully generated a preliminary schedule, but its greedy packing fragmented some heats and left many registrations unscheduled.

The generated `schedule_plan.csv` contains sessions for 28 distinct event IDs, so the remaining event coverage should also be checked.

### Missing information

- No event times in the source event file.
- No event venue assignments.
- No judge dataset.
- No venue feature tags.
- 1,810 team-event registrations have no team ID.

The current engine creates assumptions for venue-event compatibility and schedules events instead of simply importing an existing timetable.

### Late arrivals

Approximately 13% of participants arrive on 31 October at 10 PM.

Approximately 12% leave before 31 October at 9 AM.

Claude proposed:

- Early wave: 30 October.
- Main wave: 31 October.
- Late-arrival wave: 1 November morning.

It assumed late entrants could compete in a separate morning wave and enter finals as wildcards.

**This is a fairness decision that requires explicit director approval, not an automatic technical assumption.**

### Volunteer shortage

The resource-load analysis shows:

- Peak volunteer requirement: 74.
- Available core team on shift: 18.
- Maximum gap: 56 people.
- Volunteer coverage gaps occur for approximately 34 hours.

### Equipment shortage

| Equipment | Peak requirement | Good condition | Under repair |
|---|---:|---:|---:|
| Camera | 3 | 0 | 31 |

No camera is reported in good condition, despite three being required simultaneously.

Other equipment categories are reported as adequate by the equipment-gap CSV under the modeled concurrent requirements.

There is one reporting inconsistency worth verifying: `FINDINGS.md` says tables rely on units marked "needs check", while `equipment_gap.csv` reports six required tables and eight in good condition.

Do not treat the table shortage as confirmed until that inconsistency is reconciled.

## 4.4 Merchandise findings

The inventory analysis assumes one item per participant record for per-head merchandise.

| Merchandise | Size | Shortage |
|---|---|---:|
| T-shirt | S | 128 |
| T-shirt | M | 463 |
| T-shirt | L | 377 |
| T-shirt | XXL | 425 |
| ID card | All | 1,491 |
| Lanyard | All | 687 |
| Tote bag | All | 2,019 |
| Special badge | All | 1,954 |

XL T-shirts are in surplus by 115 under the same assumption.

Winner medals are not treated as per-participant merchandise because their demand depends on winners.

**Required features:**

- Merchandise stock monitoring.
- Size-wise demand estimation.
- Participant entitlement checking.
- QR-based issue verification.
- Duplicate claim prevention.
- Low-stock warnings.
- Inventory movement history.

The projected per-head shortages should be verified against actual entitlement policy before procurement decisions.

## 4.5 Vendor and dietary coverage findings

### Hygiene certificate problems

**Four vendors have certificates expired before the festival:**

- VND05
- VND08
- VND11
- VND13

**Four vendors have certificates expiring during the festival on 31 October:**

- VND01
- VND02
- VND04
- VND07

Only six vendors have certificates valid throughout the entire festival.

### Dietary coverage

| Dietary category | Participants in file | Valid compliant vendors | Valid vendor capacity |
|---|---:|---:|---:|
| Vegetarian | 439 | 6 | 1,590 |
| Non-vegetarian | 414 | 2 | 444 |
| Halal | 411 | 4 | 1,077 |
| Jain | 380 | 0 | 0 |
| Gluten-free | 387 | 0 | 0 |
| Nut allergy | 411 | 0 | 0 |
| Unknown dietary information | 394 | — | — |

There is no compliant vendor for Jain, gluten-free, or nut-allergy requirements in the generated coverage report.

The dataset includes two label inconsistencies:

- VND09 has a Jain thali menu but does not declare Jain in its dietary options.
- VND11 advertises vegan bowls but declares non-vegetarian and halal options instead, and its hygiene certificate is expired.

Total capacity from vendors valid throughout the festival is 1,590, while approximately 1,930 people are expected to be on site at peak.

This indicates an aggregate capacity shortfall, although actual meal adequacy also needs to be assessed per meal slot, venue, and dietary group.

**Required features:**

- Vendor compliance management.
- Certificate-expiry monitoring.
- Dietary coverage matrix.
- Vendor capacity planning.
- Vendor shutdown handling.
- Alternative vendor recommendations.
- Menu-label verification.
- Vendor payment and settlement management.

# 5. Complete Core Feature List – Must Implement

The following are the main modules required for FestOS.

## FEATURE 1: Unified Participant Management

Build one central participant record that connects every operational module.

### Required functionalities

1. Participant profile management.
2. Contingent and college mapping.
3. Multiple event registrations.
4. Arrival and departure tracking.
5. Check-in and check-out.
6. Accommodation assignment.
7. Accessibility requirements.
8. Dietary requirements.
9. Accommodation preferences.
10. Merchandise eligibility and issue status.
11. Operational status tracking.
12. Participant search and filtering.
13. Duplicate participant detection.
14. Participant record verification.
15. Participant history.
16. Cancellation and no-show management.

Each participant must have a unique ID.

Different modules must reference the same canonical participant record instead of maintaining separate copies.

## FEATURE 2: Contingent Management

Manage all 38 college contingents.

### Required functionalities

- College-level contingent profiles.
- Declared versus actual strength.
- Contingent leader details.
- Faculty and escort information.
- Arrival and departure coordination.
- Member-level attendance.
- Contingent accommodation distribution.
- Event participation summary.
- Contingent-level dietary requirements.
- Merchandise distribution status.
- Group-level operational alerts.
- Contingent fragmentation analysis.
- Contingent leader proximity tracking.

A coordinator should be able to open a contingent and view its complete operational status.

## FEATURE 3: Intelligent Accommodation Allocation Engine

**Highest-priority decision engine.**

Build an automated, explainable accommodation allocation system.

### 3.1 Accommodation resource management

- On-campus hostel management.
- External property management.
- Room and bed inventory.
- Room capacity.
- Room availability.
- Room status.
- Cleaning status.
- Maintenance status.
- Check-in and check-out windows.
- Floor and block information.
- Accessibility information.
- Gender/housing classification.
- External accommodation pricing.
- External transport availability.
- Property-level safety information.

### 3.2 Eight mandatory accommodation rules

**Rule 1: Accessibility and privacy**

Accessibility and declared privacy requirements are hard constraints.

Never trade them off for cost or contingent cohesion.

**Rule 2: Gender-appropriate allocation**

Support declared housing preferences and gender-segregated accommodation where requested.

Never assume a non-binary or undisclosed participant should be assigned to a male or female block.

Support suitable neutral or single-room options.

**Rule 3: Contingent cohesion**

Keep contingent members together wherever possible.

If splitting becomes necessary, minimize the number of splits and record the reason.

**Rule 4: Leader and escort proximity**

- Contingent leaders should remain near their group.
- Faculty and staff escorts should be separately housed but nearby.
- Their relationship with the contingent should remain visible.

**Rule 5: Room capacity and readiness**

- Respect bed capacity.
- Check room readiness.
- Consider cleaning duration.
- Prevent double booking.
- Validate check-in and check-out windows.
- Support rolling occupancy.

**Rule 6: Event schedules and transportation**

Consider:

- Early events.
- Late-night events.
- External property travel.
- Transportation windows.
- Safety coverage.
- Participant age and other applicable safeguards.

**Rule 7: External accommodation cost**

Calculate external accommodation cost for each participant/property assignment.

Respect the budget and require authorized approval for high-risk budget exceptions.

**Rule 8: Unknown information**

Blank values must remain UNKNOWN.

Do not treat missing information as consent, eligibility, gender, dietary clearance, or absence of need.

### 3.3 Allocation algorithms

Implement a staged allocation process.

**Stage A – Hard constraint filtering**

Remove rooms/properties that cannot safely or appropriately accommodate the participant.

**Stage B – Contingent packing**

Prioritize larger contingents, keep compatible groups together, and minimize unnecessary splits.

**Stage C – External accommodation**

Allocate overflow only to suitable verified properties, considering cost, travel, and safety.

**Stage D – Shortage analysis**

Show unallocated participants, their contingent, gender/housing status, accessibility needs, and the blocking reasons.

**Stage E – Alternative plans**

Generate three candidate plans:

| Plan | Objective |
|---|---|
| Plan A: Cohesion-first | Minimize contingent splitting |
| Plan B: Cost-first | Minimize external accommodation costs |
| Plan C: Balanced | Balance cohesion, expenditure, and travel |

The user should be able to compare:

- On-campus placements.
- External placements.
- Unallocated participants.
- Contingent splits.
- Total cost.
- Safety flags.
- Accessibility issues.
- Relaxed soft constraints.

### 3.4 Explainable allocation

For each assignment, store:

- Participant ID.
- Assigned room/property.
- Constraints satisfied.
- Soft preferences relaxed.
- Reason for relaxation.
- Alternatives rejected.
- Cost.
- Confidence or verification status.
- Approval information.

### 3.5 Allocation overrides

High-risk overrides must require:

- Authorized user.
- Appropriate role.
- Mandatory reason.
- Timestamp.
- Audit entry.

Hard accessibility, safety, and privacy constraints must not be quietly converted into optimization preferences.

## FEATURE 4: Event and Venue Scheduling Engine

Build an intelligent scheduling system for 31 events and nine venues.

### Event management

- Event profiles.
- Event duration.
- Event type.
- Event requirements.
- Solo/team classification.
- Round information.
- Participant registrations.
- Required judges.
- Required volunteers.
- Required equipment.

### Venue management

- Venue capacity.
- Availability windows.
- Operating hours.
- Accessibility.
- Equipment compatibility.
- Venue requirements.
- Setup time.
- Teardown time.

### Conflict detection

Detect:

1. Participant clashes.
2. Team clashes.
3. Judge double-booking.
4. Volunteer double-booking.
5. Venue double-booking.
6. Capacity violations.
7. Equipment conflicts.
8. Insufficient travel time between venues.
9. Setup and teardown conflicts.
10. Event operating-hour conflicts.

### Advanced scheduling functionality

- Automatic venue suggestions.
- Alternative event time suggestions.
- Automatic conflict resolution recommendations.
- Round dependencies.
- Result declaration buffers.
- Preliminary, semifinal, and final scheduling.
- Travel-time calculations.
- Schedule version history.
- Conflict severity classification.
- Unscheduled participant reporting.

When an event cannot be scheduled, do not silently discard its participants.

Show the reason and offer possible alternatives.

**Important:** The existing schedule is only a draft. It has 987 unscheduled registrations and 28 unplaced later-round sessions. A better clustering approach or OR-Tools CP-SAT optimization should be evaluated, particularly to reduce the 987 unscheduled registrations.

## FEATURE 5: Logistics and Inventory Management

Build time- and location-aware inventory tracking.

### Required functionalities

- Equipment inventory.
- Merchandise inventory.
- Item categorization.
- Stock quantity.
- Reserved stock.
- Available stock.
- In-transit stock.
- Damaged stock.
- Under-repair stock.
- Awaiting-return stock.
- Warehouse/location management.
- Inventory transfers.
- Transfer completion.
- Issue and return operations.
- Stock movement history.
- Low-stock alerts.
- Resource allocation to events.

Do not treat physical stock as equivalent to available stock.

The system must distinguish between items physically present, reserved, transferred, damaged, or unavailable.

### Advanced requirement

Equipment assigned to one venue must not simultaneously be considered available at another venue.

Consider transportation time when scheduling equipment transfers.

## FEATURE 6: Merchandise Distribution and QR Verification

Create a dedicated merchandise distribution module.

### Required functionalities

- Merchandise catalog.
- T-shirt size management.
- Participant merchandise entitlement.
- Stock tracking.
- Size-wise demand.
- Reservation management.
- Merchandise counters.
- Distribution transactions.
- QR code generation.
- QR code scanning.
- Duplicate claim detection.
- Issue history.
- Issuing volunteer information.

### Critical rule

Each participant must receive an entitled merchandise item only once.

Use:

- A unique participant/item entitlement.
- A database uniqueness constraint.
- Transactional stock reduction.
- An idempotent issuing API.
- Canonical participant identity.

When the same QR code is scanned twice, show:

> Already issued.

Display the original issue timestamp, counter, and staff member.

## FEATURE 7: Food Vendor Management

Create a complete vendor operations module.

### Required functionalities

- Vendor profiles.
- Menus.
- Dietary categories.
- Meal/service capacity.
- Operating hours.
- Vendor rates.
- Contract information.
- Hygiene certificates.
- Certificate expiry monitoring.
- Vendor status.
- Vendor assignments.
- Food service locations.
- Payment terms.
- Settlement tracking.
- Vendor interruption management.

### Dietary coverage matrix

Match vendor capabilities against participant dietary requirements.

Support categories such as:

- Vegetarian.
- Non-vegetarian.
- Vegan.
- Jain.
- Halal.
- Gluten-free.
- Nut allergy.
- Other declared allergies or dietary restrictions.

Unknown dietary requirements must remain unknown.

### Vendor shutdown response

When a vendor shuts down:

1. Identify affected service locations.
2. Identify affected meal slots.
3. Calculate unavailable meal capacity.
4. Identify dietary categories with coverage gaps.
5. Find suitable replacement vendors.
6. Check backup capacity.
7. Calculate cost changes.
8. Generate replacement recommendations.
9. Draft notifications.
10. Update operational state after approval.

## FEATURE 8: Staff and Volunteer Management

Manage all 48 core team members and their operational deployment.

### Required functionalities

- Staff profiles.
- Staff roles.
- Skills.
- Shift schedules.
- Event assignments.
- Venue assignments.
- Availability.
- Shift overlap detection.
- Volunteer requirement calculations.
- Understaffed event alerts.
- Overloaded staff detection.
- Emergency replacement suggestions.
- Shift handover notes.

The system should calculate staffing demand across simultaneous sessions and identify uncovered slots.

## FEATURE 9: Central Operational Control Dashboard

Build the main command centre.

The dashboard must prioritize exceptions, not simply present decorative statistics.

### Important dashboard metrics

- Total participants.
- Arrived participants.
- Checked-in participants.
- Pending arrivals.
- Accommodation occupancy.
- Available beds.
- Unplaced participants.
- Active event sessions.
- Open schedule conflicts.
- Equipment availability.
- Merchandise stock.
- Vendor status.
- Food coverage gaps.
- Staff availability.
- Open incidents.
- Pending approvals.
- Active overrides.

### Priority attention queue

Rank problems using:

`Severity × Urgency × People Affected`

Examples:

- Participants with unconfirmed accessibility needs arriving within six hours.
- Unplaced participants.
- Hostel capacity shortages.
- Blocking event conflicts in the next four hours.
- Expired hygiene certificates.
- Vendors with inadequate dietary capacity.
- Equipment shortages.
- Understaffed events.
- Pending high-risk approvals.
- Duplicate records awaiting verification.
- Late or missing arrivals.

Every alert should have a direct action to resolve the issue.

## FEATURE 10: Role-Based Access Control and Security

Implement role-specific permissions.

### Recommended roles

| Role | Access |
|---|---|
| Festival Director | Full operational overview and high-risk approvals |
| Accommodation Lead | Hostel, property, accessibility, and room allocation |
| Event Lead | Events, schedules, venues, judges, and volunteers |
| Logistics Manager | Equipment and inventory |
| Merchandise Manager | Merchandise entitlement and issue |
| Food Operations Manager | Vendors, menus, and food coverage |
| Finance Manager | Costs, contracts, and settlements |
| Volunteer | Limited check-in and merchandise scanning |
| Auditor | Read-only audit history |

### Security requirements

- Secure authentication.
- Role-based authorization.
- Field-level permission checks.
- Contact information masking.
- Sensitive information masking.
- Protected medical/accessibility data.
- Protected room allocation data.
- Audit history.
- Export restrictions.
- Controlled access to sensitive fields.

### Break-glass access

For special situations, an authorized user may request temporary access to a normally masked field.

The system must require a reason and record the access in the audit log.

## FEATURE 11: Audit and Decision History

Maintain a complete history of important operational changes.

Every important mutation should store:

- Action.
- Previous state.
- New state.
- User.
- Role.
- Timestamp.
- Reason.
- Approval.
- Related incident/change ID.

### Decision explanation cards

For every important decision, show:

- Why the decision was recommended.
- Which hard constraints were satisfied.
- Which soft constraints were relaxed.
- Which alternatives were rejected.
- Cost impact.
- People affected.
- Who approved it.

Build an override register showing all high-risk exceptions.

# 6. System-Wide Innovation Features Recommended by Claude

These features go beyond the original requirements and should be considered important differentiators.

## 6.1 Change Impact Engine / Blast Radius Analysis

**Highest-impact innovation.**

Create a dependency graph connecting:

```text
Participant → Contingent → Registration → Event → Venue → Equipment → Vendor

Participant → Arrival → Check-in → Accommodation → Meal requirements → Vendor

Participant → Merchandise eligibility → Stock → Distribution counter
```

Whenever an operational change occurs, traverse the connected entities and calculate the downstream impact.

### Example

A bus is delayed by three hours.

FestOS should identify:

- Which participants will arrive late.
- Which check-ins will be delayed.
- Which accommodation assignments are affected.
- Which meal requirements shift.
- Which event registrations are at risk.
- Which merchandise distributions need adjustment.
- Which staff deployments require changes.

### Important functionality

- Visual impact tree.
- Affected entity counts.
- Severity levels.
- Proposed resolutions.
- Impact comparison before and after change.
- Downstream update tracking.

This is the central innovation because it directly solves the main problem of the festival.

## 6.2 Decision Log with Explainable "Why" Cards

Every important allocation and operational decision should have a one-click explanation.

For example:

"Participant assigned to Hostel B because it satisfies accessibility and privacy requirements, while the alternative external property exceeds the available budget."

Store the reason, constraints, rejected alternatives, and approving person.

## 6.3 Constraint Relaxation Ladder

When the system cannot satisfy all soft preferences, use a transparent relaxation order.

**Hard constraints – Never automatically relaxed:**

- Accessibility.
- Privacy.
- Safety.
- Required housing preferences.

**Soft preferences – May be relaxed with explanation:**

1. Contingent cohesion.
2. Accommodation cost.
3. Proximity.

Generate alternatives such as:

- Plan A: Fewer contingent splits, higher accommodation expenditure.
- Plan B: Lower expenditure, more contingent splits.
- Plan C: Balanced recommendation.

Show the trade-offs instead of silently selecting one result.

## 6.4 Unknown as a First-Class Data State

All important fields should support:

- YES.
- NO.
- UNKNOWN.

A blank field must never automatically become NO.

Build:

- Missing-information dashboard.
- Verification queue.
- Participant confirmation status.
- Data owner.
- Last verification timestamp.
- Impact of missing information.
- Priority ranking.

## 6.5 Duplicate and Reconciliation Workbench

Create a separate interface showing:

- Raw participant count.
- Expected count.
- Declared contingent count.
- Exact duplicates.
- Likely duplicates.
- Possible duplicates.
- Withdrawn participants.
- Invalid records.
- Unresolved records.
- Confidence scores.

Allow authorized organizers to:

- Compare two records side by side.
- Merge records.
- Keep records separate.
- Review linked registrations.
- Preserve original record IDs.
- Undo merges.
- Audit every decision.

Do not automatically merge people merely because they have similar names.

## 6.6 Minimal-Change Replanning Engine

After a disruption, do not completely rebuild the entire festival plan.

Instead, preserve as much of the original plan as possible.

Prioritize:

- Minimum number of people relocated.
- Minimum schedule disruption.
- Minimum resource movement.
- Preservation of contingent cohesion.
- Minimum cost increase.
- Preservation of existing approved allocations.

Show the number of changes required compared with the original plan.

## 6.7 Scenario Simulator / Sandbox

Allow an organizer to test operational changes without immediately modifying live data.

Example:

"What happens if Hostel B closes?"

The simulator should:

1. Copy the current operational state.
2. Apply the hypothetical disruption.
3. Run impact analysis.
4. Generate alternative plans.
5. Compare costs and operational consequences.
6. Let the organizer commit or discard the scenario.

Support multiple scenarios such as hostel closure, vendor shutdown, and venue changes.

## 6.8 Risk Heatmap

Create a risk dashboard using:

- Severity.
- Time until impact.
- Number of people affected.
- Resource criticality.
- Uncertainty.

Display operational risks visually so organizers understand which problem needs attention first.

## 6.9 Role-Aware Interfaces

Provide separate interfaces for:

- Volunteers.
- Department coordinators.
- Accommodation managers.
- Event managers.
- Finance managers.
- Festival directors.

Volunteer interfaces should have large buttons and minimal data exposure.

## 6.10 Vendor Fallback Mapping

Whenever a vendor becomes unavailable, automatically find replacement vendors according to:

- Dietary suitability.
- Certificate validity.
- Operating hours.
- Spare capacity.
- Venue location.
- Service cost.

Generate notifications for affected departments.

## 6.11 Offline-Tolerant Check-in

Build a Progressive Web App (PWA) that supports basic check-in and merchandise scanning with unreliable internet.

Store safe pending operations locally and synchronize when connectivity returns.

Prevent duplicate or conflicting server updates during synchronization.

## 6.12 Natural-Language Command Bar

Allow an organizer to type commands such as:

- "Show the impact of closing Hostel C."
- "Find accommodation for the unplaced participants."
- "Which events are affected by camera shortages?"
- "Find alternative vendors for Jain meals."
- "Show the participants arriving after 10 PM."

The LLM should convert the request into a structured command.

The deterministic rules engine should validate the request and calculate the decision.

Humans should approve important changes.

The intended principle:

> AI proposes. Deterministic logic validates. Humans approve.

## 6.13 Forecasting and Predictive Analytics

Forecast:

- Arrival peaks.
- Check-in queues.
- Meal demand.
- Accommodation demand.
- Merchandise demand.
- Equipment requirements.
- Volunteer demand.

Use historical information or the available festival timetable where meaningful.

Do not present assumptions as predictions.

## 6.14 Notification Drafting

When an important operational change happens, generate message drafts for:

- Contingent leaders.
- Volunteers.
- Vendors.
- Accommodation coordinators.
- Event organizers.

Require approval before sending.

Mock sending is sufficient for the hackathon.

## 6.15 Financial Management

Include:

- External accommodation spending.
- Vendor settlements.
- Merchandise costs.
- Budget utilization.
- Payment deadlines.
- Cost variance.
- Approved emergency spending.
- Budget override reporting.

## 6.16 Post-Festival Reporting

Generate a final operational report from the audit history.

Include:

- Participant attendance.
- Accommodation utilization.
- Event completion.
- Inventory usage.
- Vendor performance.
- Incident history.
- Financial expenditure.
- Operational delays.
- Outstanding settlements.

# 7. Three Standalone, High-Impact Features Suggested Later by Claude

These are distinct innovations that can differentiate FestOS from ordinary event-management applications.

## FEATURE A: Fest Pre-Mortem – Predictive Festival Resilience Simulator

**Concept**

Instead of waiting for the festival to experience a failure, FestOS should proactively test whether its current operational plan can survive unexpected disruptions.

The system should simulate possible future failures before they happen.

### Possible disruptions

- Bus delayed by three hours.
- Hostel suddenly closes.
- Vendor stops operating.
- Camera or equipment fails.
- Venue becomes unavailable.
- Staff shortage.
- Sudden increase in accommodation demand.
- Transportation interruption.
- Contingent arrives later than scheduled.

### Core functionalities

1. Sandbox simulation.
2. Random disruption generation.
3. Multi-scenario simulation.
4. Time-based simulation.
5. Impact calculation.
6. Identification of single points of failure.
7. Risk ranking.
8. Operational resilience score.
9. Suggested preventive actions.
10. Scenario history.

### Timeline scrubber

Create a time slider through which organizers can inspect the festival hour by hour.

The timeline should display:

- Accommodation availability.
- Bed occupancy.
- Food demand.
- Vendor availability.
- Venue utilization.
- Equipment demand.
- Volunteer coverage.
- Transportation requirements.
- Critical operational risks.

### Resilience score

Create an explainable score based on:

- Number of people affected by simulated disruptions.
- Critical resource dependencies.
- Accommodation shortages.
- Vendor redundancy.
- Venue redundancy.
- Equipment availability.
- Staffing coverage.
- Safety coverage.

Do not present this as a scientifically validated probability of success. Define and disclose the scoring methodology.

### Example

At 10 PM on 31 October:

- A group of participants is staying at Lakeview.
- Limited transportation is available.
- Some participants have early or late event commitments.
- The system identifies the risk and displays it before the disruption actually happens.

### Why this feature stands out

Most applications react to a failure.

Fest Pre-Mortem predicts weaknesses in the plan before the festival experiences them.

**Demo moment:** Drag the timeline to a critical time and show the operational risks appearing in advance.

## FEATURE B: Unknowns Burn-down – Value-of-Information Intelligence

**Concept**

The festival data has many missing fields, particularly gender, accommodation preferences, accessibility, and dietary requirements.

Most applications simply list missing fields.

FestOS should identify which missing information is most valuable to resolve first.

This feature should rank unknown information according to how much it can improve operational outcomes.

### Core idea

Not all missing information has equal importance.

For example:

- A missing housing preference may prevent someone from being assigned to a suitable room.
- An unconfirmed dietary requirement may cause a vendor coverage problem.
- Missing accessibility information may create an accommodation safety issue.
- An unknown arrival time may make transport planning inaccurate.

The system should prioritize the missing information that can have the greatest positive impact on the festival.

### Core functionalities

1. Identify unknown fields.
2. Identify participants affected.
3. Rank unknowns by operational impact.
4. Calculate the potential improvement from confirmation.
5. Generate minimal confirmation requests.
6. Allow leaders or desk volunteers to record verified information.
7. Re-run relevant allocation logic.
8. Show before-and-after results.
9. Explain why a participant remains unallocated.
10. Maintain a confirmation history.

### Value-of-information ranking

For each unknown field, simulate possible outcomes and measure the improvement.

Possible metrics:

- Beds recovered or made eligible.
- Unplaced participants reduced.
- Lower accommodation costs.
- Better contingent cohesion.
- Improved dietary coverage.
- Reduced safety uncertainty.

Example:

"Confirming housing preferences for these 120 participants could make approximately 90 additional beds eligible and reduce the number of unplaced participants by 40."

These numbers are illustrative; the system must calculate actual results from current records.

### The "Why Not?" button

Every unplaced participant should have a button:

**Why is this participant not allocated?**

The system should explain:

- Which requirement is blocking the assignment.
- Which information is missing.
- Which rooms or properties were rejected.
- What would change if the missing information were confirmed.
- Whether an alternative placement exists.

### Confirmation mechanism

Use:

- Minimal confirmation links for contingent leaders.
- Verification by authorized desk volunteers.
- Field-specific verification.
- Timestamp and verification source.
- Audit history.

### Why this feature stands out

The system doesn't simply report missing data.

It actively reduces uncertainty by identifying which questions should be answered first.

## FEATURE C: Duty-of-Care and Shuttle Planner

**Concept**

Create a dedicated safety and transportation planning module.

The current data pack includes:

- Participant arrival and departure times.
- External accommodation properties.
- Property distances.
- Transportation availability indicators.
- Participants below 18.
- Late-night arrivals and departures.

But there is no dedicated transport dataset.

FestOS should derive a basic transportation and duty-of-care plan from the existing accommodation and arrival information.

### Core functionalities

**1. Shuttle planning**

- Identify participants travelling to external properties.
- Group journeys by property.
- Group arrivals and departures by time.
- Calculate required shuttle runs.
- Estimate passenger demand.
- Compare demand with assumed vehicle capacity.
- Identify transport shortages.

**2. Night-safety roster**

- Identify late-night arrivals.
- Identify late-night departures.
- Identify minors in external accommodation.
- Identify participants with uncovered safety arrangements.
- Assign named escorts or volunteers.
- Track whether the arrangement has been verified.

**3. Guardian approval**

Create a dedicated queue for minors placed in external accommodation.

Each entry should show:

- Participant ID.
- Contingent.
- External property.
- Stay duration.
- Guardian approval status.
- Escort assignment.
- Transport arrangement.
- Responsible coordinator.

**4. Transport alerts**

Example:

"14 participants are scheduled to leave Lakeview at midnight, but no verified shuttle is assigned."

**5. Safety coverage dashboard**

Display:

- People requiring transport.
- Confirmed shuttle capacity.
- Uncovered transport requests.
- Late-night movement.
- Minor accommodation approvals.
- Unassigned escorts.
- External property risk.

### Important assumptions

Because the dataset does not contain a complete transportation schedule, the following must remain configurable assumptions:

- Shuttle capacity.
- Number of vehicles.
- Driver availability.
- Travel duration.
- Transport operating hours.
- Escort availability.

### Why this feature stands out

It addresses a real-world duty-of-care issue rather than merely managing rooms and event schedules.

**Demo moment:** Show how the system identifies participants who have an external accommodation assignment but do not have a confirmed late-night transport or safety arrangement.

### Recommended development order

If development time is limited:

1. Unknowns Burn-down.
2. Duty-of-Care and Shuttle Planner.
3. Fest Pre-Mortem.

These three features are independent enhancements, although they can reuse the same allocation, dependency, and simulation engines.

# 8. Additional Edge Cases That Must Be Handled

## Participant and contingent edge cases

- Two people have the same name.
- Participant appears in multiple records.
- Participant cancels after accommodation has been allocated.
- Participant becomes a no-show.
- Participant arrives late.
- Contingent arrives after the allocation is frozen.
- Contingent size exceeds the capacity of a single hostel block.
- Contingent leader is also a competitor.
- Escort is also a judge or competitor.
- Staff members are incorrectly counted as ordinary participants.

## Accommodation edge cases

- Room becomes unavailable after allocation.
- Room is available physically but cleaning is incomplete.
- Two participants require the same limited accessible room.
- External property has no verified accessibility information.
- Participant has unknown housing preference.
- Participant requires a single/private room.
- Gender-neutral accommodation is unavailable.
- Participant checks out but the room cannot immediately be reused.
- New participants arrive after existing accommodation allocation.
- External property has no transportation after a specific time.
- Two organizers attempt to allocate the same room simultaneously.

## Event and scheduling edge cases

- Participant is registered for overlapping events.
- Participant cannot travel between two consecutive events.
- Team is missing a member assignment.
- Judge is associated with a participating college.
- Judge is also a contingent participant.
- Venue becomes unavailable during an event.
- Venue capacity is reduced.
- Event duration increases.
- Event is cancelled or merged.
- Event round results are delayed.
- Equipment is shared between distant venues.
- Equipment transfer cannot finish before the next event.
- Volunteers are double-booked.
- Judges are double-booked.

## Logistics and merchandise edge cases

- Inventory transfer gets delayed.
- Equipment is damaged during transport.
- Merchandise is reserved but not collected.
- Duplicate QR scanning.
- Duplicate participant records claim the same entitlement.
- Two volunteers attempt to issue the same item simultaneously.
- Stock count does not match physical inventory.
- Returned merchandise is not immediately available for redistribution.

## Food vendor edge cases

- Vendor certificate expires during the festival.
- Vendor closes unexpectedly.
- Vendor exceeds its operating capacity.
- Menu differs from declared dietary coverage.
- Vendor claims a dietary category without proper confirmation.
- No vendor supports a specific allergy requirement.
- Dietary information is missing.
- Backup vendor cannot handle the additional capacity.
- Vendor payment is delayed or disputed.

## Staff and operational edge cases

- Volunteer shift overlaps.
- Staff member is assigned to two venues.
- Critical event has no assigned volunteer.
- Emergency staff replacement is required.
- A disruption happens during shift change.
- Staff handover information is missing.
- No nearby staff member is available at a disrupted venue.

## System-level edge cases

- Time formats differ across CSV files.
- Date formats are inconsistent.
- Timezone normalization is required.
- Import file contains missing columns.
- CSV contains invalid rows.
- Two admins update the same record concurrently.
- Override is used without proper justification.
- Sensitive information appears in exports.
- Data synchronization creates duplicate transactions.
- Network connectivity is lost during check-in.
- A disruption occurs while another disruption is being resolved.

# 9. Assumptions and Unknowns Register

The application must visibly maintain an Assumptions Register.

Do not silently assume values when the dataset does not provide them.

### Assumptions in Claude's actual planning engine

| Parameter | Engine assumption |
|---|---|
| Cleaning between occupants | 3 hours |
| Late-night window | 10 PM–6 AM |
| Minor age threshold | Below 18 |
| Setup buffer | 15 minutes |
| Teardown buffer | 15 minutes |
| Travel between venues | 15 minutes |
| Round result buffer | 60 minutes |
| Semifinal entrants | 50% of preliminary entrants |
| Finalist estimate | 10%, minimum 8 |
| Check-in buffer | 60 minutes before first event |
| Venue capacity | Maximum simultaneous competitors in a heat |
| Wheelchair requirement | Accessible room only |
| Ground-floor requirement | Ground floor only |
| Near-washroom / visual assistance | Manual verification |
| External property accessibility | Unverified |
| External property gender suitability | Unverified |
| External stay budget | Not supplied |
| Venue requirements mapping | Assumed and editable |
| Events without timing | Schedule generated |
| Equipment quantity | One unit unless explicitly specified otherwise |

**Important discrepancy:** An earlier conceptual assumption list suggested a 60-minute cleaning buffer, whereas the actual uploaded engine uses 3 hours. The generated allocation was based on the engine's 3-hour setting. The final implementation must select and display one verified/configurable value rather than mixing the two.

The blueprint also recommended counting UNKNOWN accommodation demand as possible demand, whereas the actual planning script filters for `accommodation_requested == 'yes'`. The final system must separately account for confirmed and possible accommodation demand.

Other assumptions to document:

- Who qualifies as a participant?
- Are volunteers and escorts included in accommodation demand?
- Are local students excluded from accommodation?
- How are gender/housing preferences confirmed?
- What is the external accommodation budget?
- What are travel times between external properties and venues?
- What should happen to late arrivals?
- Should late arrivals join preliminaries or use a special wave?
- How should event cancellation affect registrations and vendors?
- How should unknown information be treated during allocation?

Every assumption should display:

- Assumption name.
- Current value.
- Source.
- Responsible owner.
- Last updated time.
- Reason.
- Operational impact if changed.

# 10. Recommended Technical Architecture

Claude recommended a simple but modular architecture suitable for a 24-hour hackathon.

## 10.1 Technology stack

| Layer | Recommended technology |
|---|---|
| Frontend | React + Vite |
| Styling | Tailwind CSS |
| Backend | Python + FastAPI |
| Database | SQLite with WAL mode, or PostgreSQL |
| ORM | SQLAlchemy / SQLModel |
| Authentication | JWT with role claims |
| Optimization | Greedy + local repair, optional OR-Tools CP-SAT |
| Data processing | Pandas |
| Duplicate detection | RapidFuzz |
| Charts | Recharts |
| Deployment | Docker Compose or local run |

The architecture should remain a modular monolith rather than unnecessarily complex microservices.

## 10.2 System architecture

```text
                FESTIVAL DATA PACK
                        |
                        v
                 IMPORT PIPELINE
                        |
                        v
                  STAGING TABLES
                        |
                        v
               VALIDATION & RECONCILIATION
                        |
                 HUMAN VERIFICATION
                        |
                        v
               UNIFIED CORE DATABASE
                        |
        +---------------+----------------+
        |               |                |
        v               v                v
  Accommodation     Scheduling       Inventory
     Engine            Engine          Ledger
        |               |                |
        +---------------+----------------+
                        |
        +---------------+----------------+
        |               |                |
        v               v                v
     Vendors        Staff/Shifts     Safety/Transport
                        |
                        v
                  CHANGE SERVICE
               VALIDATE -> APPLY -> AUDIT
                        |
          +-------------+-------------+
          |             |             |
          v             v             v
     IMPACT GRAPH   ATTENTION QUEUE  DECISION LOG
          |             |             |
          +-------------+-------------+
                        |
                        v
                  REST API + RBAC
                        |
                        v
                  REACT FRONTEND
```

### Central engineering principle

Every mutation should pass through one common service layer.

The service should:

1. Validate the requested change.
2. Check constraints.
3. Record the previous state.
4. Apply the change transactionally.
5. Generate an audit event.
6. Calculate downstream impact.
7. Generate alternative recommendations.
8. Require approval when necessary.

# 11. Recommended Database Entities

Use a relational database with clearly defined relationships.

| Table | Purpose |
|---|---|
| participant | Participant information and operational status |
| contingent | College and group information |
| registration | Participant-to-event mapping |
| event | Event definition and timing |
| event_requirement | Judges, volunteers, and equipment requirements |
| venue | Venue capacity and availability |
| travel_time | Estimated travel between locations |
| room | Hostel rooms and room attributes |
| external_property | External accommodation details |
| stay_assignment | Participant accommodation allocation |
| inventory_item | Equipment and merchandise catalog |
| inventory_movement | Inventory transaction ledger |
| merch_claim | Merchandise entitlement and issue history |
| vendor | Vendor profiles and compliance |
| vendor_assignment | Vendor-to-venue and meal-slot mapping |
| staff | Core team and volunteer profiles |
| audit_event | Immutable operational history |
| change_set | Operational changes and impact |
| assumption | Configurable assumptions |
| override | High-risk exception records |
| incident | Disruption records and resolutions |
| approval | Authorization history |
| shift | Staff shift and duty assignments |
| transport | Vehicles, routes, and shuttle operations |
| shuttle_assignment | Participant movement and safety assignments |

### Important relationships

- One contingent has multiple participants.
- One participant can have multiple event registrations.
- One event can involve multiple participants and teams.
- Events require venues, equipment, judges, and volunteers.
- One accommodation plan contains multiple assignments.
- Participants have time-bound accommodation assignments.
- Inventory movements connect different locations.
- Vendors are assigned to food service windows and venues.
- Every major state change creates a change-set and audit entry.

A `plan_id` should distinguish candidate accommodation plans from the currently approved live plan.

# 12. Core Algorithmic Requirements

## 12.1 Accommodation allocation

Use a hard-filter-first approach.

Hard constraints must eliminate invalid options before optimization begins.

Then optimize:

- Contingent cohesion.
- Cost.
- Leader proximity.
- Travel time.
- Room utilization.

Use greedy allocation with local repair for rapid implementation.

Consider OR-Tools CP-SAT where more complete optimization is needed.

Do not claim a mathematically optimal allocation if only a heuristic is being used.

## 12.2 Scheduling

Use interval-overlap detection, resource availability checks, and travel buffers.

A basic time-overlap condition is:

```text
Start_A < End_B  AND  Start_B < End_A
```

Also consider:

- Setup and teardown.
- Travel between venues.
- Shared equipment.
- Staff availability.
- Round dependencies.
- Result declaration buffers.

Use a sweep-line or interval scheduling approach for conflict detection.

For candidate resolution, evaluate alternative venue/time combinations and rank them according to conflicts resolved, new conflicts created, and people affected.

## 12.3 Inventory

Every stock change must be recorded as a movement transaction.

Do not use simple overwriting of stock quantities.

Track:

- On-hand.
- Reserved.
- In transit.
- Damaged.
- Awaiting return.

## 12.4 Merchandise issuance

Use database transactions and a unique constraint on:

`Canonical Participant ID + Item ID`

Two simultaneous claims must never both succeed.

## 12.5 Impact engine

Every operational disruption should produce a structured result:

```text
Change
   |
   v
Validate
   |
   v
Apply to scenario / state
   |
   v
Calculate downstream impact
   |
   v
Generate recommendations
   |
   v
Show comparison
   |
   v
Human approval
   |
   v
Commit
   |
   v
Audit and verify
```

# 13. Disruption Management Console

Build one dedicated Disruption Console containing all seven live-test scenarios.

Each scenario should have:

- A button or form to inject the disruption.
- A simulation option.
- An impact preview.
- A proposed recovery plan.
- A comparison of alternatives.
- An approval action.
- A real state update after approval.
- A change-history record.

### The seven mandatory live-test scenarios

| Scenario | Expected system response |
|---|---|
| Late contingent | Update arrivals, accommodation, events, food, merchandise, and transport demand |
| Duplicate participant | Reconcile records and linked reservations |
| Hostel closure | Find affected participants and reallocate |
| Equipment failure | Identify dependent events and alternative equipment |
| Venue change | Recheck capacity, time, participants, travel, and resources |
| Vendor shutdown | Identify dietary gaps and replacement vendors |
| Duplicate merchandise claim | Reject second claim and show original transaction |

The system must make real changes to its operational state. Static demonstrations or hardcoded notifications are insufficient.

# 14. Expected Data Import and Export Outputs

The platform should be capable of generating the following reports.

| Output | Purpose |
|---|---|
| reconciliation_report.csv | Explain participant count and duplicates |
| data_quality_report.csv | Missing fields and invalid records |
| accommodation_plan_A.csv | Cohesion-first accommodation |
| accommodation_plan_B.csv | Cost-first accommodation |
| accommodation_plan_C.csv | Balanced accommodation |
| shortage_report.csv | Unplaced participants and reasons |
| accommodation_summary.csv | Group-wise distribution |
| schedule_plan.csv | Generated event schedule |
| conflicts_report.csv | Event and resource conflicts |
| unscheduled_entrants.csv | Participants without event slots |
| inventory_plan.csv | Stock and shortage |
| equipment_gap.csv | Equipment availability |
| vendor_coverage.csv | Dietary coverage |
| vendor_compliance.csv | Vendor certificate status |
| staff_coverage.csv | Volunteer requirements versus availability |
| bed_demand_timeline.csv | Accommodation demand over time |
| resource_load_timeline.csv | Staffing and equipment requirements over time |
| assumptions.md | All system assumptions |
| incident_report.csv | Disruptions and resolutions |
| audit_report.csv | Operational decision history |

# 15. Testing and Reliability Requirements

The application must be tested for both normal operation and failure conditions.

### Accommodation tests

- Accessibility requirements are never violated.
- No room capacity is exceeded.
- No bed is double-booked.
- Cleaning intervals are respected.
- Unknown housing information is not silently assigned.
- All unallocated participants have documented reasons.

### Scheduling tests

- No venue double-booking.
- No overlapping assignment of shared participants.
- No insufficient travel windows.
- No equipment double allocation.
- No volunteer double assignment.
- No scheduling outside valid venue hours.

### Inventory tests

- Stock movements balance.
- Reserved stock is not issued twice.
- In-transit stock is not counted at both locations.
- Damaged stock is unavailable.
- Duplicate merchandise claims produce only one success.

### Data tests

- Malformed CSV files are handled.
- Missing columns generate clear errors.
- Invalid records are quarantined.
- Unknown values remain unknown.
- Duplicate merges can be reversed.
- Original raw records are preserved.

### System tests

- Role-based permissions are enforced.
- Sensitive information is masked.
- Changes generate audit events.
- Concurrent updates are handled using version checks.
- Failed transactions do not leave partial state.
- Seed data can reset the application.
- Golden tests reproduce the expected outputs.

# 16. Suggested 24-Hour Development Plan

| Time | Development focus |
|---|---|
| Hours 0–2 | Data profiling, assumptions, schema, and architecture |
| Hours 2–5 | Import pipeline, validation, duplicate detection, reconciliation |
| Hours 5–10 | Accommodation engine and scheduling conflict detector |
| Hours 10–12 | Control dashboard, impact graph, and decision log |
| Hour 12 | Adapt to the hackathon twist |
| Hours 12–16 | Inventory, merchandise, vendors, RBAC, and audit |
| Hours 16–20 | Impact engine, disruption console, and scenario testing |
| Hours 20–22 | UI improvements, mobile volunteer view, reports, and bugs |
| Hours 22–24 | Code freeze, README, AI disclosure, and pitch rehearsal |

### Priority if time becomes limited

1. Data import and reconciliation.
2. Accommodation allocation with explainability.
3. Scheduling and conflict detection.
4. Disruption console and impact engine.
5. Merchandise issue ledger.
6. RBAC and audit.
7. Vendor coverage.
8. Advanced innovations.

Do not sacrifice working decision-making features for decorative UI elements.

# 17. Pitch and Submission Requirements

### Mandatory deliverables

1. A working portal that judges can interact with.
2. Sample accommodation, scheduling, and inventory plans generated from the data pack.
3. Seven-minute pitch.
4. Three-minute question-and-answer session.
5. Setup instructions.
6. Test credentials.
7. AI disclosure slide.

### Suggested seven-minute pitch

| Time | Presentation |
|---|---|
| 0:00–0:45 | The original festival problem |
| 0:45–1:45 | Data reconciliation and actual operational problems |
| 1:45–3:00 | Accommodation allocation and alternative plans |
| 3:00–4:30 | Live hostel disruption and impact analysis |
| 4:30–5:30 | Scheduling, inventory, and vendor operations |
| 5:30–6:15 | Security, permissions, and audit history |
| 6:15–6:45 | Assumptions and limitations |
| 6:45–7:00 | AI disclosure |

### AI disclosure

Include:

**What AI did:**

- Code scaffolding.
- Boilerplate generation.
- Test generation.
- Data analysis assistance.
- Deduplication suggestions.
- Natural-language command interpretation.
- Communication drafts.

**What the team decided:**

- Hard and soft constraint hierarchy.
- Accessibility and privacy rules.
- Unknown-data treatment.
- Safety requirements.
- Override policies.
- Human approval requirements.

**How outputs were verified:**

- Unit tests.
- Property tests.
- Hand-calculated examples.
- Constraint validation.
- Review of generated plans.
- Manual review of flagged records.

### Known limitations to disclose

- Greedy allocation is heuristic and not provably optimal.
- Travel times may be assumed.
- Real transport integrations may not exist.
- Some vendor or accessibility information needs manual confirmation.
- Synthetic participant data is used.
- SQLite has limited concurrent scaling.
- Actual notifications may be mocked.
- Generated schedule quality is limited by missing source times, venues, team IDs, and judge data.

# 18. Recommended Final Product Structure

The following navigation can organize all the functionalities into a practical interface.

| Section | Main functionality |
|---|---|
| Overview | Central operational dashboard |
| Participants | Participant profiles and records |
| Contingents | College and group management |
| Check-in | QR-based arrival verification |
| Accommodation | Allocation and room management |
| Events & Venues | Scheduling and conflicts |
| Logistics | Equipment and inventory |
| Merchandise | Entitlements and QR issuance |
| Vendors & Food | Dietary coverage and compliance |
| Staff & Shifts | Volunteer scheduling |
| Transportation | Shuttle and safety planning |
| Incident Center | Disruption management |
| Impact Analysis | Downstream change analysis |
| Scenario Simulator | What-if analysis |
| Fest Pre-Mortem | Predictive resilience |
| Unknowns Burn-down | Missing-information resolution |
| AI Command Center | Natural-language operations |
| Data Reconciliation | Data quality and duplicates |
| Reports | Financial and operational reports |
| Audit & Permissions | Security and decisions |

# 19. Final Innovation Priorities

| No. | Feature | Main value |
|---:|---|---|
| 1 | Change Impact Engine | Identifies downstream effects of any change |
| 2 | Unknowns Burn-down | Resolves the most valuable missing information |
| 3 | Duty-of-Care & Shuttle Planner | Improves safety and transportation coordination |
| 4 | Fest Pre-Mortem | Tests resilience before disruptions happen |
| 5 | Decision Explanation Cards | Makes decisions transparent |
| 6 | Minimal-Change Replanner | Prevents unnecessary operational disruption |
| 7 | Scenario Simulator | Tests changes before committing |
| 8 | Constraint Relaxation Ladder | Shows defensible alternatives |
| 9 | Risk Heatmap | Prioritizes important problems |
| 10 | Duplicate Reconciliation Workbench | Improves data accuracy |
| 11 | QR Merchandise Ledger | Prevents duplicate distribution |
| 12 | Vendor Fallback Intelligence | Maintains dietary and service coverage |
| 13 | Staff Shift Coverage | Detects staffing shortages |
| 14 | Offline-Tolerant Check-in | Handles unreliable connectivity |
| 15 | Natural-Language Command Bar | Simplifies operational interaction |
| 16 | Arrival and Meal Forecasting | Anticipates future resource demand |
| 17 | Broadcast Draft Generation | Improves coordination |
| 18 | Financial Intelligence | Tracks expenditure and settlement |
| 19 | Post-Fest Reporting | Provides an auditable festival summary |

**Strategic recommendation:** Make the Change Impact Engine the central intelligence layer, then build the three independent innovations—Fest Pre-Mortem, Unknowns Burn-down, and Duty-of-Care & Shuttle Planner—as distinct capabilities around the operational data and decision engine.

# 20. Important Implementation Clarifications

Before starting implementation in another chat, the following discrepancies and limitations must be considered.

1. The original narrative says approximately 2,400 participants, but the data contains 2,836 records and the contingent declarations total 2,842. Do not force the application to show exactly 2,400.
2. The planning engine generated two accommodation plans (cohesion-first and cost-first). The third balanced plan is a proposed requirement and still needs implementation.
3. The current schedule is not final. It has 987 unscheduled registrations and 28 unplaced later-round sessions.
4. The event dataset lacks original times and venue assignments. Any generated schedule must be labelled as an assumed plan.
5. The dataset does not contain judges, and 1,810 team-event registrations lack team IDs.
6. The current engine identifies 71 minors in external accommodation requiring guardian approval.
7. External properties lack verified accessibility and gender-segregation information. External accommodation should not automatically be considered suitable for every participant.
8. The vendor coverage data shows critical Jain, gluten-free, and nut-allergy gaps.
9. The data pack does not include a transportation dataset. Shuttle capacity and schedules must be marked as assumptions.
10. The external accommodation budget has not been provided. The system should use an adjustable budget parameter and display costs.
11. The accommodation algorithm's actual cleaning buffer is three hours, not the one-hour value proposed in an earlier conceptual assumption list.
12. The final system needs separate demand reporting for confirmed accommodation requests and unresolved/possible requests.
13. Duplicate candidates should be reviewed by an authorized human. Similar names alone are not reliable proof of duplicate identity.
14. A zero venue-overlap result does not establish that all participant, judge, volunteer, travel, and equipment conflicts have been resolved.
15. Vendor capacity should be evaluated by meal time, venue, and dietary category, not only as one overall aggregate.

# 21. Final Product Vision

FestOS should become an explainable, intelligent, and disruption-resilient festival operations platform.

It should operate using the following lifecycle:

```text
+------------------------------+
| 1. UNDERSTAND                 |
| Collect, verify and reconcile |
| festival information         |
+------------------------------+
               |
               v
+------------------------------+
| 2. ANALYZE                    |
| Understand resource          |
| constraints and dependencies |
+------------------------------+
               |
               v
+------------------------------+
| 3. PREDICT                    |
| Calculate risks, shortages   |
| and downstream impacts       |
+------------------------------+
               |
               v
+------------------------------+
| 4. DECIDE                     |
| Generate explainable plans   |
| and alternatives             |
+------------------------------+
               |
               v
+------------------------------+
| 5. APPROVE                    |
| Human authorization for      |
| important operational changes|
+------------------------------+
               |
               v
+------------------------------+
| 6. EXECUTE                    |
| Apply the decision and update|
| connected modules            |
+------------------------------+
               |
               v
+------------------------------+
| 7. VERIFY                     |
| Validate results, record     |
| decisions and preserve audit |
| history                      |
+------------------------------+
```

**The ultimate objective is to build a system that does not merely tell organizers what is happening, but helps them understand what could happen, what they should do, and what consequences their decisions will create.**

---

# END OF MASTER SPECIFICATION
