# FestOS Complete REST API Specification Index (`docs/API.md`)

> **Title:** FestOS API  
> **Version:** 0.1.0  
> **Total Registered Endpoints:** 215 distinct paths, 240 HTTP operations across 32 modules  
> **Format:** OpenAPI 3.1.0 compliant  

---

## 1. Architectural & API Conventions

- **Base Path:** `/api/v1/<module>` (with root aliases mounted for key operational routes).
- **Standard Response Envelope:**
  ```json
  {
    "data": { ... },
    "meta": { "total": 100, "page": 1, "page_size": 20 },
    "warnings": []
  }
  ```
- **Standard Error Envelope:**
  ```json
  {
    "error": {
      "code": "CONSTRAINT_VIOLATION",
      "message": "Human-readable explanation",
      "details": [ { "code": "CAPACITY_EXCEEDED", "path": "room_id", "hard": true } ],
      "request_id": "req_8f1b3c9d"
    }
  }
  ```
- **Mutating Actions via ChangeService:** Every write operation generates an immutable `ChangeSet` and `AuditEvent` record.
- **Idempotency & Optimistic Concurrency:**
  - Header `Idempotency-Key: <uuid>` prevents duplicate network retries.
  - Body `expected_version: <int>` guards against concurrent write race conditions (`409 VERSION_CONFLICT`).
- **Dry-Run Support:** Query param or body flag `dry_run=true` returns downstream impact preview without committing state.
- **Authentication:** Bearer token (`Authorization: Bearer <JWT>`) or testing headers (`X-Actor-Role`, `X-Actor-Id`).

---

## 2. Table of Contents & Module Directory

- [Accommodation](#accommodation) (22 endpoints)
- [Approvals](#approvals) (5 endpoints)
- [Assumptions](#assumptions) (6 endpoints)
- [Audit](#audit) (4 endpoints)
- [Auth](#auth) (6 endpoints)
- [Checkin](#checkin) (9 endpoints)
- [Commands](#commands) (3 endpoints)
- [Contingents](#contingents) (4 endpoints)
- [Data Quality](#data-quality) (1 endpoints)
- [Events](#events) (11 endpoints)
- [Example Flow](#example-flow) (1 endpoints)
- [Finance & Commercials](#finance-&-commercials) (11 endpoints)
- [Food Operations](#food-operations) (5 endpoints)
- [Imports](#imports) (5 endpoints)
- [Notification Engine](#notification-engine) (9 endpoints)
- [Overrides](#overrides) (3 endpoints)
- [Participants](#participants) (7 endpoints)
- [Reconciliation](#reconciliation) (8 endpoints)
- [Reports](#reports) (4 endpoints)
- [Schedule](#schedule) (12 endpoints)
- [System](#system) (2 endpoints)
- [Unknowns](#unknowns) (9 endpoints)
- [Vendors](#vendors) (8 endpoints)
- [Venues](#venues) (8 endpoints)
- [dashboard](#dashboard) (3 endpoints)
- [decisions](#decisions) (4 endpoints)
- [forecasting](#forecasting) (7 endpoints)
- [impact](#impact) (2 endpoints)
- [incidents](#incidents) (2 endpoints)
- [logistics](#logistics) (15 endpoints)
- [merchandise](#merchandise) (7 endpoints)
- [premortem](#premortem) (7 endpoints)
- [scenarios](#scenarios) (8 endpoints)
- [staff](#staff) (10 endpoints)
- [transport](#transport) (12 endpoints)

---

## 3. Module Operations Registry

### <a id="accommodation"></a>Accommodation

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`POST`** | `/api/v1/accommodation/assignments/manual` | Manual Assignment Endpoint | `manual_assignment_endpoint_api_v1_accommodation_assignments_manual_post` |
| **`GET`** | `/api/v1/accommodation/decision-cards/{plan_id}` | Get Plan Decision Card | `get_plan_decision_card_api_v1_accommodation_decision_cards__plan_id__get` |
| **`GET`** | `/api/v1/accommodation/demand-timeline` | Get Bed Demand Timeline View | `get_bed_demand_timeline_view_api_v1_accommodation_demand_timeline_get` |
| **`POST`** | `/api/v1/accommodation/generate-plan` | Generate Candidate Plans | `generate_candidate_plans_api_v1_accommodation_generate_plan_post` |
| **`GET`** | `/api/v1/accommodation/plans` | List Candidate Plans | `list_candidate_plans_api_v1_accommodation_plans_get` |
| **`GET`** | `/api/v1/accommodation/plans/compare` | Compare Candidate Plans | `compare_candidate_plans_api_v1_accommodation_plans_compare_get` |
| **`POST`** | `/api/v1/accommodation/plans/generate` | Generate Candidate Plans | `generate_candidate_plans_api_v1_accommodation_plans_generate_post` |
| **`GET`** | `/api/v1/accommodation/plans/live` | Get Live Plan Endpoint | `get_live_plan_endpoint_api_v1_accommodation_plans_live_get` |
| **`POST`** | `/api/v1/accommodation/plans/live/allocate-incremental` | Allocate Incremental Endpoint | `allocate_incremental_endpoint_api_v1_accommodation_plans_live_allocate_incremental_post` |
| **`POST`** | `/api/v1/accommodation/plans/live/freeze` | Freeze Live Plan Endpoint | `freeze_live_plan_endpoint_api_v1_accommodation_plans_live_freeze_post` |
| **`GET`** | `/api/v1/accommodation/plans/{id}` | Get Plan Detail | `get_plan_detail_api_v1_accommodation_plans__id__get` |
| **`POST`** | `/api/v1/accommodation/plans/{id}/commit` | Commit Candidate Plan Endpoint | `commit_candidate_plan_endpoint_api_v1_accommodation_plans__id__commit_post` |
| **`GET`** | `/api/v1/accommodation/plans/{id}/shortages` | Get Shortages | `get_shortages_api_v1_accommodation_plans__id__shortages_get` |
| **`GET`** | `/api/v1/accommodation/properties` | List External Properties | `list_external_properties_api_v1_accommodation_properties_get` |
| **`PATCH`** | `/api/v1/accommodation/properties/{id}` | Update Property Endpoint | `update_property_endpoint_api_v1_accommodation_properties__id__patch` |
| **`POST`** | `/api/v1/accommodation/repair` | Repair Accommodation Endpoint | `repair_accommodation_endpoint_api_v1_accommodation_repair_post` |
| **`GET`** | `/api/v1/accommodation/reports/{report_name}` | Download Accommodation Report | `download_accommodation_report_api_v1_accommodation_reports__report_name__get` |
| **`GET`** | `/api/v1/accommodation/rooms` | List On Campus Rooms | `list_on_campus_rooms_api_v1_accommodation_rooms_get` |
| **`PATCH`** | `/api/v1/accommodation/rooms/{id}` | Update Room Endpoint | `update_room_endpoint_api_v1_accommodation_rooms__id__patch` |
| **`POST`** | `/api/v1/accommodation/rooms/{id}/cleaning-complete` | Complete Cleaning Endpoint | `complete_cleaning_endpoint_api_v1_accommodation_rooms__id__cleaning_complete_post` |
| **`GET`** | `/api/v1/accommodation/shortages` | Get Shortages | `get_shortages_api_v1_accommodation_shortages_get` |
| **`GET`** | `/api/v1/accommodation/why-not/{participant_id}` | Get Why Not Diagnosis | `get_why_not_diagnosis_api_v1_accommodation_why_not__participant_id__get` |

### <a id="approvals"></a>Approvals

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/approvals` | List Approvals | `list_approvals_api_v1_approvals_get` |
| **`GET`** | `/api/v1/approvals/policies` | Get Approval Policies | `get_approval_policies_api_v1_approvals_policies_get` |
| **`GET`** | `/api/v1/approvals/{id}` | Get Approval Detail | `get_approval_detail_api_v1_approvals__id__get` |
| **`POST`** | `/api/v1/approvals/{id}/approve` | Post Approve | `post_approve_api_v1_approvals__id__approve_post` |
| **`POST`** | `/api/v1/approvals/{id}/reject` | Post Reject | `post_reject_api_v1_approvals__id__reject_post` |

### <a id="assumptions"></a>Assumptions

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/assumptions` | Get Assumptions | `get_assumptions_api_v1_assumptions_get` |
| **`PUT`** | `/api/v1/assumptions` | Put Update Assumption | `put_update_assumption_api_v1_assumptions_put` |
| **`GET`** | `/api/v1/assumptions/{key}` | Get Assumption By Key | `get_assumption_by_key_api_v1_assumptions__key__get` |
| **`PUT`** | `/api/v1/assumptions/{key}` | Put Update Assumption By Key | `put_update_assumption_by_key_api_v1_assumptions__key__put` |
| **`GET`** | `/api/v1/assumptions/{key}/dependents` | Get Assumption Module Dependents | `get_assumption_module_dependents_api_v1_assumptions__key__dependents_get` |
| **`GET`** | `/api/v1/assumptions/{key}/history` | Get Assumption Change History | `get_assumption_change_history_api_v1_assumptions__key__history_get` |

### <a id="audit"></a>Audit

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/audit/events` | List Audit Events | `list_audit_events_api_v1_audit_events_get` |
| **`GET`** | `/api/v1/audit/export/csv` | Export Audit Csv | `export_audit_csv_api_v1_audit_export_csv_get` |
| **`GET`** | `/api/v1/audit/timeline/{entity_type}/{entity_id}` | Get Entity Timeline | `get_entity_timeline_api_v1_audit_timeline__entity_type___entity_id__get` |
| **`GET`** | `/api/v1/audit/verify` | Verify Audit Hash Chain | `verify_audit_hash_chain_api_v1_audit_verify_get` |

### <a id="auth"></a>Auth

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/auth/break-glass` | List Break Glass Grants | `list_break_glass_grants_api_v1_auth_break_glass_get` |
| **`POST`** | `/api/v1/auth/break-glass` | Post Break Glass | `post_break_glass_api_v1_auth_break_glass_post` |
| **`POST`** | `/api/v1/auth/login` | Post Login | `post_login_api_v1_auth_login_post` |
| **`GET`** | `/api/v1/auth/me` | Get Me | `get_me_api_v1_auth_me_get` |
| **`GET`** | `/api/v1/auth/permissions` | Get Permissions | `get_permissions_api_v1_auth_permissions_get` |
| **`POST`** | `/api/v1/auth/refresh` | Post Refresh | `post_refresh_api_v1_auth_refresh_post` |

### <a id="checkin"></a>Checkin

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/checkin/board` | Get Checkin Board | `get_checkin_board_api_v1_checkin_board_get` |
| **`POST`** | `/api/v1/checkin/checkin` | Checkin Endpoint | `checkin_endpoint_api_v1_checkin_checkin_post` |
| **`POST`** | `/api/v1/checkin/checkout` | Checkout Endpoint | `checkout_endpoint_api_v1_checkin_checkout_post` |
| **`GET`** | `/api/v1/checkin/participant/{id}` | Get Participant Detail Endpoint | `get_participant_detail_endpoint_api_v1_checkin_participant__id__get` |
| **`PATCH`** | `/api/v1/checkin/participant/{id}/arrival` | Update Arrival Endpoint | `update_arrival_endpoint_api_v1_checkin_participant__id__arrival_patch` |
| **`GET`** | `/api/v1/checkin/reallocations/suggestions` | Get Reallocation Suggestions Endpoint | `get_reallocation_suggestions_endpoint_api_v1_checkin_reallocations_suggestions_get` |
| **`GET`** | `/api/v1/checkin/search` | Search Participants Endpoint | `search_participants_endpoint_api_v1_checkin_search_get` |
| **`POST`** | `/api/v1/checkin/sync` | Sync Offline Batch Endpoint | `sync_offline_batch_endpoint_api_v1_checkin_sync_post` |
| **`POST`** | `/api/v1/checkin/verify-arrival` | Checkin Endpoint | `checkin_endpoint_api_v1_checkin_verify_arrival_post` |

### <a id="commands"></a>Commands

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/commands` | List Command Intents | `list_command_intents_api_v1_commands_get` |
| **`POST`** | `/api/v1/commands/execute` | Execute Structured Command | `execute_structured_command_api_v1_commands_execute_post` |
| **`POST`** | `/api/v1/commands/parse` | Parse Natural Command | `parse_natural_command_api_v1_commands_parse_post` |

### <a id="contingents"></a>Contingents

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/contingents` | Get Contingents List | `get_contingents_list_api_v1_contingents_get` |
| **`GET`** | `/api/v1/contingents/{id}` | Get Contingent Profile | `get_contingent_profile_api_v1_contingents__id__get` |
| **`PATCH`** | `/api/v1/contingents/{id}` | Update Contingent Profile | `update_contingent_profile_api_v1_contingents__id__patch` |
| **`GET`** | `/api/v1/contingents/{id}/status` | Get Contingent Operational Status | `get_contingent_operational_status_api_v1_contingents__id__status_get` |

### <a id="data-quality"></a>Data Quality

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/data-quality` | Get Data Quality | `get_data_quality_api_v1_data_quality_get` |

### <a id="events"></a>Events

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/events` | Get All Events | `get_all_events_api_v1_events_get` |
| **`POST`** | `/api/v1/events` | Create Event | `create_event_api_v1_events_post` |
| **`GET`** | `/api/v1/events/judges` | Get Judges | `get_judges_api_v1_events_judges_get` |
| **`POST`** | `/api/v1/events/judges` | Create Judge | `create_judge_api_v1_events_judges_post` |
| **`GET`** | `/api/v1/events/teams/provisional` | Get Provisional Team Reconciliation | `get_provisional_team_reconciliation_api_v1_events_teams_provisional_get` |
| **`GET`** | `/api/v1/events/{event_id}` | Get Event | `get_event_api_v1_events__event_id__get` |
| **`PUT`** | `/api/v1/events/{event_id}` | Update Event | `update_event_api_v1_events__event_id__put` |
| **`POST`** | `/api/v1/events/{event_id}/cancel` | Cancel Event | `cancel_event_api_v1_events__event_id__cancel_post` |
| **`POST`** | `/api/v1/events/{event_id}/extend-duration` | Extend Event Duration | `extend_event_duration_api_v1_events__event_id__extend_duration_post` |
| **`POST`** | `/api/v1/events/{event_id}/merge` | Merge Event | `merge_event_api_v1_events__event_id__merge_post` |
| **`GET`** | `/api/v1/events/{event_id}/registrations` | Get Registrations | `get_registrations_api_v1_events__event_id__registrations_get` |

### <a id="example-flow"></a>Example Flow

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`POST`** | `/api/v1/_example/items` | Post Create Example Item | `post_create_example_item_api_v1__example_items_post` |

### <a id="finance-&-commercials"></a>Finance & Commercials

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/finance/accommodation-spend` | Get Accommodation Spend Endpoint | `get_accommodation_spend_endpoint_api_v1_finance_accommodation_spend_get` |
| **`GET`** | `/api/v1/finance/budget-overrides-report` | Get Overrides Report Endpoint | `get_overrides_report_endpoint_api_v1_finance_budget_overrides_report_get` |
| **`POST`** | `/api/v1/finance/budget/set` | Set Budget Endpoint | `set_budget_endpoint_api_v1_finance_budget_set_post` |
| **`GET`** | `/api/v1/finance/emergency-spend` | Get Emergency Spend Endpoint | `get_emergency_spend_endpoint_api_v1_finance_emergency_spend_get` |
| **`POST`** | `/api/v1/finance/emergency-spend` | Propose Emergency Spend Endpoint | `propose_emergency_spend_endpoint_api_v1_finance_emergency_spend_post` |
| **`GET`** | `/api/v1/finance/merchandise-costs` | Get Merchandise Costs Endpoint | `get_merchandise_costs_endpoint_api_v1_finance_merchandise_costs_get` |
| **`GET`** | `/api/v1/finance/overrides-report` | Get Overrides Report Endpoint | `get_overrides_report_endpoint_api_v1_finance_overrides_report_get` |
| **`GET`** | `/api/v1/finance/summary` | Get Finance Summary Endpoint | `get_finance_summary_endpoint_api_v1_finance_summary_get` |
| **`GET`** | `/api/v1/finance/vendor-settlements` | Get Vendor Settlements Endpoint | `get_vendor_settlements_endpoint_api_v1_finance_vendor_settlements_get` |
| **`POST`** | `/api/v1/finance/vendor-settlements/{id}/dispute` | Open Dispute Endpoint | `open_dispute_endpoint_api_v1_finance_vendor_settlements__id__dispute_post` |
| **`POST`** | `/api/v1/finance/vendor-settlements/{id}/pay` | Record Payment Endpoint | `record_payment_endpoint_api_v1_finance_vendor_settlements__id__pay_post` |

### <a id="food-operations"></a>Food Operations

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/food/compliance` | Get Food Compliance Endpoint | `get_food_compliance_endpoint_api_v1_food_compliance_get` |
| **`GET`** | `/api/v1/food/compliance-flags` | Get Food Compliance Endpoint | `get_food_compliance_endpoint_api_v1_food_compliance_flags_get` |
| **`GET`** | `/api/v1/food/coverage` | Get Food Coverage Endpoint | `get_food_coverage_endpoint_api_v1_food_coverage_get` |
| **`GET`** | `/api/v1/food/meal-slots` | List Meal Slots Endpoint | `list_meal_slots_endpoint_api_v1_food_meal_slots_get` |
| **`GET`** | `/api/v1/food/slots` | List Meal Slots Endpoint | `list_meal_slots_endpoint_api_v1_food_slots_get` |

### <a id="imports"></a>Imports

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/imports` | Get Import History | `get_import_history_api_v1_imports_get` |
| **`POST`** | `/api/v1/imports` | Upload Import File | `upload_import_file_api_v1_imports_post` |
| **`GET`** | `/api/v1/imports/{id}` | Get Import Batch Details | `get_import_batch_details_api_v1_imports__id__get` |
| **`GET`** | `/api/v1/imports/{id}/issues` | Get Import Batch Issues | `get_import_batch_issues_api_v1_imports__id__issues_get` |
| **`POST`** | `/api/v1/imports/{id}/promote` | Post Promote Import Batch | `post_promote_import_batch_api_v1_imports__id__promote_post` |

### <a id="notification-engine"></a>Notification Engine

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/notifications/drafts` | List Drafts Endpoint | `list_drafts_endpoint_api_v1_notifications_drafts_get` |
| **`POST`** | `/api/v1/notifications/drafts/generate` | Generate Drafts Endpoint | `generate_drafts_endpoint_api_v1_notifications_drafts_generate_post` |
| **`GET`** | `/api/v1/notifications/drafts/{id}` | Get Draft Endpoint | `get_draft_endpoint_api_v1_notifications_drafts__id__get` |
| **`PATCH`** | `/api/v1/notifications/drafts/{id}` | Update Draft Endpoint | `update_draft_endpoint_api_v1_notifications_drafts__id__patch` |
| **`PUT`** | `/api/v1/notifications/drafts/{id}` | Update Draft Endpoint | `update_draft_endpoint_api_v1_notifications_drafts__id__put` |
| **`POST`** | `/api/v1/notifications/drafts/{id}/approve` | Approve Draft Endpoint | `approve_draft_endpoint_api_v1_notifications_drafts__id__approve_post` |
| **`POST`** | `/api/v1/notifications/drafts/{id}/send` | Send Draft Endpoint | `send_draft_endpoint_api_v1_notifications_drafts__id__send_post` |
| **`GET`** | `/api/v1/notifications/log` | Get Log Endpoint | `get_log_endpoint_api_v1_notifications_log_get` |
| **`GET`** | `/api/v1/notifications/templates` | List Templates Endpoint | `list_templates_endpoint_api_v1_notifications_templates_get` |

### <a id="overrides"></a>Overrides

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/overrides` | List Overrides | `list_overrides_api_v1_overrides_get` |
| **`POST`** | `/api/v1/overrides` | Post Create Override | `post_create_override_api_v1_overrides_post` |
| **`GET`** | `/api/v1/overrides/{id}` | Get Override Detail | `get_override_detail_api_v1_overrides__id__get` |

### <a id="participants"></a>Participants

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/participants` | Get Participants | `get_participants_api_v1_participants_get` |
| **`POST`** | `/api/v1/participants` | Create Participant | `create_participant_api_v1_participants_post` |
| **`GET`** | `/api/v1/participants/{id}` | Get Participant By Id | `get_participant_by_id_api_v1_participants__id__get` |
| **`PATCH`** | `/api/v1/participants/{id}` | Update Participant | `update_participant_api_v1_participants__id__patch` |
| **`GET`** | `/api/v1/participants/{id}/360` | Get Participant 360 View | `get_participant_360_view_api_v1_participants__id__360_get` |
| **`POST`** | `/api/v1/participants/{id}/status` | Transition Status | `transition_status_api_v1_participants__id__status_post` |
| **`GET`** | `/api/v1/participants/{id}/timeline` | Get Participant Timeline | `get_participant_timeline_api_v1_participants__id__timeline_get` |

### <a id="reconciliation"></a>Reconciliation

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/reconciliation/compare` | Get Duplicate Comparison | `get_duplicate_comparison_api_v1_reconciliation_compare_get` |
| **`GET`** | `/api/v1/reconciliation/duplicates` | Get Duplicate Candidates | `get_duplicate_candidates_api_v1_reconciliation_duplicates_get` |
| **`GET`** | `/api/v1/reconciliation/flags` | Get Operational Edge Case Flags | `get_operational_edge_case_flags_api_v1_reconciliation_flags_get` |
| **`GET`** | `/api/v1/reconciliation/history` | Get Merge Audit History | `get_merge_audit_history_api_v1_reconciliation_history_get` |
| **`POST`** | `/api/v1/reconciliation/keep-separate` | Keep Separate Decision | `keep_separate_decision_api_v1_reconciliation_keep_separate_post` |
| **`POST`** | `/api/v1/reconciliation/merge` | Merge Duplicate Participants | `merge_duplicate_participants_api_v1_reconciliation_merge_post` |
| **`POST`** | `/api/v1/reconciliation/undo-merge/{merge_id}` | Undo Merge Operation | `undo_merge_operation_api_v1_reconciliation_undo_merge__merge_id__post` |
| **`GET`** | `/api/v1/reconciliation/waterfall` | Get Reconciliation Waterfall | `get_reconciliation_waterfall_api_v1_reconciliation_waterfall_get` |

### <a id="reports"></a>Reports

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/reports` | List Reports | `list_reports_api_v1_reports_get` |
| **`GET`** | `/api/v1/reports/bundle.zip` | Download Reports Bundle | `download_reports_bundle_api_v1_reports_bundle_zip_get` |
| **`GET`** | `/api/v1/reports/post-festival` | Get Post Festival Summary | `get_post_festival_summary_api_v1_reports_post_festival_get` |
| **`GET`** | `/api/v1/reports/{name}` | Download Report | `download_report_api_v1_reports__name__get` |

### <a id="schedule"></a>Schedule

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/schedule/conflicts` | Get Conflicts | `get_conflicts_api_v1_schedule_conflicts_get` |
| **`POST`** | `/api/v1/schedule/conflicts/{conflict_id}/apply-resolution` | Apply Resolution | `apply_resolution_api_v1_schedule_conflicts__conflict_id__apply_resolution_post` |
| **`GET`** | `/api/v1/schedule/conflicts/{conflict_id}/resolutions` | Get Resolutions For Conflict | `get_resolutions_for_conflict_api_v1_schedule_conflicts__conflict_id__resolutions_get` |
| **`POST`** | `/api/v1/schedule/generate` | Post Generate Schedule | `post_generate_schedule_api_v1_schedule_generate_post` |
| **`GET`** | `/api/v1/schedule/sessions` | Get Sessions | `get_sessions_api_v1_schedule_sessions_get` |
| **`POST`** | `/api/v1/schedule/sessions/{session_id}/change-venue` | Change Session Venue | `change_session_venue_api_v1_schedule_sessions__session_id__change_venue_post` |
| **`POST`** | `/api/v1/schedule/sessions/{session_id}/move` | Move Session | `move_session_api_v1_schedule_sessions__session_id__move_post` |
| **`GET`** | `/api/v1/schedule/timeline` | Get Gantt Timeline | `get_gantt_timeline_api_v1_schedule_timeline_get` |
| **`GET`** | `/api/v1/schedule/unscheduled` | Get Unscheduled Entrants Endpoint | `get_unscheduled_entrants_endpoint_api_v1_schedule_unscheduled_get` |
| **`GET`** | `/api/v1/schedule/versions` | Get Versions | `get_versions_api_v1_schedule_versions_get` |
| **`GET`** | `/api/v1/schedule/versions/{version_id}` | Get Version | `get_version_api_v1_schedule_versions__version_id__get` |
| **`POST`** | `/api/v1/schedule/versions/{version_id}/restore` | Restore Version | `restore_version_api_v1_schedule_versions__version_id__restore_post` |

### <a id="system"></a>System

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/meta` | Get Meta | `get_meta_api_v1_meta_get` |
| **`GET`** | `/health` | Get Health | `get_health_health_get` |

### <a id="unknowns"></a>Unknowns

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`POST`** | `/api/v1/unknowns/confirm/{token}` | Submit Token Confirmation | `submit_token_confirmation_api_v1_unknowns_confirm__token__post` |
| **`POST`** | `/api/v1/unknowns/confirmation-requests` | Create Batched Confirmation Request | `create_batched_confirmation_request_api_v1_unknowns_confirmation_requests_post` |
| **`GET`** | `/api/v1/unknowns/history/{entity_type}/{entity_id}/{field}` | Get Verification History For Field | `get_verification_history_for_field_api_v1_unknowns_history__entity_type___entity_id___field__get` |
| **`GET`** | `/api/v1/unknowns/items` | Get Unknown Field Items | `get_unknown_field_items_api_v1_unknowns_items_get` |
| **`GET`** | `/api/v1/unknowns/queue` | Get Verification Queue | `get_verification_queue_api_v1_unknowns_queue_get` |
| **`GET`** | `/api/v1/unknowns/ranking` | Get Value Of Information Ranking | `get_value_of_information_ranking_api_v1_unknowns_ranking_get` |
| **`POST`** | `/api/v1/unknowns/token` | Create Field Confirmation Token | `create_field_confirmation_token_api_v1_unknowns_token_post` |
| **`POST`** | `/api/v1/unknowns/verify` | Verify Field Value | `verify_field_value_api_v1_unknowns_verify_post` |
| **`GET`** | `/api/v1/unknowns/why-not/{participant_id}` | Get Participant Why Not Explanation | `get_participant_why_not_explanation_api_v1_unknowns_why_not__participant_id__get` |

### <a id="vendors"></a>Vendors

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/vendors` | List Vendors Endpoint | `list_vendors_endpoint_api_v1_vendors_get` |
| **`GET`** | `/api/v1/vendors/compliance` | Get Compliance Endpoint | `get_compliance_endpoint_api_v1_vendors_compliance_get` |
| **`GET`** | `/api/v1/vendors/reports/{report_name}` | Download Vendor Report Endpoint | `download_vendor_report_endpoint_api_v1_vendors_reports__report_name__get` |
| **`GET`** | `/api/v1/vendors/{id}` | Get Vendor Detail Endpoint | `get_vendor_detail_endpoint_api_v1_vendors__id__get` |
| **`POST`** | `/api/v1/vendors/{id}/shutdown` | Execute Shutdown Endpoint | `execute_shutdown_endpoint_api_v1_vendors__id__shutdown_post` |
| **`POST`** | `/api/v1/vendors/{id}/shutdown-analysis` | Shutdown Impact Endpoint | `shutdown_impact_endpoint_api_v1_vendors__id__shutdown_analysis_post` |
| **`POST`** | `/api/v1/vendors/{id}/shutdown-execute` | Execute Shutdown Endpoint | `execute_shutdown_endpoint_api_v1_vendors__id__shutdown_execute_post` |
| **`POST`** | `/api/v1/vendors/{id}/shutdown-impact` | Shutdown Impact Endpoint | `shutdown_impact_endpoint_api_v1_vendors__id__shutdown_impact_post` |

### <a id="venues"></a>Venues

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/venues` | Get All Venues | `get_all_venues_api_v1_venues_get` |
| **`POST`** | `/api/v1/venues` | Create Venue | `create_venue_api_v1_venues_post` |
| **`GET`** | `/api/v1/venues/compatibility` | Get Venue Event Compatibility | `get_venue_event_compatibility_api_v1_venues_compatibility_get` |
| **`PUT`** | `/api/v1/venues/compatibility` | Set Venue Event Compatibility | `set_venue_event_compatibility_api_v1_venues_compatibility_put` |
| **`GET`** | `/api/v1/venues/travel-times` | Get All Travel Times | `get_all_travel_times_api_v1_venues_travel_times_get` |
| **`PUT`** | `/api/v1/venues/travel-times` | Update Travel Time | `update_travel_time_api_v1_venues_travel_times_put` |
| **`GET`** | `/api/v1/venues/{venue_id}` | Get Venue | `get_venue_api_v1_venues__venue_id__get` |
| **`PUT`** | `/api/v1/venues/{venue_id}` | Update Venue | `update_venue_api_v1_venues__venue_id__put` |

### <a id="dashboard"></a>dashboard

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/dashboard/attention` | Get Attention Queue | `get_attention_queue_api_v1_dashboard_attention_get` |
| **`GET`** | `/api/v1/dashboard/heatmap` | Get Risk Heatmap | `get_risk_heatmap_api_v1_dashboard_heatmap_get` |
| **`GET`** | `/api/v1/dashboard/metrics` | Get Metrics | `get_metrics_api_v1_dashboard_metrics_get` |

### <a id="decisions"></a>decisions

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/decisions` | List Decisions | `list_decisions_api_v1_decisions_get` |
| **`POST`** | `/api/v1/decisions` | Create Decision | `create_decision_api_v1_decisions_post` |
| **`GET`** | `/api/v1/decisions/{id}` | Get Decision | `get_decision_api_v1_decisions__id__get` |
| **`GET`** | `/api/v1/decisions/{id}/why` | Get Why Explanation | `get_why_explanation_api_v1_decisions__id__why_get` |

### <a id="forecasting"></a>forecasting

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/forecasting` | Get Crowd Forecasting | `get_crowd_forecasting_api_v1_forecasting_get` |
| **`GET`** | `/api/v1/forecasting/arrivals-queue` | Get Arrivals And Checkin Queues | `get_arrivals_and_checkin_queues_api_v1_forecasting_arrivals_queue_get` |
| **`GET`** | `/api/v1/forecasting/bed-demand` | Get Bed Demand Projection | `get_bed_demand_projection_api_v1_forecasting_bed_demand_get` |
| **`GET`** | `/api/v1/forecasting/crowd` | Get Crowd Forecasting | `get_crowd_forecasting_api_v1_forecasting_crowd_get` |
| **`GET`** | `/api/v1/forecasting/demand-timeline` | Get Multi Domain Demand Timeline | `get_multi_domain_demand_timeline_api_v1_forecasting_demand_timeline_get` |
| **`GET`** | `/api/v1/forecasting/reports/{name}` | Get Forecasting Report Endpoint | `get_forecasting_report_endpoint_api_v1_forecasting_reports__name__get` |
| **`GET`** | `/api/v1/forecasting/resource-load` | Get Resource Load Projection | `get_resource_load_projection_api_v1_forecasting_resource_load_get` |

### <a id="impact"></a>impact

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/impact` | Get Blast Radius | `get_blast_radius_api_v1_impact_get` |
| **`GET`** | `/api/v1/impact/blast-radius` | Get Blast Radius | `get_blast_radius_api_v1_impact_blast_radius_get` |

### <a id="incidents"></a>incidents

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/incidents` | List Incidents | `list_incidents_api_v1_incidents_get` |
| **`POST`** | `/api/v1/incidents` | Create Incident | `create_incident_api_v1_incidents_post` |

### <a id="logistics"></a>logistics

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/logistics/equipment/find` | Find Equipment | `find_equipment_api_v1_logistics_equipment_find_get` |
| **`GET`** | `/api/v1/logistics/equipment/{id}/failure-analysis` | Failure Analysis | `failure_analysis_api_v1_logistics_equipment__id__failure_analysis_get` |
| **`GET`** | `/api/v1/logistics/items` | List Items | `list_items_api_v1_logistics_items_get` |
| **`GET`** | `/api/v1/logistics/items/{id}` | Get Item | `get_item_api_v1_logistics_items__id__get` |
| **`GET`** | `/api/v1/logistics/ledger/balance` | Verify Ledger Balance | `verify_ledger_balance_api_v1_logistics_ledger_balance_get` |
| **`GET`** | `/api/v1/logistics/locations` | List Locations | `list_locations_api_v1_logistics_locations_get` |
| **`GET`** | `/api/v1/logistics/movements` | List Movements | `list_movements_api_v1_logistics_movements_get` |
| **`POST`** | `/api/v1/logistics/movements` | Record Movement | `record_movement_api_v1_logistics_movements_post` |
| **`GET`** | `/api/v1/logistics/reconciliation-flags` | Get Reconciliation Flags | `get_reconciliation_flags_api_v1_logistics_reconciliation_flags_get` |
| **`GET`** | `/api/v1/logistics/reports/equipment-gap` | Get Equipment Gap Report | `get_equipment_gap_report_api_v1_logistics_reports_equipment_gap_get` |
| **`GET`** | `/api/v1/logistics/reports/inventory-plan` | Get Inventory Plan Report | `get_inventory_plan_report_api_v1_logistics_reports_inventory_plan_get` |
| **`POST`** | `/api/v1/logistics/stocktake` | Stocktake Adjust | `stocktake_adjust_api_v1_logistics_stocktake_post` |
| **`GET`** | `/api/v1/logistics/transfers` | List Transfers | `list_transfers_api_v1_logistics_transfers_get` |
| **`POST`** | `/api/v1/logistics/transfers` | Create Transfer | `create_transfer_api_v1_logistics_transfers_post` |
| **`POST`** | `/api/v1/logistics/transfers/{id}/complete` | Complete Transfer | `complete_transfer_api_v1_logistics_transfers__id__complete_post` |

### <a id="merchandise"></a>merchandise

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/merchandise/catalog` | Get Catalog | `get_catalog_api_v1_merchandise_catalog_get` |
| **`POST`** | `/api/v1/merchandise/issue` | Issue Item | `issue_item_api_v1_merchandise_issue_post` |
| **`GET`** | `/api/v1/merchandise/policy` | Get Policy | `get_policy_api_v1_merchandise_policy_get` |
| **`GET`** | `/api/v1/merchandise/qr/{participant_id}` | Get Qr | `get_qr_api_v1_merchandise_qr__participant_id__get` |
| **`POST`** | `/api/v1/merchandise/scan` | Scan Qr | `scan_qr_api_v1_merchandise_scan_post` |
| **`POST`** | `/api/v1/merchandise/sync` | Sync Offline | `sync_offline_api_v1_merchandise_sync_post` |
| **`POST`** | `/api/v1/merchandise/void` | Void Claim | `void_claim_api_v1_merchandise_void_post` |

### <a id="premortem"></a>premortem

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/premortem` | Get Premortem Resilience | `get_premortem_resilience_api_v1_premortem_get` |
| **`POST`** | `/api/v1/premortem/disruptions/multi-run` | Run Multi Disruptions Endpoint | `run_multi_disruptions_endpoint_api_v1_premortem_disruptions_multi_run_post` |
| **`POST`** | `/api/v1/premortem/disruptions/run` | Run Targeted Disruption Endpoint | `run_targeted_disruption_endpoint_api_v1_premortem_disruptions_run_post` |
| **`GET`** | `/api/v1/premortem/resilience` | Get Premortem Resilience | `get_premortem_resilience_api_v1_premortem_resilience_get` |
| **`GET`** | `/api/v1/premortem/scenarios` | Get Premortem Scenarios History | `get_premortem_scenarios_history_api_v1_premortem_scenarios_get` |
| **`GET`** | `/api/v1/premortem/spofs` | Get Single Points Of Failure | `get_single_points_of_failure_api_v1_premortem_spofs_get` |
| **`GET`** | `/api/v1/premortem/timeline` | Get Hourly Timeline | `get_hourly_timeline_api_v1_premortem_timeline_get` |

### <a id="scenarios"></a>scenarios

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/scenarios` | List Scenarios | `list_scenarios_api_v1_scenarios_get` |
| **`POST`** | `/api/v1/scenarios` | Create Scenario | `create_scenario_api_v1_scenarios_post` |
| **`GET`** | `/api/v1/scenarios/{id}` | Get Scenario | `get_scenario_api_v1_scenarios__id__get` |
| **`POST`** | `/api/v1/scenarios/{id}/actions` | Execute Scenario Action | `execute_scenario_action_api_v1_scenarios__id__actions_post` |
| **`POST`** | `/api/v1/scenarios/{id}/commit` | Commit Scenario | `commit_scenario_api_v1_scenarios__id__commit_post` |
| **`GET`** | `/api/v1/scenarios/{id}/compare` | Compare Scenario | `compare_scenario_api_v1_scenarios__id__compare_get` |
| **`POST`** | `/api/v1/scenarios/{id}/discard` | Discard Scenario | `discard_scenario_api_v1_scenarios__id__discard_post` |
| **`POST`** | `/api/v1/scenarios/{id}/simulate-incident` | Simulate Incident | `simulate_incident_api_v1_scenarios__id__simulate_incident_post` |

### <a id="staff"></a>staff

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/staff` | List Staff | `list_staff_api_v1_staff_get` |
| **`GET`** | `/api/v1/staff/conflicts` | Get Conflicts | `get_conflicts_api_v1_staff_conflicts_get` |
| **`GET`** | `/api/v1/staff/demand` | Get Demand | `get_demand_api_v1_staff_demand_get` |
| **`GET`** | `/api/v1/staff/overloaded` | Get Overloaded | `get_overloaded_api_v1_staff_overloaded_get` |
| **`GET`** | `/api/v1/staff/replacements/suggest` | Suggest Replacements | `suggest_replacements_api_v1_staff_replacements_suggest_get` |
| **`GET`** | `/api/v1/staff/reports/staff-coverage` | Get Staff Coverage Report | `get_staff_coverage_report_api_v1_staff_reports_staff_coverage_get` |
| **`GET`** | `/api/v1/staff/shifts` | List Shifts | `list_shifts_api_v1_staff_shifts_get` |
| **`POST`** | `/api/v1/staff/shifts/assign` | Assign Shift | `assign_shift_api_v1_staff_shifts_assign_post` |
| **`POST`** | `/api/v1/staff/shifts/{id}/replace` | Replace Shift | `replace_shift_api_v1_staff_shifts__id__replace_post` |
| **`GET`** | `/api/v1/staff/{id}` | Get Staff | `get_staff_api_v1_staff__id__get` |

### <a id="transport"></a>transport

| Method | Endpoint Path | Summary | Operation ID |
|---|---|---|---|
| **`GET`** | `/api/v1/transport/alerts` | Get Alerts | `get_alerts_api_v1_transport_alerts_get` |
| **`GET`** | `/api/v1/transport/assumptions` | Get Assumptions | `get_assumptions_api_v1_transport_assumptions_get` |
| **`PATCH`** | `/api/v1/transport/assumptions` | Update Assumptions | `update_assumptions_api_v1_transport_assumptions_patch` |
| **`GET`** | `/api/v1/transport/coverage/summary` | Get Coverage Summary | `get_coverage_summary_api_v1_transport_coverage_summary_get` |
| **`GET`** | `/api/v1/transport/feasibility` | Get Feasibility | `get_feasibility_api_v1_transport_feasibility_get` |
| **`GET`** | `/api/v1/transport/guardians/queue` | Get Guardians Queue | `get_guardians_queue_api_v1_transport_guardians_queue_get` |
| **`POST`** | `/api/v1/transport/guardians/{id}/approve` | Approve Guardian | `approve_guardian_api_v1_transport_guardians__id__approve_post` |
| **`GET`** | `/api/v1/transport/safety/night-roster` | Get Night Roster | `get_night_roster_api_v1_transport_safety_night_roster_get` |
| **`POST`** | `/api/v1/transport/safety/verify` | Verify Safety | `verify_safety_api_v1_transport_safety_verify_post` |
| **`GET`** | `/api/v1/transport/shuttles/plan` | Get Shuttle Plan | `get_shuttle_plan_api_v1_transport_shuttles_plan_get` |
| **`GET`** | `/api/v1/transport/shuttles/runs` | List Runs | `list_runs_api_v1_transport_shuttles_runs_get` |
| **`POST`** | `/api/v1/transport/shuttles/runs` | Create Run | `create_run_api_v1_transport_shuttles_runs_post` |

