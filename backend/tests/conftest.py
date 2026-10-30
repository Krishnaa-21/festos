# OWNER: P1
import pytest
from app.core.bus import clear_subscribers
from app.core.clock import set_demo_time
from app.schemas.common import Actor, Role
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture(autouse=True)
def clean_test_env():
    """Reset clock and bus subscriptions before each test."""
    set_demo_time(None)
    clear_subscribers()
    yield
    set_demo_time(None)
    clear_subscribers()

@pytest.fixture
def session():
    """Provide an isolated, in-memory SQLite database session for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    SQLModel.metadata.drop_all(engine)

@pytest.fixture
def director_actor():
    return Actor(
        id="usr_director",
        name="Festival Director",
        role=Role.FESTIVAL_DIRECTOR.value,
        contingent_id=None
    )

@pytest.fixture
def volunteer_actor():
    return Actor(
        id="usr_volunteer",
        name="Field Volunteer",
        role=Role.VOLUNTEER.value,
        contingent_id=None
    )
