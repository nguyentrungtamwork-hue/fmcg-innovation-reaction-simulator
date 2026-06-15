"""Local SQLite backup helper (Phase 25).

Copies the active SQLite database file to `backups/` with a timestamped name,
optionally compressing it to a .zip. Safe by default: never touches `.env` or any
secret, and exits cleanly if the DB file does not exist.

    cd backend
    python scripts/backup_sqlite.py            # copy to backups/fmcg_sim_<ts>.db
    python scripts/backup_sqlite.py --zip      # also/instead write a .zip
    python scripts/backup_sqlite.py --out DIR  # choose a different output dir

Only works for SQLite databases (the local/demo default). For Postgres, use your
platform's backup tooling — see docs/DATA_MANAGEMENT.md.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import zipfile
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import get_settings  # noqa: E402


def _sqlite_path(database_url: str) -> str | None:
    if not database_url.startswith("sqlite"):
        return None
    # sqlite:///./fmcg_sim.db  or  sqlite:////data/fmcg_sim.db
    path = database_url.split("sqlite:///", 1)[-1]
    return os.path.abspath(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Back up the local SQLite database.")
    parser.add_argument("--zip", action="store_true", help="Write a compressed .zip backup.")
    parser.add_argument("--out", default=None, help="Output directory (default: backend/backups).")
    args = parser.parse_args()

    settings = get_settings()
    db_path = _sqlite_path(settings.database_url)
    if db_path is None:
        print(f"Not a SQLite database ({settings.database_url.split(':', 1)[0]}://…) — nothing to back up.")
        print("Use your platform's backup tooling for non-SQLite databases.")
        return 0
    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path} — nothing to back up yet.")
        return 0

    out_dir = args.out or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backups"))
    os.makedirs(out_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.splitext(os.path.basename(db_path))[0]

    if args.zip:
        zip_path = os.path.join(out_dir, f"{base}_{ts}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(db_path, arcname=os.path.basename(db_path))
        print(f"Backup written: {zip_path}")
    else:
        dest = os.path.join(out_dir, f"{base}_{ts}.db")
        shutil.copy2(db_path, dest)
        print(f"Backup written: {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
