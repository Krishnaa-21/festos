export interface StaffMember {
  id: string;
  name: string;
  email: string;
  role: "VOLUNTEER" | "COORDINATOR" | "LEAD" | "SECURITY" | "MEDICAL";
  skills: string[];
  totalHoursWorked: number;
  consecutiveHours: number;
  isOverloaded: boolean;
  hasConflict: boolean;
  assignedVenueId?: string;
  phone?: string;
}

export interface ShiftAssignment {
  id: string;
  staffId: string;
  staffName: string;
  role: "VOLUNTEER" | "COORDINATOR" | "LEAD" | "SECURITY" | "MEDICAL";
  venueId: string;
  venueName: string;
  hour: string; // e.g. "08:00", "10:00", "12:00", etc.
  date: string;
  status: "ASSIGNED" | "CONFIRMED" | "IN_PROGRESS" | "COMPLETED" | "REPLACED";
  isOverloaded?: boolean;
  isOverlapping?: boolean;
  handoverCompleted?: boolean;
  handoverNotes?: string;
}

export interface CoverageHourlySlot {
  hour: string;
  demand: number;
  onShift: number;
  deficit: number;
  status: "SURPLUS" | "COVERED" | "TIGHT" | "UNCOVERED";
}

export interface HandoverNoteRecord {
  id: string;
  venueId: string;
  venueName: string;
  hour: string;
  outgoingStaffName: string;
  incomingStaffName: string;
  notes: string;
  timestamp: string;
  isMissing: boolean;
  acknowledgedByIncoming: boolean;
}

export interface ReplacementCandidate {
  staffId: string;
  name: string;
  role: string;
  matchScore: number; // 0 - 100
  skillsMatched: string[];
  hoursWorkedToday: number;
  proximityMinutes: number;
  reason: string;
}

