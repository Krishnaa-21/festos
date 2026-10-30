# API Specification: `reconciliation`

> Owner: `P1`  
> Base Path: `/api/v1/reconciliation`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The `reconciliation` module provides the single source of truth for participant counts and duplicate resolution across Aarohan (EPINOIA 2026).
Key functions:
- **Honest Reconciliation Waterfall**: Dissects the 2,836 (raw rosters) vs 2,842 (declared contingents) vs 2,400 (narrative planning) discrepancy without forcing artificial numbers.
- **Deterministic Deduplication Engine**: Detects potential duplicates using contingent/phonetic blocking and multi-signal RapidFuzz scoring (name, phone, college, age, overlapping events). Never flags `LIKELY` on name similarity alone.
- **Workbench Side-by-Side Review**: Compare duplicate candidates with linked event registrations and merchandise claims.
- **Reversible Merging**: Consolidates records into a canonical participant, repointing registrations and claims while saving the complete pre-merge state in `merge_record`. Blocks merge if conflicting merchandise claims exist.
- **Byte-Identical Undo**: Restores pre-merge participant, registration, and claim state exactly as it was.
- **Edge-Case Detection**: Identifies dual-role anomalies (leaders who compete, escorts who judge, core team staff appearing as participants).

---

## 2. Endpoints

### 2.1 `GET /api/v1/reconciliation/waterfall`
- **Description**: Returns the comprehensive counts panel and reconciliation waterfall explaining the gap between declared, raw, and narrative numbers.
- **Response `200 OK`**:
```json
{
  "data": {
    "counts": {
      "raw": 2836,
      "narrative_expected": 2400,
      "declared": 2842,
      "declared_vs_raw_gap": -6,
      "exact_duplicates": 0,
      "likely_duplicates": 7,
      "possible_duplicates": 305,
      "withdrawn": 0,
      "invalid": 3,
      "unresolved": 312,
      "quarantined": 0
    },
    "waterfall": [
      {
        "step": "DECLARED_TOTAL",
        "label": "Total Declared Across 38 Contingents",
        "count": 2842,
        "delta": 2842,
        "note": "Sum of strength_declared in contingents.csv"
      },
      {
        "step": "CONTINGENT_DEFICIT",
        "label": "Under-declared Contingent Gaps (C05, C18, C32)",
        "count": 2822,
        "delta": -20,
        "note": "C05 (-8), C18 (-5), C32 (-7) submitted fewer names than declared"
      },
      {
        "step": "CONTINGENT_SURPLUS",
        "label": "Over-declared Contingent Gaps (C02, C03, C09, C27)",
        "count": 2836,
        "delta": 14,
        "note": "C27 (+7), C09 (+5), C02 (+1), C03 (+1) submitted more names than declared"
      },
      {
        "step": "RAW_ROSTER_TOTAL",
        "label": "Raw Imported Participant Rosters",
        "count": 2836,
        "delta": 0,
        "note": "Exact count in participants.csv"
      },
      {
        "step": "INVALID_DATES",
        "label": "Invalid Departure Prior to Arrival",
        "count": 2833,
        "delta": -3,
        "note": "3 records have departure_datetime < arrival_datetime"
      },
      {
        "step": "LIKELY_DUPLICATES",
        "label": "High Confidence Duplicates to Review",
        "count": 2826,
        "delta": -7,
        "note": "Multi-signal matches (name + contact/age/registrations)"
      },
      {
        "step": "NARRATIVE_SURPLUS",
        "label": "Unexplained Surplus Over Narrative Baseline",
        "count": 2400,
        "delta": -426,
        "note": "Surplus roster participants over early planning narrative (2,400)"
      }
    ]
  },
  "meta": {},
  "warnings": [
    "7 contingents have strength discrepancies against submitted rosters."
  ]
}
```

---

### 2.2 `GET /api/v1/reconciliation/duplicates`
- **Description**: List identified duplicate candidate pairs filtered by confidence classification or status.
- **Query Parameters**:
  - `page` (int, default: 1)
  - `page_size` (int, default: 20)
  - `classification` (string, optional: `EXACT`, `LIKELY`, `POSSIBLE`)
  - `status` (string, optional: `PENDING`, `RESOLVED`, `IGNORED`)
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "dup_0102a",
        "participant_a_id": "P0412",
        "participant_b_id": "P1845",
        "participant_a_name": "Aditya Verma",
        "participant_b_name": "Aditya Verma",
        "college_a": "BITS Pilani",
        "college_b": "BITS Pilani",
        "score": 0.92,
        "classification": "LIKELY",
        "reasons": {
          "name_similarity": 1.0,
          "contingent_match": true,
          "phone_similarity": 0.9,
          "age_match": true,
          "overlapping_registrations": ["EV04"]
        },
        "status": "PENDING",
        "created_at": "2026-10-30T10:00:00Z"
      }
    ],
    "total": 7,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `GET /api/v1/reconciliation/compare`
- **Description**: Detailed side-by-side comparison of two participant records including registrations and merchandise claims.
- **Query Parameters**:
  - `id1` (string, required): First participant ID
  - `id2` (string, required): Second participant ID
- **Response `200 OK`**:
```json
{
  "data": {
    "participant_a": {
      "id": "P0412",
      "name": "Aditya Verma",
      "college": "BITS Pilani",
      "contingent_id": "C08",
      "phone": "+91 98765 11111",
      "email": "aditya@bits.edu",
      "status": "EXPECTED",
      "registrations": [
        {"event_id": "EV04", "name": "Debate", "team_id": null}
      ],
      "claims": []
    },
    "participant_b": {
      "id": "P1845",
      "name": "Aditya Verma",
      "college": "BITS Pilani",
      "contingent_id": "C08",
      "phone": "+91 98765 11111",
      "email": null,
      "status": "EXPECTED",
      "registrations": [
        {"event_id": "EV04", "name": "Debate", "team_id": null}
      ],
      "claims": []
    },
    "comparison": {
      "name_similarity": 1.0,
      "contingent_match": true,
      "phone_match": true,
      "merch_conflict": false,
      "can_merge": true
    }
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.4 `POST /api/v1/reconciliation/merge`
- **Description**: Merge a duplicate participant into a canonical participant via `ChangeService` (`participant.merge`).
  - Canonical record is updated with missing fields from the loser.
  - Loser record status is updated to `MERGED` and pointed to `canonical_participant_id`.
  - Linked registrations and claims are repointed to the canonical ID.
  - Complete pre-state is persisted in `merge_record` for byte-identical restoration.
  - **Fails with `422 CONSTRAINT_VIOLATION`** if both participants already have conflicting merchandise claims.
- **Headers**:
  - `Idempotency-Key` (required UUID)
- **Request Body**:
```json
{
  "expected_version": 1,
  "reason": "Duplicate verified: same college, phone, and event registration",
  "dry_run": false,
  "payload": {
    "canonical_id": "P0412",
    "merged_id": "P1845",
    "candidate_id": "dup_0102a"
  }
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "merge_record_id": "mrg_abc12345",
    "canonical_id": "P0412",
    "merged_id": "P1845",
    "repointed_registrations": 1,
    "repointed_claims": 0,
    "status": "APPLIED"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.5 `POST /api/v1/reconciliation/undo-merge/{merge_id}`
- **Description**: Revert a merge operation via `ChangeService` (`participant.undo_merge`), restoring both records, registrations, and claims to their exact byte-identical pre-merge state.
- **Headers**:
  - `Idempotency-Key` (required UUID)
- **Request Body**:
```json
{
  "reason": "Organiser identified distinct individuals upon desk review",
  "dry_run": false
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "merge_record_id": "mrg_abc12345",
    "restored_canonical_id": "P0412",
    "restored_participant_id": "P1845",
    "status": "REVERTED"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.6 `POST /api/v1/reconciliation/keep-separate`
- **Description**: Dismiss a duplicate candidate pair and record a decision not to merge.
- **Request Body**:
```json
{
  "candidate_id": "dup_0102a",
  "reason": "Verified through contingent leader: two different students with the same name"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "candidate_id": "dup_0102a",
    "status": "IGNORED"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.7 `GET /api/v1/reconciliation/flags`
- **Description**: Retrieve flagged operational edge cases across participants.
- **Response `200 OK`**:
```json
{
  "data": {
    "same_name_different_people": [
      {
        "name": "Rahul Sharma",
        "count": 4,
        "contingents": ["C01", "C12", "C22", "C35"],
        "note": "Distinct individuals with identical names across institutions"
      }
    ],
    "leaders_competing": [
      {
        "participant_id": "P0102",
        "name": "Rohan Deshmukh",
        "contingent_id": "C05",
        "registered_events": ["EV01"]
      }
    ],
    "escorts_judging": [],
    "staff_as_participants": [
      {
        "participant_id": "P0899",
        "name": "Kunal Singh",
        "staff_id": "ST14",
        "staff_role": "LOGISTICS_CREW"
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```
