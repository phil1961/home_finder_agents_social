# ─────────────────────────────────────────────
# File: app/services/registry.py
# App Version: 2026.03.14 | File Version: 1.4.0
# Last Modified: 2026-03-14
# ─────────────────────────────────────────────
"""
app/services/registry.py
─────────────────────────
Manages the master registry.db that tracks all HomeFinder site instances.
Uses raw sqlite3 (not Flask-SQLAlchemy) so it can be accessed before the
per-request site DB is determined.

Registry DB location: instance/registry.db  (relative to project root)
Override via env: HOMEFINDER_REGISTRY=<absolute path>

Schema
──────
sites
  id              INTEGER PK
  site_key        TEXT UNIQUE      e.g. "charleston", "atlanta"
  display_name    TEXT             e.g. "Charleston, SC"
  db_path         TEXT             relative path: "instance/charleston.db"
  map_center_lat  REAL
  map_center_lon  REAL
  map_zoom        INTEGER
  map_bounds_json TEXT             [[sw_lat,sw_lon],[ne_lat,ne_lon]]
  zip_codes_json  TEXT             ["29401","29403",...]  flat list used by pipeline
  target_areas_json TEXT           {"Area Name":["29401",...]}  named groupings for dashboard
  active          BOOLEAN
  owner_email     TEXT             email of the owner user in this site's DB
  pipeline_last_run DATETIME
  listing_count   INTEGER          cached, updated by pipeline
  created_at      DATETIME
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

MODULE_VERSION = "2026.03.07-multitenant"
log = logging.getLogger(__name__)
log.warning(f"registry.py loaded — version {MODULE_VERSION}")

# ── Registry DB path ──────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).parent.parent.parent
REGISTRY_PATH = Path(os.environ.get("HOMEFINDER_REGISTRY",
                                    str(_PROJECT_ROOT / "instance" / "registry.db")))

# ── Default seed site (Charleston) ────────────────────────────────────────────
_DEFAULT_SITE = {
    "site_key": "charleston",
    "display_name": "Charleston, SC",
    "db_path": "instance/charlestonsc.db",
    "map_center_lat": 32.78,
    "map_center_lon": -79.94,
    "map_zoom": 10,
    "map_bounds_json": json.dumps([[32.40, -80.50], [33.20, -79.40]]),
    "zip_codes_json": json.dumps([
        "29401", "29403", "29405", "29407", "29412", "29414",
        "29418", "29420", "29455", "29456", "29464", "29466",
        "29483", "29485", "29486",
    ]),
    "active": 1,
    "owner_email": "",
}


# ── Connection helper ─────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(REGISTRY_PATH), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


# ── Init / schema ─────────────────────────────────────────────────────────────

def init_registry():
    """Create registry.db and seed the default Charleston site if empty."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sites (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                site_key          TEXT    UNIQUE NOT NULL,
                display_name      TEXT    NOT NULL,
                db_path           TEXT    NOT NULL,
                map_center_lat    REAL    DEFAULT 32.78,
                map_center_lon    REAL    DEFAULT -79.94,
                map_zoom          INTEGER DEFAULT 10,
                map_bounds_json   TEXT,
                zip_codes_json    TEXT,
                target_areas_json TEXT,
                active            BOOLEAN DEFAULT 1,
                owner_email       TEXT    DEFAULT '',
                pipeline_last_run DATETIME,
                listing_count     INTEGER DEFAULT 0,
                created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        # Migrations: add columns if upgrading from older schema
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(sites)").fetchall()}
        if "target_areas_json" not in existing_cols:
            conn.execute("ALTER TABLE sites ADD COLUMN target_areas_json TEXT")
            conn.commit()
        if "scheduler_paused" not in existing_cols:
            conn.execute("ALTER TABLE sites ADD COLUMN scheduler_paused BOOLEAN DEFAULT 0")
            conn.commit()

        # Billing tier columns (added 2026-03-14)
        if "billing_plan" not in existing_cols:
            conn.execute("ALTER TABLE sites ADD COLUMN billing_plan TEXT DEFAULT 'free'")
            conn.commit()
        if "monthly_budget" not in existing_cols:
            conn.execute("ALTER TABLE sites ADD COLUMN monthly_budget REAL DEFAULT 0")
            conn.commit()
        if "monthly_limit_ai" not in existing_cols:
            conn.execute("ALTER TABLE sites ADD COLUMN monthly_limit_ai INTEGER DEFAULT 0")
            conn.commit()
        if "monthly_limit_fetch" not in existing_cols:
            conn.execute("ALTER TABLE sites ADD COLUMN monthly_limit_fetch INTEGER DEFAULT 0")
            conn.commit()
        if "billing_email" not in existing_cols:
            conn.execute("ALTER TABLE sites ADD COLUMN billing_email TEXT")
            conn.commit()
        if "billing_cycle_start" not in existing_cols:
            conn.execute("ALTER TABLE sites ADD COLUMN billing_cycle_start INTEGER DEFAULT 1")
            conn.commit()

        # POI landmarks for proximity scoring (added 2026-03-14)
        if "landmarks_json" not in existing_cols:
            conn.execute("ALTER TABLE sites ADD COLUMN landmarks_json TEXT DEFAULT '[]'")
            conn.commit()

        # Master site controls (added 2026-03-14)
        if "scheduler_locked" not in existing_cols:
            conn.execute("ALTER TABLE sites ADD COLUMN scheduler_locked BOOLEAN DEFAULT 0")
            conn.commit()
        if "max_fetches_per_run" not in existing_cols:
            conn.execute("ALTER TABLE sites ADD COLUMN max_fetches_per_run INTEGER DEFAULT 0")
            conn.commit()

        # Seed default site if table is empty
        count = conn.execute("SELECT COUNT(*) FROM sites").fetchone()[0]
        if count == 0:
            conn.execute("""
                INSERT INTO sites
                    (site_key, display_name, db_path,
                     map_center_lat, map_center_lon, map_zoom,
                     map_bounds_json, zip_codes_json, active, owner_email)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                _DEFAULT_SITE["site_key"],
                _DEFAULT_SITE["display_name"],
                _DEFAULT_SITE["db_path"],
                _DEFAULT_SITE["map_center_lat"],
                _DEFAULT_SITE["map_center_lon"],
                _DEFAULT_SITE["map_zoom"],
                _DEFAULT_SITE["map_bounds_json"],
                _DEFAULT_SITE["zip_codes_json"],
                _DEFAULT_SITE["active"],
                _DEFAULT_SITE["owner_email"],
            ))
            conn.commit()


# ── Read operations ───────────────────────────────────────────────────────────

def get_site(site_key: str) -> dict | None:
    """Return site config dict for the given key, or None if not found / inactive."""
    log.debug(f"get_site({site_key!r}) — registry: {REGISTRY_PATH}")
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM sites WHERE site_key = ? AND active = 1", (site_key,)
        ).fetchone()
    result = dict(row) if row else None
    log.debug(f"get_site({site_key!r}) → {result['db_path'] if result else 'NOT FOUND'}")
    return result


def get_site_any(site_key: str) -> dict | None:
    """Return site config including inactive sites (for admin edit)."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM sites WHERE site_key = ?", (site_key,)
        ).fetchone()
    return dict(row) if row else None


def get_all_sites() -> list[dict]:
    """Return all sites sorted by display_name."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM sites ORDER BY display_name"
        ).fetchall()
    return [dict(r) for r in rows]


def get_default_site_key() -> str:
    """Return the site_key of the first active site, for fallback use."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT site_key FROM sites WHERE active = 1 ORDER BY id LIMIT 1"
        ).fetchone()
    return row[0] if row else "charleston"


# ── Write operations ──────────────────────────────────────────────────────────

def create_site(site_key: str, display_name: str, db_path: str, **kwargs) -> dict:
    """Insert a new site record. Raises ValueError if site_key already exists."""
    if get_site_any(site_key):
        raise ValueError(f"Site key '{site_key}' already exists")

    with _connect() as conn:
        conn.execute("""
            INSERT INTO sites
                (site_key, display_name, db_path,
                 map_center_lat, map_center_lon, map_zoom,
                 map_bounds_json, zip_codes_json, owner_email, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            site_key,
            display_name,
            db_path,
            kwargs.get("map_center_lat", 39.5),   # neutral US center
            kwargs.get("map_center_lon", -98.35),
            kwargs.get("map_zoom", 10),
            kwargs.get("map_bounds_json"),
            kwargs.get("zip_codes_json"),
            kwargs.get("owner_email", ""),
        ))
        conn.commit()
    return get_site_any(site_key)


def update_site(site_key: str, **fields) -> dict | None:
    """Update arbitrary fields on a site record."""
    allowed = {
        "display_name", "db_path", "map_center_lat", "map_center_lon",
        "map_zoom", "map_bounds_json", "zip_codes_json", "target_areas_json",
        "active", "owner_email", "scheduler_paused",
        "billing_plan", "monthly_budget", "monthly_limit_ai",
        "monthly_limit_fetch", "billing_email", "billing_cycle_start",
        "landmarks_json",
        "scheduler_locked", "max_fetches_per_run",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_site_any(site_key)

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [site_key]
    with _connect() as conn:
        conn.execute(f"UPDATE sites SET {set_clause} WHERE site_key = ?", values)
        conn.commit()
    return get_site_any(site_key)


def set_pipeline_ran(site_key: str, listing_count: int):
    """Update pipeline_last_run and listing_count after a pipeline run."""
    with _connect() as conn:
        conn.execute("""
            UPDATE sites
            SET pipeline_last_run = ?, listing_count = ?
            WHERE site_key = ?
        """, (datetime.now(timezone.utc).isoformat(), listing_count, site_key))
        conn.commit()


def delete_site(site_key: str):
    """Permanently delete a site record (does NOT delete the DB file)."""
    with _connect() as conn:
        conn.execute("DELETE FROM sites WHERE site_key = ?", (site_key,))
        conn.commit()
