# OWNER: P3
from sqlmodel import Session, select

from app.core.registry import register_seeder
from app.core.security import get_password_hash
from app.models.audit import User
from app.schemas.common import Role

SEED_USERS = [
    {
        "id": "usr_dir_01",
        "email": "director@festos.internal",
        "raw_password": "FestOSDirector2026!",
        "full_name": "Festival Director",
        "role": Role.FESTIVAL_DIRECTOR.value,
        "contingent_id": None
    },
    {
        "id": "usr_acc_01",
        "email": "accommodation@festos.internal",
        "raw_password": "FestOSAccommodation2026!",
        "full_name": "Accommodation Lead",
        "role": Role.ACCOMMODATION_LEAD.value,
        "contingent_id": None
    },
    {
        "id": "usr_eve_01",
        "email": "events@festos.internal",
        "raw_password": "FestOSEvents2026!",
        "full_name": "Event Lead",
        "role": Role.EVENT_LEAD.value,
        "contingent_id": None
    },
    {
        "id": "usr_log_01",
        "email": "logistics@festos.internal",
        "raw_password": "FestOSLogistics2026!",
        "full_name": "Logistics Manager",
        "role": Role.LOGISTICS_MANAGER.value,
        "contingent_id": None
    },
    {
        "id": "usr_mer_01",
        "email": "merch@festos.internal",
        "raw_password": "FestOSMerch2026!",
        "full_name": "Merchandise Manager",
        "role": Role.MERCHANDISE_MANAGER.value,
        "contingent_id": None
    },
    {
        "id": "usr_foo_01",
        "email": "food@festos.internal",
        "raw_password": "FestOSFood2026!",
        "full_name": "Food Operations Manager",
        "role": Role.FOOD_OPS_MANAGER.value,
        "contingent_id": None
    },
    {
        "id": "usr_fin_01",
        "email": "finance@festos.internal",
        "raw_password": "FestOSFinance2026!",
        "full_name": "Finance Manager",
        "role": Role.FINANCE_MANAGER.value,
        "contingent_id": None
    },
    {
        "id": "usr_vol_01",
        "email": "volunteer@festos.internal",
        "raw_password": "FestOSVolunteer2026!",
        "full_name": "Volunteer Alpha",
        "role": Role.VOLUNTEER.value,
        "contingent_id": "C01"
    },
    {
        "id": "usr_vol_02",
        "email": "volunteer.gate1@festos.internal",
        "raw_password": "FestOSVolunteer2026!",
        "full_name": "Volunteer Gate 1",
        "role": Role.VOLUNTEER.value,
        "contingent_id": None
    },
    {
        "id": "usr_vol_03",
        "email": "volunteer.merch@festos.internal",
        "raw_password": "FestOSVolunteer2026!",
        "full_name": "Volunteer Merch Desk",
        "role": Role.VOLUNTEER.value,
        "contingent_id": None
    },
    {
        "id": "usr_aud_01",
        "email": "auditor@festos.internal",
        "raw_password": "FestOSAuditor2026!",
        "full_name": "Compliance Auditor",
        "role": Role.AUDITOR.value,
        "contingent_id": None
    },
]


@register_seeder(name="seed_users", order=20)
def seed_users(session: Session) -> None:
    """Seed one user account per role plus extra volunteers according to docs/TEST_CREDENTIALS.md."""
    for user_info in SEED_USERS:
        existing = session.exec(select(User).where(User.email == user_info["email"])).first()
        if not existing:
            user = User(
                id=user_info["id"],
                email=user_info["email"],
                hashed_password=get_password_hash(user_info["raw_password"]),
                full_name=user_info["full_name"],
                role=user_info["role"],
                contingent_id=user_info["contingent_id"],
                is_active=True
            )
            session.add(user)
    session.commit()
