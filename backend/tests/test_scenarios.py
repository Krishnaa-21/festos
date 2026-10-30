# OWNER: P1
import os

from app.core.db import get_engine, init_db, use_scenario
from app.models.change import Assumption
from sqlmodel import Session, select


def test_scenario_db_redirect():
    scenario_id = "test_scenario_alpha"
    scenario_file = f"scenarios/{scenario_id}.db"

    # Clean up prior test runs if needed
    if os.path.exists(scenario_file):
        os.remove(scenario_file)

    import uuid
    uid = uuid.uuid4().hex[:6]
    main_key = f"main_key_{uid}"
    scen_key = f"scen_key_{uid}"

    # In default context:
    main_engine = get_engine()
    init_db(main_engine)
    with Session(main_engine) as session:
        session.add(Assumption(key=main_key, value="100", owner="P1", source="TEST", reason="R", impact_if_changed="I"))
        session.commit()

    # Enter scenario context:
    with use_scenario(scenario_id):
        scen_engine = get_engine()
        assert "scenarios" in str(scen_engine.url)
        assert scenario_id in str(scen_engine.url)

        with Session(scen_engine) as session:
            session.add(Assumption(key=scen_key, value="200", owner="P1", source="TEST", reason="R", impact_if_changed="I"))
            session.commit()

            # Scenario DB has scen_key
            scen_item = session.exec(select(Assumption).where(Assumption.key == scen_key)).first()
            assert scen_item is not None
            assert scen_item.value == "200"

    # Outside scenario context, revert to default:
    reverted_engine = get_engine()
    with Session(reverted_engine) as session:
        # Main DB has main_key
        main_item = session.exec(select(Assumption).where(Assumption.key == main_key)).first()
        assert main_item is not None
        # Main DB DOES NOT have scen_key
        isolated = session.exec(select(Assumption).where(Assumption.key == scen_key)).first()
        assert isolated is None

    # Cleanup test scenario db file
    if os.path.exists(scenario_file):
        try:
            os.remove(scenario_file)
        except Exception:
            pass
