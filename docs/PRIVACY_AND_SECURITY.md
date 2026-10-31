# FestOS Privacy, Security & Data Protection Architecture (`docs/PRIVACY_AND_SECURITY.md`)

> **Festival:** Aarohan (EPINOIA 2026, IIM Indore)  
> **Compliance & Standards:** Digital Personal Data Protection (DPDP) Act alignment, Zero-Trust Role-Based Access Control (RBAC), gateway-level field masking, cryptographic audit hash chains, and emergency break-glass elevation.

---

## 1. Zero-Trust Role Matrix & Permissions

FestOS strictly enforces principle-of-least-privilege across nine distinct operational roles. Permissions follow the format `<module>:<read|write|approve|export|sensitive>`.

| Role | Primary Scope | Sensitive Data Access | Key Restrictions |
|---|---|:---:|---|
| **`FESTIVAL_DIRECTOR`** | Full command cockpit, cross-module governance, policy oversight | Unmasked (Direct) | All actions logged to immutable audit ledger |
| **`ACCOMMODATION_LEAD`** | Hostels, external properties, room allocation, bed turnover | Corridors & Stays | Cannot alter financial budgets or event scoring |
| **`EVENT_LEAD`** | Event heats, venues, scheduling, judge and team rosters | Event Participants | Cannot access participant phone/email or room keys |
| **`LOGISTICS_MANAGER`** | Central Store, equipment requisitions, stage AV inventory | Asset Tags | No personal participant PII |
| **`MERCHANDISE_MANAGER`** | Kit quotas, sizing ledger, distribution counters | Entitlement Only | No contact details or accommodation data |
| **`FOOD_OPS_MANAGER`** | F&B vendors, meal slots, dietary matrix, hygiene compliance | Dietary Profiles | No room numbers, phone numbers, or academic records |
| **`FINANCE_MANAGER`** | Vendor settlements, emergency funds, budget ceilings | Contracts & Spend | No participant contact or accommodation data |
| **`VOLUNTEER`** | Desk mobile view: badge check-in & merchandise scanning | **STRICTLY MASKED** | Screen limited to name & contingent; phone/email stripped |
| **`AUDITOR`** | Read-only compliance, override registers, cryptographic verify | Read-Only Masked | Zero write or mutation capability across entire API |

### 1.1 Volunteer Mobile View Isolation
Student volunteers operate arrival gates and merchandise counters on shared mobile devices. To prevent unauthorized data exposure:
- The volunteer interface (`VolunteerMobileView.tsx`) exposes only two high-touch workflows: **Check-in Desk** and **Merchandise Counter**.
- Gateways strip email, phone number, medical/accessibility notes, and room allocations before serializing JSON to volunteer sessions.
- Audio cues (distinct success/error chimes) and high-contrast touch targets streamline operations without displaying personal rosters.

---

## 2. Gateway-Level Serializer Field Masking

Rather than relying on frontend view hiding, FestOS enforces deterministic data masking in backend Pydantic serializers (`app/core/masking.py`). Unprivileged actors receive sanitized tokens.

| Field | Raw Format | Masked Output | Purpose & Protection |
|---|---|---|---|
| **Phone Number** | `+91-8480737211` | `+91-8480***211` | Prevents unauthorized contact harvesting |
| **Email Address** | `meera.bose@iimindore.ac.in` | `m***@iimindore.ac.in` | Protects institutional student identity |
| **Guardian / Escort Phone** | `+91-9821034412` | `+91-9821***412` | Protects minor emergency contact records |
| **Medical / Accessibility** | `Wheelchair required / Asthma` | `SPECIAL_NEED_RECORDED` | Protects health data from general view |
| **Room Assignment** | `Room 102, Bed 1 (Hostel A)` | `CORRIDOR_ASSIGNED` | Protects student physical safety and whereabouts |

Field masking is automatically bypassed only when:
1. The actor holds the `FESTIVAL_DIRECTOR` role; or
2. The actor holds an active, unexpired **Break-Glass Elevation** grant.

---

## 3. Emergency Break-Glass Protocol

When life safety, medical emergencies, or police inquiries require immediate access to full unmasked PII, coordinators may invoke the **Break-Glass Elevation Protocol** (`POST /api/v1/auth/break-glass`).

```text
+-----------------------+     +------------------------+     +------------------------+
| 1. Emergency Trigger  | --> | 2. Mandatory Justify   | --> | 3. Cryptographic Audit |
| Coordinator requests  |     | Minimum 10-char reason |     | Immutable audit record |
| elevated PII access   |     | recorded into database |     | logged to SHA-256 chain|
+-----------------------+     +------------------------+     +------------------------+
                                                                         |
                                                                         v
+-----------------------+     +------------------------+     +------------------------+
| 6. Automatic Revoke   | <-- | 5. Unmasked Gateway    | <-- | 4. 15-Minute TTL Grant |
| Immediate return to   |     | Serializers permit full|     | Ephemeral token active |
| masked zero-trust     |     | medical/contact access |     | for exactly 15 minutes |
+-----------------------+     +------------------------+     +------------------------+
```

### 3.1 Break-Glass Safeguards
- **Mandatory Justification:** Requests with missing or trivial reasons (e.g. "need info") are rejected with `400 BAD_REQUEST`.
- **Ephemeral 15-Minute TTL:** Elevation grants automatically expire after exactly 900 seconds (`15 minutes`). Active countdown timer displays in the top navigation bar.
- **Forensic Attribution:** The requesting coordinator's ID, client IP, timestamp, and justification reason are committed to the cryptographic audit trail.

---

## 4. Cryptographic Append-Only Audit Ledger

FestOS treats audit logging not as an optional text log, but as a core database security primitive (`AuditEvent` table in SQLite/PostgreSQL).

### 4.1 SHA-256 Hash Chaining
Every mutating action committed through `ChangeService` appends an audit event linked to its predecessor:
$$\text{Current Hash} = \text{SHA-256}(\text{Previous Hash} \parallel \text{Timestamp} \parallel \text{Actor ID} \parallel \text{Action} \parallel \text{Entity ID} \parallel \text{Payload JSON})$$

- **Genesis Seed:** The initial migration seeds a known cryptographic genesis hash.
- **Verification Endpoint (`GET /api/v1/audit/verify`):** Traverses the entire chain from genesis to head, recalculating hashes. Any modified, inserted, or reordered record breaks the chain and triggers an immediate compliance alert.

### 4.2 Database Tamper Prevention
To prevent rogue direct SQL manipulation:
```sql
-- SQLite Database Triggers Preventing Audit Tampering
CREATE TRIGGER IF NOT EXISTS audit_prevent_update
BEFORE UPDATE ON audit_event
BEGIN
    SELECT RAISE(ABORT, 'SECURITY VIOLATION: audit_event records are strictly append-only and cannot be updated.');
END;

CREATE TRIGGER IF NOT EXISTS audit_prevent_delete
BEFORE DELETE ON audit_event
BEGIN
    SELECT RAISE(ABORT, 'SECURITY VIOLATION: audit_event records are strictly append-only and cannot be deleted.');
END;
```

---

## 5. Export Controls & CSV Protection

Mass data exfiltration via CSV downloads is a common festival security leak. FestOS enforces strict export governance:
- **Explicit Permission Gate:** Every report endpoint (e.g. `GET /api/v1/reports/export/{report_name}`) verifies that the caller's JWT token contains `<module>:export`.
- **Serializer Sanitization:** Exported CSVs respect the caller's role masking. Exporting as a Volunteer or Event Lead generates CSVs with masked phone numbers (`+91-8480***211`).
- **CSV Formula Injection Defense:** String values starting with `=`, `+`, `-`, or `@` are prefixed with an apostrophe `'` to prevent spreadsheet command execution (DDE injection).

---

## 6. What is NOT Protected (And Why)

To balance data protection with high-tempo festival execution, the following operational datasets are intentionally public within the internal network:

1. **Competition Heats & Stage Rosters:**
   - *Data:* Participant names, college names, team IDs, event titles, and stage schedules.
   - *Rationale:* Necessary for public venue displays, audio announcements, live scoring boards, and audience programs.
2. **Campus Facility & Venue Schedules:**
   - *Data:* Venue capacities, operating hours, and equipment deployments.
   - *Rationale:* Campus infrastructure is non-confidential operational information.
3. **Food Vendor Menus & Operating Hours:**
   - *Data:* Vendor trading names, dietary tags (Veg/Non-Veg/Jain), and meal slot capacity.
   - *Rationale:* Required for participant meal navigation and festival dining maps.
4. **Aggregated Operational KPIs:**
   - *Data:* Total checked-in counts, bed occupancy percentages, and meal redemption totals.
   - *Rationale:* Anonymous rollups are necessary for executive monitoring and contain zero identifying student PII.
