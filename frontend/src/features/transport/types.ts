export interface TransportAssumptions {
  shuttle_capacity_seats: number;
  shuttle_vehicle_count: number;
  shuttle_travel_min: number;
  transport_hours: string;
  cleaning_buffer_minutes: number;
  late_night_start: string;
  late_night_end: string;
  minor_age_threshold: number;
}

export interface ShuttlePlanSlot {
  id: string;
  propertyId: string;
  propertyName: string;
  hour: string; // e.g. "08:00"
  passengerDemand: number;
  assignedVehicles: number;
  confirmedCapacity: number;
  deficit: number;
  status: "OK" | "DEFICIT" | "SURPLUS";
}

export interface NightSafetyParticipant {
  id: string;
  participantId: string;
  name: string;
  contingentId: string;
  contingentName: string;
  origin: string;
  destination: string;
  travelTime: string;
  isMinor: boolean;
  assignedEscortId?: string;
  assignedEscortName?: string;
  isVerified: boolean;
  verifiedAt?: string;
  verifiedBy?: string;
}

export interface GuardianQueueEntry {
  id: string;
  participantId: string;
  name: string;
  age: number;
  contingentId: string;
  contingentName: string;
  externalProperty: string;
  stayDuration: string;
  guardianName: string;
  guardianContact: string;
  isMasked: boolean;
  status: "PENDING_REVIEW" | "APPROVED" | "REJECTED";
  escortAssigned?: string;
  reviewReason?: string;
  reviewedBy?: string;
}

export interface SafetyCoverageSummary {
  totalRequiringTransport: number;
  confirmedShuttleCapacity: number;
  uncoveredTransportRequests: number;
  lateNightMovements: number;
  minorExternalAccommodations: number;
  unassignedEscorts: number;
  highRiskPropertyTrips: number;
}

export interface TransportAlert {
  id: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  message: string;
  suggestedActionLabel: string;
  actionPayload: Record<string, any>;
  isResolved: boolean;
}

