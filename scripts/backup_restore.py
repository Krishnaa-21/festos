#!/usr/bin/env python3
"""FestOS Database Backup and Restore Utility.

Provides commands to snapshot, backup, and restore the SQLite production database.
Usage:
    python scripts/backup_restore.py snapshot            # Snapshot live DB to data/snapshots/demo.db
    python scripts/backup_restore.py backup [output.db]  # Create timestamped backup
    python scripts/backup_restore.py restore [input.db]   # Restore live DB from snapshot
"""

import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "backend" / "festos.db"
SNAPSHOTS_DIR = REPO_ROOT / "data" / "snapshots"
DEMO_SNAPSHOT_PATH = SNAPSHOTS_DIR / "demo.db"


def get_live_db_path() -> Path:
    """Resolve the active database path from environment or default."""
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url.startswith("sqlite:///"):
        rel_path = db_url.replace("sqlite:///", "")
        candidate = (REPO_ROOT / rel_path).resolve()
        if candidate.exists():
            return candidate

    root_db = REPO_ROOT / "festos.db"
    if root_db.exists():
        return root_db
    backend_db = REPO_ROOT / "backend" / "festos.db"
    if backend_db.exists():
        return backend_db

    return root_db


def backup_database(src: Path, dst: Path) -> None:
    """Uses SQLite backup API to safely create a consistent copy."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        raise FileNotFoundError(f"Source database not found at {src}")

    # Connect and perform online backup
    src_conn = sqlite3.connect(str(src))
    dst_conn = sqlite3.connect(str(dst))
    try:
        src_conn.backup(dst_conn)
        print(f"[SUCCESS] Database successfully backed up to {dst}")
    finally:
        dst_conn.close()
        src_conn.close()


def restore_database(src: Path, dst: Path) -> None:
    """Restores database from a snapshot using SQLite backup API or atomic copy."""
    if not src.exists():
        raise FileNotFoundError(f"Snapshot file not found at {src}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    src_conn = sqlite3.connect(str(src))
    dst_conn = sqlite3.connect(str(dst))
    try:
        src_conn.backup(dst_conn)
        print(f"[SUCCESS] Database successfully restored from {src} to {dst}")
    finally:
        dst_conn.close()
        src_conn.close()


def main():
    parser = argparse.ArgumentParser(description="FestOS Backup and Restore CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # snapshot command
    subparsers.add_parser("snapshot", help="Save current DB as data/snapshots/demo.db")

    # backup command
    backup_parser = subparsers.add_parser("backup", help="Create a timestamped backup")
    backup_parser.add_argument("output", nargs="?", default=None, help="Destination file path")

    # restore command
    restore_parser = subparsers.add_parser("restore", help="Restore DB from snapshot")
    restore_parser.add_argument("source", nargs="?", default=None, help="Source snapshot file")

    args = parser.parse_args()
    live_db = get_live_db_path()

    if args.command == "snapshot":
        backup_database(live_db, DEMO_SNAPSHOT_PATH)
    elif args.command == "backup":
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = Path(args.output) if args.output else SNAPSHOTS_DIR / f"festos_{timestamp}.db"
        backup_database(live_db, target)
    elif args.command == "restore":
        source = Path(args.source) if args.source else DEMO_SNAPSHOT_PATH
        restore_database(source, live_db)


if __name__ == "__main__":
    main()
