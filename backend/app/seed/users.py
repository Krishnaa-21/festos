# OWNER: P3
from sqlmodel import Session, select

from app.core.registry import register_seeder
from app.models.audit import User
from app.schemas.common import Role


@register_seeder(name="seed_users", order=20)
def seed_users(session: Session) -> None:
    """Seed initial system and admin accounts."""
    director = session.exec(select(User).where(User.email == "director@festos.internal")).first()
    if not director:
        director = User(
            id="usr_director_01",
            email="director@festos.internal",
            hashed_password="mock-hashed-password",
            full_name="Festival Director",
            role=Role.FESTIVAL_DIRECTOR.value,
            is_active=True
        )
        session.add(director)
