# FestOS Operational Resilience Score Methodology

> **IMPORTANT DISCLAIMER**: The Operational Resilience Score is an **operational planning indicator**, designed to help organizers spot structural vulnerabilities, bottlenecks, and single points of failure across festival domains. It is **NOT** a scientifically validated statistical probability of festival success or failure.

---

## 1. Executive Summary

FestOS Principle #1 states: *"Operations over optics: A beautiful UI that hides an unplaced contingent or a meal deficit is a failure."*

The Fest Pre-Mortem Resilience Score evaluates the festival's ability to withstand shocks and absorb disruptions before they materialize. Rather than measuring historical execution, it evaluates the **structural redundancy** and **slack** present in the current operational plans (accommodation, food, venues, equipment, transport, volunteers, safety).

---

## 2. Mathematical Formulation

The overall resilience score $R \in [0, 100]$ is a weighted linear combination of eight normalized domain component scores $S_i \in [0, 100]$:

$$R = \sum_{i=1}^{8} w_i \cdot S_i$$

where $\sum_{i=1}^{8} w_i = 1.00$.

### Component Weights and Definitions

| Component ID | Component Name | Weight ($w_i$) | Description & Metric | Target Condition for 100 pts |
| :--- | :--- | :---: | :--- | :--- |
| **$C_1$** | **Disruption Impact Resistance** | **0.20** | Proportion of festival population unaffected under stress-test disruption scenarios. | Zero participants displaced or stranded under multi-disruption runs. |
| **$C_2$** | **Critical Dependencies & SPOFs** | **0.15** | Absence of Single Points of Failure (resources whose loss halts operations for $\ge 50$ people without alternatives). | Zero unmitigated SPOFs identified across venues, transport, and hostels. |
| **$C_3$** | **Accommodation Shortage Buffer** | **0.15** | Available bed capacity buffer over peak demand: $\frac{\text{Capacity} - \text{Demand}}{\text{Demand}}$. | Positive buffer $\ge 5\%$ surplus unallocated beds. |
| **$C_4$** | **Vendor & Food Redundancy** | **0.10** | Availability of alternative dietary caterers (Veg, Non-Veg, Jain) per dining zone. | Every meal zone has $\ge 2$ operational vendors with dietary coverage. |
| **$C_5$** | **Venue Redundancy** | **0.10** | Peak venue utilization headroom: $100 - \max(\text{Utilization \%})$. | Peak venue utilization $\le 85\%$ leaving buffer for rain/delays. |
| **$C_6$** | **Equipment Availability** | **0.10** | Unallocated standby equipment buffer for critical production items (mics, projectors, PAs). | $\ge 15\%$ spare units available in central depot. |
| **$C_7$** | **Staff & Volunteer Coverage** | **0.10** | Ratio of assigned volunteer shifts to required shift slots across all timetable events. | Volunteer ratio $\ge 1.0$ (100% shift coverage, no open gaps). |
| **$C_8$** | **Safety & Duty-of-Care Coverage** | **0.10** | Verification rate of minor curfews, medical emergency contacts, and safe transit escorts. | 100% of high-risk participants (minors, special needs) have confirmed escorts. |

---

## 3. Component Score Calculations

### 3.1 Disruption Impact Resistance ($S_1$)
$$S_1 = \max\left(0, 100 \times \left(1 - \frac{\text{Total Unique People Disrupted in Simulation}}{\text{Total Registered Participants}}\right)\right)$$

### 3.2 Critical Dependencies & SPOFs ($S_2$)
$$S_2 = \max\left(0, 100 - (\text{Critical SPOF Count} \times 25) - (\text{Moderate SPOF Count} \times 10)\right)$$

### 3.3 Accommodation Buffer ($S_3$)
$$S_3 = \begin{cases} 
100 & \text{if } \text{Available Beds} \ge 1.05 \times \text{Peak Demand} \\
100 \times \frac{\text{Available Beds}}{\text{Peak Demand}} & \text{if } \text{Available Beds} < \text{Peak Demand} \\
80 + 20 \times \frac{\text{Available Beds} - \text{Demand}}{0.05 \times \text{Demand}} & \text{otherwise}
\end{cases}$$

### 3.4 Vendor Redundancy ($S_4$)
$$S_4 = 100 \times \frac{\text{Meal Slots with } \ge 2 \text{ Caterers}}{\text{Total Meal Slots}}$$

### 3.5 Venue Redundancy ($S_5$)
$$S_5 = \max\left(0, \min\left(100, 100 - (\text{Peak Utilization \%} - 70) \times 2\right)\right)$$

### 3.6 Equipment Availability ($S_6$)
$$S_6 = \min\left(100, 100 \times \frac{\text{Available Standby Units}}{\max(1, 0.15 \times \text{Allocated Units})}\right)$$

### 3.7 Staff & Volunteer Coverage ($S_7$)
$$S_7 = \min\left(100, 100 \times \frac{\text{Assigned Volunteer Hours}}{\max(1, \text{Required Volunteer Hours})}\right)$$

### 3.8 Safety Coverage ($S_8$)
$$S_8 = 100 \times \frac{\text{Minors with Verified Guardian Contact}}{\max(1, \text{Total Minors Under 18})}$$

---

## 4. API Representation

The resilience score is exposed via `GET /api/v1/premortem/resilience`:
```json
{
  "data": {
    "festival_resilience_score": 78.4,
    "max_score": 100.0,
    "rating": "MODERATE_RESILIENCE",
    "disclaimer": "Planning indicator for identifying operational vulnerabilities; not a probability of success.",
    "methodology_url": "docs/RESILIENCE_METHOD.md",
    "components": {
      "disruption_resistance": { "score": 75.0, "weight": 0.20, "weighted_score": 15.0 },
      "critical_dependencies_spofs": { "score": 65.0, "weight": 0.15, "weighted_score": 9.75 },
      "accommodation_buffer": { "score": 82.0, "weight": 0.15, "weighted_score": 12.30 },
      "vendor_redundancy": { "score": 80.0, "weight": 0.10, "weighted_score": 8.00 },
      "venue_redundancy": { "score": 85.0, "weight": 0.10, "weighted_score": 8.50 },
      "equipment_availability": { "score": 70.0, "weight": 0.10, "weighted_score": 7.00 },
      "staff_volunteer_coverage": { "score": 88.0, "weight": 0.10, "weighted_score": 8.80 },
      "safety_coverage": { "score": 90.0, "weight": 0.10, "weighted_score": 9.00 }
    },
    "top_bottlenecks": [
      "Hostel Block C is an unmitigated SPOF (140 beds lost if disconnected)",
      "Amphitheatre has zero Jain catering redundancy for Lunch Day 2"
    ]
  }
}
```

---

## 5. Sensitivity to Redundancy Additions

By design:
1. Adding external standby accommodation immediately increases $S_3$ and overall $R$.
2. Adding a secondary backup caterer to vulnerable zones increases $S_4$.
3. Replacing a single high-capacity bus with two staggered shuttles reduces SPOF severity, increasing $S_2$ and $R$.
