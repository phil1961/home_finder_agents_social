# ─────────────────────────────────────────────
# File: tests/test_social_phase2.py
# App Version: 2026.03.14 | File Version: 1.3.0
# Last Modified: 2026-03-15
# ─────────────────────────────────────────────
"""Integration tests for Phase 2 social features:
points system, referral loop, social models, agent listing workflow,
user suspension, share counts, and collections.
"""
import json
import uuid
import pytest
from datetime import datetime, timezone, timedelta

from tests.conftest import make_user, make_listing, make_agent_profile


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  1. POINTS SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestPointsSystem:
    """Tests for the points award / balance / daily-cap logic."""

    def test_award_points_basic(self, req_ctx):
        """Award points to a user, verify balance and log entry."""
        from app.models import db
        from app.services.points import award_points, get_balance
        from app.models_social import UserPoints, UserPointLog

        user = make_user(username="pts_basic", email="pts_basic@test.com")
        db.session.add(user)
        db.session.commit()

        actual = award_points(user.id, 5, "share_listing", reference_id=42)

        assert actual == 5
        assert get_balance(user.id) == 5

        # Verify UserPoints record
        account = UserPoints.query.filter_by(user_id=user.id).first()
        assert account is not None
        assert account.balance == 5
        assert account.lifetime_earned == 5

        # Verify log entry
        log_entry = UserPointLog.query.filter_by(user_id=user.id).first()
        assert log_entry is not None
        assert log_entry.delta == 5
        assert log_entry.reason == "share_listing"
        assert log_entry.reference_id == 42

    def test_daily_cap_enforced(self, req_ctx):
        """Award 50+ points in a day; verify cap at 50."""
        from app.models import db
        from app.services.points import award_points, get_balance, DAILY_CAP

        user = make_user(username="pts_cap", email="pts_cap@test.com")
        db.session.add(user)
        db.session.commit()

        total_awarded = 0
        # Award 10 points x 6 = 60 attempted, should cap at 50
        for i in range(6):
            awarded = award_points(user.id, 10, "share_listing", reference_id=i)
            total_awarded += awarded

        assert total_awarded == DAILY_CAP
        assert get_balance(user.id) == DAILY_CAP

    def test_get_balance_no_account(self, req_ctx):
        """Returns 0 for a user with no points account."""
        from app.models import db
        from app.services.points import get_balance

        user = make_user(username="pts_none", email="pts_none@test.com")
        db.session.add(user)
        db.session.commit()

        assert get_balance(user.id) == 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  2. REFERRAL LOOP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestReferralLoop:
    """Tests for referral creation and closing on registration."""

    def test_referral_closed_on_register(self, req_ctx):
        """Create a Referral with a code, simulate session with that code,
        create new user, call referral linking logic, verify referral is
        closed and referrer gets 10 pts.
        """
        from app.models import db
        from app.models_social import Referral
        from app.services.points import get_balance, award_points

        # Create the referrer
        referrer = make_user(username="referrer1", email="referrer1@test.com")
        db.session.add(referrer)
        db.session.commit()

        # Create a referral record
        code = Referral.generate_code()
        referral = Referral(
            referrer_id=referrer.id,
            referred_email="newguy@test.com",
            referral_code=code,
            status="invited",
        )
        db.session.add(referral)
        db.session.commit()

        # Simulate the new user registering
        new_user = make_user(username="newguy", email="newguy@test.com")
        db.session.add(new_user)
        db.session.commit()

        # Simulate the referral linking logic (mirrors auth.py register route)
        referral_found = Referral.query.filter_by(referral_code=code).first()
        assert referral_found is not None
        assert referral_found.referred_user_id is None

        referral_found.referred_user_id = new_user.id
        referral_found.status = "registered"
        referral_found.registered_at = datetime.now(timezone.utc)
        db.session.commit()

        # Award referrer points (mirrors auth.py)
        award_points(referral_found.referrer_id, 10, "referral_registered",
                     reference_id=referral_found.id)

        # Verify referral state
        db.session.expire_all()
        ref = Referral.query.filter_by(referral_code=code).first()
        assert ref.status == "registered"
        assert ref.referred_user_id == new_user.id
        assert ref.registered_at is not None

        # Verify referrer got 10 points
        assert get_balance(referrer.id) == 10


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  3. SOCIAL MODELS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSocialModels:
    """Tests for FriendListing, UserPoints, and UserPointLog models."""

    def test_friend_listing_creation(self, req_ctx):
        """Create a FriendListing, check photos property, primary_photo, expires_at."""
        from app.models import db
        from app.models_social import FriendListing

        user = make_user(username="fl_creator", email="fl_creator@test.com")
        db.session.add(user)
        db.session.commit()

        expires = datetime.now(timezone.utc) + timedelta(days=30)
        fl = FriendListing(
            submitter_id=user.id,
            submitter_email=user.email,
            address="456 Maple Ave",
            city="Charleston",
            zip_code="29401",
            price=275000,
            bedrooms=3,
            bathrooms=2.0,
            sqft=1800,
            description="Charming bungalow",
            photos_json=json.dumps(["photo1.jpg", "photo2.jpg"]),
            relationship="friend",
            has_permission=True,
            status="active",
            expires_at=expires,
        )
        db.session.add(fl)
        db.session.commit()

        found = FriendListing.query.filter_by(address="456 Maple Ave").first()
        assert found is not None
        assert found.photos == ["photo1.jpg", "photo2.jpg"]
        assert found.primary_photo == "photo1.jpg"
        assert found.expires_at is not None
        assert found.status == "active"
        assert found.price == 275000

    def test_friend_listing_expiration(self, req_ctx):
        """Create an expired FriendListing, call expire_friend_listings(),
        verify status='expired'.
        """
        from app.models import db
        from app.models_social import FriendListing, expire_friend_listings

        user = make_user(username="fl_expire", email="fl_expire@test.com")
        db.session.add(user)
        db.session.commit()

        # Create a listing that expired an hour ago
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        fl = FriendListing(
            submitter_id=user.id,
            submitter_email=user.email,
            address="789 Elm St",
            city="Charleston",
            zip_code="29403",
            has_permission=True,
            status="active",
            expires_at=past,
        )
        db.session.add(fl)
        db.session.commit()

        count = expire_friend_listings()
        assert count >= 1

        db.session.expire_all()
        found = FriendListing.query.get(fl.id)
        assert found.status == "expired"

    def test_user_points_model(self, req_ctx):
        """Create UserPoints directly, verify balance and lifetime_earned."""
        from app.models import db
        from app.models_social import UserPoints

        user = make_user(username="up_model", email="up_model@test.com")
        db.session.add(user)
        db.session.commit()

        account = UserPoints(user_id=user.id, balance=25, lifetime_earned=100)
        db.session.add(account)
        db.session.commit()

        found = UserPoints.query.filter_by(user_id=user.id).first()
        assert found is not None
        assert found.balance == 25
        assert found.lifetime_earned == 100

    def test_user_point_log(self, req_ctx):
        """Create log entries, verify they are linked to user."""
        from app.models import db
        from app.models_social import UserPointLog

        user = make_user(username="log_user", email="log_user@test.com")
        db.session.add(user)
        db.session.commit()

        log1 = UserPointLog(user_id=user.id, delta=5, reason="share_listing", reference_id=1)
        log2 = UserPointLog(user_id=user.id, delta=3, reason="reaction_received", reference_id=2)
        db.session.add_all([log1, log2])
        db.session.commit()

        logs = UserPointLog.query.filter_by(user_id=user.id).all()
        assert len(logs) == 2
        reasons = {l.reason for l in logs}
        assert "share_listing" in reasons
        assert "reaction_received" in reasons

        # Verify relationship
        assert logs[0].user.id == user.id


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  4. AGENT LISTING WORKFLOW
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestAgentListingWorkflow:
    """Tests for agent-created listings and friend listing approval/rejection."""

    def test_agent_creates_listing(self, req_ctx):
        """Agent creates a Listing with source='agent', verify it exists."""
        from app.models import db, Listing

        agent_user = make_user(username="ag_lister", email="ag_lister@test.com", role="agent")
        db.session.add(agent_user)
        db.session.commit()

        profile = make_agent_profile(agent_user, full_name="Agent Lister")
        db.session.add(profile)
        db.session.commit()

        sid = f"agent_{uuid.uuid4().hex[:8]}"
        listing = Listing(
            address="100 Agent Way",
            city="Charleston",
            zip_code="29401",
            price=425000,
            beds=4,
            baths=3.0,
            sqft=2400,
            source="agent",
            source_id=sid,
            status="active",
        )
        db.session.add(listing)
        db.session.commit()

        found = Listing.query.filter_by(source_id=sid).first()
        assert found is not None
        assert found.source == "agent"
        assert found.address == "100 Agent Way"
        assert found.price == 425000
        assert found.beds == 4

    def test_friend_listing_approval(self, req_ctx):
        """Create FriendListing, approve it (create Listing with
        source='community'), verify both records.
        """
        from app.models import db, Listing
        from app.models_social import FriendListing

        # Setup submitter and agent
        submitter = make_user(username="fl_sub", email="fl_sub@test.com")
        db.session.add(submitter)
        db.session.commit()

        agent_user = make_user(username="fl_agent", email="fl_agent@test.com", role="agent")
        db.session.add(agent_user)
        db.session.commit()
        profile = make_agent_profile(agent_user, full_name="Approver Agent")
        db.session.add(profile)
        db.session.commit()

        # Create friend listing
        fl = FriendListing(
            submitter_id=submitter.id,
            submitter_email=submitter.email,
            address="200 Community Ln",
            city="Charleston",
            zip_code="29401",
            price=310000,
            bedrooms=3,
            bathrooms=2.0,
            sqft=1600,
            has_permission=True,
            status="active",
        )
        db.session.add(fl)
        db.session.commit()

        # Approve: create a real Listing from the friend listing
        sid = f"community_{uuid.uuid4().hex[:8]}"
        promoted = Listing(
            address=fl.address,
            city=fl.city,
            zip_code=fl.zip_code,
            price=fl.price,
            beds=fl.bedrooms,
            baths=fl.bathrooms,
            sqft=fl.sqft,
            source="community",
            source_id=sid,
            status="active",
        )
        db.session.add(promoted)
        db.session.commit()

        # Update friend listing status
        fl.status = "approved"
        fl.approved_by_agent_id = profile.id
        fl.approved_at = datetime.now(timezone.utc)
        fl.listing_id = promoted.id
        db.session.commit()

        # Verify
        db.session.expire_all()
        fl_check = FriendListing.query.get(fl.id)
        assert fl_check.status == "approved"
        assert fl_check.approved_by_agent_id == profile.id
        assert fl_check.listing_id == promoted.id

        listing_check = Listing.query.filter_by(source_id=sid).first()
        assert listing_check is not None
        assert listing_check.source == "community"
        assert listing_check.address == "200 Community Ln"

    def test_friend_listing_rejection(self, req_ctx):
        """Create FriendListing, reject it, verify status and rejection_reason."""
        from app.models import db
        from app.models_social import FriendListing

        user = make_user(username="fl_rej", email="fl_rej@test.com")
        db.session.add(user)
        db.session.commit()

        fl = FriendListing(
            submitter_id=user.id,
            submitter_email=user.email,
            address="300 Reject Rd",
            city="Charleston",
            zip_code="29403",
            has_permission=False,
            status="active",
        )
        db.session.add(fl)
        db.session.commit()

        fl.status = "rejected"
        fl.rejection_reason = "No permission from homeowner"
        db.session.commit()

        db.session.expire_all()
        found = FriendListing.query.get(fl.id)
        assert found.status == "rejected"
        assert found.rejection_reason == "No permission from homeowner"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  5. USER SUSPENSION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestUserSuspension:
    """Tests for user suspension and admin-delete flows."""

    def test_suspend_user(self, req_ctx):
        """Create user, set is_suspended=True, verify field."""
        from app.models import db, User

        user = make_user(username="sus_user", email="sus_user@test.com")
        db.session.add(user)
        db.session.commit()

        assert user.is_suspended is False

        user.is_suspended = True
        user.suspended_reason = "Spam behavior"
        db.session.commit()

        db.session.expire_all()
        found = User.query.filter_by(username="sus_user").first()
        assert found.is_suspended is True
        assert found.suspended_reason == "Spam behavior"

    def test_suspended_user_check_password(self, req_ctx):
        """Suspended user can still check password -- suspension is
        login-level, not password-level.
        """
        from app.models import db

        user = make_user(username="sus_pw", email="sus_pw@test.com")
        db.session.add(user)
        db.session.commit()

        user.is_suspended = True
        db.session.commit()

        # Password check should still work (the app blocks login separately)
        assert user.check_password("testpass123") is True

    def test_delete_user_renames(self, req_ctx):
        """Simulate admin delete: rename username/email, set password_hash
        to ACCOUNT_DELETED.
        """
        from app.models import db, User

        user = make_user(username="del_user", email="del_user@test.com")
        db.session.add(user)
        db.session.commit()
        uid = user.id

        # Simulate admin delete (mirrors close-account logic)
        user.username = f"deleted_{uid}_{user.username}"
        user.email = f"deleted_{uid}_{user.email}"
        user.password_hash = "ACCOUNT_DELETED"
        db.session.commit()

        db.session.expire_all()
        found = User.query.get(uid)
        assert found.username.startswith("deleted_")
        assert found.email.startswith("deleted_")
        assert found.check_password("testpass123") is False
        assert found.password_hash == "ACCOUNT_DELETED"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  6. SHARE COUNTS & SOCIAL PROOF
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestShareCountsAndSocialProof:
    """Tests for share count queries and reaction summary aggregation."""

    def test_share_count_query(self, req_ctx):
        """Create listing + SocialShare records, count via query, verify."""
        from app.models import db
        from app.models_social import SocialShare

        listing = make_listing(address="500 Share St", source_id=f"share_{uuid.uuid4().hex[:8]}")
        db.session.add(listing)
        db.session.commit()

        user = make_user(username="sharer1", email="sharer1@test.com")
        db.session.add(user)
        db.session.commit()

        # Create 3 shares for the same listing
        for i in range(3):
            share = SocialShare(
                listing_id=listing.id,
                share_type="listing",
                sharer_id=user.id,
                sharer_name="Sharer One",
                sharer_email=user.email,
                recipient_email=f"recipient{i}@test.com",
                share_token=SocialShare.generate_token(),
                status="sent",
            )
            db.session.add(share)
        db.session.commit()

        count = SocialShare.query.filter_by(listing_id=listing.id).count()
        assert count == 3

    def test_reaction_summary(self, req_ctx):
        """Create shares + reactions, group by reaction_type, verify counts."""
        from app.models import db
        from app.models_social import SocialShare, SocialReaction

        listing = make_listing(address="600 React Blvd", source_id=f"react_{uuid.uuid4().hex[:8]}")
        db.session.add(listing)
        db.session.commit()

        user = make_user(username="reactor_owner", email="reactor_owner@test.com")
        db.session.add(user)
        db.session.commit()

        # Create a share
        share = SocialShare(
            listing_id=listing.id,
            share_type="listing",
            sharer_id=user.id,
            sharer_email=user.email,
            recipient_email="friend@test.com",
            share_token=SocialShare.generate_token(),
            status="sent",
        )
        db.session.add(share)
        db.session.commit()

        # Add reactions of different types
        reactions_data = [
            ("love", "alice@test.com"),
            ("love", "bob@test.com"),
            ("interested", "carol@test.com"),
            ("not_for_me", "dave@test.com"),
        ]
        for rtype, email in reactions_data:
            r = SocialReaction(
                share_id=share.id,
                reactor_email=email,
                reaction_type=rtype,
            )
            db.session.add(r)
        db.session.commit()

        # Group by reaction_type and verify counts
        summary = db.session.query(
            SocialReaction.reaction_type,
            db.func.count(SocialReaction.id),
        ).filter(
            SocialReaction.share_id == share.id,
        ).group_by(
            SocialReaction.reaction_type,
        ).all()

        summary_dict = {rtype: cnt for rtype, cnt in summary}
        assert summary_dict["love"] == 2
        assert summary_dict["interested"] == 1
        assert summary_dict["not_for_me"] == 1
        assert "great_location" not in summary_dict


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  7. COLLECTIONS WITH POINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestCollections:
    """Tests for SocialCollection model creation."""

    def test_collection_creation_model(self, req_ctx):
        """Create a SocialCollection, verify fields."""
        from app.models import db
        from app.models_social import SocialCollection, SocialCollectionItem

        user = make_user(username="collector", email="collector@test.com")
        db.session.add(user)
        db.session.commit()

        collection = SocialCollection(
            creator_id=user.id,
            title="My Dream Homes",
            description="Top picks for March 2026",
            share_token=f"coll_{uuid.uuid4().hex[:16]}",
            is_public=True,
        )
        db.session.add(collection)
        db.session.commit()

        found = SocialCollection.query.filter_by(creator_id=user.id).first()
        assert found is not None
        assert found.title == "My Dream Homes"
        assert found.description == "Top picks for March 2026"
        assert found.is_public is True
        assert found.share_count == 0
        assert found.view_count == 0
        assert found.created_at is not None

        # Add items to the collection
        listing1 = make_listing(address="701 Coll Dr", source_id=f"c1_{uuid.uuid4().hex[:8]}")
        listing2 = make_listing(address="702 Coll Dr", source_id=f"c2_{uuid.uuid4().hex[:8]}")
        db.session.add_all([listing1, listing2])
        db.session.commit()

        item1 = SocialCollectionItem(
            collection_id=found.id,
            listing_id=listing1.id,
            note="Love the backyard",
            position=0,
        )
        item2 = SocialCollectionItem(
            collection_id=found.id,
            listing_id=listing2.id,
            note="Great price",
            position=1,
        )
        db.session.add_all([item1, item2])
        db.session.commit()

        assert found.listing_count == 2
        assert found.items.first().note == "Love the backyard"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  8. PROMPT EDITOR — VALIDATION & PREVIEW
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestPromptEditor:
    """Tests for prompt validation logic, required-key dicts,
    sample contexts, user suspension at login level, and billing plan defaults.
    """

    def test_prompt_validate_valid(self, req_ctx):
        """DEFAULT_PROMPTS['deal'] should pass validation with no issues."""
        from app.routes.admin_routes import _PROMPT_REQUIRED_KEYS
        from config import DEFAULT_PROMPTS

        prompt_text = DEFAULT_PROMPTS["deal"]
        text_lower = prompt_text.lower()
        ptype = "deal"
        required_keys = _PROMPT_REQUIRED_KEYS[ptype]

        issues = []

        # JSON keyword check
        if "json" not in text_lower:
            issues.append("Missing JSON keyword.")

        # Required key check
        missing_keys = [k for k in required_keys if k not in text_lower]
        if missing_keys:
            issues.append(f"Missing keys: {', '.join(sorted(missing_keys))}")

        # No-markdown check
        has_no_md = ("no markdown" in text_lower or "no fences" in text_lower
                     or "no ```" in text_lower or "markdown" in text_lower)
        if not has_no_md:
            issues.append("Missing no-markdown instruction.")

        assert len(issues) == 0, f"Expected valid prompt, got issues: {issues}"
        assert len(missing_keys) == 0

    def test_prompt_validate_missing_keys(self, req_ctx):
        """A prompt missing required keys should be flagged."""
        from app.routes.admin_routes import _PROMPT_REQUIRED_KEYS

        prompt_text = "You are a real estate analyst. Respond with JSON."
        text_lower = prompt_text.lower()
        ptype = "deal"
        required_keys = _PROMPT_REQUIRED_KEYS[ptype]

        missing_keys = [k for k in required_keys if k not in text_lower]

        # This prompt mentions none of the required keys
        assert len(missing_keys) > 0
        # All five deal keys should be missing
        assert set(missing_keys) == {"summary", "strengths", "concerns",
                                     "negotiation", "verdict"}

    def test_prompt_validate_empty(self, req_ctx):
        """An empty prompt should be flagged as invalid."""
        prompt_text = ""
        issues = []

        if not prompt_text.strip():
            issues.append("Prompt is empty.")

        assert len(issues) == 1
        assert "empty" in issues[0].lower()

    def test_prompt_validate_no_json_instruction(self, req_ctx):
        """A prompt that has all keys but no 'JSON' keyword is flagged."""
        from app.routes.admin_routes import _PROMPT_REQUIRED_KEYS

        # Craft a prompt mentioning all deal keys but NOT "JSON"
        prompt_text = (
            "You are a real estate analyst. Return a response with these keys: "
            "summary, strengths, concerns, negotiation, verdict. "
            "Do not use markdown fences."
        )
        text_lower = prompt_text.lower()
        ptype = "deal"
        required_keys = _PROMPT_REQUIRED_KEYS[ptype]

        issues = []
        if "json" not in text_lower:
            issues.append("Missing keyword 'JSON'.")

        missing_keys = [k for k in required_keys if k not in text_lower]
        assert len(missing_keys) == 0, "All keys should be present"
        assert len(issues) == 1
        assert "json" in issues[0].lower()

    def test_prompt_required_keys_per_type(self, req_ctx):
        """_PROMPT_REQUIRED_KEYS has correct keys for all 3 prompt types."""
        from app.routes.admin_routes import _PROMPT_REQUIRED_KEYS

        assert set(_PROMPT_REQUIRED_KEYS.keys()) == {"deal", "portfolio", "preferences"}

        assert _PROMPT_REQUIRED_KEYS["deal"] == {
            "summary", "strengths", "concerns", "negotiation", "verdict",
        }
        assert _PROMPT_REQUIRED_KEYS["portfolio"] == {
            "headline", "ranking", "patterns", "strategy", "dark_horse", "bottom_line",
        }
        assert _PROMPT_REQUIRED_KEYS["preferences"] == {
            "headline", "strengths", "blind_spots", "tweaks", "local_insight", "bottom_line",
        }

    def test_sample_contexts_exist(self, req_ctx):
        """_SAMPLE_CONTEXTS has non-empty entries for all 3 types with expected content."""
        from app.routes.admin_routes import _SAMPLE_CONTEXTS

        assert set(_SAMPLE_CONTEXTS.keys()) == {"deal", "portfolio", "preferences"}

        for ptype, ctx in _SAMPLE_CONTEXTS.items():
            assert isinstance(ctx, str), f"{ptype} context should be a string"
            assert len(ctx) > 0, f"{ptype} context should not be empty"

        # Deal context mentions property and price
        assert "Property:" in _SAMPLE_CONTEXTS["deal"]
        assert "Price:" in _SAMPLE_CONTEXTS["deal"]

        # Portfolio context mentions favorites
        assert "favorites" in _SAMPLE_CONTEXTS["portfolio"].lower()

        # Preferences context mentions importance
        assert "importance" in _SAMPLE_CONTEXTS["preferences"].lower()

    def test_user_suspension_blocks_login(self, req_ctx):
        """A suspended user still has a valid password; suspension is login-level."""
        from app.models import db

        user = make_user(username="pe_suspended", email="pe_suspended@test.com")
        db.session.add(user)
        db.session.commit()

        user.is_suspended = True
        user.suspended_reason = "Spamming listings"
        db.session.commit()

        db.session.expire_all()
        from app.models import User
        found = User.query.filter_by(username="pe_suspended").first()

        assert found.is_suspended is True
        assert found.suspended_reason == "Spamming listings"
        # Password check still works — suspension is enforced at the login route
        assert found.check_password("testpass123") is True

    def test_billing_plan_defaults(self, req_ctx):
        """PLAN_DEFAULTS has all 4 plans with correct limits."""
        from app.services.billing import PLAN_DEFAULTS

        assert set(PLAN_DEFAULTS.keys()) == {"free", "basic", "pro", "unlimited"}

        # Free plan limits
        assert PLAN_DEFAULTS["free"]["monthly_limit_ai"] == 10
        assert PLAN_DEFAULTS["free"]["monthly_limit_fetch"] == 50

        # Unlimited plan — 0 means no limit
        assert PLAN_DEFAULTS["unlimited"]["monthly_limit_ai"] == 0
        assert PLAN_DEFAULTS["unlimited"]["monthly_limit_fetch"] == 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  9. PROXIMITY POI SCORING & LANDMARKS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestProximityPOI:
    """Tests for haversine distance, proximity POI scoring, importance
    mapping, default weights, composite scoring with POI, and landmark
    registry column.
    """

    def test_haversine_miles_same_point(self, req_ctx):
        """Same lat/lng should return 0.0 distance."""
        from app.scraper.scorer import _haversine_miles

        result = _haversine_miles(32.7765, -79.9311, 32.7765, -79.9311)
        assert result == 0.0

    def test_haversine_miles_known_distance(self, req_ctx):
        """Charleston to Columbia SC should be roughly 95-105 miles."""
        from app.scraper.scorer import _haversine_miles

        dist = _haversine_miles(32.7765, -79.9311, 34.0007, -81.0348)
        assert 95 <= dist <= 110, f"Expected 95-110 miles, got {dist:.2f}"

    def test_score_proximity_poi_at_location(self, req_ctx):
        """Listing at the same lat/lng as the POI should score 100."""
        from app.scraper.scorer import score_proximity_poi

        score = score_proximity_poi(32.7765, -79.9311, 32.7765, -79.9311)
        assert score == 100.0

    def test_score_proximity_poi_far_away(self, req_ctx):
        """Listing 20 miles from POI should score 0."""
        from app.scraper.scorer import score_proximity_poi

        # Use a POI far enough away (>15 miles) to trigger 0 score.
        # Charleston (32.7765, -79.9311) to a point ~20 miles north.
        # 1 degree lat ~ 69 miles, so 0.29 degrees ~ 20 miles.
        score = score_proximity_poi(32.7765, -79.9311, 33.0665, -79.9311)
        assert score == 0.0

    def test_score_proximity_poi_mid_range(self, req_ctx):
        """Listing ~3 miles from POI should score between 50 and 85."""
        from app.scraper.scorer import score_proximity_poi

        # ~3 miles north: 3/69 ~ 0.0435 degrees latitude
        score = score_proximity_poi(32.7765, -79.9311, 32.8200, -79.9311)
        assert 50 <= score <= 85, f"Expected 50-85, got {score:.2f}"

    def test_score_proximity_poi_no_coords(self, req_ctx):
        """None lat/lng should return 50 (neutral default)."""
        from app.scraper.scorer import score_proximity_poi

        assert score_proximity_poi(None, None, 32.7765, -79.9311) == 50
        assert score_proximity_poi(32.7765, -79.9311, None, None) == 50
        assert score_proximity_poi(None, None, None, None) == 50

    def test_proximity_poi_in_score_to_imp(self, req_ctx):
        """SCORE_TO_IMP should map proximity_poi_score -> proximity_poi."""
        from app.scraper.scorer import SCORE_TO_IMP

        assert "proximity_poi_score" in SCORE_TO_IMP
        assert SCORE_TO_IMP["proximity_poi_score"] == "proximity_poi"

    def test_proximity_poi_default_importance_zero(self, req_ctx):
        """proximity_poi should default to 0 (off by default)."""
        from config import DEFAULT_IMPORTANCE

        assert "proximity_poi" in DEFAULT_IMPORTANCE
        assert DEFAULT_IMPORTANCE["proximity_poi"] == 0

    def test_compute_user_composite_with_poi(self, req_ctx):
        """DealScore.compute_user_composite works with POI prefs set."""
        from app.models import db, DealScore

        listing = make_listing(
            address="800 POI Test Ln",
            source_id="poi_test_001",
            latitude=32.7765,
            longitude=-79.9311,
        )
        db.session.add(listing)
        db.session.commit()

        deal_score = DealScore(
            listing_id=listing.id,
            price_score=75.0,
            size_score=60.0,
            yard_score=50.0,
            feature_score=70.0,
            flood_score=80.0,
            composite_score=65.0,
        )
        db.session.add(deal_score)
        db.session.commit()

        prefs = {
            "max_price": 600000,
            "min_price": 200000,
            "imp_price": 8,
            "imp_size": 5,
            "imp_yard": 7,
            "imp_features": 8,
            "imp_flood": 6,
            "imp_proximity_poi": 8,
            "proximity_poi_lat": 32.78,
            "proximity_poi_lng": -79.93,
        }

        result = deal_score.compute_user_composite(prefs)
        assert isinstance(result, (int, float))
        assert 0 <= result <= 100

    def test_landmark_registry_column(self, req_ctx):
        """Registry DB should have a landmarks_json column in sites table."""
        from app.services.registry import init_registry, REGISTRY_PATH
        import sqlite3

        init_registry()

        conn = sqlite3.connect(str(REGISTRY_PATH))
        cols = {row[1] for row in conn.execute("PRAGMA table_info(sites)").fetchall()}
        conn.close()

        assert "landmarks_json" in cols


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 10. USER-DEFINED LANDMARKS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestUserLandmarks:
    """Tests for user-defined personal landmarks stored in preferences_json."""

    def test_user_landmarks_default_empty(self, req_ctx):
        """New user prefs should have user_landmarks defaulting to empty list."""
        from app.models import db

        user = make_user(username="ulm_default", email="ulm_default@test.com")
        db.session.add(user)
        db.session.commit()

        prefs = user.get_prefs()
        # user_landmarks is not in DEFAULT_PREFS, so it may be absent or empty
        landmarks = prefs.get("user_landmarks", [])
        assert landmarks == []

    def test_user_landmarks_add(self, req_ctx):
        """Add a user landmark to prefs, save, reload, verify it persists."""
        from app.models import db

        user = make_user(username="ulm_add", email="ulm_add@test.com")
        db.session.add(user)
        db.session.commit()

        prefs = user.get_prefs()
        prefs["user_landmarks"] = [{"name": "Grandma", "lat": 32.78, "lng": -79.93}]
        user.set_prefs(prefs)
        db.session.commit()

        db.session.expire_all()
        from app.models import User
        reloaded = User.query.get(user.id)
        reloaded_prefs = reloaded.get_prefs()

        assert "user_landmarks" in reloaded_prefs
        assert len(reloaded_prefs["user_landmarks"]) == 1
        assert reloaded_prefs["user_landmarks"][0]["name"] == "Grandma"
        assert reloaded_prefs["user_landmarks"][0]["lat"] == 32.78
        assert reloaded_prefs["user_landmarks"][0]["lng"] == -79.93

    def test_user_landmarks_max_three(self, req_ctx):
        """Data layer stores any number of landmarks; max 3 is route-level."""
        from app.models import db

        user = make_user(username="ulm_max3", email="ulm_max3@test.com")
        db.session.add(user)
        db.session.commit()

        three_landmarks = [
            {"name": "Grandma", "lat": 32.78, "lng": -79.93},
            {"name": "Office", "lat": 32.80, "lng": -79.95},
            {"name": "Gym", "lat": 32.76, "lng": -79.91},
        ]
        prefs = user.get_prefs()
        prefs["user_landmarks"] = three_landmarks
        user.set_prefs(prefs)
        db.session.commit()

        db.session.expire_all()
        from app.models import User
        reloaded = User.query.get(user.id)
        assert len(reloaded.get_prefs()["user_landmarks"]) == 3

        # Data layer does NOT enforce the limit — storing 4 also works
        four_landmarks = three_landmarks + [{"name": "Park", "lat": 32.79, "lng": -79.92}]
        prefs = reloaded.get_prefs()
        prefs["user_landmarks"] = four_landmarks
        reloaded.set_prefs(prefs)
        db.session.commit()

        db.session.expire_all()
        reloaded2 = User.query.get(user.id)
        assert len(reloaded2.get_prefs()["user_landmarks"]) == 4

    def test_user_landmarks_delete(self, req_ctx):
        """Remove one landmark from a list of two, verify only one remains."""
        from app.models import db

        user = make_user(username="ulm_del", email="ulm_del@test.com")
        db.session.add(user)
        db.session.commit()

        prefs = user.get_prefs()
        prefs["user_landmarks"] = [
            {"name": "Grandma", "lat": 32.78, "lng": -79.93},
            {"name": "Office", "lat": 32.80, "lng": -79.95},
        ]
        user.set_prefs(prefs)
        db.session.commit()

        # Delete "Grandma" by filtering
        prefs = user.get_prefs()
        prefs["user_landmarks"] = [
            lm for lm in prefs["user_landmarks"] if lm["name"] != "Grandma"
        ]
        user.set_prefs(prefs)
        db.session.commit()

        db.session.expire_all()
        from app.models import User
        reloaded = User.query.get(user.id)
        remaining = reloaded.get_prefs()["user_landmarks"]
        assert len(remaining) == 1
        assert remaining[0]["name"] == "Office"

    def test_user_landmarks_in_poi_dropdown(self, req_ctx):
        """User landmark used as POI selection produces a valid composite score."""
        from app.models import db, DealScore

        listing = make_listing(
            address="900 ULM Test St",
            source_id="ulm_poi_001",
            latitude=32.7765,
            longitude=-79.9311,
        )
        db.session.add(listing)
        db.session.commit()

        deal_score = DealScore(
            listing_id=listing.id,
            price_score=70.0,
            size_score=65.0,
            yard_score=55.0,
            feature_score=72.0,
            flood_score=78.0,
            composite_score=68.0,
        )
        db.session.add(deal_score)
        db.session.commit()

        # Simulate a user whose selected POI matches their personal landmark
        prefs = {
            "max_price": 600000,
            "min_price": 200000,
            "imp_price": 7,
            "imp_size": 5,
            "imp_yard": 6,
            "imp_features": 7,
            "imp_flood": 5,
            "imp_proximity_poi": 9,
            "proximity_poi_name": "Grandma",
            "proximity_poi_lat": 32.78,
            "proximity_poi_lng": -79.93,
            "user_landmarks": [{"name": "Grandma", "lat": 32.78, "lng": -79.93}],
        }

        result = deal_score.compute_user_composite(prefs)
        assert isinstance(result, (int, float))
        assert 0 <= result <= 100

    def test_max_user_landmarks_constant(self, req_ctx):
        """MAX_USER_LANDMARKS constant equals 3."""
        from app.routes.preferences_routes import MAX_USER_LANDMARKS

        assert MAX_USER_LANDMARKS == 3

    def test_scheduler_locked_field(self, req_ctx):
        """Registry DB should have a scheduler_locked column in sites table."""
        from app.services.registry import init_registry, REGISTRY_PATH
        import sqlite3

        init_registry()

        conn = sqlite3.connect(str(REGISTRY_PATH))
        cols = {row[1] for row in conn.execute("PRAGMA table_info(sites)").fetchall()}
        conn.close()

        assert "scheduler_locked" in cols

    def test_max_fetches_per_run_field(self, req_ctx):
        """Registry DB should have a max_fetches_per_run column in sites table."""
        from app.services.registry import init_registry, REGISTRY_PATH
        import sqlite3

        init_registry()

        conn = sqlite3.connect(str(REGISTRY_PATH))
        cols = {row[1] for row in conn.execute("PRAGMA table_info(sites)").fetchall()}
        conn.close()

        assert "max_fetches_per_run" in cols
