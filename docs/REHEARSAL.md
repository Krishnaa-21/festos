# FestOS Rehearsal Harness & Disruption Flow Timing Benchmarks

> **Acceptance Standard:** The complete live demo runs twice in a row in under seven minutes with no manual database edits, returning to a pristine state in under one minute via `make reset-demo`.

---

## 1. Quick Rehearsal Command Reference

| Action | Command | Expected Execution Time | Purpose |
|---|---|---|---|
| **Full Health Check** | `make pre-demo-check` | **~5 seconds** | Tests snapshot speed, 9 role logins, 32 module endpoints, 7 disruptions, audit chain |
| **Instant Reset** | `make reset-demo` | **< 1.0 second** | Restores `data/snapshots/demo.db` onto `backend/festos.db` atomically |
| **Launch API Server** | `make dev-api` | **Instant** | Runs FastAPI on `http://localhost:8000` |
| **Launch Frontend** | `make dev-web` | **~1.5 seconds** | Runs Vite on `http://localhost:5173` |
| **Consistency Suite** | `make consistency` | **~1.2 seconds** | Validates `public.py` contracts, ChangeService routes, serializer masking |
| **E2E Smoke Verification** | `make smoke` | **~4.0 seconds** | Python client end-to-end regression validation |

---

## 2. Disruption Flow Timing Benchmarks

Under FestOS operational guidelines, **every live-test path (inject $\rightarrow$ preview $\rightarrow$ approve $\rightarrow$ see consequences) must be completable in under one minute using the keyboard**.

Automated benchmarks measured on the demo build:

| Scenario | API Latency | UI Flow Duration | Downstream Subsystems Updated & Verified |
|---|---|---|---|
| **1. Late Contingent Arrival (C01)** | `8.1 ms` | `~18 seconds` | Contingent arrival wave pushed (+180 min); heats dynamically swapped; late dinner tokens reserved; shuttle window delayed. |
| **2. Duplicate Participant Merge (P0002 $\rightarrow$ P0001)** | `9.9 ms` | `~15 seconds` | Canonical participant merged; ghost bed `H1-102-B` released to available inventory; duplicate event registrations consolidated. |
| **3. Hostel Closure Evacuation (Hostel 3)** | `76.0 ms` | `~28 seconds` | 85 displaced beds evacuated; Lakeview Resort & Guest House assigned; 7 Express Shuttle loops scheduled; Annapurna West dining tokens assigned. |
| **4. Equipment Console Failure (EQ01)** | `4.2 ms` | `~14 seconds` | Main stage 32-Ch digital audio console failed; Warehouse B backup rig debited; stage sound engineer assigned; soundcheck slot shifted. |
| **5. Venue Emergency Relocation (V01 $\rightarrow$ V02)** | `3.8 ms` | `~16 seconds` | Flooded Amphitheatre (V07) vacated; Indoor Sports Complex (V02, Cap: 900) booked for 450 pax; 15-minute inter-venue travel window verified. |
| **6. Vendor Hygiene Shutdown (VND04)** | `16.7 ms` | `~20 seconds` | Spice Kitchen suspended for health violation; 220 Jain & Vegan lunch tokens diverted to FSSAI-verified Annapurna Caterers; broadcast notice dispatched. |
| **7. Duplicate Merch Claim Enforcement** | `13.5 ms` | `~8 seconds` | Repeat QR scan rejected with `409 ALREADY_ISSUED`; original transaction metadata (Counter 1, Pooja Sharma, timestamp) displayed on screen. |
| **Total Cumulative Disruption Run** | **`~132 ms`** | **`< 2.5 minutes`** | **Well within the 7-minute presentation limit!** |

---

## 3. Pre-Demo Verification Checklist (T-15 Minutes)

Run this checklist 15 minutes before judges arrive:

- [ ] **Hardware & Power**:
  - Laptop connected to AC power adapter (no battery saver throttling).
  - External display / HDMI projector tested at 1080p (1920x1080) resolution.
  - Secondary backup laptop powered on and cloned on branch `p3/24-qa-pitch`.
- [ ] **Network & Offline Fallback**:
  - Local Wi-Fi connected, but PWA Service Worker verified: app continues running seamlessly if Wi-Fi disconnects.
  - IndexedDB Dexie offline queue verified with 3 cached scans.
- [ ] **Database State**:
  - Run `make reset-demo` once to guarantee clean baseline.
  - Verify `festos.db` contains 2,836 participants, 38 contingents, 200 rooms / 710 campus beds, 14 vendors, and 9 venues.
- [ ] **Browser Setup**:
  - Google Chrome open in Incognito or clean profile at `http://localhost:5173`.
  - Zoom level set to 100% or 110% for crisp projector legibility.
  - DevTools closed or docked to bottom for inspecting offline mode toggling.
- [ ] **Credentials Check**:
  - Pre-fill Director credentials: `director@festos.internal` / `FestOSDirector2026!`.
  - Volunteer tab open in split window or mobile responsive mode (360px): `volunteer@festos.internal` / `FestOSVolunteer2026!`.

---

## 4. Rehearsal Execution Protocol (7-Minute Dry Run)

1. **Timer Start (0:00)**: Speaker 1 begins Problem Statement while Executive Overview loads.
2. **Reconciliation (0:45)**: Navigate to `/reconciliation` via `G` then `R`. Demonstrate Waterfall and 426 unexplained remainder.
3. **Accommodation Plans (1:45)**: Navigate to `/accommodation`. Compare Plan A, Plan B, and Plan C. Open Why-not? drawer for unplaced participant.
4. **Live Hostel Disruption (3:00)**: Navigate to `/incidents`. Click Hostel Closure card. Dry-run $\rightarrow$ Compare Plans $\rightarrow$ Approve with Reason $\rightarrow$ Inspect Downstream Tracker $\rightarrow$ Open Impact Tree.
5. **Scheduling & Merch (4:30)**: Conflict Panel $\rightarrow$ 10 conflict types $\rightarrow$ Merchandise double scan fraud rejection.
6. **Security & Audit (5:30)**: Break-glass unmasking with audit event entry $\rightarrow$ Override register $\rightarrow$ Role-gated volunteer mobile isolation.
7. **Assumptions & AI Disclosure (6:15)**: `/reports` assumptions tab $\rightarrow$ 180 min cleaning buffer $\rightarrow$ AI disclosure card.
8. **Timer Stop (7:00)**: Reset system for judges via `make reset-demo` in terminal.
