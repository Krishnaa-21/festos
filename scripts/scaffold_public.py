import os

modules_p1 = [
    'participants', 'contingents', 'reconciliation', 'events', 'venues',
    'schedule', 'logistics', 'merchandise', 'staff', 'transport',
    'dashboard', 'decisions', 'scenarios', 'commands', 'reports'
]
modules_p2 = [
    'imports', 'assumptions', 'accommodation', 'checkin', 'vendors',
    'food', 'finance', 'notifications', 'incidents', 'impact',
    'unknowns', 'premortem', 'forecasting'
]
modules_p3 = [
    'auth', 'audit', 'approvals', 'overrides'
]

ownership = {}
for m in modules_p1: ownership[m] = 'P1'
for m in modules_p2: ownership[m] = 'P2'
for m in modules_p3: ownership[m] = 'P3'

template = """# OWNER: {owner}
from datetime import datetime
from typing import Any, Dict, List
from sqlmodel import Session
from app.schemas.common import EntityRef, RiskItem

def summary(session: Session, now: datetime) -> Dict[str, Any]:
    \"\"\"Return module KPI summary as of `now`.\"\"\"
    return {{"module": "{slug}", "status": "OPERATIONAL"}}

def risks(session: Session, now: datetime) -> List[RiskItem]:
    \"\"\"Return active risks evaluated as of `now`.\"\"\"
    return []

def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    \"\"\"Return downstream entities affected by entity_type:entity_id.\"\"\"
    return []
"""

for slug, owner in ownership.items():
    s_dir = f'backend/app/services/{slug}'
    os.makedirs(s_dir, exist_ok=True)
    pub_file = os.path.join(s_dir, 'public.py')
    if not os.path.exists(pub_file):
        with open(pub_file, 'w', encoding='utf-8') as f:
            f.write(template.format(owner=owner, slug=slug))

print('All 32 public.py contracts created.')
