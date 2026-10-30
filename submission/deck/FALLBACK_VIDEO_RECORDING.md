# FestOS Screen-Recorded Fallback Video Guide

> **Purpose:** In the event of projector failure, AV disconnection, or judging laptop issues, this document provides the exact timestamped screenplay, click choreography, and audio voiceover transcript for the 7-minute screen-recorded fallback video (`festos_demo_fallback_1080p.mp4`).

---

## Technical Recording Specifications
- **Resolution:** 1080p Full HD (1920 $\times$ 1080), 60 FPS
- **Display Zoom:** 110% Chrome zoom for high projector legibility
- **Audio:** Crisp microphone capture, zero background noise, 48kHz AAC
- **Theme:** FestOS Dark Mode (`#070B14`)
- **Video File Location:** `submission/deck/festos_demo_fallback_1080p.mp4`

---

## Scene-by-Scene Recording Protocol

### Scene 1: Festival Problem & Executive Command Overview (0:00 – 0:45)
- **URL:** `http://localhost:5173/dashboard`
- **Visuals:**
  - Cursor highlights the KPI metric tiles: 2,836 Raw Entrants vs 2,842 Declared vs 2,400 Narrative Claim.
  - Hover over the **Prioritised Attention Queue**: 3 urgent accessibility arrivals highlighted with Attention Score 60.
  - Cursor scrolls down to show the **Risk Heatmap** (Severity $\times$ Time-to-Impact bubble chart).
- **Voiceover:**
  > *"Welcome to FestOS. Managing 2,836 participants, 38 university contingents, and 1,450 beds across Aarohan 2026 cannot be done on spreadsheets. FestOS is the real-time operational command center where every disruption calculates downstream consequences."*

---

### Scene 2: Golden Headcount & Reconciliation Waterfall (0:45 – 1:45)
- **Action:** Press key chord `G` then `R` (or click **Reconciliation** on sidebar).
- **URL:** `http://localhost:5173/reconciliation`
- **Visuals:**
  - Waterfall chart animates: 2,400 deduped portal registrations + 436 late arrivals = 2,836 raw participants.
  - Cursor clicks into the **Unexplained Remainder of 426 participants** that legacy spreadsheets silently truncated.
  - Click **Duplicates Workbench** tab: Click pair `P0102` / `P0103`. Click **Compare Side-by-Side** to reveal identical phone/email but differing dates of birth.
- **Voiceover:**
  > *"Rule number one: Never force 2,400. We capture all 2,836 records, flag 3 malformed rows in quarantine, and surface an unexplained remainder of 426 participants for human audit without dangerous auto-merges."*

---

### Scene 3: Three Transparent Accommodation Plans & Why-Not? (1:45 – 3:00)
- **Action:** Click **Accommodation** on sidebar.
- **URL:** `http://localhost:5173/accommodation`
- **Visuals:**
  - Toggle between **Plan A** (Cohesion-First, +₹42,500), **Plan B** (Cost-First, +₹21,000), and **Plan C** (Balanced Optimization).
  - Drag the **Bed Demand Timeline Scrubber** to Day 1 20:00 showing 99.3% campus bed occupancy.
  - Click **Why-not?** on unplaced participant `P0281`: Drawer slides in showing the 180-min cleaning buffer and ground-floor wheelchair requirement.
- **Voiceover:**
  > *"We built three deterministic plans rather than an unexplainable black-box MILP. And when a participant cannot be accommodated on campus, the Why-not? diagnosis panel explains the exact constraint bottleneck."*

---

### Scene 4: Live Disruption Injection & Impact Analysis (3:00 – 4:30)
- **Action:** Click **Incident Center** on sidebar.
- **URL:** `http://localhost:5173/incidents`
- **Visuals:**
  - Seven scenario cards visible. Click **Inject Disruption** on **Hostel Closure Card**.
  - Click **Preview Impact (Dry Run)**: Blast radius calculates in 76ms (85 affected beds).
  - Click **Compare Recovery Plans**: Plan A selected.
  - Click **Authorize Plan**: `ConfirmWithReason` modal opens. Show confirm button disabled when blank; type operational reason and confirm.
  - **Verification Screen** renders showing before/after delta and Downstream Tracker (Accommodation, Transport, Catering `UPDATED`).
  - Click **Inspect Impact Tree**: Interactive tree renders expanding into 85 participant nodes.
- **Voiceover:**
  > *"At 06:30 AM, Hostel 3 plumbing bursts. In under 30 seconds, the organizer runs a dry-run blast radius, compares recovery plans, signs off with a mandatory justification, and verifies cascading state changes across rooms, shuttle loops, and dining tokens."*

---

### Scene 5: Scheduling Conflicts, QR Merchandise & Vendors (4:30 – 5:30)
- **Action:** Navigate to `/events` then `/merchandise`.
- **Visuals:**
  - Conflict Panel displays 10 evaluated conflict types; camera shortage recommendation shown.
  - Merchandise Desk: Scan QR for `P0102` $\rightarrow$ T-shirt issued.
  - Re-scan QR for `P0102` $\rightarrow$ Immediate red alert: **ALREADY ISSUED (409 Conflict)** with original desk metadata.
- **Voiceover:**
  > *"Our double-entry inventory ledger evaluates all 10 conflict types. And on the merchandise desk, a hard database uniqueness constraint instantly catches duplicate QR fraud."*

---

### Scene 6: Zero-Trust RBAC, Break-Glass & Offline PWA (5:30 – 6:15)
- **Action:** Navigate to `/participants` then open DevTools Network tab.
- **Visuals:**
  - Phone numbers masked with red **BREAK GLASS** badge. Click Break-Glass, fill medical rationale, unmask contact, and show corresponding entry in `/audit`.
  - Toggle network to **Offline**: Scan 2 participants in Volunteer Mobile View $\rightarrow$ Buffered in IndexedDB.
  - Toggle network to **Online**: Click Sync $\rightarrow$ Exactly-once execution with duplicate ignored.
- **Voiceover:**
  > *"Volunteers see only minimal flows. In emergencies, Break-Glass elevation unmasks medical data while writing an indelible SHA-256 audit entry. And when Wi-Fi drops, our PWA offline queue buffers scans safely."*

---

### Scene 7: Assumptions, AI Disclosure & 0.08s Reset (6:15 – 7:00)
- **Action:** Navigate to `/reports` assumptions tab, then switch to terminal.
- **Visuals:**
  - Display Section 10 Assumptions Table: `cleaning_buffer_minutes = 180`.
  - Click **Download Bundle (.ZIP)** showing all 20 Section 14 reports.
  - Open terminal: Run `make reset-demo`.
  - Terminal prints: `[SUCCESS] Database successfully restored in 0.080 seconds`.
- **Voiceover:**
  > *"Assumptions are explicit. AI proposes, logic validates, humans approve. And with make reset-demo, our entire system returns to a known baseline in 0.08 seconds. FestOS is fully rehearsed and ready for Aarohan 2026."*
