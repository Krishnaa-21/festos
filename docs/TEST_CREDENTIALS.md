# FestOS Test Credentials

This document provides system-seeded accounts for testing and verification across all nine festival operational roles, plus extra volunteers.

| Role | Name | Email | Password | Primary Scope / Capabilities |
|---|---|---|---|---|
| **FESTIVAL_DIRECTOR** | Festival Director | `director@festos.internal` | `FestOSDirector2026!` | Full system overview, hard constraint relaxation, high-risk approvals |
| **ACCOMMODATION_LEAD** | Accommodation Lead | `accommodation@festos.internal` | `FestOSAccommodation2026!` | Hostels, external properties, room allocation, accessibility |
| **EVENT_LEAD** | Event Lead | `events@festos.internal` | `FestOSEvents2026!` | Events, schedules, venues, judges, volunteers |
| **LOGISTICS_MANAGER** | Logistics Manager | `logistics@festos.internal` | `FestOSLogistics2026!` | Equipment, vehicles, inventory tracking |
| **MERCHANDISE_MANAGER** | Merchandise Manager | `merch@festos.internal` | `FestOSMerch2026!` | Merchandise entitlement, size distribution, ledger |
| **FOOD_OPS_MANAGER** | Food Operations Manager | `food@festos.internal` | `FestOSFood2026!` | Vendors, menus, meal slot dietary coverage |
| **FINANCE_MANAGER** | Finance Manager | `finance@festos.internal` | `FestOSFinance2026!` | Costs, vendor contracts, budget thresholds, settlements |
| **VOLUNTEER** | Volunteer Alpha | `volunteer@festos.internal` | `FestOSVolunteer2026!` | Limited check-in, QR merchandise scanning |
| **VOLUNTEER** | Volunteer Gate 1 | `volunteer.gate1@festos.internal` | `FestOSVolunteer2026!` | Arrival gate scanning & badge verification |
| **VOLUNTEER** | Volunteer Merch Desk | `volunteer.merch@festos.internal` | `FestOSVolunteer2026!` | Merchandise distribution desk |
| **AUDITOR** | Compliance Auditor | `auditor@festos.internal` | `FestOSAuditor2026!` | Read-only audit log, hash chain verification, export verification |

## Security & Lockout Policy
- Passwords are securely hashed with `bcrypt` / `argon2`.
- Account lockout triggers after **5 consecutive failed attempts** for a 15-minute cooldown.
- JWT tokens carry role claims and are valid for 30 minutes (access) and 7 days (refresh).
- Break-glass grants require mandatory reason and auto-expire within a 15-minute TTL.
