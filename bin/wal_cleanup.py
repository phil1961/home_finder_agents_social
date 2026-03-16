# v20260309-1
"""
wal_cleanup.py
──────────────
Double-click (or run from the project root) to checkpoint and drain all
SQLite -wal and -shm files attached to HomeFinder databases.

What it does:
  1. Finds every .db file in the instance/ folder
  2. Opens each one and runs PRAGMA wal_checkpoint(TRUNCATE)
     — this flushes all committed WAL pages back into the main DB
  3. Closes the connection (releases locks)
  4. Reports any -wal / -shm files that still exist afterward
     (they'll be 0 bytes and safe to delete, or gone entirely)

Run this while the Flask server is STOPPED for cleanest results,
but it is safe to run while the server is running too.
"""

import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
INSTANCE_DIR = PROJECT_ROOT / "instance"

# ── Colours for Windows terminal (works in Windows Terminal, plain cmd shows raw codes)
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"


def checkpoint(db_path: Path) -> tuple[str, str]:
    """
    Run WAL checkpoint on a single DB file.
    Returns (status, message).
    """
    try:
        conn = sqlite3.connect(str(db_path), timeout=5)
        # TRUNCATE mode: checkpoints and zeros out the WAL file
        result = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        conn.close()
        # result = (busy, log, checkpointed)
        # busy=1 means another connection is holding a lock
        if result and result[0] == 1:
            return "BUSY", f"Another process holds a lock — try again after stopping the server"
        return "OK", f"Checkpointed (log={result[1]}, moved={result[2]})" if result else "OK"
    except sqlite3.OperationalError as e:
        return "ERROR", str(e)


def check_leftover(db_path: Path) -> list[str]:
    """Return names of any -wal / -shm files that still exist (even if 0 bytes)."""
    leftovers = []
    for suffix in ["-wal", "-shm"]:
        f = db_path.with_name(db_path.name + suffix)
        if f.exists():
            size = f.stat().st_size
            leftovers.append(f"{f.name} ({size} bytes)")
    return leftovers


def main():
    print()
    print(f"{CYAN}HomeFinder WAL Cleanup{RESET}")
    print(f"Instance dir: {INSTANCE_DIR}")
    print()

    if not INSTANCE_DIR.exists():
        print(f"{RED}ERROR: instance/ directory not found at {INSTANCE_DIR}{RESET}")
        input("\nPress Enter to close.")
        sys.exit(1)

    db_files = sorted(INSTANCE_DIR.glob("*.db"))
    if not db_files:
        print(f"{YELLOW}No .db files found in {INSTANCE_DIR}{RESET}")
        input("\nPress Enter to close.")
        return

    any_issues = False

    for db_path in db_files:
        wal = db_path.with_name(db_path.name + "-wal")
        shm = db_path.with_name(db_path.name + "-shm")
        has_wal = wal.exists()
        has_shm = shm.exists()

        if not has_wal and not has_shm:
            print(f"  {GREEN}CLEAN{RESET}  {db_path.name}")
            continue

        # Has WAL/SHM — checkpoint it
        flags = []
        if has_wal: flags.append(f"-wal ({wal.stat().st_size:,} bytes)")
        if has_shm: flags.append(f"-shm ({shm.stat().st_size:,} bytes)")
        print(f"  {YELLOW}FOUND{RESET}  {db_path.name}  [{', '.join(flags)}]")

        status, msg = checkpoint(db_path)

        if status == "OK":
            leftovers = check_leftover(db_path)
            if not leftovers:
                print(f"         {GREEN}→ Checkpointed and cleaned.{RESET}")
            else:
                # Files still exist but should be 0 bytes — safe to delete
                print(f"         {YELLOW}→ Checkpointed. Leftover (should be 0 bytes): {', '.join(leftovers)}{RESET}")
                any_issues = True
        elif status == "BUSY":
            print(f"         {RED}→ BUSY — {msg}{RESET}")
            any_issues = True
        else:
            print(f"         {RED}→ ERROR — {msg}{RESET}")
            any_issues = True

    print()
    if any_issues:
        print(f"{YELLOW}Some files could not be fully cleaned.{RESET}")
        print("Stop the Flask server and run this script again for a complete drain.")
    else:
        print(f"{GREEN}All databases are clean.{RESET}")

    print()
    input("Press Enter to close.")


if __name__ == "__main__":
    main()
