# ─────────────────────────────────────────────
# File: app/models_social.py
# App Version: 2026.03.14 | File Version: 1.2.0
# Last Modified: 2026-03-14
# ─────────────────────────────────────────────
"""Social feature models for HomeFinder Social."""
import json
import secrets
from datetime import datetime, timezone

from app.models import db

MODULE_VERSION = "2026.03.13-social"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SOCIAL SHARES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SocialShare(db.Model):
    """A listing or collection shared from one person to another."""
    __tablename__ = "social_shares"

    id = db.Column(db.Integer, primary_key=True)

    # What was shared
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=True, index=True)
    collection_id = db.Column(db.Integer, db.ForeignKey("social_collections.id"), nullable=True, index=True)
    share_type = db.Column(db.String(20), nullable=False, default="listing")  # listing, collection

    # Who shared it (nullable for guests)
    sharer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    sharer_name = db.Column(db.String(120))
    sharer_email = db.Column(db.String(254))

    # Who it was shared with
    recipient_email = db.Column(db.String(254), nullable=False, index=True)
    recipient_name = db.Column(db.String(120))
    recipient_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)

    # Context
    relationship = db.Column(db.String(30))  # friend, family, coworker, neighbor, client, agent
    message = db.Column(db.Text)  # personal note

    # Tracking
    share_token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    status = db.Column(db.String(20), default="sent", nullable=False)  # sent, viewed, clicked, replied
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    viewed_at = db.Column(db.DateTime)
    clicked_at = db.Column(db.DateTime)

    # Relationships
    sharer = db.relationship("User", foreign_keys=[sharer_id],
                             backref=db.backref("shares_sent", lazy="dynamic"))
    recipient_user = db.relationship("User", foreign_keys=[recipient_user_id],
                                     backref=db.backref("shares_received", lazy="dynamic"))
    listing = db.relationship("Listing", backref=db.backref("social_shares", lazy="dynamic"))
    collection = db.relationship("SocialCollection", foreign_keys=[collection_id],
                                 backref=db.backref("shares", lazy="dynamic"))
    reactions = db.relationship("SocialReaction", back_populates="share",
                                cascade="all, delete-orphan", lazy="dynamic")

    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)

    def mark_viewed(self):
        if not self.viewed_at:
            self.viewed_at = datetime.now(timezone.utc)
            if self.status == "sent":
                self.status = "viewed"

    def mark_clicked(self):
        if not self.clicked_at:
            self.clicked_at = datetime.now(timezone.utc)
            self.status = "clicked"

    def __repr__(self):
        return f"<SocialShare {self.share_type} → {self.recipient_email}>"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SOCIAL REACTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REACTION_TYPES = [
    ("love", "Love It", "bi-heart-fill", "text-danger"),
    ("interested", "Interested", "bi-eye-fill", "text-primary"),
    ("great_location", "Great Location", "bi-geo-alt-fill", "text-success"),
    ("too_expensive", "Too Pricey", "bi-currency-dollar", "text-warning"),
    ("not_for_me", "Not For Me", "bi-x-circle", "text-secondary"),
]


class SocialReaction(db.Model):
    """A recipient's reaction to a shared listing."""
    __tablename__ = "social_reactions"
    __table_args__ = (
        db.UniqueConstraint("share_id", "reactor_email", name="uq_reaction_share_reactor"),
    )

    id = db.Column(db.Integer, primary_key=True)
    share_id = db.Column(db.Integer, db.ForeignKey("social_shares.id"), nullable=False, index=True)
    reactor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reactor_email = db.Column(db.String(254), nullable=False)
    reaction_type = db.Column(db.String(30), nullable=False)  # love, interested, great_location, too_expensive, not_for_me
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    share = db.relationship("SocialShare", back_populates="reactions")
    reactor = db.relationship("User", backref=db.backref("social_reactions", lazy="dynamic"))

    def __repr__(self):
        return f"<SocialReaction {self.reaction_type} by {self.reactor_email}>"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SOCIAL COLLECTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SocialCollection(db.Model):
    """A curated group of listings that can be shared."""
    __tablename__ = "social_collections"

    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    share_token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    is_public = db.Column(db.Boolean, default=False)
    share_count = db.Column(db.Integer, default=0)
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    creator = db.relationship("User", backref=db.backref("social_collections", lazy="dynamic"))
    items = db.relationship("SocialCollectionItem", back_populates="collection",
                            cascade="all, delete-orphan", lazy="dynamic",
                            order_by="SocialCollectionItem.position")

    @property
    def listing_count(self):
        return self.items.count()

    def __repr__(self):
        return f"<SocialCollection '{self.title}' by user {self.creator_id}>"


class SocialCollectionItem(db.Model):
    """A listing within a collection."""
    __tablename__ = "social_collection_items"
    __table_args__ = (
        db.UniqueConstraint("collection_id", "listing_id", name="uq_collection_listing"),
    )

    id = db.Column(db.Integer, primary_key=True)
    collection_id = db.Column(db.Integer, db.ForeignKey("social_collections.id"), nullable=False, index=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=False, index=True)
    note = db.Column(db.Text)  # why this listing is in the collection
    position = db.Column(db.Integer, default=0)
    added_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    collection = db.relationship("SocialCollection", back_populates="items")
    listing = db.relationship("Listing")

    def __repr__(self):
        return f"<SocialCollectionItem collection={self.collection_id} listing={self.listing_id}>"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  REFERRALS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Referral(db.Model):
    """Tracks user referrals for monetization."""
    __tablename__ = "referrals"
    __table_args__ = (
        db.UniqueConstraint("referrer_id", "referred_email", name="uq_referral_pair"),
    )

    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    referred_email = db.Column(db.String(254), nullable=False, index=True)
    referred_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    referral_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    status = db.Column(db.String(20), default="invited", nullable=False)  # invited, registered, active, converted
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    registered_at = db.Column(db.DateTime)
    converted_at = db.Column(db.DateTime)

    referrer = db.relationship("User", foreign_keys=[referrer_id],
                               backref=db.backref("referrals_sent", lazy="dynamic"))
    referred_user = db.relationship("User", foreign_keys=[referred_user_id],
                                    backref=db.backref("referred_by", lazy="dynamic"))

    @staticmethod
    def generate_code():
        return secrets.token_urlsafe(8).upper()[:10]

    def __repr__(self):
        return f"<Referral {self.referral_code} → {self.referred_email}>"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  USER POINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class UserPoints(db.Model):
    """Aggregate points balance for a user."""
    __tablename__ = "user_points"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False, index=True)
    balance = db.Column(db.Integer, default=0, nullable=False)
    lifetime_earned = db.Column(db.Integer, default=0, nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref=db.backref("points_account", uselist=False))

    def __repr__(self):
        return f"<UserPoints user={self.user_id} balance={self.balance}>"


class UserPointLog(db.Model):
    """Individual points transaction log entry."""
    __tablename__ = "user_point_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    delta = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(50), nullable=False)  # share_listing, reaction_received, referral_registered, collection_created, friend_listing
    reference_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref=db.backref("point_logs", lazy="dynamic"))

    def __repr__(self):
        return f"<UserPointLog user={self.user_id} delta={self.delta} reason={self.reason}>"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  FRIEND LISTINGS ("Add a Home")
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class FriendListing(db.Model):
    """A user-submitted listing (friend's home, neighbor, etc.)."""
    __tablename__ = "friend_listings"

    id = db.Column(db.Integer, primary_key=True)
    submitter_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    submitter_email = db.Column(db.String(254), nullable=False)
    address = db.Column(db.String(300), nullable=False)
    city = db.Column(db.String(100))
    zip_code = db.Column(db.String(10), index=True)
    price = db.Column(db.Integer)
    bedrooms = db.Column(db.Integer)
    bathrooms = db.Column(db.Float)
    sqft = db.Column(db.Integer)
    description = db.Column(db.Text)
    photos_json = db.Column(db.Text, default="[]")  # JSON array of filenames
    relationship = db.Column(db.String(30))  # my_home, friend, neighbor, family
    has_permission = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(20), default="active", nullable=False)  # active, expired, removed, approved, rejected
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime)

    # Agent approval workflow
    approved_by_agent_id = db.Column(db.Integer, db.ForeignKey("agent_profiles.id"), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=True)
    rejection_reason = db.Column(db.String(200), nullable=True)

    submitter = db.relationship("User", backref=db.backref("friend_listings", lazy="dynamic"))
    approved_by_agent = db.relationship("AgentProfile", backref=db.backref("approved_friend_listings", lazy="dynamic"))
    promoted_listing = db.relationship("Listing", backref=db.backref("friend_listing_source", uselist=False))

    @property
    def photos(self):
        try:
            return json.loads(self.photos_json or "[]")
        except (ValueError, TypeError):
            return []

    @property
    def primary_photo(self):
        photos = self.photos
        return photos[0] if photos else None

    def __repr__(self):
        return f"<FriendListing '{self.address}' by {self.submitter_email}>"


def expire_friend_listings():
    """Mark expired friend listings. Safe to call from pipeline or startup."""
    now = datetime.now(timezone.utc)
    expired = FriendListing.query.filter(
        FriendListing.status == "active",
        FriendListing.expires_at <= now,
    ).all()
    for fl in expired:
        fl.status = "expired"
    if expired:
        db.session.commit()
    return len(expired)
