# FestOS Test Matrix & Invariant Verification (Spec Section 15)

**Specification Reference**: Spec Section 15 ("Testing and Reliability Requirements"), Section 8 ("Edge Cases That Must Be Handled"), and Section 20 ("Important Implementation Clarifications").  
**System State**: Verified on branch `p2/20-hardening`  
**Overall Status**: `100% PASS` (All invariants verified by automated regression, concurrency, and property test suites)

---

## 1. Accommodation Invariants

| Invariant / Bullet | Test File | Test Function(s) | Status | Enforced Invariant & Method |
|---|---|---|:---:|---|
| **Accessibility never violated** | `backend/tests/accommodation/test_accommodation_engine.py`<br>`backend/tests/hardening/test_property_engines.py` | `test_wheelchair_and_ground_floor_hard_rules`<br>`test_property_accommodation_invariants` | **PASS** | Hard Rule: Wheelchair users placed *only* in `accessible=True` rooms; ground-floor users placed *only* on `floor=0`. Ineligible rooms filtered before allocation. |
| **No capacity exceeded** | `backend/tests/accommodation/test_accommodation_engine.py`<br>`backend/tests/hardening/test_property_engines.py` | `test_hand_calculated_small_fixture`<br>`test_property_accommodation_invariants` | **PASS** | Simultaneous bed allocations within any room never exceed `room.capacity`. External properties bounded by verified contract beds. |
| **No bed double-booked** | `backend/tests/accommodation/test_accommodation_engine.py`<br>`backend/tests/test_model_constraints.py`<br>`backend/tests/hardening/test_concurrency_hardening.py` | `test_bed_timeline_unbook`<br>`test_stay_assignment_unique_active_bed_constraint`<br>`test_concurrent_same_bed_allocation_rejected` | **PASS** | Timeline intervals enforce disjoint stays per bed key. SQLite/Postgres unique active bed constraint and transactional ChangeService prevent concurrent double-booking. |
| **Cleaning respected** | `backend/tests/accommodation/test_accommodation_engine.py`<br>`backend/tests/accommodation/test_accommodation_ops.py` | `test_cleaning_interval_respected`<br>`test_turnaround_cleaning_buffer_respected` | **PASS** | Default 180-minute (`cleaning_buffer_minutes=180`) turnover window strictly enforced between checkout and subsequent checkin of the same bed. |
| **UNKNOWN housing never silently assigned** | `backend/tests/accommodation/test_accommodation_engine.py`<br>`backend/tests/unknowns/test_unknowns.py` | `test_unknown_never_silently_assigned`<br>`test_unknown_queue_ranked_by_count_times_criticality` | **PASS** | Participants with `gender="UNKNOWN"` or unknown housing preferences are *never* silently placed in gender-segregated dorms; quarantined with `GENDER_OR_HOUSING_UNKNOWN` reason. |
| **Every unplaced participant has a reason** | `backend/tests/accommodation/test_accommodation_api.py`<br>`backend/tests/accommodation/test_accommodation_engine.py`<br>`backend/tests/unknowns/test_voi_ranking.py` | `test_why_not_endpoint`<br>`test_unallocated_participants_have_reasons`<br>`test_why_not_counterfactuals` | **PASS** | Fixed taxonomy: `HARD_ACCESSIBILITY`, `GENDER_OR_HOUSING_UNKNOWN`, `TRANSPORT_RESTRICTED`, `NO_ELIGIBLE_PROPERTY`, `BUDGET`, `MISSING_INFO`, `CAPACITY`. Why-Not card explains counterfactual requirements. |

---

## 2. Scheduling Invariants

| Invariant / Bullet | Test File | Test Function(s) | Status | Enforced Invariant & Method |
|---|---|---|:---:|---|
| **No venue double-booking** | `backend/tests/schedule/test_conflicts.py`<br>`backend/tests/schedule/test_property_schedule.py` | `test_conflict_venue_double_booking`<br>`test_property_generated_schedules_invariants` | **PASS** | Venue intervals include 15-minute setup and 15-minute teardown buffers (`curr.end_at + 15m <= next.start_at - 15m`). Collisions trigger conflict records. |
| **No overlapping shared participants** | `backend/tests/schedule/test_conflicts.py`<br>`backend/tests/schedule/test_property_schedule.py`<br>`backend/tests/hardening/test_property_engines.py` | `test_conflict_participant_clash`<br>`test_property_generated_schedules_invariants`<br>`test_property_scheduling_invariants` | **PASS** | Participants enrolled in multiple events are verified for disjoint event windows (`p.end_at + travel_min <= next.start_at`). Clashes prevent concurrent placement. |
| **No insufficient travel windows** | `backend/tests/schedule/test_conflicts.py`<br>`backend/tests/schedule/test_cascades.py` | `test_conflict_insufficient_travel_time`<br>`test_downstream_session_push_cascade` | **PASS** | Travel matrix between distinct venues requires dynamic minimum travel time (default 15m or pairwise matrix lookup) for both participants and equipment. |
| **No equipment double allocation** | `backend/tests/schedule/test_conflicts.py`<br>`backend/tests/logistics/test_equipment_allocation.py` | `test_conflict_equipment_conflict`<br>`test_find_equipment_on_site_and_transfers` | **PASS** | Equipment ledger tracks active commitments per session. Shortages or simultaneous usage across distant venues flag equipment clash. |
| **No volunteer double assignment** | `backend/tests/schedule/test_conflicts.py`<br>`backend/tests/staff/test_staff_coverage.py` | `test_conflict_volunteer_double_booking`<br>`test_staff_shift_scheduling_and_overlap_detection` | **PASS** | Volunteer shifts enforce single-session presence; overlaps flagged immediately with alternative volunteer suggestions. |
| **Nothing outside venue hours** | `backend/tests/schedule/test_conflicts.py`<br>`backend/tests/schedule/test_conflicts.py` | `test_conflict_operating_hour_conflict`<br>`test_zero_venue_overlaps_is_never_reported_as_zero_conflicts` | **PASS** | Sessions must start and end within venue operating window (e.g. 08:00 - 22:00); late sessions trigger `VENUE_OPERATING_HOURS_VIOLATION`. |

---

## 3. Inventory & Merchandise Invariants

| Invariant / Bullet | Test File | Test Function(s) | Status | Enforced Invariant & Method |
|---|---|---|:---:|---|
| **Movements balance** | `backend/tests/logistics/test_ledger_maths.py` | `test_ledger_balance_consistency_check`<br>`test_stock_bucket_projection_formula` | **PASS** | Double-entry movement ledger: `on_hand = initial + received - issued - damaged - in_transit`. Balance checked on every transfer. |
| **Reserved stock never issued twice** | `backend/tests/logistics/test_ledger_maths.py`<br>`backend/tests/merchandise/test_merchandise_policy.py` | `test_stock_bucket_projection_formula`<br>`test_reserved_stock_never_issued_twice` | **PASS** | Available to issue is strictly `on_hand - reserved`. Reserved allocations lock items until explicit claim or cancellation. |
| **In-transit not counted twice** | `backend/tests/logistics/test_ledger_maths.py` | `test_in_transit_counted_at_neither_endpoint` | **PASS** | Stock in transit between location A and B is deducted from location A immediately and only credited to location B upon verified receipt (`status="RECEIVED"`). |
| **Damaged unavailable** | `backend/tests/logistics/test_ledger_maths.py`<br>`backend/tests/logistics/test_equipment_allocation.py` | `test_damaged_stock_unavailable`<br>`test_damaged_equipment_unavailable` | **PASS** | Items with `condition="damaged"` or moved to damaged bucket are filtered out of allocation algorithms. |
| **Duplicate merchandise claims yield one success** | `backend/tests/merchandise/test_issuance_concurrency.py`<br>`backend/tests/hardening/test_concurrency_hardening.py` | `test_concurrent_issuance_produces_exactly_one_success`<br>`test_duplicate_qr_scan_yields_already_issued_with_original_details` | **PASS** | DB unique constraint on `(canonical_participant_id, item_id)` combined with transactional issuance guarantees exactly one 200 OK and subsequent 409 `ALREADY_ISSUED`. |

---

## 4. Data Integrity & Ingestion Invariants

| Invariant / Bullet | Test File | Test Function(s) | Status | Enforced Invariant & Method |
|---|---|---|:---:|---|
| **Malformed CSV** | `backend/tests/imports/test_importer_engine.py`<br>`backend/tests/hardening/test_validation_hardening.py` | `test_malformed_csv_error`<br>`test_corrupted_csv_delimiters_and_encoding_quarantined` | **PASS** | Tolerant CSV engine handles unclosed quotes, broken delimiters, BOM characters, raising clean `MalformedCSVError` (422) instead of server 500. |
| **Missing columns** | `backend/tests/imports/test_importer_engine.py`<br>`backend/tests/hardening/test_validation_hardening.py` | `test_missing_required_columns`<br>`test_corrupted_missing_columns_quarantined_with_actionable_error` | **PASS** | Validates required schema columns against known aliases; missing critical columns abort promotion with actionable `MissingColumnsError`. |
| **Quarantine** | `backend/tests/imports/test_import_pipeline.py`<br>`backend/tests/imports/test_importer_engine.py` | `test_import_and_promote_pipeline`<br>`test_quarantine_rows_carry_reasons` | **PASS** | Corrupt rows (invalid dates, negative ages, bad numbers) are isolated into `quarantine_row` with human-readable error reasons; valid rows continue to staging. |
| **UNKNOWN stays UNKNOWN** | `backend/tests/imports/test_importer_engine.py`<br>`backend/tests/unknowns/test_unknowns.py` | `test_unknown_stays_unknown`<br>`test_field_verification_through_change_service` | **PASS** | Missing values are explicitly recorded as literal `"UNKNOWN"` string, never converted to `False`, `None`, empty string, or arbitrary default. |
| **Merges reversible** | `backend/tests/reconciliation/test_reconciliation.py`<br>`backend/tests/participants/test_participants.py` | `test_merge_and_byte_identical_undo_merge`<br>`test_participant_merge_and_revert_via_change_service` | **PASS** | `merge_record` captures byte-identical pre-merge snapshot of registrations, merch claims, and stays; `undo_merge` restores canonical and secondary states perfectly. |
| **Raw records preserved** | `backend/tests/imports/test_importer_engine.py`<br>`backend/tests/imports/test_import_pipeline.py` | `test_raw_records_preserved_byte_for_byte`<br>`test_idempotent_reimport` | **PASS** | Ingested files are stored immutable in `raw_record` with SHA-256 row hashes; canonical tables reference `source_row_id`. |

---

## 5. System, Security & Reliability Invariants

| Invariant / Bullet | Test File | Test Function(s) | Status | Enforced Invariant & Method |
|---|---|---|:---:|---|
| **RBAC enforced** | `backend/tests/test_security_p3.py`<br>`backend/tests/hardening/test_security_review.py` | `test_rbac_allow_deny_matrix`<br>`test_all_endpoints_enforce_rbac_or_authentication` | **PASS** | 9-role permission matrix enforced by `@require_permission` on every mutating and sensitive route. Unauthorized calls return 403 `FORBIDDEN`. |
| **Sensitive data masked** | `backend/tests/test_security_p3.py`<br>`backend/tests/hardening/test_security_review.py` | `test_masking_per_role`<br>`test_pii_never_leaks_in_serializers_or_error_messages` | **PASS** | Phone, email, medical notes, room numbers masked for unauthorized roles (e.g. Volunteer, Auditor) via `core.masking`. Unmasked only via scoped break-glass. |
| **Changes audited** | `backend/tests/test_change_service.py`<br>`backend/tests/test_security_p3.py` | `test_change_service_success`<br>`test_audit_hash_chain_verification` | **PASS** | Every mutation via `ChangeService` appends an immutable `AuditEvent` and `ChangeSet` with SHA-256 cryptographic prev_hash chaining. |
| **Concurrent updates use version checks** | `backend/tests/test_change_service.py`<br>`backend/tests/hardening/test_concurrency_hardening.py` | `test_change_service_version_conflict`<br>`test_concurrent_record_edit_optimistic_locking` | **PASS** | `ChangeRequest.expected_version` matches entity `version`. Stale concurrent updates reject with 409 `VERSION_CONFLICT`. |
| **Failed transactions leave no partial state** | `backend/tests/test_change_service.py`<br>`backend/tests/hardening/test_concurrency_hardening.py` | `test_change_service_rollback_leaves_no_partial_state`<br>`test_fault_injection_handler_exception_clean_rollback` | **PASS** | Mid-transaction exceptions trigger full atomic rollback of entity modifications, ChangeSets, and audit entries. |
| **Seed reset works** | `backend/tests/hardening/test_determinism.py`<br>`scripts/backup_restore.py` | `test_seed_reset_idempotent_and_deterministic`<br>`test_snapshot_and_restore_cycle` | **PASS** | `make reset` / `python -m app.seed reset` clears state, recreates schema, and reliably loads base fixtures with identical row counts and hashes. |
| **Golden tests reproduce outputs** | `backend/tests/reports/test_golden_outputs.py`<br>`backend/tests/accommodation/test_accommodation_engine.py` | `test_golden_outputs_exist_and_regression_stable`<br>`test_golden_run_data_pack` | **PASS** | Real data pack generates known reference metrics: peak bed demand ~1,601 at 30 Oct 18:00, 20 Section 14 CSV files with exact schema headers. |
