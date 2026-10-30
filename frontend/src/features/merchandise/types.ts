export interface MerchandiseItem {
  id: string;
  name: string;
  size: string;
  on_hand: number;
  reserved: number;
  available: number;
  is_per_head: boolean;
}

export interface SizeBreakdownItem {
  demand: number;
  stock: number;
  net: number;
  shortage_alert?: boolean;
  count?: number;
  flag?: string;
}

export interface MerchandisePolicy {
  policy_name: string;
  is_editable: boolean;
  rules: {
    item: string;
    entitlement: string;
    per_head: boolean;
  }[];
  size_breakdown: Record<string, SizeBreakdownItem>;
}

export interface IssueHistoryItem {
  claim_id: string;
  participant_id: string;
  participant_name: string;
  item_name: string;
  counter_id: string;
  issued_by: string;
  issued_at: string;
}

export interface QRTokenData {
  participant_id: string;
  token: string;
  qr_svg: string;
  entitlements: string[];
}

export interface VolunteerScanResult {
  valid: boolean;
  canonical_participant_id: string;
  name: string;
  contingent: string;
  entitlements: {
    item: string;
    status: "ISSUED" | "PENDING";
    claim_id?: string;
    size?: string;
  }[];
}

export interface IssueSuccessResponse {
  claim_id: string;
  canonical_participant_id: string;
  item_id: string;
  item_name: string;
  status: "ISSUED";
  issued_at: string;
  counter_id: string;
  issued_by: string;
}

export interface AlreadyIssuedErrorDetails {
  claim_id: string;
  canonical_participant_id: string;
  claimed_at: string;
  counter_id: string;
  issued_by: string;
}
