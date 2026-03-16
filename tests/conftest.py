# ─────────────────────────────────────────────
# File: tests/conftest.py
# App Version: 2026.03.12 | File Version: 1.0.0
# Last Modified: 2026-03-13
# ─────────────────────────────────────────────
"""Shared fixtures for HomeFinder regression tests."""
import json
import os
import sqlite3
import tempfile

import pytest

# Ensure minimal env vars are set before any app imports
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("RAPIDAPI_KEY", "test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test")
os.environ.setdefault("MAIL_SERVER", "localhost")
os.environ.setdefault("MAIL_PORT", "25")
os.environ.setdefault("MAIL_USERNAME", "test@test.com")
os.environ.setdefault("MAIL_PASSWORD", "test")
os.environ.setdefault("MAIL_USE_TLS", "0")


@pytest.fixture()
def app(tmp_path):
    """Create a minimal Flask app with a temporary site DB for testing."""
    registry_path = str(tmp_path / "registry.db")
    site_db_path = str(tmp_path / "testsite.db")

    # Point registry module at our temp DB
    os.environ["HOMEFINDER_REGISTRY"] = registry_path

    # Create registry DB with a test site
    conn = sqlite3.connect(registry_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_key TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            db_path TEXT NOT NULL,
            map_center_lat REAL DEFAULT 32.78,
            map_center_lon REAL DEFAULT -79.93,
            map_zoom INTEGER DEFAULT 12,
            map_bounds_json TEXT DEFAULT '[]',
            zip_codes_json TEXT DEFAULT '[]',
            target_areas_json TEXT DEFAULT '{}',
            active BOOLEAN DEFAULT 1,
            owner_email TEXT DEFAULT '',
            pipeline_last_run DATETIME,
            listing_count INTEGER DEFAULT 0,
            scheduler_paused INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        INSERT INTO sites (site_key, display_name, db_path, map_center_lat, map_center_lon,
                           zip_codes_json, target_areas_json, active)
        VALUES ('testsite', 'Test Market', ?, 32.78, -79.93,
                '["29401","29403"]', '{"Downtown":["29401"],"Suburbs":["29403"]}', 1)
    """, (site_db_path,))
    conn.commit()
    conn.close()

    # Reload the registry module to pick up new path
    import app.services.registry as reg_mod
    from pathlib import Path
    reg_mod.REGISTRY_PATH = Path(registry_path)

    from config import Config

    class TestConfig(Config):
        TESTING = True
        WTF_CSRF_ENABLED = False
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{site_db_path}"
        MAIL_SUPPRESS_SEND = True

    from app import create_app
    application = create_app(TestConfig)

    yield application


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture()
def req_ctx(app):
    """Push a full request context with site binding and DB tables created."""
    with app.test_request_context(
        "/",
        environ_base={"HTTP_X_HOMEFINDER_SITE": "testsite"},
    ):
        from flask import g
        from app.services.registry import get_site
        site = get_site("testsite")
        if site:
            g.site = site
            from app import _get_site_engine
            g.site_engine = _get_site_engine(site["db_path"])
            from app.models import db
            db.metadata.create_all(g.site_engine)
            from app.migrations import apply_all
            apply_all(g.site_engine, app.logger)
        yield app


def make_user(username="testuser", email="test@example.com", role="client",
              password="testpass123", verified=True, **kwargs):
    """Create a User instance (not yet committed)."""
    from app.models import User
    user = User(username=username, email=email, role=role, **kwargs)
    user.set_password(password)
    user.is_verified = verified
    return user


def make_listing(address="123 Oak Dr", city="Charleston", zip_code="29401",
                 price=350000, beds=4, baths=2.5, sqft=2200, status="active",
                 source="zillow", source_id=None, **kwargs):
    """Create a Listing instance (not yet committed)."""
    from app.models import Listing
    if source_id is None:
        import uuid
        source_id = f"zillow_{uuid.uuid4().hex[:8]}"
    return Listing(
        address=address, city=city, zip_code=zip_code, price=price,
        beds=beds, baths=baths, sqft=sqft, status=status,
        source=source, source_id=source_id, **kwargs,
    )


def make_agent_profile(user, full_name="Test Agent", status="approved", **kwargs):
    """Create an AgentProfile for the given user (not yet committed)."""
    from app.models import AgentProfile
    return AgentProfile(user_id=user.id, full_name=full_name, status=status, **kwargs)
