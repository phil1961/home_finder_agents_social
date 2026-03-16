# ─────────────────────────────────────────────
# File: config.py
# App Version: 2026.03.14 | File Version: 1.3.0
# Last Modified: 2026-03-14
# ─────────────────────────────────────────────
"""Application configuration."""
# NOTE: DEFAULT_IMPORTANCE is defined at module level below and imported by
# both app.scraper.scorer and app.models (User.DEFAULT_PREFS) so that the
# 17 scoring weights are defined in exactly one place.
import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


# ── Search criteria ──────────────────────────────────────────────
MAX_PRICE = 600_000
MIN_BEDS = 4
MIN_BATHS = 3
MUST_HAVE = ["garage", "porch", "patio"]

# TARGET_AREAS removed — area/zip configuration is now per-user in preferences_json.
# The owner's preferences serve as the canonical mapping for the pipeline.
# Default areas are defined in User.DEFAULT_PREFS in models.py.

# ── Default importance weights (0-10) — single source of truth ────
# Used by scorer.py for composite scoring and by models.py for User.DEFAULT_PREFS.
DEFAULT_IMPORTANCE = {
    "price": 8, "size": 5, "yard": 7, "features": 8, "flood": 6,
    "year_built": 5, "single_story": 7, "price_per_sqft": 4,
    "days_on_market": 3, "hoa": 6, "proximity_medical": 5,
    "proximity_grocery": 5, "community_pool": 6, "property_tax": 4,
    "lot_ratio": 3, "price_trend": 4, "walkability": 3,
    "proximity_poi": 0,  # off by default — user picks a landmark to enable
}

AVOID_AREAS = ["East Goose Creek", "Upper Summerville"]
GREAT_DEAL_SCORE_THRESHOLD = 75  # composite score out of 100

APP_VERSION = "2026.03.12"

# ── Default AI system prompts ────────────────────────────────────
# These are used when no PromptOverride exists for a given type.
# Owners and agents can override these via the Prompts admin pages.
DEFAULT_PROMPTS = {
    "deal": (
        "You are a real estate analyst working exclusively for the buyer. "
        "Your job is to give honest, adversarial advice that serves only the buyer's interests. "
        "Be specific and direct — reference actual numbers from the listing data. "
        "Never soften criticism to protect the seller or agent. "
        "Respond ONLY with a JSON object (no markdown fences) with these exact keys:\n"
        "  summary     — one sentence verdict on whether this is worth pursuing\n"
        "  strengths   — concrete positives (2-4 bullet points as a single string)\n"
        "  concerns    — honest red flags and risks (2-4 bullet points as a single string)\n"
        "  negotiation — specific leverage points and a dollar amount for the opening offer\n"
        "  verdict     — exactly one of: strong_buy, worth_considering, or pass"
    ),
    "portfolio": (
        "You are a real estate analyst helping a buyer compare their shortlisted properties. "
        "Rank them honestly, identify patterns, and give actionable advice. "
        "Respond ONLY with a JSON object (no markdown fences) with these exact keys:\n"
        "  headline    — one bold sentence summarizing the portfolio situation\n"
        "  ranking     — numbered list of properties ranked best to worst with brief reasoning\n"
        "  patterns    — themes, common strengths or weaknesses across the set\n"
        "  strategy    — what to do next, including any negotiation plays\n"
        "  dark_horse  — the underrated pick or a contrarian take the buyer may have missed\n"
        "  bottom_line — final recommendation in 1-2 sentences"
    ),
    "preferences": (
        "You are a real estate scoring preferences advisor. "
        "Review the buyer's importance weights and give honest, specific feedback. "
        "Respond ONLY with a JSON object (no markdown fences) with these exact keys:\n"
        "  headline      — one sentence overall assessment of the configuration\n"
        "  strengths     — what is well-configured and why\n"
        "  blind_spots   — factors they may be underweighting given their goals\n"
        "  tweaks        — specific slider changes with brief rationale for each\n"
        "  local_insight — advice specific to this market area\n"
        "  bottom_line   — final recommendation in 1-2 sentences"
    ),
}


# ── Flask / SQLAlchemy ───────────────────────────────────────────
class Config:
    APP_VERSION = APP_VERSION
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'charlestonsc.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Session / Remember-me ────────────────────────────────────
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)

    # ── API Keys ─────────────────────────────────────────────────
    RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    GOOGLE_MAPS_KEY = os.environ.get("GOOGLE_MAPS_KEY", "")
    GEOAPIFY_KEY = os.environ.get("GEOAPIFY_KEY", "")
    FETCH_INTERVAL_HOURS = int(os.environ.get("FETCH_INTERVAL_HOURS", 6))

    # ── Flask-Mail (SMTP) ────────────────────────────────────────
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER", "HomeFinder <noreply@homefinder.local>"
    )

    # ── Verification token expiry ────────────────────────────────
    VERIFICATION_TOKEN_MAX_AGE = 3600  # 1 hour
