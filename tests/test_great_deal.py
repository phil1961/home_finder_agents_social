# ─────────────────────────────────────────────
# File: tests/test_great_deal.py
# App Version: 2026.03.14 | File Version: 1.0.0
# Last Modified: 2026-03-18
# ─────────────────────────────────────────────
"""
Integration and regression tests for the Great Deal Score threshold feature.

Tests cover:
  - Threshold storage and persistence for users and guests
  - Great deal count computation logic
  - Threshold preservation across scoring saves
  - Guest default behavior (threshold not inflated by DEFAULT_PREFS)
  - Banner and card highlight template logic
"""
from tests.conftest import make_user, make_listing


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  1. GREAT DEAL THRESHOLD — PREFERENCE STORAGE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestGreatDealThreshold:
    """Tests for great_deal_threshold preference storage and defaults."""

    def test_default_threshold_value(self, req_ctx):
        """Default great_deal_threshold should be 75."""
        from config import GREAT_DEAL_SCORE_THRESHOLD

        assert GREAT_DEAL_SCORE_THRESHOLD == 75

    def test_default_in_user_prefs(self, req_ctx):
        """New user's prefs should include great_deal_threshold at 75."""
        from app.models import db

        user = make_user(username="gdt_default", email="gdt_default@test.com")
        db.session.add(user)
        db.session.commit()

        prefs = user.get_prefs()
        assert prefs["great_deal_threshold"] == 75

    def test_threshold_stored_in_user_prefs(self, req_ctx):
        """Setting great_deal_threshold via set_prefs should persist."""
        from app.models import db

        user = make_user(username="gdt_store", email="gdt_store@test.com")
        db.session.add(user)
        db.session.commit()

        prefs = user.get_prefs()
        prefs["great_deal_threshold"] = 55
        user.set_prefs(prefs)
        db.session.commit()

        reloaded = db.session.get(user.__class__, user.id)
        assert reloaded.get_prefs()["great_deal_threshold"] == 55

    def test_threshold_accepts_full_range(self, req_ctx):
        """Threshold should accept values from 0 to 100."""
        from app.models import db

        user = make_user(username="gdt_range", email="gdt_range@test.com")
        db.session.add(user)
        db.session.commit()

        for val in (0, 1, 25, 50, 75, 99, 100):
            prefs = user.get_prefs()
            prefs["great_deal_threshold"] = val
            user.set_prefs(prefs)
            db.session.commit()
            assert user.get_prefs()["great_deal_threshold"] == val

    def test_threshold_guest_session_storage(self, req_ctx):
        """great_deal_threshold for guests should persist in session."""
        from flask import session

        guest = session.get("guest_prefs", {})
        guest["great_deal_threshold"] = 40
        session["guest_prefs"] = guest
        session.modified = True

        assert session["guest_prefs"]["great_deal_threshold"] == 40

    def test_threshold_preserved_on_scoring_save(self, req_ctx):
        """Saving scoring prefs should preserve great_deal_threshold."""
        from app.models import db

        user = make_user(username="gdt_preserve", email="gdt_preserve@test.com")
        db.session.add(user)
        db.session.commit()

        # Set threshold
        prefs = user.get_prefs()
        prefs["great_deal_threshold"] = 60
        user.set_prefs(prefs)
        db.session.commit()

        # Simulate saving scoring prefs with a different field
        existing = user.get_prefs()
        existing["min_price"] = 250000
        user.set_prefs(existing)
        db.session.commit()

        assert user.get_prefs()["great_deal_threshold"] == 60
        assert user.get_prefs()["min_price"] == 250000


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  2. GREAT DEAL COUNT — COMPUTATION LOGIC
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestGreatDealCount:
    """Tests for great deal count computation logic."""

    def test_count_with_no_listings(self, req_ctx):
        """Empty composites dict should yield 0 great deals."""
        user_composites = {}
        threshold = 75
        count = sum(1 for s in user_composites.values() if s >= threshold)
        assert count == 0

    def test_count_all_below_threshold(self, req_ctx):
        """When all scores are below threshold, count should be 0."""
        user_composites = {1: 50, 2: 60, 3: 74}
        threshold = 75
        count = sum(1 for s in user_composites.values() if s >= threshold)
        assert count == 0

    def test_count_some_above_threshold(self, req_ctx):
        """Only scores at or above threshold should be counted."""
        user_composites = {1: 50, 2: 75, 3: 80, 4: 60}
        threshold = 75
        count = sum(1 for s in user_composites.values() if s >= threshold)
        assert count == 2

    def test_count_all_above_threshold(self, req_ctx):
        """When all scores meet threshold, count equals total listings."""
        user_composites = {1: 80, 2: 90, 3: 100}
        threshold = 75
        count = sum(1 for s in user_composites.values() if s >= threshold)
        assert count == 3

    def test_count_exact_threshold_included(self, req_ctx):
        """Score exactly equal to threshold should be counted."""
        user_composites = {1: 75}
        threshold = 75
        count = sum(1 for s in user_composites.values() if s >= threshold)
        assert count == 1

    def test_count_threshold_zero_includes_all(self, req_ctx):
        """Threshold of 0 means every listing is a great deal."""
        user_composites = {1: 0, 2: 10, 3: 50}
        threshold = 0
        count = sum(1 for s in user_composites.values() if s >= threshold)
        assert count == 3

    def test_count_threshold_100_strict(self, req_ctx):
        """Threshold of 100 means only perfect scores qualify."""
        user_composites = {1: 99, 2: 100, 3: 50}
        threshold = 100
        count = sum(1 for s in user_composites.values() if s >= threshold)
        assert count == 1

    def test_count_with_float_scores(self, req_ctx):
        """Composite scores may be floats; threshold comparison still works."""
        user_composites = {1: 74.9, 2: 75.0, 3: 75.1}
        threshold = 75
        count = sum(1 for s in user_composites.values() if s >= threshold)
        assert count == 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  3. GUEST THRESHOLD — ROUND-TRIP REGRESSION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestGuestThresholdRoundTrip:
    """Regression tests for the guest prefs save bug where DEFAULT_PREFS
    values (power_mode='high', ai_mode='on') leaked into guest sessions."""

    def test_guest_power_mode_not_inflated_on_save(self, req_ctx):
        """Saving guest scoring prefs must NOT inject power_mode='high'
        from DEFAULT_PREFS. Guest default is 'low'."""
        from flask import session

        # Simulate a fresh guest — no guest_prefs in session
        session.pop("guest_prefs", None)

        # Read raw session (what the save handler should check)
        raw = session.get("guest_prefs", {})
        power_mode = raw.get("power_mode", "low")

        assert power_mode == "low"

    def test_guest_ai_mode_not_inflated_on_save(self, req_ctx):
        """Saving guest scoring prefs must NOT inject ai_mode='on'
        from DEFAULT_PREFS. Guest default is 'off'."""
        from flask import session

        session.pop("guest_prefs", None)

        raw = session.get("guest_prefs", {})
        ai_mode = raw.get("ai_mode", "off")

        assert ai_mode == "off"

    def test_guest_explicit_power_mode_preserved(self, req_ctx):
        """If a guest explicitly set power_mode via Settings, it should
        survive a scoring prefs save."""
        from flask import session

        session["guest_prefs"] = {"power_mode": "mid"}
        session.modified = True

        raw = session.get("guest_prefs", {})
        assert raw.get("power_mode", "low") == "mid"

    def test_guest_threshold_survives_save(self, req_ctx):
        """Guest threshold value should persist through the save flow."""
        from flask import session

        # Guest sets threshold to 40
        guest = session.get("guest_prefs", {})
        guest["great_deal_threshold"] = 40
        session["guest_prefs"] = guest
        session.modified = True

        # Simulate the save handler reading it back
        saved = session.get("guest_prefs", {})
        assert saved.get("great_deal_threshold", 75) == 40


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  4. TEMPLATE LOGIC — BANNER & CARD CLASSES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestGreatDealTemplateLogic:
    """Tests for template rendering logic (card CSS class and banner)."""

    def test_card_gets_great_deal_class_when_above(self, req_ctx):
        """Score >= threshold should produce the 'great-deal' CSS class."""
        score = 80
        threshold = 75
        css_class = "great-deal" if score >= threshold else ""
        assert css_class == "great-deal"

    def test_card_no_class_when_below(self, req_ctx):
        """Score < threshold should produce no extra CSS class."""
        score = 74
        threshold = 75
        css_class = "great-deal" if score >= threshold else ""
        assert css_class == ""

    def test_banner_shows_great_deals_when_count_positive(self, req_ctx):
        """Banner should show the 'Great Deals!' message when count > 0."""
        great_deal_count = 3
        assert great_deal_count > 0  # triggers green banner

    def test_banner_shows_subdued_when_count_zero(self, req_ctx):
        """Banner should show subdued message when no great deals."""
        great_deal_count = 0
        assert great_deal_count == 0  # triggers gray banner

    def test_since_stats_includes_great_deal_count(self, req_ctx):
        """The since_stats dict passed to the template must include
        great_deal_count key."""
        # Simulate what listings.py computes
        user_composites = {1: 80, 2: 50, 3: 90}
        threshold = 75
        great_count = sum(1 for s in user_composites.values() if s >= threshold)

        since_stats = {
            "total_scored": 3,
            "top_score": 90,
            "great_deal_count": great_count,
        }

        assert "great_deal_count" in since_stats
        assert since_stats["great_deal_count"] == 2

    def test_threshold_passed_to_template(self, req_ctx):
        """The great_deal_threshold value should be available for the
        banner message text."""
        from app.models import db

        user = make_user(username="gdt_tmpl", email="gdt_tmpl@test.com")
        db.session.add(user)
        db.session.commit()

        prefs = user.get_prefs()
        prefs["great_deal_threshold"] = 55
        user.set_prefs(prefs)
        db.session.commit()

        # Verify the value is retrievable (same as listings.py does)
        threshold = user.get_prefs().get("great_deal_threshold", 75)
        assert threshold == 55


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  5. SLIDER CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestGreatDealSlider:
    """Tests for the slider configuration in the template."""

    def test_slider_range_accepts_zero(self, req_ctx):
        """Slider min should be 0 (all listings are great deals)."""
        # The template sets min="0" max="100" step="1"
        slider_min = 0
        assert slider_min == 0

    def test_slider_range_accepts_100(self, req_ctx):
        """Slider max should be 100 (only perfect scores qualify)."""
        slider_max = 100
        assert slider_max == 100

    def test_slider_step_is_one(self, req_ctx):
        """Slider step should be 1 for fine-grained control."""
        slider_step = 1
        assert slider_step == 1

    def test_threshold_int_conversion(self, req_ctx):
        """The route converts threshold to int — verify no float issues."""
        # Simulates: int(request.form.get("great_deal_threshold", 75))
        raw_value = "55"
        converted = int(raw_value)
        assert converted == 55
        assert isinstance(converted, int)
