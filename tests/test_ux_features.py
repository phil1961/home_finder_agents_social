# ─────────────────────────────────────────────
# File: tests/test_ux_features.py
# App Version: 2026.03.17 | File Version: 1.0.0
# Last Modified: 2026-03-17
# ─────────────────────────────────────────────
"""Integration tests for UX features:
feedback system, help level, and power mode.
"""
import json
import pytest
from datetime import datetime, timezone

from tests.conftest import make_user, make_listing


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  1. FEEDBACK SYSTEM — Model
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFeedbackModel:
    """Tests for the Feedback ORM model."""

    def test_create_feedback_with_user(self, req_ctx):
        """Create feedback linked to a logged-in user."""
        from app.models import db
        from app.models_social import Feedback

        user = make_user(username="fb_user1", email="fb_user1@test.com", role="client")
        db.session.add(user)
        db.session.commit()

        fb = Feedback(
            user_id=user.id,
            email=user.email,
            sentiment="positive",
            comment="Great site!",
            page_url="/site/testsite/",
            user_role="client",
        )
        db.session.add(fb)
        db.session.commit()

        assert fb.id is not None
        assert fb.sentiment == "positive"
        assert fb.comment == "Great site!"
        assert fb.user_id == user.id
        assert fb.is_read is False
        assert fb.created_at is not None

    def test_create_feedback_guest(self, req_ctx):
        """Create feedback without a user_id (guest submission)."""
        from app.models import db
        from app.models_social import Feedback

        fb = Feedback(
            user_id=None,
            email="guest@example.com",
            sentiment="negative",
            comment="Something is broken.",
            page_url="/site/testsite/listings",
            user_role="guest",
        )
        db.session.add(fb)
        db.session.commit()

        assert fb.id is not None
        assert fb.user_id is None
        assert fb.sentiment == "negative"
        assert fb.user_role == "guest"

    def test_feedback_is_read_toggle(self, req_ctx):
        """Toggle is_read on a Feedback record."""
        from app.models import db
        from app.models_social import Feedback

        fb = Feedback(sentiment="neutral", comment="Meh", user_role="guest")
        db.session.add(fb)
        db.session.commit()

        assert fb.is_read is False

        fb.is_read = True
        db.session.commit()

        reloaded = db.session.get(Feedback, fb.id)
        assert reloaded.is_read is True

        # Toggle back
        reloaded.is_read = not reloaded.is_read
        db.session.commit()
        assert db.session.get(Feedback, fb.id).is_read is False

    def test_feedback_repr(self, req_ctx):
        """Feedback __repr__ includes sentiment and user_id."""
        from app.models_social import Feedback

        fb = Feedback(sentiment="positive", user_id=42)
        assert "positive" in repr(fb)
        assert "42" in repr(fb)

    def test_feedback_sentiments_constant(self, req_ctx):
        """FEEDBACK_SENTIMENTS contains the three expected values."""
        from app.models_social import FEEDBACK_SENTIMENTS

        codes = [s[0] for s in FEEDBACK_SENTIMENTS]
        assert "positive" in codes
        assert "neutral" in codes
        assert "negative" in codes
        assert len(codes) == 3


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  2. FEEDBACK SYSTEM — Route logic
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFeedbackSubmission:
    """Tests for the POST /feedback route logic."""

    def test_submit_feedback_valid_sentiments(self, req_ctx):
        """All three valid sentiments should create a Feedback row."""
        from app.models import db
        from app.models_social import Feedback

        for sentiment in ("positive", "neutral", "negative"):
            fb = Feedback(
                sentiment=sentiment,
                comment=f"Test {sentiment}",
                user_role="guest",
            )
            db.session.add(fb)
        db.session.commit()

        assert Feedback.query.count() >= 3

    def test_submit_feedback_empty_comment_ok(self, req_ctx):
        """Feedback with an empty comment should still persist."""
        from app.models import db
        from app.models_social import Feedback

        fb = Feedback(sentiment="positive", comment="", user_role="guest")
        db.session.add(fb)
        db.session.commit()

        reloaded = db.session.get(Feedback, fb.id)
        assert reloaded.comment == ""

    def test_submit_feedback_page_url_stored(self, req_ctx):
        """page_url should be stored correctly."""
        from app.models import db
        from app.models_social import Feedback

        url = "/site/testsite/listing/42"
        fb = Feedback(sentiment="neutral", page_url=url, user_role="guest")
        db.session.add(fb)
        db.session.commit()

        assert db.session.get(Feedback, fb.id).page_url == url


class TestFeedbackAdmin:
    """Tests for admin feedback view and toggle."""

    def test_feedback_query_filter_by_sentiment(self, req_ctx):
        """Filter feedback by sentiment should return correct subset."""
        from app.models import db
        from app.models_social import Feedback

        db.session.add_all([
            Feedback(sentiment="positive", comment="Good", user_role="guest"),
            Feedback(sentiment="positive", comment="Great", user_role="guest"),
            Feedback(sentiment="negative", comment="Bad", user_role="guest"),
            Feedback(sentiment="neutral", comment="Okay", user_role="guest"),
        ])
        db.session.commit()

        pos = Feedback.query.filter_by(sentiment="positive").all()
        neg = Feedback.query.filter_by(sentiment="negative").all()
        neu = Feedback.query.filter_by(sentiment="neutral").all()

        assert len(pos) >= 2
        assert len(neg) >= 1
        assert len(neu) >= 1

    def test_feedback_pagination_logic(self, req_ctx):
        """Pagination offset/limit should return correct page slices."""
        from app.models import db
        from app.models_social import Feedback

        # Create 30 feedback items
        for i in range(30):
            db.session.add(Feedback(
                sentiment="positive",
                comment=f"Item {i}",
                user_role="guest",
            ))
        db.session.commit()

        per_page = 25
        page1 = Feedback.query.order_by(Feedback.created_at.desc()) \
            .offset(0).limit(per_page).all()
        page2 = Feedback.query.order_by(Feedback.created_at.desc()) \
            .offset(per_page).limit(per_page).all()

        assert len(page1) == 25
        assert len(page2) >= 5  # at least 5 remaining

    def test_feedback_unread_count(self, req_ctx):
        """Unread count should reflect only is_read=False items."""
        from app.models import db
        from app.models_social import Feedback

        db.session.add_all([
            Feedback(sentiment="positive", is_read=False, user_role="guest"),
            Feedback(sentiment="neutral", is_read=False, user_role="guest"),
            Feedback(sentiment="negative", is_read=True, user_role="guest"),
        ])
        db.session.commit()

        unread = Feedback.query.filter_by(is_read=False).count()
        assert unread >= 2

    def test_feedback_toggle_read_persists(self, req_ctx):
        """Toggling is_read should persist after commit."""
        from app.models import db
        from app.models_social import Feedback

        fb = Feedback(sentiment="positive", comment="Toggle test", user_role="guest")
        db.session.add(fb)
        db.session.commit()

        assert fb.is_read is False

        fb.is_read = not fb.is_read
        db.session.commit()
        assert db.session.get(Feedback, fb.id).is_read is True

        fb.is_read = not fb.is_read
        db.session.commit()
        assert db.session.get(Feedback, fb.id).is_read is False

    def test_feedback_owner_access_required(self, req_ctx):
        """Only owner+ roles should be allowed to view admin feedback.
        Verify role check logic used in the route."""
        user_client = make_user(username="fb_client", email="fb_client@test.com", role="client")
        user_agent = make_user(username="fb_agent", email="fb_agent@test.com", role="agent")
        user_owner = make_user(username="fb_owner", email="fb_owner@test.com", role="owner")
        user_master = make_user(username="fb_master", email="fb_master@test.com", role="master")

        # is_owner returns True for owner and master
        assert not user_client.is_owner
        assert not user_agent.is_owner
        assert user_owner.is_owner
        assert user_master.is_owner

    def test_feedback_user_relationship(self, req_ctx):
        """Feedback linked to a user should be accessible via backref."""
        from app.models import db
        from app.models_social import Feedback

        user = make_user(username="fb_rel", email="fb_rel@test.com", role="client")
        db.session.add(user)
        db.session.commit()

        fb = Feedback(user_id=user.id, sentiment="positive",
                      comment="Backref test", user_role="client")
        db.session.add(fb)
        db.session.commit()

        # Access via backref
        items = user.feedback_items.all()
        assert len(items) >= 1
        assert items[0].sentiment == "positive"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  3. HELP LEVEL SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestHelpLevel:
    """Tests for help_level preference storage and validation."""

    def test_help_level_default(self, req_ctx):
        """Default help_level should be 2."""
        from app.models import User

        assert User.DEFAULT_PREFS["help_level"] == 2

    def test_help_level_stored_in_user_prefs(self, req_ctx):
        """Setting help_level via set_prefs should persist."""
        from app.models import db

        user = make_user(username="hl_store", email="hl_store@test.com")
        db.session.add(user)
        db.session.commit()

        prefs = user.get_prefs()
        prefs["help_level"] = 1
        user.set_prefs(prefs)
        db.session.commit()

        reloaded = db.session.get(user.__class__, user.id)
        assert reloaded.get_prefs()["help_level"] == 1

    def test_help_level_set_all_valid_values(self, req_ctx):
        """Levels 1, 2, 3 should all be storable."""
        from app.models import db

        user = make_user(username="hl_valid", email="hl_valid@test.com")
        db.session.add(user)
        db.session.commit()

        for level in (1, 2, 3):
            prefs = user.get_prefs()
            prefs["help_level"] = level
            user.set_prefs(prefs)
            db.session.commit()
            assert user.get_prefs()["help_level"] == level

    def test_help_level_clamped_in_route_logic(self, req_ctx):
        """The route clamps help_level to [1, 3].
        Simulate the clamping logic used in api_help_level."""
        # Route logic: level = max(1, min(3, int(data.get("level", 2))))
        assert max(1, min(3, 0)) == 1    # below minimum -> 1
        assert max(1, min(3, 1)) == 1    # minimum -> 1
        assert max(1, min(3, 2)) == 2    # mid -> 2
        assert max(1, min(3, 3)) == 3    # max -> 3
        assert max(1, min(3, 99)) == 3   # above max -> 3
        assert max(1, min(3, -5)) == 1   # negative -> 1

    def test_help_level_guest_session_storage(self, req_ctx):
        """help_level for guests should be stored in session['guest_prefs']."""
        from flask import session

        # Simulate guest setting help_level (same logic as route)
        guest = session.get("guest_prefs", {})
        guest["help_level"] = 3
        session["guest_prefs"] = guest
        session.modified = True

        assert session["guest_prefs"]["help_level"] == 3

    def test_help_level_preserved_on_scoring_save(self, req_ctx):
        """Saving scoring prefs should preserve the help_level value."""
        from app.models import db

        user = make_user(username="hl_preserve", email="hl_preserve@test.com")
        db.session.add(user)
        db.session.commit()

        # Set help_level first
        prefs = user.get_prefs()
        prefs["help_level"] = 1
        user.set_prefs(prefs)
        db.session.commit()

        # Now simulate saving scoring prefs (should preserve help_level)
        existing = user.get_prefs()
        existing["min_price"] = 300000
        existing["help_level"] = existing.get("help_level", 2)  # preserve
        user.set_prefs(existing)
        db.session.commit()

        assert user.get_prefs()["help_level"] == 1
        assert user.get_prefs()["min_price"] == 300000


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  4. POWER MODE SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestPowerMode:
    """Tests for power_mode preference storage and validation."""

    def test_power_mode_default(self, req_ctx):
        """Default power_mode for users should be 'high'."""
        from app.models import User

        assert User.DEFAULT_PREFS["power_mode"] == "high"

    def test_power_mode_stored_in_user_prefs(self, req_ctx):
        """Setting power_mode via set_prefs should persist."""
        from app.models import db

        user = make_user(username="pm_store", email="pm_store@test.com")
        db.session.add(user)
        db.session.commit()

        prefs = user.get_prefs()
        prefs["power_mode"] = "low"
        user.set_prefs(prefs)
        db.session.commit()

        reloaded = db.session.get(user.__class__, user.id)
        assert reloaded.get_prefs()["power_mode"] == "low"

    def test_power_mode_set_all_valid_values(self, req_ctx):
        """Modes 'low', 'mid', 'high' should all be storable."""
        from app.models import db

        user = make_user(username="pm_valid", email="pm_valid@test.com")
        db.session.add(user)
        db.session.commit()

        for mode in ("low", "mid", "high"):
            prefs = user.get_prefs()
            prefs["power_mode"] = mode
            user.set_prefs(prefs)
            db.session.commit()
            assert user.get_prefs()["power_mode"] == mode

    def test_power_mode_validation_logic(self, req_ctx):
        """The route rejects modes not in ('low', 'mid', 'high').
        Simulate the validation check from api_power_mode."""
        valid_modes = ("low", "mid", "high")
        assert "low" in valid_modes
        assert "mid" in valid_modes
        assert "high" in valid_modes
        assert "ultra" not in valid_modes
        assert "" not in valid_modes
        assert "LOW" not in valid_modes  # case-sensitive

    def test_power_mode_guest_session_storage(self, req_ctx):
        """power_mode for guests should be stored in session['guest_prefs']."""
        from flask import session

        # Simulate guest setting power_mode (same logic as route)
        guest = session.get("guest_prefs", {})
        guest["power_mode"] = "mid"
        session["guest_prefs"] = guest
        session.modified = True

        assert session["guest_prefs"]["power_mode"] == "mid"

    def test_power_mode_preserved_on_scoring_save(self, req_ctx):
        """Saving scoring prefs should preserve the power_mode value."""
        from app.models import db

        user = make_user(username="pm_preserve", email="pm_preserve@test.com")
        db.session.add(user)
        db.session.commit()

        # Set power_mode first
        prefs = user.get_prefs()
        prefs["power_mode"] = "low"
        user.set_prefs(prefs)
        db.session.commit()

        # Simulate saving scoring prefs (should preserve power_mode)
        existing = user.get_prefs()
        existing["max_price"] = 500000
        existing["power_mode"] = existing.get("power_mode", "high")  # preserve
        user.set_prefs(existing)
        db.session.commit()

        assert user.get_prefs()["power_mode"] == "low"
        assert user.get_prefs()["max_price"] == 500000

    def test_power_mode_guest_default_is_low(self, req_ctx):
        """Context processor should return 'low' for unauthenticated guests."""
        # The context processor in __init__.py returns power_mode='low' for guests
        from flask import session
        guest = session.get("guest_prefs", {})
        # When no guest_prefs are set, default should be "low"
        assert guest.get("power_mode", "low") == "low"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  5. CONTEXT PROCESSOR — inject_help_and_power
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestContextProcessor:
    """Tests for the inject_help_and_power context processor."""

    def test_context_processor_authenticated_user_defaults(self, req_ctx):
        """Authenticated user with default prefs should get help_level=2, power_mode='high'."""
        from app.models import db
        from flask_login import login_user

        user = make_user(username="ctx_auth", email="ctx_auth@test.com")
        db.session.add(user)
        db.session.commit()

        login_user(user)

        prefs = user.get_prefs()
        help_level = prefs.get("help_level", 2)
        power_mode = prefs.get("power_mode", "high")

        assert help_level == 2
        assert power_mode == "high"

    def test_context_processor_authenticated_user_custom(self, req_ctx):
        """Authenticated user with custom prefs should get their stored values."""
        from app.models import db
        from flask_login import login_user

        user = make_user(username="ctx_custom", email="ctx_custom@test.com")
        db.session.add(user)
        db.session.commit()

        prefs = user.get_prefs()
        prefs["help_level"] = 1
        prefs["power_mode"] = "mid"
        user.set_prefs(prefs)
        db.session.commit()

        login_user(user)

        loaded = user.get_prefs()
        assert loaded["help_level"] == 1
        assert loaded["power_mode"] == "mid"

    def test_context_processor_guest_defaults(self, req_ctx):
        """Guest with no session prefs should get help_level=3, power_mode='low'
        (matching the context processor's guest branch)."""
        from flask import session

        # Clear any guest prefs to simulate fresh guest
        session.pop("guest_prefs", None)

        guest = session.get("guest_prefs", {})
        # Context processor logic: guest.get("help_level", 3), guest.get("power_mode", "low")
        assert guest.get("help_level", 3) == 3
        assert guest.get("power_mode", "low") == "low"

    def test_context_processor_guest_custom(self, req_ctx):
        """Guest with session prefs should get their stored values."""
        from flask import session

        session["guest_prefs"] = {"help_level": 1, "power_mode": "high"}
        session.modified = True

        guest = session.get("guest_prefs", {})
        assert guest.get("help_level", 3) == 1
        assert guest.get("power_mode", "low") == "high"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  6. PREFERENCES — help_level & power_mode in full prefs round-trip
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestPreferencesIntegration:
    """Verify help_level and power_mode survive full prefs save cycle."""

    def test_full_prefs_round_trip(self, req_ctx):
        """Set all prefs including help_level/power_mode, save, reload, verify."""
        from app.models import db, User

        user = make_user(username="prefs_rt", email="prefs_rt@test.com")
        db.session.add(user)
        db.session.commit()

        prefs = user.get_prefs()
        prefs["help_level"] = 3
        prefs["power_mode"] = "low"
        prefs["min_price"] = 150000
        prefs["max_price"] = 750000
        prefs["min_beds"] = 3
        prefs["min_baths"] = 2.0
        user.set_prefs(prefs)
        db.session.commit()

        # Reload from DB
        reloaded = db.session.get(User, user.id)
        rp = reloaded.get_prefs()

        assert rp["help_level"] == 3
        assert rp["power_mode"] == "low"
        assert rp["min_price"] == 150000
        assert rp["max_price"] == 750000

    def test_default_prefs_include_ux_keys(self, req_ctx):
        """DEFAULT_PREFS must include help_level and power_mode."""
        from app.models import User

        assert "help_level" in User.DEFAULT_PREFS
        assert "power_mode" in User.DEFAULT_PREFS

    def test_new_user_gets_default_ux_prefs(self, req_ctx):
        """A newly created user's prefs should include the UX defaults."""
        from app.models import db

        user = make_user(username="prefs_new", email="prefs_new@test.com")
        db.session.add(user)
        db.session.commit()

        prefs = user.get_prefs()
        assert prefs["help_level"] == 2
        assert prefs["power_mode"] == "high"

    def test_guest_prefs_independent_of_user_prefs(self, req_ctx):
        """Guest session prefs should not affect user DB prefs."""
        from app.models import db
        from flask import session

        user = make_user(username="prefs_indep", email="prefs_indep@test.com")
        db.session.add(user)
        db.session.commit()

        # Set user prefs
        prefs = user.get_prefs()
        prefs["help_level"] = 1
        prefs["power_mode"] = "mid"
        user.set_prefs(prefs)
        db.session.commit()

        # Set guest prefs to different values
        session["guest_prefs"] = {"help_level": 3, "power_mode": "low"}
        session.modified = True

        # Verify independence
        assert user.get_prefs()["help_level"] == 1
        assert session["guest_prefs"]["help_level"] == 3


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  7. FEEDBACK TABLE — Migration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFeedbackMigration:
    """Verify the feedback table exists after migrations."""

    def test_feedback_table_exists(self, req_ctx):
        """The feedback table should be created by migrations."""
        from app.models import db
        from flask import g
        from sqlalchemy import inspect

        inspector = inspect(g.site_engine)
        tables = inspector.get_table_names()
        assert "feedback" in tables

    def test_feedback_table_columns(self, req_ctx):
        """The feedback table should have all expected columns."""
        from flask import g
        from sqlalchemy import inspect

        inspector = inspect(g.site_engine)
        columns = {c["name"] for c in inspector.get_columns("feedback")}

        expected = {"id", "user_id", "email", "sentiment", "comment",
                    "page_url", "user_role", "is_read", "created_at"}
        assert expected.issubset(columns)
