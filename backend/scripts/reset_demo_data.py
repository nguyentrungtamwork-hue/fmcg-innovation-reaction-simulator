"""Reset demo data (Phase 25).

Deletes demo projects (and all their related rows) whose name starts with
"FreshPlus Demo". Safe by default — wiping ALL projects requires both `--all`
and `--yes`.

    cd backend
    python scripts/reset_demo_data.py                 # delete FreshPlus Demo projects
    python scripts/reset_demo_data.py --prefix "Foo"  # custom name prefix
    python scripts/reset_demo_data.py --all --yes     # delete EVERY project (destructive)
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services import data_export_service  # noqa: E402
from app.storage.database import SessionLocal  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete demo projects and their data.")
    parser.add_argument("--prefix", default="FreshPlus Demo", help="Project name prefix to match.")
    parser.add_argument("--all", action="store_true", help="Delete ALL projects (destructive).")
    parser.add_argument("--yes", action="store_true", help="Confirm a destructive --all wipe.")
    args = parser.parse_args()

    if args.all and not args.yes:
        print("Refusing to delete ALL projects without --yes. Aborting.")
        return 1

    db = SessionLocal()
    try:
        result = data_export_service.reset_demo_data(db, name_prefix=args.prefix, all_data=args.all)
    finally:
        db.close()
    print(f"Deleted {result['projects_deleted']} project(s). Rows removed: {result['counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
