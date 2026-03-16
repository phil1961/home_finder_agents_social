# v20260309-1
# migrate_roles.py
# One-time migration: rename role='user' → 'client' or 'principal' in all site DBs.
#
# Run from the project root after deploying updated code but BEFORE restarting the server:
#   activate.bat
#   python migrate_roles.py
#
# Safe to run multiple times — only touches rows with role='user'.
# Never touches master, owner, or agent accounts.

import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
REGISTRY_PATH = PROJECT_ROOT / "instance" / "registry.db"


def get_site_db_paths():
    """Return all active site db_paths from the registry."""
    if not REGISTRY_PATH.exists():
        print(f"ERROR: Registry not found at {REGISTRY_PATH}")
        sys.exit(1)
    conn = sqlite3.connect(str(REGISTRY_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT site_key, db_path FROM sites").fetchall()
    conn.close()
    return rows


def migrate_site(site_key, db_path):
    abs_path = PROJECT_ROOT / db_path
    if not abs_path.exists():
        print(f"  SKIP {site_key}: DB not found at {abs_path}")
        return

    try:
        conn = sqlite3.connect(str(abs_path), timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")

        # Count affected rows first
        principals = conn.execute(
            "SELECT COUNT(*) FROM users WHERE role='user' AND agent_id IS NOT NULL"
        ).fetchone()[0]
        clients = conn.execute(
            "SELECT COUNT(*) FROM users WHERE role='user' AND agent_id IS NULL"
        ).fetchone()[0]

        if principals == 0 and clients == 0:
            print(f"  OK   {site_key}: no role='user' rows, nothing to migrate")
            conn.close()
            return

        conn.execute("""
            UPDATE users SET role='principal'
            WHERE role='user' AND agent_id IS NOT NULL
        """)
        conn.execute("""
            UPDATE users SET role='client'
            WHERE role='user'
        """)
        conn.commit()
        conn.close()
        print(f"  DONE {site_key}: {principals} → principal, {clients} → client")

    except sqlite3.OperationalError as e:
        print(f"  SKIP {site_key}: {e} ({abs_path.name})")


def main():
    print(f"HomeFinder role migration — user → client/principal")
    print(f"Registry: {REGISTRY_PATH}")
    print()
    sites = get_site_db_paths()
    if not sites:
        print("No sites found in registry.")
        return
    for row in sites:
        migrate_site(row["site_key"], row["db_path"])
    print()
    print("Migration complete.")


if __name__ == "__main__":
    main()
