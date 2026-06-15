"""Prune the bounded app-log trail (Phase 25).

Removes old `AppLogEntry` rows beyond APP_LOG_MAX_ENTRIES, and optionally any
entries older than N days. Safe by default (only prunes to the configured cap).

    cd backend
    python scripts/prune_app_logs.py               # prune to APP_LOG_MAX_ENTRIES
    python scripts/prune_app_logs.py --max 100     # prune to a custom cap
    python scripts/prune_app_logs.py --older-than-days 30
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import delete  # noqa: E402

from app.models import AppLogEntry  # noqa: E402
from app.services import app_log_service  # noqa: E402
from app.storage.database import SessionLocal  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Prune the bounded app-log trail.")
    parser.add_argument("--max", type=int, default=None, help="Cap to prune down to (default: APP_LOG_MAX_ENTRIES).")
    parser.add_argument("--older-than-days", type=int, default=None, help="Also delete entries older than N days.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        aged = 0
        if args.older_than_days is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=args.older_than_days)
            aged = db.execute(
                delete(AppLogEntry).where(AppLogEntry.timestamp < cutoff)
            ).rowcount or 0
        pruned = app_log_service.prune_old_logs(db, max_entries=args.max)
        db.commit()
        print(f"Pruned {pruned} entries over cap" + (f"; deleted {aged} older-than entries." if args.older_than_days else "."))
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
