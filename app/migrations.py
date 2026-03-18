# ─────────────────────────────────────────────
# File: app/migrations.py
# App Version: 2026.03.14 | File Version: 1.6.0
# Last Modified: 2026-03-17
# ─────────────────────────────────────────────
"""
app/migrations.py
─────────────────
Consolidated, idempotent schema migrations for all per-site SQLite databases.

Public API
──────────
    apply_all(engine, logger=None)

This module is intentionally self-contained: it imports from `app.models`
(for `db.metadata`) and uses `sqlalchemy` directly — never from `app.__init__`
— to avoid circular-import issues with the factory pattern.
"""

import logging
from sqlalchemy import inspect, text

_log = logging.getLogger(__name__)


def apply_all(engine, logger=None):
    """Apply every migration idempotently against *engine*.

    1. Column-level migrations on users, listings, deal_scores, agent_profiles.
    2. Ensure all six auxiliary tables exist.

    Safe to call on every request / startup — each step checks before acting.
    """
    log = logger or _log

    with engine.connect() as conn:
        inspector = inspect(engine)

        # ── 1. Column migrations ───────────────────────────────────────

        # ── Users table ──────────────────────────────────────
        if inspector.has_table("users"):
            user_cols = {c["name"] for c in inspector.get_columns("users")}
            if "preferences_json" not in user_cols:
                conn.execute(text('ALTER TABLE users ADD COLUMN preferences_json TEXT DEFAULT "{}"'))
                log.info("Migration: added preferences_json to users")
            if "role" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'"))
                log.info("Migration: added role to users")
            if "agent_id" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN agent_id INTEGER REFERENCES agent_profiles(id)"))
                log.info("Migration: added agent_id to users")
            if "is_suspended" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_suspended BOOLEAN DEFAULT 0"))
                log.info("Migration: added is_suspended to users")
            if "suspended_reason" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN suspended_reason VARCHAR(200)"))
                log.info("Migration: added suspended_reason to users")

            # Set palarson as owner if not already
            result = conn.execute(text(
                "UPDATE users SET role = 'owner' WHERE username = 'palarson' AND role != 'owner'"
            ))
            if result.rowcount > 0:
                log.info("Migration: set palarson as owner")

        # ── Listings table ───────────────────────────────────
        if inspector.has_table("listings"):
            listing_cols = {c["name"] for c in inspector.get_columns("listings")}
            new_listing_cols = {
                "stories": "INTEGER",
                "is_single_story": "BOOLEAN",
                "hoa_monthly": "FLOAT",
                "list_date": "DATETIME",
                "days_on_market": "INTEGER",
                "property_tax_annual": "FLOAT",
                "has_community_pool": "BOOLEAN DEFAULT 0",
                "nearest_hospital_miles": "FLOAT",
                "nearest_grocery_miles": "FLOAT",
                "walkability_score": "FLOAT",
                "price_change_pct": "FLOAT",
                "place_name": "VARCHAR(100)",
                "details_json": "TEXT",
                "details_fetched": "BOOLEAN DEFAULT 0",
                "description": "TEXT",
            }
            for col_name, col_type in new_listing_cols.items():
                if col_name not in listing_cols:
                    conn.execute(text(f"ALTER TABLE listings ADD COLUMN {col_name} {col_type}"))
                    log.info(f"Migration: added {col_name} to listings")

        # ── Deal scores table ────────────────────────────────
        if inspector.has_table("deal_scores"):
            score_cols = {c["name"] for c in inspector.get_columns("deal_scores")}
            if "extended_scores_json" not in score_cols:
                conn.execute(text('ALTER TABLE deal_scores ADD COLUMN extended_scores_json TEXT DEFAULT "{}"'))
                log.info("Migration: added extended_scores_json to deal_scores")

        # ── Agent profiles table ─────────────────────────────
        if inspector.has_table("agent_profiles"):
            agent_cols = {c["name"] for c in inspector.get_columns("agent_profiles")}
            agent_new = {
                "brand_color": "VARCHAR(7) DEFAULT '#2563eb'",
                "brand_logo_url": "VARCHAR(500)",
                "brand_icon": "VARCHAR(50)",
                "brand_tagline": "VARCHAR(200)",
                "brand_tagline_style": "VARCHAR(30) DEFAULT 'plain'",
            }
            for col_name, col_type in agent_new.items():
                if col_name not in agent_cols:
                    conn.execute(text(f"ALTER TABLE agent_profiles ADD COLUMN {col_name} {col_type}"))
                    log.info(f"Migration: added {col_name} to agent_profiles")

        # ── 2. Ensure auxiliary tables ─────────────────────────────────

        # listing_notes
        if not inspector.has_table("listing_notes"):
            conn.execute(text("""
                CREATE TABLE listing_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    listing_id INTEGER NOT NULL REFERENCES listings(id),
                    note_text TEXT DEFAULT '',
                    visited BOOLEAN DEFAULT 0,
                    scheduled_visit BOOLEAN DEFAULT 0,
                    not_interested BOOLEAN DEFAULT 0,
                    made_offer BOOLEAN DEFAULT 0,
                    updated_at DATETIME,
                    UNIQUE(user_id, listing_id)
                )
            """))
            conn.execute(text("CREATE INDEX ix_listing_notes_user_id ON listing_notes(user_id)"))
            conn.execute(text("CREATE INDEX ix_listing_notes_listing_id ON listing_notes(listing_id)"))
            log.info("Migration: created listing_notes table")

        # api_call_log
        if not inspector.has_table("api_call_log"):
            conn.execute(text("""
                CREATE TABLE api_call_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER REFERENCES users(id),
                    call_type VARCHAR(30) NOT NULL,
                    detail VARCHAR(200),
                    success BOOLEAN DEFAULT 1,
                    called_at DATETIME
                )
            """))
            conn.execute(text("CREATE INDEX ix_api_call_log_user_id  ON api_call_log(user_id)"))
            conn.execute(text("CREATE INDEX ix_api_call_log_call_type ON api_call_log(call_type)"))
            conn.execute(text("CREATE INDEX ix_api_call_log_called_at ON api_call_log(called_at)"))
            log.info("Migration: created api_call_log table")

        # cached_analysis
        if not inspector.has_table("cached_analysis"):
            conn.execute(text("""
                CREATE TABLE cached_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    analysis_type VARCHAR(60) NOT NULL,
                    listing_id INTEGER REFERENCES listings(id),
                    result_json TEXT NOT NULL,
                    created_at DATETIME,
                    UNIQUE(user_id, analysis_type, listing_id)
                )
            """))
            conn.execute(text("CREATE INDEX ix_cached_analysis_user ON cached_analysis(user_id)"))
            log.info("Migration: created cached_analysis table")

        # agent_client_notes
        if not inspector.has_table("agent_client_notes"):
            conn.execute(text("""
                CREATE TABLE agent_client_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id INTEGER NOT NULL REFERENCES agent_profiles(id),
                    client_id INTEGER NOT NULL REFERENCES users(id),
                    notes TEXT DEFAULT '',
                    pre_approved BOOLEAN DEFAULT 0,
                    signed_agreement BOOLEAN DEFAULT 0,
                    tour_scheduled BOOLEAN DEFAULT 0,
                    offer_submitted BOOLEAN DEFAULT 0,
                    active_searching BOOLEAN DEFAULT 0,
                    updated_at DATETIME,
                    UNIQUE(agent_id, client_id)
                )
            """))
            conn.execute(text("CREATE INDEX ix_acn_agent_id  ON agent_client_notes(agent_id)"))
            conn.execute(text("CREATE INDEX ix_acn_client_id ON agent_client_notes(client_id)"))
            log.info("Migration: created agent_client_notes table")

        # owner_agent_notes
        if not inspector.has_table("owner_agent_notes"):
            conn.execute(text("""
                CREATE TABLE owner_agent_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id INTEGER NOT NULL UNIQUE REFERENCES agent_profiles(id),
                    notes TEXT DEFAULT '',
                    contract_signed BOOLEAN DEFAULT 0,
                    background_checked BOOLEAN DEFAULT 0,
                    mls_verified BOOLEAN DEFAULT 0,
                    updated_at DATETIME
                )
            """))
            conn.execute(text("CREATE INDEX ix_oan_agent_id ON owner_agent_notes(agent_id)"))
            log.info("Migration: created owner_agent_notes table")

        # prompt_overrides
        if not inspector.has_table("prompt_overrides"):
            conn.execute(text("""
                CREATE TABLE prompt_overrides (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id INTEGER REFERENCES agent_profiles(id),
                    prompt_type VARCHAR(20) NOT NULL,
                    system_prompt TEXT NOT NULL,
                    updated_at DATETIME,
                    UNIQUE(agent_id, prompt_type)
                )
            """))
            conn.execute(text("CREATE INDEX ix_po_agent_id ON prompt_overrides(agent_id)"))
            log.info("Migration: created prompt_overrides table")

        # ── Column-level migrations ────────────────────────────────
        cols = {r[1] for r in conn.execute(text(
            "PRAGMA table_info(api_call_log)")).fetchall()}
        if "trigger" not in cols:
            conn.execute(text(
                "ALTER TABLE api_call_log ADD COLUMN trigger VARCHAR(20) DEFAULT 'manual'"))
            log.info("Migration: added 'trigger' column to api_call_log")
        if "site_key" not in cols:
            conn.execute(text(
                "ALTER TABLE api_call_log ADD COLUMN site_key VARCHAR(50)"))
            log.info("Migration: added 'site_key' column to api_call_log")
        if "zip_code" not in cols:
            conn.execute(text(
                "ALTER TABLE api_call_log ADD COLUMN zip_code VARCHAR(10)"))
            log.info("Migration: added 'zip_code' column to api_call_log")
        for col_name, col_type in [
            ("response_time_ms", "INTEGER"),
            ("http_status", "INTEGER"),
            ("results_count", "INTEGER"),
            ("page_number", "INTEGER"),
            ("quota_remaining", "INTEGER"),
        ]:
            if col_name not in cols:
                conn.execute(text(
                    f"ALTER TABLE api_call_log ADD COLUMN {col_name} {col_type}"))
                log.info(f"Migration: added '{col_name}' column to api_call_log")

        # street_watches
        if not inspector.has_table("street_watches"):
            conn.execute(text("""
                CREATE TABLE street_watches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email VARCHAR(254) NOT NULL,
                    user_id INTEGER REFERENCES users(id),
                    street_name VARCHAR(200) NOT NULL,
                    zip_code VARCHAR(10) NOT NULL,
                    label VARCHAR(200),
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at DATETIME,
                    last_alerted_at DATETIME,
                    unsubscribe_token VARCHAR(64) NOT NULL UNIQUE,
                    UNIQUE(email, street_name, zip_code)
                )
            """))
            conn.execute(text("CREATE INDEX ix_sw_email ON street_watches(email)"))
            conn.execute(text("CREATE INDEX ix_sw_user_id ON street_watches(user_id)"))
            conn.execute(text("CREATE INDEX ix_sw_lookup ON street_watches(zip_code, street_name, is_active)"))
            log.info("Migration: created street_watches table")

        # street_watch_alerts
        if not inspector.has_table("street_watch_alerts"):
            conn.execute(text("""
                CREATE TABLE street_watch_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    watch_id INTEGER NOT NULL REFERENCES street_watches(id),
                    listing_id INTEGER NOT NULL REFERENCES listings(id),
                    alert_type VARCHAR(30) NOT NULL,
                    detail_json TEXT DEFAULT '{}',
                    created_at DATETIME,
                    emailed_at DATETIME,
                    UNIQUE(watch_id, listing_id, alert_type)
                )
            """))
            conn.execute(text("CREATE INDEX ix_swa_watch_id ON street_watch_alerts(watch_id)"))
            conn.execute(text("CREATE INDEX ix_swa_listing_id ON street_watch_alerts(listing_id)"))
            log.info("Migration: created street_watch_alerts table")

        # ── 3. Social tables ─────────────────────────────────────────

        # social_shares
        if not inspector.has_table("social_shares"):
            conn.execute(text("""
                CREATE TABLE social_shares (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    listing_id INTEGER REFERENCES listings(id),
                    collection_id INTEGER REFERENCES social_collections(id),
                    share_type VARCHAR(20) NOT NULL DEFAULT 'listing',
                    sharer_id INTEGER REFERENCES users(id),
                    sharer_name VARCHAR(120),
                    sharer_email VARCHAR(254),
                    recipient_email VARCHAR(254) NOT NULL,
                    recipient_name VARCHAR(120),
                    recipient_user_id INTEGER REFERENCES users(id),
                    relationship VARCHAR(30),
                    message TEXT,
                    share_token VARCHAR(64) NOT NULL UNIQUE,
                    status VARCHAR(20) DEFAULT 'sent' NOT NULL,
                    created_at DATETIME,
                    viewed_at DATETIME,
                    clicked_at DATETIME
                )
            """))
            conn.execute(text("CREATE INDEX ix_ss_listing_id ON social_shares(listing_id)"))
            conn.execute(text("CREATE INDEX ix_ss_collection_id ON social_shares(collection_id)"))
            conn.execute(text("CREATE INDEX ix_ss_sharer_id ON social_shares(sharer_id)"))
            conn.execute(text("CREATE INDEX ix_ss_recipient_email ON social_shares(recipient_email)"))
            conn.execute(text("CREATE INDEX ix_ss_recipient_user_id ON social_shares(recipient_user_id)"))
            conn.execute(text("CREATE INDEX ix_ss_share_token ON social_shares(share_token)"))
            log.info("Migration: created social_shares table")

        # social_reactions
        if not inspector.has_table("social_reactions"):
            conn.execute(text("""
                CREATE TABLE social_reactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    share_id INTEGER NOT NULL REFERENCES social_shares(id),
                    reactor_user_id INTEGER REFERENCES users(id),
                    reactor_email VARCHAR(254) NOT NULL,
                    reaction_type VARCHAR(30) NOT NULL,
                    comment TEXT,
                    created_at DATETIME,
                    UNIQUE(share_id, reactor_email)
                )
            """))
            conn.execute(text("CREATE INDEX ix_sr_share_id ON social_reactions(share_id)"))
            log.info("Migration: created social_reactions table")

        # social_collections
        if not inspector.has_table("social_collections"):
            conn.execute(text("""
                CREATE TABLE social_collections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    creator_id INTEGER NOT NULL REFERENCES users(id),
                    title VARCHAR(200) NOT NULL,
                    description TEXT,
                    share_token VARCHAR(64) NOT NULL UNIQUE,
                    is_public BOOLEAN DEFAULT 0,
                    share_count INTEGER DEFAULT 0,
                    view_count INTEGER DEFAULT 0,
                    created_at DATETIME,
                    updated_at DATETIME
                )
            """))
            conn.execute(text("CREATE INDEX ix_sc_creator_id ON social_collections(creator_id)"))
            conn.execute(text("CREATE INDEX ix_sc_share_token ON social_collections(share_token)"))
            log.info("Migration: created social_collections table")

        # social_collection_items
        if not inspector.has_table("social_collection_items"):
            conn.execute(text("""
                CREATE TABLE social_collection_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collection_id INTEGER NOT NULL REFERENCES social_collections(id),
                    listing_id INTEGER NOT NULL REFERENCES listings(id),
                    note TEXT,
                    position INTEGER DEFAULT 0,
                    added_at DATETIME,
                    UNIQUE(collection_id, listing_id)
                )
            """))
            conn.execute(text("CREATE INDEX ix_sci_collection_id ON social_collection_items(collection_id)"))
            conn.execute(text("CREATE INDEX ix_sci_listing_id ON social_collection_items(listing_id)"))
            log.info("Migration: created social_collection_items table")

        # referrals
        if not inspector.has_table("referrals"):
            conn.execute(text("""
                CREATE TABLE referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL REFERENCES users(id),
                    referred_email VARCHAR(254) NOT NULL,
                    referred_user_id INTEGER REFERENCES users(id),
                    referral_code VARCHAR(20) NOT NULL UNIQUE,
                    status VARCHAR(20) DEFAULT 'invited' NOT NULL,
                    created_at DATETIME,
                    registered_at DATETIME,
                    converted_at DATETIME,
                    UNIQUE(referrer_id, referred_email)
                )
            """))
            conn.execute(text("CREATE INDEX ix_ref_referrer_id ON referrals(referrer_id)"))
            conn.execute(text("CREATE INDEX ix_ref_referred_email ON referrals(referred_email)"))
            conn.execute(text("CREATE INDEX ix_ref_referral_code ON referrals(referral_code)"))
            log.info("Migration: created referrals table")

        # user_points
        if not inspector.has_table("user_points"):
            conn.execute(text("""
                CREATE TABLE user_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
                    balance INTEGER DEFAULT 0 NOT NULL,
                    lifetime_earned INTEGER DEFAULT 0 NOT NULL,
                    updated_at DATETIME
                )
            """))
            conn.execute(text("CREATE INDEX ix_up_user_id ON user_points(user_id)"))
            log.info("Migration: created user_points table")

        # user_point_log
        if not inspector.has_table("user_point_log"):
            conn.execute(text("""
                CREATE TABLE user_point_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    delta INTEGER NOT NULL,
                    reason VARCHAR(50) NOT NULL,
                    reference_id INTEGER,
                    created_at DATETIME
                )
            """))
            conn.execute(text("CREATE INDEX ix_upl_user_id ON user_point_log(user_id)"))
            log.info("Migration: created user_point_log table")

        # friend_listings
        if not inspector.has_table("friend_listings"):
            conn.execute(text("""
                CREATE TABLE friend_listings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    submitter_id INTEGER REFERENCES users(id),
                    submitter_email VARCHAR(254) NOT NULL,
                    address VARCHAR(300) NOT NULL,
                    city VARCHAR(100),
                    zip_code VARCHAR(10),
                    price INTEGER,
                    bedrooms INTEGER,
                    bathrooms FLOAT,
                    sqft INTEGER,
                    description TEXT,
                    photos_json TEXT DEFAULT '[]',
                    relationship VARCHAR(30),
                    has_permission BOOLEAN NOT NULL DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'active' NOT NULL,
                    created_at DATETIME,
                    expires_at DATETIME
                )
            """))
            conn.execute(text("CREATE INDEX ix_fl_submitter_id ON friend_listings(submitter_id)"))
            conn.execute(text("CREATE INDEX ix_fl_zip_code ON friend_listings(zip_code)"))
            log.info("Migration: created friend_listings table")

        # friend_listings: agent approval workflow columns
        if inspector.has_table("friend_listings"):
            fl_cols = {c["name"] for c in inspector.get_columns("friend_listings")}
            for col_name, col_type in [
                ("approved_by_agent_id", "INTEGER REFERENCES agent_profiles(id)"),
                ("approved_at", "DATETIME"),
                ("listing_id", "INTEGER REFERENCES listings(id)"),
                ("rejection_reason", "VARCHAR(200)"),
            ]:
                if col_name not in fl_cols:
                    conn.execute(text(f"ALTER TABLE friend_listings ADD COLUMN {col_name} {col_type}"))
                    log.info(f"Migration: added '{col_name}' to friend_listings")

        # feedback
        if not inspector.has_table("feedback"):
            conn.execute(text("""
                CREATE TABLE feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER REFERENCES users(id),
                    email VARCHAR(254),
                    sentiment VARCHAR(20) NOT NULL,
                    comment TEXT DEFAULT '',
                    page_url VARCHAR(500),
                    user_role VARCHAR(20),
                    is_read BOOLEAN NOT NULL DEFAULT 0,
                    created_at DATETIME
                )
            """))
            conn.execute(text("CREATE INDEX ix_fb_user_id ON feedback(user_id)"))
            conn.execute(text("CREATE INDEX ix_fb_created_at ON feedback(created_at)"))
            log.info("Migration: created feedback table")

        conn.commit()

    log.info(f"apply_all: migrations complete for {engine.url}")
