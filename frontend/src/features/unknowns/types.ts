export type VerificationMethodLabel =
  | "DIRECT_LEADER_SMS"
  | "ARRIVAL_KIOSK"
  | "WHATSAPP_LINK"
  | "CALL_DESK"
  | "PORTAL_FORM"
  | "ADMIN_OVERRIDE";

export interface UnknownQueueItem {
  field: string;
  entity_type: string;
  count: number;
  criticality: number;
  score: number;
  owner: string;
  impact_text: string;
  computed_gain: string; // e.g. "+85 beds unlocked for allocation"
  method_label: VerificationMethodLabel;
  sample_entity_ids: string[];
}

export interface UnresolvedItem {
  id: string;
  name: string;
  contingent_id: string;
  field: string;
  current_value: string;
  status: "UNKNOWN" | "CLAIMED" | "VERIFIED";
  owner: string;
  computed_gain?: string;
  method_label?: VerificationMethodLabel;
}

export interface VerificationHistoryItem {
  id: string;
  entity_id: string;
  field: string;
  status: string;
  value: string;
  source: string;
  verified_by: string;
  verified_at: string;
  previous_value?: string;
}

export interface WhyNotParticipantExplanation {
  participantId: string;
  name: string;
  contingentId: string;
  contingentName: string;
  status: string;
  isUnplaced: boolean;
  blockingReasons: Array<{
    field: string;
    currentValue: string;
    ruleName: string;
    explanation: string;
    fixAction: string;
  }>;
  availableOptions: string[];
}

