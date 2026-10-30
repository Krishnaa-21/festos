# OWNER: P1
import logging

from sqlmodel import Session

from app.core.db import get_engine, init_db, reset_db
from app.core.registry import get_seeders

logger = logging.getLogger("festos.seed")

def run_seeders(reset: bool = False) -> None:
    """Run all registered seeders ordered by execution order."""
    engine = get_engine()
    if reset:
        logger.info("Dropping and recreating database tables...")
        reset_db(engine)
    else:
        init_db(engine)

    seeders = get_seeders()
    logger.info(f"Found {len(seeders)} registered seeder(s)...")

    with Session(engine) as session:
        for order, name, fn in seeders:
            logger.info(f"Running seeder [{order}] {name}...")
            try:
                fn(session)
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error(f"Seeder '{name}' failed: {e}", exc_info=True)
                raise e
    logger.info("Database seeding completed.")
