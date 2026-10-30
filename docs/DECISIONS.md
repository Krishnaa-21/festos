# Architecture Decision Records (ADRs)

This document tracks all significant architectural and design decisions for FestOS.

---

## ADR Template

### ADR-YYYYMMDD-N: [Title of Decision]

- **Status**: [PROPOSED | ACCEPTED | REJECTED | DEPRECATED | SUPERSEDED]
- **Date**: YYYY-MM-DD
- **Owner**: [P1 | P2 | P3]
- **Deciders**: [Names/Roles]

#### Context and Problem Statement
What is the problem being solved? What are the constraints, requirements, or driving forces?

#### Decision Drivers
- Cohesion, consistency, or scalability
- Hard constraints (accessibility, privacy, safety)
- Team velocity and parallel execution without merge conflicts

#### Considered Options
1. Option 1
2. Option 2
3. Option 3

#### Decision Outcome
Chosen option: [Option X], because [rationale].

##### Positive Consequences
- ...

##### Negative Consequences / Trade-offs
- ...

#### Validation and Review
How do we verify this decision?

---

## Accepted Decisions

### ADR-20261030-1: Modular Monolith and Strict Ownership Boundaries
- **Status**: ACCEPTED
- **Date**: 2026-10-30
- **Owner**: P1
- **Deciders**: P1, P2, P3
- **Outcome**: FestOS is structured as a modular monolith in a single repository with strict CODEOWNERS boundaries. Every mutation flows through `ChangeService`, ensuring auditability, optimistic concurrency, and zero file collisions across workstreams.

### ADR-20261030-2: SQLite WAL with Scenario Isolation
- **Status**: ACCEPTED
- **Date**: 2026-10-30
- **Owner**: P1
- **Outcome**: SQLite running in WAL mode with `foreign_keys=ON` and `busy_timeout=5000` is used by default. Scenario simulation redirects database sessions dynamically via `use_scenario(scenario_id)` to isolated scenario databases without polluting production tables.
