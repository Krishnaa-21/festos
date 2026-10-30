# OWNER: P2
from datetime import time
import pytest
from sqlmodel import Session, select

from app.models.change import ChangeSet
from app.models.ops import Assumption
from app.schemas.common import Actor, Role
from app.services.assumptions.service import (
    ASSUMPTION_CATALOG,
    clear_assumption_cache,
    get_assumption,
    get_assumption_dependents,
    list_assumptions,
    seed_all_assumptions,
    update_assumption,
)


@pytest.fixture
def actor():
    return Actor(id="usr_director", role=Role.FESTIVAL_DIRECTOR.value)


def test_seed_all_assumptions(session: Session):
    """Verify all 25 FestOS baseline assumptions are seeded correctly."""
    count = seed_all_assumptions(session)
    assert count == 25
    rows = session.exec(select(Assumption)).all()
    assert len(rows) == 25

    # Check key specific assumptions
    keys = {a.key for a in rows}
    assert "cleaning_buffer_minutes" in keys
    assert "minor_age_threshold" in keys
    assert "transport_hours" in keys
    assert "semifinal_ratio" in keys
    assert "expected_participants_narrative" in keys


def test_get_assumption_typed(session: Session):
    """Verify get_assumption casts values into Python typed objects (int, float, bool, time_range)."""
    seed_all_assumptions(session)
    clear_assumption_cache()

    # Integer
    cleaning = get_assumption("cleaning_buffer_minutes", session=session)
    assert cleaning == 180
    assert isinstance(cleaning, int)

    minor = get_assumption("minor_age_threshold", session=session)
    assert minor == 18
    assert isinstance(minor, int)

    # Float
    semi = get_assumption("semifinal_ratio", session=session)
    assert semi == 0.5
    assert isinstance(semi, float)

    # Boolean
    escorts = get_assumption("include_leaders_escorts_in_demand", session=session)
    assert escorts is True
    assert isinstance(escorts, bool)

    # Time range string
    trans_hours = get_assumption("transport_hours", session=session)
    assert trans_hours == "06:00-22:00"


def test_get_assumption_caching_and_invalidation(session: Session, director_actor: Actor):
    """Verify get_assumption caches values in-memory and invalidates upon change."""
    seed_all_assumptions(session)
    clear_assumption_cache()

    val1 = get_assumption("cleaning_buffer_minutes", session=session)
    assert val1 == 180

    # Update via ChangeService
    res = update_assumption(
        session=session,
        key="cleaning_buffer_minutes",
        value="120",
        actor=director_actor,
        reason="Optimized turnaround workflow",
    )
    assert res.success

    # Value should reflect update immediately due to cache invalidation
    val2 = get_assumption("cleaning_buffer_minutes", session=session)
    assert val2 == 120



def test_assumption_crud_via_change_service(session: Session, director_actor: Actor):
    """Verify assumptions are modified through ChangeService and produce audited ChangeSets."""
    seed_all_assumptions(session)

    res = update_assumption(
        session=session,
        key="minor_age_threshold",
        value="17",
        actor=director_actor,
        reason="Policy exception requested by core team",
    )
    assert res.success

    # Verify ChangeSet in database
    cs = session.exec(select(ChangeSet).where(ChangeSet.entity_id == "minor_age_threshold")).first()
    assert cs is not None
    assert cs.action == "assumptions.update"
    assert cs.actor_id == director_actor.id
    assert cs.payload["new_value"] == "17"
    assert cs.previous_state["value"] == "18"


def test_assumption_validation(session: Session, director_actor: Actor):
    """Verify typed validation rejects invalid or malformed assumption values."""
    seed_all_assumptions(session)

    # Negative integer where min_val is 0
    res = update_assumption(
        session=session,
        key="cleaning_buffer_minutes",
        value="-10",
        actor=director_actor,
        reason="Invalid negative",
    )
    assert not res.success
    assert "Invalid value" in (res.error or "")

    # Invalid boolean string
    res_bool = update_assumption(
        session=session,
        key="include_leaders_escorts_in_demand",
        value="maybe",
        actor=director_actor,
        reason="Invalid boolean",
    )
    assert not res_bool.success
    assert "Invalid value" in (res_bool.error or "")


def test_assumption_dependents_preview(session: Session):
    """Verify dependent modules are correctly surfaced for each assumption key."""
    deps_cleaning = get_assumption_dependents("cleaning_buffer_minutes")
    assert "accommodation" in deps_cleaning.dependent_modules

    deps_semi = get_assumption_dependents("semifinal_ratio")
    assert "schedule" in deps_semi.dependent_modules

    deps_minor = get_assumption_dependents("minor_age_threshold")
    assert "accommodation" in deps_minor.dependent_modules
    assert "imports" in deps_minor.dependent_modules


