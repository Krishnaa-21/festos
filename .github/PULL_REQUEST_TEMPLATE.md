## Pull Request

### Description
<!-- Brief description of the changes and the problem solved -->

### Owner & Branch
- **Owner**: P1 | P2 | P3
- **Branch**: `p<N>/<slug>` -> `develop`

### Definition of Done Checklist (FESTOS Context Section 12)
- [ ] `docs/api/<module>.md` contract pushed first
- [ ] router + service + engine + models + schemas, mutations through `ChangeService`, audit and Why cards where relevant
- [ ] `public.py` with `summary`, `risks`, `dependents`
- [ ] seeder or fixtures included
- [ ] pytest including the listed edge cases
- [ ] lint, typecheck and type generation green (`make lint test gen-types`)
- [ ] `INTEGRATION_LOG` entry added
- [ ] no hardcoded demo numbers, no secrets, sensitive fields masked

### Cross-Owner Review
- [ ] If editing files outside your ownership, tagged the designated owner for approval (label: `cross-owner`).
