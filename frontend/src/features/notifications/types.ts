export type NotificationAudience =
  | "LEADERS"
  | "VOLUNTEERS"
  | "VENDORS"
  | "COORDINATORS"
  | "ORGANISERS";

export interface NotificationDraft {
  id: string;
  audience: NotificationAudience;
  audienceLabel: string;
  recipientCount: number;
  subject: string;
  body: string;
  priority: "URGENT" | "HIGH" | "NORMAL";
  status: "DRAFT" | "APPROVED" | "SENT" | "FAILED";
  triggerIncidentId?: string;
  triggerEventLabel?: string;
  createdAt: string;
  approvedBy?: string;
  sentAt?: string;
}

export interface DeliveryLogEntry {
  id: string;
  draftId: string;
  audience: NotificationAudience;
  audienceLabel: string;
  recipientCount: number;
  channel: "SMS_BROADCAST" | "WHATSAPP_API" | "IN_APP_PUSH" | "EMAIL_DIGEST";
  subject: string;
  bodyPreview: string;
  sentAt: string;
  deliveredCount: number;
  acknowledgedCount: number;
  status: "DELIVERED" | "ACKNOWLEDGED" | "PARTIAL_FAIL";
}

