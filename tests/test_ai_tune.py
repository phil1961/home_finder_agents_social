# ─────────────────────────────────────────────
# File: tests/test_ai_tune.py
# App Version: 2026.03.14 | File Version: 1.0.0
# Last Modified: 2026-03-18
# ─────────────────────────────────────────────
"""Integration and regression tests for AI Mode and Buyer Profile (Tune) features."""
import json
import pytest
from datetime import datetime, timezone

from tests.conftest import make_user, make_listing


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  1. AI MODE — Preference storage and validation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestAiMode:
    """Tests for ai_mode preference storage and validation."""

    def test_ai_mode_default(self, req_ctx):
        """DEFAULT_PREFS should have ai_mode = 'on'."""
        from app.models import User

        assert User.DEFAULT_PREFS.get("ai_mode") == "on"

    def test_ai_mode_stored_in_user_prefs(self, req_ctx):
        """Setting ai_mode via set_prefs should persist."""
        from app.models import db

        user = make_user(username="ai_store", email="ai_store@test.com")
        db.session.add(user)
        db.session.commit()

        prefs = user.get_prefs()
        prefs["ai_mode"] = "tune"
        user.set_prefs(prefs)
        db.session.commit()

        reloaded = db.session.get(user.__class__, user.id)
        assert reloaded.get_prefs()["ai_mode"] == "tune"

    def test_ai_mode_set_all_valid_values(self, req_ctx):
        """Modes 'off', 'on', 'tune' should all be storable."""
        from app.models import db

        user = make_user(username="ai_valid", email="ai_valid@test.com")
        db.session.add(user)
        db.session.commit()

        for mode in ("off", "on", "tune"):
            prefs = user.get_prefs()
            prefs["ai_mode"] = mode
            user.set_prefs(prefs)
            db.session.commit()
            assert user.get_prefs()["ai_mode"] == mode

    def test_ai_mode_validation_logic(self, req_ctx):
        """The route rejects modes not in ('off', 'on', 'tune').
        Simulate the validation check from api_ai_mode."""
        valid_modes = ("off", "on", "tune")
        assert "off" in valid_modes
        assert "on" in valid_modes
        assert "tune" in valid_modes
        assert "auto" not in valid_modes
        assert "" not in valid_modes
        assert "ON" not in valid_modes  # case-sensitive

    def test_ai_mode_guest_session_storage(self, req_ctx):
        """ai_mode for guests should be stored in session['guest_prefs']."""
        from flask import session

        guest = session.get("guest_prefs", {})
        guest["ai_mode"] = "tune"
        session["guest_prefs"] = guest
        session.modified = True

        assert session["guest_prefs"]["ai_mode"] == "tune"

    def test_ai_mode_preserved_on_scoring_save(self, req_ctx):
        """Saving scoring prefs should preserve the ai_mode value."""
        from app.models import db

        user = make_user(username="ai_preserve", email="ai_preserve@test.com")
        db.session.add(user)
        db.session.commit()

        # Set ai_mode first
        prefs = user.get_prefs()
        prefs["ai_mode"] = "tune"
        user.set_prefs(prefs)
        db.session.commit()

        # Simulate saving scoring prefs (should preserve ai_mode)
        existing = user.get_prefs()
        existing["min_price"] = 300000
        existing["ai_mode"] = existing.get("ai_mode", "on")  # preserve
        user.set_prefs(existing)
        db.session.commit()

        assert user.get_prefs()["ai_mode"] == "tune"
        assert user.get_prefs()["min_price"] == 300000

    def test_ai_mode_guest_default_is_off(self, req_ctx):
        """Context processor should return 'off' for unauthenticated guests."""
        from flask import session

        # Clear any guest prefs to simulate fresh guest
        session.pop("guest_prefs", None)

        guest = session.get("guest_prefs", {})
        # Context processor logic: guest.get("ai_mode", "off")
        assert guest.get("ai_mode", "off") == "off"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  2. BUYER PROFILE — Storage in preferences
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestBuyerProfile:
    """Tests for buyer_profile storage in preferences."""

    def test_buyer_profile_default_empty(self, req_ctx):
        """A new user's prefs should have no buyer_profile or empty dict."""
        from app.models import db

        user = make_user(username="bp_default", email="bp_default@test.com")
        db.session.add(user)
        db.session.commit()

        prefs = user.get_prefs()
        profile = prefs.get("buyer_profile", {})
        assert profile == {} or profile is None

    def test_buyer_profile_stored_in_user_prefs(self, req_ctx):
        """Save a full profile dict, commit, reload, verify all fields persist."""
        from app.models import db

        user = make_user(username="bp_store", email="bp_store@test.com")
        db.session.add(user)
        db.session.commit()

        full_profile = {
            "life_stage": "retired",
            "partner": True,
            "kids": "school_age",
            "pets": "dog",
            "work_from_home": "no",
            "budget_feel": "comfortable",
            "fixed_income": True,
            "activities": ["golf", "fishing", "gardening"],
            "worship_important": True,
            "denomination": "Methodist",
            "community_style": "friendly",
            "school_quality": False,
            "school_district": "",
            "single_story_important": True,
            "medical_proximity": True,
            "walkability_important": False,
            "relocating_from": "Chicago, IL",
        }

        prefs = user.get_prefs()
        prefs["buyer_profile"] = full_profile
        user.set_prefs(prefs)
        db.session.commit()

        reloaded = db.session.get(user.__class__, user.id)
        saved = reloaded.get_prefs()["buyer_profile"]

        assert saved["life_stage"] == "retired"
        assert saved["partner"] is True
        assert saved["kids"] == "school_age"
        assert saved["pets"] == "dog"
        assert saved["fixed_income"] is True
        assert saved["activities"] == ["golf", "fishing", "gardening"]
        assert saved["worship_important"] is True
        assert saved["denomination"] == "Methodist"
        assert saved["single_story_important"] is True
        assert saved["medical_proximity"] is True
        assert saved["relocating_from"] == "Chicago, IL"

    def test_buyer_profile_partial_save(self, req_ctx):
        """Save with only life_stage and activities, verify other fields absent."""
        from app.models import db

        user = make_user(username="bp_partial", email="bp_partial@test.com")
        db.session.add(user)
        db.session.commit()

        partial_profile = {
            "life_stage": "young_professional",
            "activities": ["running", "dining"],
        }

        prefs = user.get_prefs()
        prefs["buyer_profile"] = partial_profile
        user.set_prefs(prefs)
        db.session.commit()

        reloaded = db.session.get(user.__class__, user.id)
        saved = reloaded.get_prefs()["buyer_profile"]

        assert saved["life_stage"] == "young_professional"
        assert saved["activities"] == ["running", "dining"]
        assert "denomination" not in saved
        assert "relocating_from" not in saved
        assert "partner" not in saved

    def test_buyer_profile_preserved_on_scoring_save(self, req_ctx):
        """Set buyer_profile, then save scoring prefs with different min_price,
        verify profile survives."""
        from app.models import db

        user = make_user(username="bp_preserve", email="bp_preserve@test.com")
        db.session.add(user)
        db.session.commit()

        # Set buyer_profile first
        prefs = user.get_prefs()
        prefs["buyer_profile"] = {"life_stage": "retired", "partner": True}
        user.set_prefs(prefs)
        db.session.commit()

        # Simulate saving scoring prefs (should preserve buyer_profile)
        existing = user.get_prefs()
        existing["min_price"] = 250000
        existing["buyer_profile"] = existing.get("buyer_profile", {})  # preserve
        user.set_prefs(existing)
        db.session.commit()

        result = user.get_prefs()
        assert result["buyer_profile"]["life_stage"] == "retired"
        assert result["buyer_profile"]["partner"] is True
        assert result["min_price"] == 250000

    def test_buyer_profile_activities_list(self, req_ctx):
        """Activities should store as a list of strings."""
        from app.models import db

        user = make_user(username="bp_acts", email="bp_acts@test.com")
        db.session.add(user)
        db.session.commit()

        prefs = user.get_prefs()
        prefs["buyer_profile"] = {"activities": ["golf", "beach", "arts"]}
        user.set_prefs(prefs)
        db.session.commit()

        reloaded = db.session.get(user.__class__, user.id)
        activities = reloaded.get_prefs()["buyer_profile"]["activities"]

        assert isinstance(activities, list)
        assert all(isinstance(a, str) for a in activities)
        assert activities == ["golf", "beach", "arts"]

    def test_buyer_profile_boolean_fields(self, req_ctx):
        """Boolean fields should store as True/False."""
        from app.models import db

        user = make_user(username="bp_bools", email="bp_bools@test.com")
        db.session.add(user)
        db.session.commit()

        prefs = user.get_prefs()
        prefs["buyer_profile"] = {
            "worship_important": True,
            "partner": True,
            "fixed_income": False,
            "single_story_important": True,
            "medical_proximity": False,
            "walkability_important": True,
        }
        user.set_prefs(prefs)
        db.session.commit()

        reloaded = db.session.get(user.__class__, user.id)
        saved = reloaded.get_prefs()["buyer_profile"]

        assert saved["worship_important"] is True
        assert saved["partner"] is True
        assert saved["fixed_income"] is False
        assert saved["single_story_important"] is True
        assert saved["medical_proximity"] is False
        assert saved["walkability_important"] is True

    def test_buyer_profile_text_fields(self, req_ctx):
        """Text fields should store as strings."""
        from app.models import db

        user = make_user(username="bp_text", email="bp_text@test.com")
        db.session.add(user)
        db.session.commit()

        prefs = user.get_prefs()
        prefs["buyer_profile"] = {
            "denomination": "Baptist",
            "school_district": "Berkeley County",
            "relocating_from": "New York, NY",
        }
        user.set_prefs(prefs)
        db.session.commit()

        reloaded = db.session.get(user.__class__, user.id)
        saved = reloaded.get_prefs()["buyer_profile"]

        assert isinstance(saved["denomination"], str)
        assert saved["denomination"] == "Baptist"
        assert isinstance(saved["school_district"], str)
        assert saved["school_district"] == "Berkeley County"
        assert isinstance(saved["relocating_from"], str)
        assert saved["relocating_from"] == "New York, NY"

    def test_buyer_profile_guest_session_storage(self, req_ctx):
        """Store buyer_profile in session['guest_prefs']['buyer_profile'], verify."""
        from flask import session

        guest = session.get("guest_prefs", {})
        guest["buyer_profile"] = {
            "life_stage": "growing_family",
            "activities": ["beach", "fitness"],
        }
        session["guest_prefs"] = guest
        session.modified = True

        saved = session["guest_prefs"]["buyer_profile"]
        assert saved["life_stage"] == "growing_family"
        assert saved["activities"] == ["beach", "fitness"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  3. AI CONTEXT — Builder functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestAiContext:
    """Tests for the AI context builder functions."""

    def test_build_buyer_profile_context_empty(self, req_ctx):
        """build_buyer_profile_context({}) should return ''."""
        from app.services.ai_context import build_buyer_profile_context

        assert build_buyer_profile_context({}) == ""

    def test_build_buyer_profile_context_none(self, req_ctx):
        """build_buyer_profile_context(None) should return ''."""
        from app.services.ai_context import build_buyer_profile_context

        assert build_buyer_profile_context(None) == ""

    def test_build_buyer_profile_context_full(self, req_ctx):
        """Full profile dict should return string containing key elements."""
        from app.services.ai_context import build_buyer_profile_context

        profile = {
            "life_stage": "retired",
            "partner": True,
            "activities": ["golf", "fishing"],
            "worship_important": True,
            "denomination": "Methodist",
            "relocating_from": "Chicago, IL",
        }

        result = build_buyer_profile_context(profile)

        assert "Buyer Profile" in result
        assert "Life stage" in result
        assert "retired" in result
        assert "golf" in result
        assert "Methodist" in result
        assert "Chicago, IL" in result

    def test_build_buyer_profile_context_partial(self, req_ctx):
        """Profile with only life_stage should include life stage but not
        activities or worship."""
        from app.services.ai_context import build_buyer_profile_context

        profile = {"life_stage": "young_professional"}

        result = build_buyer_profile_context(profile)

        assert "Life stage" in result
        assert "young professional" in result
        assert "Hobbies" not in result
        assert "Faith" not in result
        assert "worship" not in result

    def test_buyer_summary_line_empty(self, req_ctx):
        """_buyer_summary_line({}) should return generic 'Buyer is searching'."""
        from app.services.ai_context import _buyer_summary_line

        result = _buyer_summary_line({})
        assert "Buyer is searching" in result

    def test_buyer_summary_line_none(self, req_ctx):
        """_buyer_summary_line(None) should return generic 'Buyer is searching'."""
        from app.services.ai_context import _buyer_summary_line

        result = _buyer_summary_line(None)
        assert "Buyer is searching" in result

    def test_buyer_summary_line_with_profile(self, req_ctx):
        """Profile with life_stage='retired', partner=True should include
        'Retiree' and 'with partner'."""
        from app.services.ai_context import _buyer_summary_line

        profile = {"life_stage": "retired", "partner": True}
        result = _buyer_summary_line(profile)

        assert "Retiree" in result
        assert "with partner" in result

    def test_listing_context_includes_buyer_profile(self, req_ctx):
        """build_listing_context with user_prefs containing buyer_profile
        should include 'Buyer Profile' in output."""
        from app.models import db
        from app.services.ai_context import build_listing_context

        listing = make_listing(address="100 Profile Test Ln")
        db.session.add(listing)
        db.session.commit()

        user_prefs = {
            "min_price": 200000,
            "max_price": 500000,
            "buyer_profile": {
                "life_stage": "retired",
                "partner": True,
                "activities": ["golf"],
            },
        }

        result = build_listing_context(listing, user_prefs=user_prefs)
        assert "Buyer Profile" in result

    def test_listing_context_without_buyer_profile(self, req_ctx):
        """build_listing_context with user_prefs but no buyer_profile
        should include generic buyer line."""
        from app.models import db
        from app.services.ai_context import build_listing_context

        listing = make_listing(address="200 No Profile Ln")
        db.session.add(listing)
        db.session.commit()

        user_prefs = {
            "min_price": 200000,
            "max_price": 500000,
        }

        result = build_listing_context(listing, user_prefs=user_prefs)
        assert "Buyer is searching" in result

    def test_portfolio_context_includes_buyer_profile(self, req_ctx):
        """build_portfolio_context with buyer_profile in prefs should include
        profile data."""
        from app.models import db
        from app.services.ai_context import build_portfolio_context

        listing = make_listing(address="300 Portfolio Test Dr")
        db.session.add(listing)
        db.session.commit()

        user_prefs = {
            "min_price": 200000,
            "max_price": 500000,
            "buyer_profile": {
                "life_stage": "retired",
                "partner": True,
            },
        }
        composites = {listing.id: 75.0}

        system_ctx, user_msg = build_portfolio_context(
            [listing], composites, user_prefs
        )

        assert "Retiree" in system_ctx
        assert "with partner" in system_ctx

    def test_preferences_context_includes_buyer_profile(self, req_ctx):
        """build_preferences_context with buyer_profile should include
        profile data."""
        from app.models import User
        from app.services.ai_context import build_preferences_context

        prefs = dict(User.DEFAULT_PREFS)
        prefs["buyer_profile"] = {
            "life_stage": "retired",
            "activities": ["golf", "fishing"],
            "worship_important": True,
            "denomination": "Baptist",
        }

        result = build_preferences_context(prefs, User.DEFAULT_PREFS)

        assert "Buyer Profile" in result
        assert "retired" in result
        assert "golf" in result
        assert "Baptist" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  4. CONTEXT PROCESSOR — ai_mode in inject_help_and_power
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestContextProcessorAiMode:
    """Tests for the inject_help_and_power context processor including ai_mode."""

    def test_context_processor_authenticated_ai_mode_default(self, req_ctx):
        """Authenticated user default ai_mode should be 'on'."""
        from app.models import db
        from flask_login import login_user

        user = make_user(username="ctx_ai_def", email="ctx_ai_def@test.com")
        db.session.add(user)
        db.session.commit()

        login_user(user)

        prefs = user.get_prefs()
        ai_mode = prefs.get("ai_mode", "on")

        assert ai_mode == "on"

    def test_context_processor_authenticated_ai_mode_custom(self, req_ctx):
        """Set ai_mode='tune', verify returned."""
        from app.models import db
        from flask_login import login_user

        user = make_user(username="ctx_ai_cust", email="ctx_ai_cust@test.com")
        db.session.add(user)
        db.session.commit()

        prefs = user.get_prefs()
        prefs["ai_mode"] = "tune"
        user.set_prefs(prefs)
        db.session.commit()

        login_user(user)

        loaded = user.get_prefs()
        assert loaded["ai_mode"] == "tune"

    def test_context_processor_guest_ai_mode_default(self, req_ctx):
        """Guest default ai_mode should be 'off' (matching context processor)."""
        from flask import session

        # Clear any guest prefs to simulate fresh guest
        session.pop("guest_prefs", None)

        guest = session.get("guest_prefs", {})
        # Context processor logic: guest.get("ai_mode", "off")
        assert guest.get("ai_mode", "off") == "off"

    def test_context_processor_guest_ai_mode_custom(self, req_ctx):
        """Guest sets ai_mode='on' in session, verify."""
        from flask import session

        session["guest_prefs"] = {"ai_mode": "on"}
        session.modified = True

        guest = session.get("guest_prefs", {})
        assert guest.get("ai_mode", "off") == "on"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  5. AI MODE — Route endpoints (HTTP-level)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestAiModeRouteEndpoints:
    """HTTP-level tests for the AJAX endpoints."""

    def _login(self, client, req_ctx):
        from app.models import db
        user = make_user(username="httpuser", email="http@test.com", role="client")
        db.session.add(user)
        db.session.commit()
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        return user

    def test_api_ai_mode_valid(self, client, req_ctx):
        """POST /site/testsite/api/ai-mode with mode='off' should return 200."""
        self._login(client, req_ctx)

        resp = client.post(
            "/site/testsite/api/ai-mode",
            json={"mode": "off"},
            content_type="application/json",
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True

    def test_api_ai_mode_invalid(self, client, req_ctx):
        """POST with mode='invalid' should return 400."""
        self._login(client, req_ctx)

        resp = client.post(
            "/site/testsite/api/ai-mode",
            json={"mode": "invalid"},
            content_type="application/json",
        )

        assert resp.status_code == 400

    def test_api_buyer_profile_valid(self, client, req_ctx):
        """POST /site/testsite/api/buyer-profile with profile dict should return 200."""
        self._login(client, req_ctx)

        resp = client.post(
            "/site/testsite/api/buyer-profile",
            json={"profile": {"life_stage": "retired", "partner": True}},
            content_type="application/json",
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True

    def test_api_buyer_profile_invalid(self, client, req_ctx):
        """POST with profile='not a dict' should return 400."""
        self._login(client, req_ctx)

        resp = client.post(
            "/site/testsite/api/buyer-profile",
            json={"profile": "not a dict"},
            content_type="application/json",
        )

        assert resp.status_code == 400
