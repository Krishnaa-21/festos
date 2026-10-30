# OWNER: P1
import os
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Dict, Generator, Optional

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

import app.models  # noqa: F401  # ensure all SQLModel tables are registered
from app.core.config import settings

# Engine cache
_engines: Dict[str, any] = {}

# ContextVar for scenario-isolated database execution
_scenario_context: ContextVar[Optional[str]] = ContextVar("scenario_context", default=None)

def _build_engine(database_url: str):
    connect_args = {}
    is_sqlite = database_url.startswith("sqlite")
    if is_sqlite:
        connect_args = {"check_same_thread": False}

    engine = create_engine(
        database_url,
        echo=False,
        connect_args=connect_args
    )

    if is_sqlite:
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.execute("PRAGMA busy_timeout=5000;")
            cursor.close()

    return engine

def get_engine(database_url: Optional[str] = None):
    scenario_id = _scenario_context.get()
    if scenario_id:
        scenario_key = f"scenario_{scenario_id}"
        if scenario_key not in _engines:
            os.makedirs("scenarios", exist_ok=True)
            scen_url = f"sqlite:///./scenarios/{scenario_id}.db"
            scen_engine = _build_engine(scen_url)
            # Ensure tables exist in scenario DB
            SQLModel.metadata.create_all(scen_engine)
            _engines[scenario_key] = scen_engine
        return _engines[scenario_key]

    url = database_url or settings.DATABASE_URL
    if url not in _engines:
        _engines[url] = _build_engine(url)
        SQLModel.metadata.create_all(_engines[url])
    return _engines[url]

def close_scenario_engine(scenario_id: str) -> None:
    """Closes and unregisters a scenario SQLite engine so file handles can be released."""
    scenario_key = f"scenario_{scenario_id}"
    if scenario_key in _engines:
        engine = _engines.pop(scenario_key)
        engine.dispose()


@contextmanager
def use_scenario(scenario_id: Optional[str]):
    """Context manager to redirect DB sessions to scenarios/<scenario_id>.db"""
    token = _scenario_context.set(scenario_id)
    try:
        yield
    finally:
        _scenario_context.reset(token)

def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session"""
    engine = get_engine()
    with Session(engine) as session:
        yield session

def init_db(engine=None) -> None:
    """Create all registered SQLModel tables"""
    target_engine = engine or get_engine()
    SQLModel.metadata.create_all(target_engine)

def reset_db(engine=None) -> None:
    """Drop and recreate all registered SQLModel tables"""
    target_engine = engine or get_engine()
    SQLModel.metadata.drop_all(target_engine)
    SQLModel.metadata.create_all(target_engine)
