import { ScenarioDefinition } from "./types";

export const SCENARIO_DEFINITIONS: ScenarioDefinition[] = [
  // 1. Late Contingent
  {
    id: "late_contingent",
    title: "Late Contingent Arrival",
    category: "Participants",
    description: "Contingent bus delayed by highway blockage. Reconciles arrival waves, adjusts preliminary heats, reserves late dinner portions, and recalculates transport windows.",
    defaultSeverity: "HIGH",
    isPrimary: true,
    defaultParams: {
      contingent_id: "C05",
      contingent_name: "IIT Bombay (42 pax)",
      delay_hours: 3,
      forfeit_policy: "DYNAMIC_SWAP",
    },
    paramFields: [
      {
        name: "contingent_id",
        label: "Contingent",
        type: "select",
        options: [
          { value: "C05", label: "C05 - IIT Bombay (42 pax)" },
          { value: "C12", label: "C12 - BITS Pilani (38 pax)" },
          { value: "C18", label: "C18 - NIT Trichy (26 pax)" },
        ],
        defaultValue: "C05",
      },
      {
        name: "delay_hours",
        label: "Delay Duration (Hours)",
        type: "number",
        defaultValue: 3,
      },
      {
        name: "forfeit_policy",
        label: "Scheduling Policy",
        type: "select",
        options: [
          { value: "DYNAMIC_SWAP", label: "Dynamic Heat Swap (Director Discretion)" },
          { value: "STRICT_FORFEIT", label: "Strict Forfeit (Rulebook)" },
        ],
        defaultValue: "DYNAMIC_SWAP",
      },
    ],
  },

  // 2. Duplicate Participant
  {
    id: "duplicate_participant",
    title: "Duplicate Participant Reconciliation",
    category: "Participants",
    description: "Candidate registered under duplicate records (P0102 / P0103) holding double room reservations and conflicting event registrations.",
    defaultSeverity: "MEDIUM",
    isPrimary: true,
    defaultParams: {
      primary_id: "P0102",
      duplicate_id: "P0103",
      merge_strategy: "CANONICAL_MERGE",
    },
    paramFields: [
      {
        name: "primary_id",
        label: "Primary Canonical ID",
        type: "text",
        defaultValue: "P0102",
      },
      {
        name: "duplicate_id",
        label: "Duplicate Candidate ID",
        type: "text",
        defaultValue: "P0103",
      },
      {
        name: "merge_strategy",
        label: "Reconciliation Action",
        type: "select",
        options: [
          { value: "CANONICAL_MERGE", label: "Merge & Release Ghost Bed (H1-102-B)" },
          { value: "FLAG_QUARANTINE", label: "Quarantine Pending Physical Check-In" },
        ],
        defaultValue: "CANONICAL_MERGE",
      },
    ],
  },

  // 3. Hostel Closure
  {
    id: "hostel_closure",
    title: "Hostel Closure / Evacuation",
    category: "Accommodation",
    description: "Hostel 3 structural plumbing failure flooding electrical conduits. Requires immediate evacuation and emergency reallocation of 85 participants to external properties.",
    defaultSeverity: "CRITICAL",
    isPrimary: true,
    defaultParams: {
      hostel_name: "Hostel 3",
      affected_beds: 85,
      target_external_prop: "Lakeview Resort",
      priority_ladder: "COHESION_FIRST",
    },
    paramFields: [
      {
        name: "hostel_name",
        label: "Affected Campus Hostel",
        type: "select",
        options: [
          { value: "Hostel 3", label: "Hostel 3 (All 85 Beds)" },
          { value: "Hostel 1 Wing B", label: "Hostel 1 Wing B (32 Beds)" },
          { value: "Hostel 2 Wing A", label: "Hostel 2 Wing A (40 Beds)" },
        ],
        defaultValue: "Hostel 3",
      },
      {
        name: "affected_beds",
        label: "Displaced Beds Count",
        type: "number",
        defaultValue: 85,
      },
      {
        name: "priority_ladder",
        label: "Relaxation Strategy",
        type: "select",
        options: [
          { value: "COHESION_FIRST", label: "Plan A: Cohesion-First (Proximity Relaxed)" },
          { value: "COST_FIRST", label: "Plan B: Cost-First (Cohesion Relaxed)" },
          { value: "BALANCED", label: "Plan C: Balanced Fast Recovery" },
        ],
        defaultValue: "COHESION_FIRST",
      },
    ],
  },

  // 4. Equipment Failure
  {
    id: "equipment_failure",
    title: "Key Equipment Failure",
    category: "Logistics",
    description: "Main Auditorium digital audio console failure 45 minutes prior to Battle of the Bands. Dependent stage events blocked; requires warehouse rig dispatch.",
    defaultSeverity: "CRITICAL",
    isPrimary: true,
    defaultParams: {
      equipment_id: "EQ-AUD-CONSOLE",
      equipment_name: "Main Stage 32-Ch Audio Console",
      venue_id: "V01",
      replacement_source: "WAREHOUSE_B",
    },
    paramFields: [
      {
        name: "equipment_name",
        label: "Failed Resource",
        type: "text",
        defaultValue: "Main Stage 32-Ch Audio Console",
      },
      {
        name: "replacement_source",
        label: "Recovery Rig Source",
        type: "select",
        options: [
          { value: "WAREHOUSE_B", label: "Logistics Warehouse B (Yamaha Backup)" },
          { value: "EXTERNAL_RENTAL", label: "Indore Sound Express Rental (+₹25,000)" },
        ],
        defaultValue: "WAREHOUSE_B",
      },
    ],
  },

  // 5. Venue Change
  {
    id: "venue_change",
    title: "Emergency Venue Relocation",
    category: "Events",
    description: "Heavy rain waterlogs Open Air Amphitheatre (V07). 450 registered attendees and staging must shift to Indoor Sports Complex (V02) with 15-minute inter-venue buffer.",
    defaultSeverity: "HIGH",
    isPrimary: true,
    defaultParams: {
      origin_venue: "Amphitheatre (V07)",
      target_venue: "Indoor Sports Complex (V02)",
      overflow_strategy: "DINING_HALL_STREAM",
    },
    paramFields: [
      {
        name: "origin_venue",
        label: "Flooded Venue",
        type: "text",
        defaultValue: "Amphitheatre (V07)",
      },
      {
        name: "target_venue",
        label: "Relocation Target",
        type: "select",
        options: [
          { value: "Indoor Sports Complex (V02)", label: "Indoor Sports Complex (V02, Cap: 900)" },
          { value: "Main Auditorium (V01)", label: "Main Auditorium (V01, Cap: 850)" },
        ],
        defaultValue: "Indoor Sports Complex (V02)",
      },
    ],
  },

  // 6. Vendor Shutdown
  {
    id: "vendor_shutdown",
    title: "Food Vendor Emergency Shutdown",
    category: "Vendors",
    description: "Vendor VND04 (Spice Kitchen) fails sudden health inspection. 220 Jain & Vegan meal tokens immediately unfulfilled for lunch slot; requires reallocation to VND01.",
    defaultSeverity: "HIGH",
    isPrimary: true,
    defaultParams: {
      vendor_id: "VND04",
      vendor_name: "Spice Kitchen (VND04)",
      affected_meals: 220,
      replacement_vendor_id: "VND01",
    },
    paramFields: [
      {
        name: "vendor_id",
        label: "Suspended Vendor",
        type: "select",
        options: [
          { value: "VND04", label: "VND04 - Spice Kitchen (Hygiene Violation)" },
          { value: "VND08", label: "VND08 - Chai Point (Power Outage)" },
        ],
        defaultValue: "VND04",
      },
      {
        name: "replacement_vendor_id",
        label: "Replacement Vendor",
        type: "select",
        options: [
          { value: "VND01", label: "VND01 - Annapurna Caterers (FSSAI Verified)" },
          { value: "VND06", label: "VND06 - Indore Royal Kitchens" },
        ],
        defaultValue: "VND01",
      },
    ],
  },

  // 7. Duplicate Merchandise Claim
  {
    id: "duplicate_merchandise_claim",
    title: "Duplicate Merchandise Claim Fraud",
    category: "Logistics",
    description: "Participant QR scanned for T-shirt kit at Counter 2 after already claiming at Counter 1. Hard DB guarantee unique(canonical_participant_id, item_id) rejects claim.",
    defaultSeverity: "MEDIUM",
    isPrimary: true,
    defaultParams: {
      participant_id: "P0102",
      counter_id: "CTR-02",
      volunteer_id: "VOL-09",
    },
    paramFields: [
      {
        name: "participant_id",
        label: "Participant ID",
        type: "text",
        defaultValue: "P0102",
      },
      {
        name: "counter_id",
        label: "Attempted Counter",
        type: "text",
        defaultValue: "CTR-02",
      },
    ],
  },

  // --- Extras (Secondary List) ---
  {
    id: "dining_power_outage",
    title: "Dining Hall Power Outage",
    category: "Operations",
    description: "Transformer trip shuts down central refrigeration and bain-maries in Central Dining Hall. Requires emergency diesel generator dispatch.",
    defaultSeverity: "HIGH",
    isPrimary: false,
    defaultParams: { backup_gen: "GEN-02", affected_stalls: 6 },
    paramFields: [
      { name: "backup_gen", label: "Backup Generator", type: "text", defaultValue: "GEN-02" },
    ],
  },
  {
    id: "wildcard_surge",
    title: "Wildcard Finalist Surge (+50 Entrants)",
    category: "Events",
    description: "Academic council approves 50 unbudgeted wildcard entrants for Flagship Case Competition. Requires judge gap filling and extra scoring tables.",
    defaultSeverity: "MEDIUM",
    isPrimary: false,
    defaultParams: { extra_entrants: 50, rounds: 2 },
    paramFields: [
      { name: "extra_entrants", label: "Additional Participants", type: "number", defaultValue: 50 },
    ],
  },
  {
    id: "medical_escort",
    title: "Medical Emergency & Escort Dispatch",
    category: "Operations",
    description: "Student injured during sports prelim. Requires immediate ambulance dispatch, security escort log, and contingent leader notification.",
    defaultSeverity: "CRITICAL",
    isPrimary: false,
    defaultParams: { ambulance_unit: "AMB-01", destination: "Apollo Hospital Indore" },
    paramFields: [
      { name: "destination", label: "Medical Center", type: "text", defaultValue: "Apollo Hospital Indore" },
    ],
  },
  {
    id: "keycard_wave",
    title: "Lost Keycard Wave in Block D",
    category: "Accommodation",
    description: "Batch of 25 electronic RFID keys demagnetized during lightning surge. Requires volunteer emergency re-keying desk.",
    defaultSeverity: "LOW",
    isPrimary: false,
    defaultParams: { batch_count: 25, block: "Block D" },
    paramFields: [
      { name: "batch_count", label: "Keycards Affected", type: "number", defaultValue: 25 },
    ],
  },
  {
    id: "flash_weather",
    title: "Severe Weather Flash Warning (Outdoor)",
    category: "Operations",
    description: "Meteorological alert: sudden 45 km/h squall line approaching in 30 minutes. Tarpaulins and stage rigging lockdowns required.",
    defaultSeverity: "HIGH",
    isPrimary: false,
    defaultParams: { warning_buffer_min: 30 },
    paramFields: [
      { name: "warning_buffer_min", label: "Warning Lead Time (Min)", type: "number", defaultValue: 30 },
    ],
  },
];

