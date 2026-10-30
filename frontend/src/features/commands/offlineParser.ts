export interface OfflineParsedCommand {
  intent:
    | "show_impact"
    | "find_accommodation_for_unplaced"
    | "affected_events_by_equipment"
    | "alternative_vendors_for_diet"
    | "list_late_arrivals"
    | "query";
  parameters: Record<string, any>;
  is_mutating: boolean;
  explanation: string;
  confidence: number;
  parser_mode: "LLM" | "OFFLINE_FALLBACK";
  simulated_result?: Record<string, any>;
}

export function parseCommandOffline(text: string): OfflineParsedCommand {
  const clean = text.trim().toLowerCase();

  // 1. Show the impact of closing Hostel C
  if (clean.includes("closing") && (clean.includes("hostel") || clean.includes("venue") || clean.includes("vendor"))) {
    const match = text.match(/closing\s+([A-Za-z0-9\s]+)/i);
    const target = match ? match[1].trim() : "Hostel C";
    return {
      intent: "show_impact",
      parameters: {
        entity_type: "room",
        entity_id: target,
        action: "close",
      },
      is_mutating: false,
      explanation: `Simulate blast radius of emergency closure for ${target}: evaluate displaced participants, meal token redirection, and shuttle demand.`,
      confidence: 0.95,
      parser_mode: "OFFLINE_FALLBACK",
      simulated_result: {
        target_entity: target,
        people_affected: 85,
        rooms_affected: 28,
        cost_delta_inr: 42500,
        unplaced_participants: 85,
        recommended_action: "Evacuate contingents C05 and C12 to Lakeview Resort.",
      },
    };
  }

  // 2. Find accommodation for unplaced participants
  if (clean.includes("unplaced") || (clean.includes("find") && clean.includes("accommodation"))) {
    return {
      intent: "find_accommodation_for_unplaced",
      parameters: {
        plan_kind: "C",
        target_group: "all_unplaced",
        cohesion_weight: 0.5,
        cost_weight: 0.3,
      },
      is_mutating: true,
      explanation:
        "Generate candidate accommodation Plan C (Balanced) for 85 unplaced participants balancing contingent unity against external hotel tariffs.",
      confidence: 0.92,
      parser_mode: "OFFLINE_FALLBACK",
      simulated_result: {
        plan_name: "Plan C: Balanced Optimization",
        placed_count: 85,
        cost_delta_inr: 3315700,
        contingent_splits: 2,
        approval_route: "/approvals",
        requires_director_approval: true,
      },
    };
  }

  // 3. Which events are affected by camera shortages?
  if (clean.includes("equipment") || clean.includes("camera") || clean.includes("shortage")) {
    const itemMatch = text.match(/(?:camera|microphone|projector|sound rig|generator)/i);
    const item = itemMatch ? itemMatch[0] : "camera";
    return {
      intent: "affected_events_by_equipment",
      parameters: {
        item,
      },
      is_mutating: false,
      explanation: `Identify scheduled flagship events and workshop venues blocked by ${item} equipment deficits.`,
      confidence: 0.9,
      parser_mode: "OFFLINE_FALLBACK",
      simulated_result: {
        item,
        deficit_count: 3,
        affected_events: [
          { id: "EV01", name: "RoboWars Flagship Arena", venue: "Gymnasium", schedule: "Oct 31 14:00" },
          { id: "EV08", name: "National Case Competition", venue: "Seminar Hall 1", schedule: "Oct 31 16:30" },
        ],
        delay_risk_min: 45,
      },
    };
  }

  // 4. Find alternative vendors for Jain meals
  if (clean.includes("jain") || clean.includes("vendor") || clean.includes("diet")) {
    return {
      intent: "alternative_vendors_for_diet",
      parameters: {
        diet: "Jain",
        max_cost_inr: 50000,
      },
      is_mutating: false,
      explanation:
        "Scan active vendor contracts for backup FSSAI-certified caterers holding verified capacity for 220 Jain meals.",
      confidence: 0.94,
      parser_mode: "OFFLINE_FALLBACK",
      simulated_result: {
        diet: "Jain",
        shortage_headcount: 220,
        primary_replacement: "VND01 (Annapurna Caterers)",
        replacement_fssai: "FSSAI-2026-CERT-0091 (Verified Active)",
        spare_capacity: 450,
        estimated_cost_inr: 35000,
      },
    };
  }

  // 5. Show the participants arriving after 10 PM
  if (clean.includes("arriving") || clean.includes("10 pm") || clean.includes("late") || clean.includes("curfew")) {
    return {
      intent: "list_late_arrivals",
      parameters: {
        after_time: "22:00",
      },
      is_mutating: false,
      explanation:
        "Filter pending participant arrivals with scheduled flights or trains arriving past the 22:00 campus curfew.",
      confidence: 0.96,
      parser_mode: "OFFLINE_FALLBACK",
      simulated_result: {
        cutoff_time: "22:00 IST",
        total_late_arrivals: 18,
        contingents_affected: ["C08 (BITS Pilani)", "C12 (IIT Madras)", "C19 (IIM Bangalore)"],
        safety_action: "Assign 4 night escorts and inform campus security main gate.",
      },
    };
  }

  // Generic fallback query
  return {
    intent: "query",
    parameters: {
      query: text,
    },
    is_mutating: false,
    explanation: `Execute operational keyword lookup and entity cross-reference for "${text}".`,
    confidence: 0.75,
    parser_mode: "OFFLINE_FALLBACK",
    simulated_result: {
      matched_records: 4,
      entity_type: "general",
      summary: "Matches found across participants, accommodation and schedule registries.",
    },
  };
}

