# ─────────────────────────────────────────────
# File: app/models.py
# App Version: 2026.03.14 | File Version: 1.7.0
# Last Modified: 2026-03-17
# ─────────────────────────────────────────────
"""Database models for HomeFinder."""
import json
import logging
import re
from datetime import datetime, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

from config import GREAT_DEAL_SCORE_THRESHOLD, DEFAULT_IMPORTANCE

MODULE_VERSION = "2026.03.06-multitenant"
log = logging.getLogger(__name__)
log.info(f"models.py loaded — version {MODULE_VERSION}")


# ── Multi-tenant DB routing ───────────────────────────────────────────────────

class MultiTenantSQLAlchemy(SQLAlchemy):
    """SQLAlchemy subclass that routes all queries to the per-request site engine.

    Flask-SQLAlchemy 3.x accesses the engine via the `engine` property.
    We override both `engine` and `get_engine` to cover all code paths.
    """

    def _site_engine(self):
        """Return g.site_engine if we're inside a request, else None."""
        try:
            from flask import g, has_app_context
            if has_app_context() and hasattr(g, "site_engine"):
                log.warning(f"_site_engine: returning g.site_engine for db_path={getattr(g, 'site', {}).get('db_path','?')!r}")
                return g.site_engine
        except Exception as exc:
            log.warning(f"_site_engine error: {exc}")
        log.warning("_site_engine: no g.site_engine, using default")
        return None

    @property
    def engine(self):
        log.warning("MultiTenantSQLAlchemy.engine property called")
        e = self._site_engine()
        return e if e is not None else super().engine

    def get_engine(self, bind_key=None):
        log.warning(f"MultiTenantSQLAlchemy.get_engine called bind_key={bind_key!r}")
        e = self._site_engine()
        return e if e is not None else super().get_engine(bind_key=bind_key)


db = MultiTenantSQLAlchemy()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  USERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), nullable=False, index=True)  # not unique — master holds four accounts on one email
    username = db.Column(db.String(40), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    is_suspended = db.Column(db.Boolean, default=False)
    suspended_reason = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)
    preferences_json = db.Column(db.Text, default="{}")

    # ── Role definitions ──────────────────────────────────────────
    # Guests are NOT in the DB — all state lives in Flask session only.
    #
    # Capability                          guest  client  principal  agent  owner  master
    # ─────────────────────────────────── ──────────────────────────────────────────────
    # Browse listings / map / detail        ✓      ✓        ✓        ✓      ✓      ✓
    # Toggle flags (fav/maybe/hide)       session  ✓        ✓        ✓      ✓      ✓
    # Save listing notes / itinerary        –      ✓        ✓        ✓      ✓      ✓
    # AI: analyze listing                   –      ✓        ✓        ✓      ✓      ✓
    # AI: analyze portfolio                 –      ✓        ✓        ✓      ✓      ✓
    # AI: analyze preferences               –      ✓        –        ✓      ✓      ✓
    # Edit own preferences                session  ✓        –*       ✓      ✓      ✓
    # Edit avoid_areas in preferences       –      –        –        –      –      ✓
    # Contact assigned agent                –      –        ✓        –      –      –
    # Agent dashboard                       –      –        –        ✓      ✓      ✓
    # Create / manage client accounts       –      –        –        ✓      ✓      ✓
    # Edit client preferences               –      –        –        ✓      ✓      ✓
    # Agent branding                        –      –        –        ✓      –      –
    # Agent AI prompt overrides             –      –        –        ✓      ✓      ✓
    # Trigger pipeline fetch                –      –        –        ✓      ✓      ✓
    # Admin: metrics / user list            –      –        –        –      ✓      ✓
    # Admin: approve / suspend agents       –      –        –        –      ✓      ✓
    # Admin: owner-level prompt overrides   –      –        –        –      ✓      ✓
    # Admin: owner–agent notes              –      –        –        –      ✓      ✓
    # Cross-site navigation (go_to_site)    –      –        –        –      –      ✓
    #
    # * principal preferences are managed by their agent, not by themselves
    role = db.Column(db.String(20), default="client", nullable=False)

    # Set for principal accounts — the agent who invited/manages them
    agent_id = db.Column(db.Integer, db.ForeignKey("agent_profiles.id"), nullable=True)

    # Relationships
    flags = db.relationship("UserFlag", back_populates="user", lazy="dynamic",
                            cascade="all, delete-orphan")
    agent_profile = db.relationship("AgentProfile", back_populates="user",
                                     uselist=False, foreign_keys="AgentProfile.user_id")
    assigned_agent = db.relationship("AgentProfile", foreign_keys=[agent_id],
                                     overlaps="agent_ref,clients")

    # ── Role helpers ───────────────────────────────────────────
    @property
    def is_master(self) -> bool:
        return self.role == "master"

    @property
    def is_owner(self) -> bool:
        return self.role in ("owner", "master")  # master can do everything owner can

    @property
    def is_agent(self) -> bool:
        return self.role == "agent"

    @property
    def is_principal(self) -> bool:
        """Agent-invited buyer — has agent_id set, preferences managed by agent."""
        return self.role == "principal"

    @property
    def is_client(self) -> bool:
        """Self-registered buyer — manages their own preferences."""
        return self.role == "client"

    @property
    def is_admin(self) -> bool:
        """Owner or agent — anyone with elevated privileges."""
        return self.role in ("owner", "agent", "master")

    # ── Default preferences ──────────────────────────────────────
    # Weights now use importance 0-10 (normalized internally)
    DEFAULT_PREFS = {
        # Search criteria
        "min_price": 200000,
        "max_price": 600000,
        "min_beds": 4,
        "min_baths": 3,
        "must_have_garage": True,
        "must_have_porch": True,
        "must_have_patio": True,
        # Target areas
        "target_areas": {},          # seeded per-site from registry at runtime
        "avoid_areas": [],
        # ── Scoring importance (0-10 scale, normalized internally) ──
        # Derived from config.DEFAULT_IMPORTANCE — single source of truth
        **{f"imp_{k}": v for k, v in DEFAULT_IMPORTANCE.items()},
        # Display
        "great_deal_threshold": GREAT_DEAL_SCORE_THRESHOLD,
        # Help level: 1=Expert, 2=Standard (tooltips), 3=Guided (tooltips+inline)
        "help_level": 2,
        # Power mode: "low" (core nav + 6 sliders), "mid" (+ advanced nav), "high" (everything)
        "power_mode": "high",
        # AI mode: "off" (hide AI panels), "on" (standard), "tune" (personalized with buyer profile)
        "ai_mode": "on",
    }

    def get_prefs(self) -> dict:
        """Return merged preferences (defaults + user overrides)."""
        try:
            saved = json.loads(self.preferences_json or "{}")
        except (json.JSONDecodeError, TypeError):
            saved = {}
        merged = dict(self.DEFAULT_PREFS)
        merged.update(saved)
        return merged

    def set_prefs(self, prefs: dict):
        """Save only values that differ from defaults."""
        diff = {}
        for k, v in prefs.items():
            if k in self.DEFAULT_PREFS and v != self.DEFAULT_PREFS[k]:
                diff[k] = v
            elif k not in self.DEFAULT_PREFS:
                diff[k] = v
        self.preferences_json = json.dumps(diff)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  AGENT PROFILES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AgentProfile(db.Model):
    __tablename__ = "agent_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    # Professional info
    full_name = db.Column(db.String(120), nullable=False)
    license_number = db.Column(db.String(50))
    brokerage = db.Column(db.String(120))
    phone = db.Column(db.String(30))
    bio = db.Column(db.Text)
    service_areas = db.Column(db.Text)               # comma-separated area names

    # Status: 'pending' → 'approved' → (or 'suspended')
    status = db.Column(db.String(20), default="pending", nullable=False)
    approved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Agent branding (shown to their clients)
    brand_color = db.Column(db.String(7), default="#2563eb")   # hex, e.g. "#1a5276"
    brand_logo_url = db.Column(db.String(500))                 # URL to agent's logo image
    brand_icon = db.Column(db.String(50))                      # Bootstrap Icon key, e.g. "bi-house-heart-fill"
    brand_tagline = db.Column(db.String(200))                  # short tagline shown in navbar
    brand_tagline_style = db.Column(db.String(30), default="plain")  # style key

    # Relationships
    user = db.relationship("User", back_populates="agent_profile",
                           foreign_keys=[user_id])
    clients = db.relationship("User", foreign_keys="User.agent_id",
                              backref="agent_ref", lazy="dynamic",
                              overlaps="assigned_agent")

    @property
    def is_approved(self) -> bool:
        return self.status == "approved"

    @property
    def client_count(self) -> int:
        return self.clients.count()

    def __repr__(self):
        return f"<AgentProfile {self.full_name} ({self.status})>"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LISTINGS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Listing(db.Model):
    __tablename__ = "listings"

    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(20), nullable=False)
    source_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    url = db.Column(db.Text)
    status = db.Column(db.String(20), default="active")

    # Property details
    address = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(80))
    zip_code = db.Column(db.String(10), index=True)
    area_name = db.Column(db.String(80), index=True)
    price = db.Column(db.Integer, index=True)
    beds = db.Column(db.Integer)
    baths = db.Column(db.Float)
    sqft = db.Column(db.Integer)
    lot_sqft = db.Column(db.Integer)
    year_built = db.Column(db.Integer)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    place_name = db.Column(db.String(100), index=True)   # Census place: "James Island CDP"

    # Features (boolean flags from scrape)
    has_garage = db.Column(db.Boolean, default=False)
    has_porch = db.Column(db.Boolean, default=False)
    has_patio = db.Column(db.Boolean, default=False)
    flood_zone = db.Column(db.String(10))
    above_flood_plain = db.Column(db.Boolean)

    # ── New fields for extended scoring ──────────────────────────
    stories = db.Column(db.Integer)                             # number of stories
    is_single_story = db.Column(db.Boolean)
    hoa_monthly = db.Column(db.Float)                           # monthly HOA fee
    list_date = db.Column(db.DateTime)                          # when listed
    days_on_market = db.Column(db.Integer)
    property_tax_annual = db.Column(db.Float)                   # estimated annual tax
    has_community_pool = db.Column(db.Boolean, default=False)
    nearest_hospital_miles = db.Column(db.Float)
    nearest_grocery_miles = db.Column(db.Float)
    walkability_score = db.Column(db.Float)                     # 0-100
    price_change_pct = db.Column(db.Float)                      # % change since first seen

    # Lazy-enriched property details from source API detail endpoint
    details_json = db.Column(db.Text)
    details_fetched = db.Column(db.Boolean, default=False)

    # Metadata
    photo_urls_json = db.Column(db.Text)
    price_history_json = db.Column(db.Text)
    description = db.Column(db.Text)
    first_seen = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    deal_score = db.relationship("DealScore", uselist=False, back_populates="listing",
                                 cascade="all, delete-orphan")
    user_flags = db.relationship("UserFlag", back_populates="listing", lazy="dynamic",
                                 cascade="all, delete-orphan")

    # ── Photo helpers ────────────────────────────────────────────

    @staticmethod
    def _resize_photo(url: str, size: str = "l") -> str:
        """Resize a photo URL to the requested size.

        Handles both URL patterns:
          Zillow:   .../{key}-p_e.jpg  → .../{key}-p_d.jpg (or -cc_ft_768.webp)
          Realtor:  ...-m{digits}s.jpg → ...-m{digits}l.jpg
        """
        if not url:
            return url
        # Zillow: -p_e, -p_f, etc. → upgrade to larger variant
        if "zillowstatic.com" in url:
            if size == "od":
                # Original/HD
                return re.sub(r'-p_[a-z]\.jpg$', '-uncropped_scaled_within_1536_1024.jpg', url)
            else:
                # Large (~768px)
                return re.sub(r'-p_[a-z]\.jpg$', '-p_d.jpg', url)
        # Realtor: suffix before .jpg
        return re.sub(r'(l-m\d+)[a-z]{1,2}(\.jpg)$', rf'\g<1>{size}\2', url)

    @property
    def photos(self) -> list[str]:
        try:
            urls = json.loads(self.photo_urls_json or "[]")
            return [u for u in urls if u]
        except (json.JSONDecodeError, TypeError):
            return []

    @property
    def photos_large(self) -> list[str]:
        return [self._resize_photo(u, "l") for u in self.photos]

    @property
    def photos_original(self) -> list[str]:
        return [self._resize_photo(u, "od") for u in self.photos]

    @property
    def primary_photo(self) -> str | None:
        photos = self.photos
        return photos[0] if photos else None

    @property
    def primary_photo_large(self) -> str | None:
        photos = self.photos_large
        return photos[0] if photos else None

    # ── Computed properties ──────────────────────────────────────

    @property
    def price_per_sqft(self) -> float | None:
        if self.price and self.sqft and self.sqft > 0:
            return round(self.price / self.sqft, 2)
        return None

    @property
    def lot_to_house_ratio(self) -> float | None:
        if self.lot_sqft and self.sqft and self.sqft > 0:
            return round(self.lot_sqft / self.sqft, 2)
        return None

    @property
    def price_history(self) -> list[dict]:
        """Full price history: past entries + current price.

        Returns list of dicts sorted oldest first:
          [{"price": 450000, "date": "2024-01-15T...", "event": "listed"},
           {"price": 425000, "date": "2024-02-20T...", "event": "reduced"},
           {"price": 419900, "date": "2024-03-10T...", "event": "current"}]
        """
        history = json.loads(self.price_history_json or "[]")
        # Append current price as the final entry
        if self.price:
            history.append({
                "price": self.price,
                "date": (self.last_seen or datetime.now(timezone.utc)).isoformat(),
                "event": "current",
            })
        return history

    @property
    def has_price_changes(self) -> bool:
        """True if the listing has had at least one price change."""
        stored = json.loads(self.price_history_json or "[]")
        return len(stored) > 1

    def __repr__(self):
        return f"<Listing {self.address} ${self.price:,}>"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DEAL SCORING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class DealScore(db.Model):
    __tablename__ = "deal_scores"

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), unique=True,
                           nullable=False, index=True)

    # Original 5 scores (0-100 each)
    price_score = db.Column(db.Float, default=0)
    size_score = db.Column(db.Float, default=0)
    yard_score = db.Column(db.Float, default=0)
    feature_score = db.Column(db.Float, default=0)
    flood_score = db.Column(db.Float, default=0)

    # Extended 12 scores (0-100 each) — stored as JSON for flexibility
    extended_scores_json = db.Column(db.Text, default="{}")

    composite_score = db.Column(db.Float, default=0, index=True)
    scored_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    listing = db.relationship("Listing", back_populates="deal_score")

    @property
    def extended_scores(self) -> dict:
        try:
            return json.loads(self.extended_scores_json or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    @extended_scores.setter
    def extended_scores(self, val: dict):
        self.extended_scores_json = json.dumps(val)

    def get_all_scores(self) -> dict:
        """Return all scores (original + extended) as flat dict."""
        scores = {
            "price_score": self.price_score,
            "size_score": self.size_score,
            "yard_score": self.yard_score,
            "feature_score": self.feature_score,
            "flood_score": self.flood_score,
        }
        scores.update(self.extended_scores)
        scores["composite_score"] = self.composite_score
        return scores

    # Map each sub-score key to its importance key (without imp_ prefix).
    # Canonical definition lives in app.scraper.scorer; imported here to
    # avoid maintaining two copies.
    from app.scraper.scorer import SCORE_TO_IMP as _SCORE_TO_IMP
    SCORE_TO_IMP = _SCORE_TO_IMP

    def compute_user_composite(self, user_prefs: dict) -> float:
        """Compute composite score using a specific user's importance weights.

        Also recomputes the price sub-score using this user's price range,
        since that's the one sub-score that varies per user.

        Args:
            user_prefs: dict from user.get_prefs() with imp_* keys (0-10)
                        and min_price / max_price

        Returns:
            Weighted average composite score (0-100).
        """
        from app.scraper.scorer import score_price, score_proximity_poi

        all_scores = self.get_all_scores()

        # Recompute price score using THIS user's price range
        if self.listing and self.listing.price:
            user_max = user_prefs.get("max_price", 600000)
            user_min = user_prefs.get("min_price", 200000)
            all_scores["price_score"] = score_price(
                self.listing.price, max_price=user_max, min_price=user_min
            )

        # Recompute proximity POI score using user's selected landmark
        poi_lat = user_prefs.get("proximity_poi_lat")
        poi_lng = user_prefs.get("proximity_poi_lng")
        if poi_lat and poi_lng and self.listing and self.listing.latitude and self.listing.longitude:
            all_scores["proximity_poi_score"] = score_proximity_poi(
                self.listing.latitude, self.listing.longitude, poi_lat, poi_lng
            )

        total_imp = 0
        composite = 0.0

        for score_key, imp_name in self.SCORE_TO_IMP.items():
            importance = user_prefs.get(f"imp_{imp_name}", 0)
            total_imp += importance

        if total_imp <= 0:
            return 50.0  # no preferences set, neutral score

        for score_key, imp_name in self.SCORE_TO_IMP.items():
            importance = user_prefs.get(f"imp_{imp_name}", 0)
            weight = importance / total_imp
            sub_score = all_scores.get(score_key, 50)
            if sub_score is None:
                sub_score = 50
            composite += sub_score * weight

        return round(composite, 1)

    def get_user_scores(self, user_prefs: dict) -> dict:
        """Return all scores with price and proximity POI recalculated for this user.

        Used by the detail page to show per-user sub-scores.
        """
        from app.scraper.scorer import score_price, score_proximity_poi

        all_scores = self.get_all_scores()

        # Recompute price score for this user
        if self.listing and self.listing.price:
            user_max = user_prefs.get("max_price", 600000)
            user_min = user_prefs.get("min_price", 200000)
            all_scores["price_score"] = score_price(
                self.listing.price, max_price=user_max, min_price=user_min
            )

        # Recompute proximity POI score using user's selected landmark
        poi_lat = user_prefs.get("proximity_poi_lat")
        poi_lng = user_prefs.get("proximity_poi_lng")
        if poi_lat and poi_lng and self.listing and self.listing.latitude and self.listing.longitude:
            all_scores["proximity_poi_score"] = score_proximity_poi(
                self.listing.latitude, self.listing.longitude, poi_lat, poi_lng
            )

        # Replace composite with this user's composite
        all_scores["composite_score"] = self.compute_user_composite(user_prefs)

        return all_scores


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PER-USER FLAGS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class UserFlag(db.Model):
    __tablename__ = "user_flags"
    __table_args__ = (
        db.UniqueConstraint("user_id", "listing_id", name="uq_user_listing"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=False, index=True)
    flag = db.Column(db.String(20), nullable=False)
    note = db.Column(db.Text)
    flagged_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="flags")
    listing = db.relationship("Listing", back_populates="user_flags")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LISTING NOTES (per-user notes + visit status)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ListingNote(db.Model):
    __tablename__ = "listing_notes"
    __table_args__ = (
        db.UniqueConstraint("user_id", "listing_id", name="uq_note_user_listing"),
    )

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"),    nullable=False, index=True)
    listing_id  = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=False, index=True)

    note_text          = db.Column(db.Text, default="")
    visited            = db.Column(db.Boolean, default=False)
    scheduled_visit    = db.Column(db.Boolean, default=False)
    not_interested     = db.Column(db.Boolean, default=False)
    made_offer         = db.Column(db.Boolean, default=False)

    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    user    = db.relationship("User",    backref=db.backref("listing_notes", lazy="dynamic"))
    listing = db.relationship("Listing", backref=db.backref("listing_notes", lazy="dynamic"))

    @property
    def visit_status(self):
        """Human-readable visit status for display."""
        if self.made_offer:        return ("Made an Offer",       "success")
        if self.not_interested:    return ("Not Interested",       "secondary")
        if self.visited:           return ("Visited",              "info")
        if self.scheduled_visit:   return ("Visit Scheduled",      "warning")
        return None


# ====================================================================
#  API CALL LOG
# ====================================================================

class ApiCallLog(db.Model):
    __tablename__ = "api_call_log"

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    # nullable — scheduler/background fetches have no user
    call_type   = db.Column(db.String(30), nullable=False, index=True)
    # 'zillow', 'realtor', 'anthropic_deal', 'anthropic_portfolio',
    # 'anthropic_prefs', 'google_places', 'google_geocode'
    detail      = db.Column(db.String(200))   # e.g. listing address, flag type
    site_key    = db.Column(db.String(50))   # which market this call was for
    zip_code    = db.Column(db.String(10))   # specific zip queried
    trigger     = db.Column(db.String(20), default="manual")  # 'manual' | 'scheduled'
    success     = db.Column(db.Boolean, default=True)
    called_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    # Diagnostics (populated by scraper modules)
    response_time_ms = db.Column(db.Integer)     # API response time in ms
    http_status      = db.Column(db.Integer)     # HTTP status code
    results_count    = db.Column(db.Integer)     # number of results returned
    page_number      = db.Column(db.Integer)     # which page of pagination
    quota_remaining  = db.Column(db.Integer)     # X-RateLimit-requests-Remaining

    user = db.relationship("User", backref=db.backref("api_calls", lazy="dynamic"))

    # Cost estimates (USD) per call — update as pricing changes
    COST_MAP = {
        "zillow":              0.005,
        "realtor":             0.005,
        "zillow_detail":       0.005,
        "realtor_detail":      0.005,
        "anthropic_deal":      0.015,
        "anthropic_portfolio": 0.025,
        "anthropic_prefs":     0.012,
        "google_places":       0.017,
        "google_geocode":      0.005,
    }

    @property
    def estimated_cost(self):
        return self.COST_MAP.get(self.call_type, 0.0)

    @classmethod
    def log(cls, call_type, user_id=None, detail=None, success=True,
            trigger="manual", site_key=None, zip_code=None,
            response_time_ms=None, http_status=None, results_count=None,
            page_number=None, quota_remaining=None):
        """Convenience: create and commit a log entry. Never raises."""
        # Auto-detect site_key and user_id from request context if not provided
        try:
            from flask import g
            if site_key is None:
                site = getattr(g, "site", None)
                if site:
                    site_key = site.get("site_key")
            if user_id is None:
                from flask_login import current_user
                if current_user and getattr(current_user, "is_authenticated", False):
                    user_id = current_user.id
        except RuntimeError:
            pass  # outside request context
        try:
            entry = cls(
                call_type=call_type,
                user_id=user_id,
                detail=detail,
                site_key=site_key,
                zip_code=zip_code,
                trigger=trigger,
                success=success,
                response_time_ms=response_time_ms,
                http_status=http_status,
                results_count=results_count,
                page_number=page_number,
                quota_remaining=quota_remaining,
            )
            db.session.add(entry)
            db.session.commit()
        except Exception as exc:
            log.warning(f"ApiCallLog.log failed: {exc}")
            db.session.rollback()


# ====================================================================
#  CACHED AI ANALYSIS RESULTS
# ====================================================================

class CachedAnalysis(db.Model):
    __tablename__ = "cached_analysis"

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id"),
                              nullable=False, index=True)
    analysis_type = db.Column(db.String(60), nullable=False)
    # Types:
    #   'deal'                 — single listing AI brief (listing_id required)
    #   'portfolio_favorite'   — portfolio analysis for favorites
    #   'portfolio_maybe'      — portfolio analysis for maybes
    #   'portfolio_hidden'     — portfolio analysis for hidden
    #   'prefs'                — preferences coach result
    listing_id    = db.Column(db.Integer, db.ForeignKey("listings.id"),
                              nullable=True, index=True)
    result_json   = db.Column(db.Text, nullable=False)
    created_at    = db.Column(db.DateTime,
                              default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("user_id", "analysis_type", "listing_id",
                            name="uq_cached_analysis"),
    )

    user    = db.relationship("User",
                               backref=db.backref("cached_analyses", lazy="dynamic"))

    @classmethod
    def save(cls, user_id, analysis_type, result, listing_id=None):
        """Upsert a cached analysis result. Never raises."""
        import json
        from datetime import datetime
        try:
            existing = cls.query.filter_by(
                user_id=user_id,
                analysis_type=analysis_type,
                listing_id=listing_id,
            ).first()
            # Stamp the result with the analysis time before storing
            stamped = dict(result)
            _now = datetime.now()
            stamped["_analyzed_at"] = _now.strftime("%#I:%M %p, %b %#d %Y")
            blob = json.dumps(stamped)
            if existing:
                existing.result_json = blob
                existing.created_at  = datetime.now(timezone.utc)
            else:
                db.session.add(cls(
                    user_id=user_id,
                    analysis_type=analysis_type,
                    listing_id=listing_id,
                    result_json=blob,
                ))
            db.session.commit()
        except Exception as exc:
            log.warning(f"CachedAnalysis.save failed: {exc}")
            db.session.rollback()

    @classmethod
    def load(cls, user_id, analysis_type, listing_id=None):
        """Return the parsed result dict or None."""
        import json
        row = cls.query.filter_by(
            user_id=user_id,
            analysis_type=analysis_type,
            listing_id=listing_id,
        ).first()
        if row:
            try:
                return json.loads(row.result_json)
            except Exception:
                return None
        return None


# ====================================================================
#  AGENT CLIENT NOTES
# ====================================================================

class AgentClientNote(db.Model):
    __tablename__ = "agent_client_notes"
    __table_args__ = (
        db.UniqueConstraint("agent_id", "client_id", name="uq_acn_agent_client"),
    )

    id               = db.Column(db.Integer, primary_key=True)
    agent_id         = db.Column(db.Integer, db.ForeignKey("agent_profiles.id"),
                                 nullable=False, index=True)
    client_id        = db.Column(db.Integer, db.ForeignKey("users.id"),
                                 nullable=False, index=True)
    notes            = db.Column(db.Text, default="")
    pre_approved     = db.Column(db.Boolean, default=False)
    signed_agreement = db.Column(db.Boolean, default=False)
    tour_scheduled   = db.Column(db.Boolean, default=False)
    offer_submitted  = db.Column(db.Boolean, default=False)
    active_searching = db.Column(db.Boolean, default=False)
    updated_at       = db.Column(db.DateTime,
                                 default=lambda: datetime.now(timezone.utc),
                                 onupdate=lambda: datetime.now(timezone.utc))

    agent  = db.relationship("AgentProfile",
                              backref=db.backref("client_notes", lazy="dynamic"))
    client = db.relationship("User",
                              backref=db.backref("agent_notes", lazy="dynamic"))

    @classmethod
    def for_agent_client(cls, agent_id: int, client_id: int):
        """Return existing note or a new unsaved instance."""
        existing = cls.query.filter_by(
            agent_id=agent_id, client_id=client_id
        ).first()
        return existing or cls(agent_id=agent_id, client_id=client_id)


# ====================================================================
#  OWNER AGENT NOTES
# ====================================================================

class OwnerAgentNote(db.Model):
    __tablename__ = "owner_agent_notes"

    id                 = db.Column(db.Integer, primary_key=True)
    agent_id           = db.Column(db.Integer, db.ForeignKey("agent_profiles.id"),
                                   nullable=False, unique=True, index=True)
    notes              = db.Column(db.Text, default="")
    contract_signed    = db.Column(db.Boolean, default=False)
    background_checked = db.Column(db.Boolean, default=False)
    mls_verified       = db.Column(db.Boolean, default=False)
    updated_at         = db.Column(db.DateTime,
                                   default=lambda: datetime.now(timezone.utc),
                                   onupdate=lambda: datetime.now(timezone.utc))

    agent = db.relationship("AgentProfile",
                             backref=db.backref("owner_note", uselist=False))

    @classmethod
    def for_agent(cls, agent_id: int):
        """Return existing note or a new unsaved instance."""
        existing = cls.query.filter_by(agent_id=agent_id).first()
        return existing or cls(agent_id=agent_id)


# ====================================================================
#  PROMPT OVERRIDES
# ====================================================================

class PromptOverride(db.Model):
    __tablename__ = "prompt_overrides"
    __table_args__ = (
        db.UniqueConstraint("agent_id", "prompt_type", name="uq_po_agent_type"),
    )

    id           = db.Column(db.Integer, primary_key=True)
    agent_id     = db.Column(db.Integer, db.ForeignKey("agent_profiles.id"),
                              nullable=True, index=True)
    prompt_type  = db.Column(db.String(20), nullable=False)
    system_prompt = db.Column(db.Text, nullable=False)
    updated_at   = db.Column(db.DateTime,
                              default=lambda: datetime.now(timezone.utc),
                              onupdate=lambda: datetime.now(timezone.utc))

    agent = db.relationship("AgentProfile",
                             backref=db.backref("prompt_overrides", lazy="dynamic"))

    @classmethod
    def resolve(cls, prompt_type: str, agent_id) -> str | None:
        """Return the effective system prompt for a given type and agent.
        Checks agent-specific override first, then site-wide (agent_id=None),
        then returns None so the caller can fall back to DEFAULT_PROMPTS."""
        if agent_id:
            row = cls.query.filter_by(prompt_type=prompt_type, agent_id=agent_id).first()
            if row:
                return row.system_prompt
        # Site-wide fallback
        row = cls.query.filter_by(prompt_type=prompt_type, agent_id=None).first()
        return row.system_prompt if row else None

    @classmethod
    def upsert(cls, prompt_type: str, system_prompt: str, agent_id=None) -> None:
        """Create or update a prompt override row."""
        row = cls.query.filter_by(prompt_type=prompt_type, agent_id=agent_id).first()
        if row:
            row.system_prompt = system_prompt
        else:
            row = cls(prompt_type=prompt_type, system_prompt=system_prompt, agent_id=agent_id)
            db.session.add(row)
        db.session.commit()

    @classmethod
    def delete(cls, prompt_type: str, agent_id=None) -> None:
        """Delete a prompt override row if it exists."""
        row = cls.query.filter_by(prompt_type=prompt_type, agent_id=agent_id).first()
        if row:
            db.session.delete(row)
            db.session.commit()

    @classmethod
    def get_for_edit(cls, prompt_type: str, agent_id=None):
        """Return the row for editing, or None if not yet overridden."""
        return cls.query.filter_by(prompt_type=prompt_type, agent_id=agent_id).first()


# ====================================================================
#  STREET WATCH
# ====================================================================

class StreetWatch(db.Model):
    __tablename__ = "street_watches"
    __table_args__ = (
        db.UniqueConstraint("email", "street_name", "zip_code",
                            name="uq_sw_email_street_zip"),
    )

    id               = db.Column(db.Integer, primary_key=True)
    email            = db.Column(db.String(254), nullable=False, index=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    street_name      = db.Column(db.String(200), nullable=False)   # normalised uppercase
    zip_code         = db.Column(db.String(10), nullable=False)
    label            = db.Column(db.String(200))                    # display version
    is_active        = db.Column(db.Boolean, default=True, nullable=False)
    created_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_alerted_at  = db.Column(db.DateTime)
    unsubscribe_token = db.Column(db.String(64), unique=True, nullable=False)

    user   = db.relationship("User", backref=db.backref("street_watches", lazy="dynamic"))
    alerts = db.relationship("StreetWatchAlert", back_populates="watch",
                             cascade="all, delete-orphan", lazy="dynamic")


class StreetWatchAlert(db.Model):
    __tablename__ = "street_watch_alerts"
    __table_args__ = (
        db.UniqueConstraint("watch_id", "listing_id", "alert_type",
                            name="uq_swa_watch_listing_type"),
    )

    id          = db.Column(db.Integer, primary_key=True)
    watch_id    = db.Column(db.Integer, db.ForeignKey("street_watches.id"), nullable=False, index=True)
    listing_id  = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=False, index=True)
    alert_type  = db.Column(db.String(30), nullable=False)  # new_listing, price_drop, back_on_market
    detail_json = db.Column(db.Text, default="{}")
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    emailed_at  = db.Column(db.DateTime)

    watch   = db.relationship("StreetWatch", back_populates="alerts")
    listing = db.relationship("Listing")
