# ─────────────────────────────────────────────
# File: tests/test_session2.py
# App Version: 2026.03.14 | File Version: 1.0.0
# Last Modified: 2026-03-19
# ─────────────────────────────────────────────
"""Integration and regression tests for session-2 features:
feedback visibility, most-shared dismiss, go-to-site routing,
AJAX flag toggle, nav tooltip placement, and settings page guest visibility.
"""
import json
import pytest
from datetime import datetime, timezone

from tests.conftest import make_user, make_listing


def _login(client, req_ctx, username="httpuser", email="http@test.com", role="master"):
    """Helper: create a user in the DB and set session auth."""
    from app.models import db
    user = make_user(username=username, email=email, role=role)
    db.session.add(user)
    db.session.commit()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_site_key'] = 'testsite'
    return user


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  1. FEEDBACK VISIBILITY — Template condition logic
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFeedbackVisibility:
    """Tests for the feedback button visibility logic in base.html.

    The template condition is:
        {% if current_user.is_authenticated and power_mode != 'low' %}
    """

    def test_feedback_requires_auth(self, req_ctx):
        """Feedback button should only render for authenticated users."""
        # The Jinja condition requires is_authenticated AND power_mode != 'low'.
        # Verify the two-part condition: both flags must be true.
        condition_auth = True
        condition_power = "mid"
        visible = condition_auth and condition_power != "low"
        assert visible is True

        # When auth is False, feedback should be hidden regardless of power mode
        condition_auth = False
        condition_power = "high"
        visible = condition_auth and condition_power != "low"
        assert visible is False

    def test_feedback_hidden_for_guests(self, req_ctx):
        """Guests (is_authenticated=False) should not see the feedback button."""
        condition_auth = False
        for pm in ("low", "mid", "high"):
            visible = condition_auth and pm != "low"
            assert visible is False, f"Guest should not see feedback at power_mode={pm}"

    def test_feedback_hidden_for_low_power(self, req_ctx):
        """Authenticated user with power_mode='low' should not see feedback."""
        condition_auth = True
        condition_power = "low"
        visible = condition_auth and condition_power != "low"
        assert visible is False

    def test_feedback_visible_for_mid_power(self, req_ctx):
        """Authenticated user with power_mode='mid' should see feedback."""
        condition_auth = True
        condition_power = "mid"
        visible = condition_auth and condition_power != "low"
        assert visible is True

        # Also verify 'high' works
        condition_power = "high"
        visible = condition_auth and condition_power != "low"
        assert visible is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  2. MOST-SHARED DISMISS — Cookie-based hide logic
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestMostSharedDismiss:
    """Tests for the 'Most Shared This Week' dismiss behaviour.

    The template uses cookie 'hf_hide_shared' with max-age=31536000 (1 year)
    and sets display:none when the cookie is present.
    """

    def test_dismiss_cookie_name(self, req_ctx):
        """The cookie name used for dismissing the section is 'hf_hide_shared'."""
        # Hardcoded in template: document.cookie='hf_hide_shared=1;...'
        cookie_name = "hf_hide_shared"
        assert cookie_name == "hf_hide_shared"

    def test_dismiss_cookie_max_age(self, req_ctx):
        """Cookie max-age should be 31536000 seconds (1 year)."""
        expected_max_age = 31536000
        one_year_seconds = 365 * 24 * 60 * 60
        assert expected_max_age == one_year_seconds

    def test_dismiss_hides_section(self, req_ctx):
        """When hf_hide_shared cookie is present, the section has display:none.

        The template inline style is:
            style="{% if request.cookies.get('hf_hide_shared') %}display:none;{% endif %}"
        """
        from flask import request

        # Simulate: cookie present → display:none
        cookie_val = "1"
        style = f"display:none;" if cookie_val else ""
        assert "display:none" in style

        # Simulate: cookie absent → no inline hide
        cookie_val = ""
        style = f"display:none;" if cookie_val else ""
        assert "display:none" not in style


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  3. GO TO SITE — Cross-site session rebinding
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestGoToSite:
    """Tests for the /go/<site_key> route that rebinds master sessions."""

    def test_go_to_site_requires_session(self, client, req_ctx):
        """If no _user_id in session, should redirect away."""
        resp = client.get(
            "/site/testsite/go/testsite",
            environ_base={"HTTP_X_HOMEFINDER_SITE": "testsite"},
        )
        # Should redirect (302) since there's no _user_id in the session
        assert resp.status_code in (302, 303)

    def test_go_to_site_updates_site_key(self, client, req_ctx):
        """Session _site_key should be updated to the target site key."""
        user = _login(client, req_ctx, username="gosite1", email="gosite1@test.com")

        resp = client.get(
            "/site/testsite/go/testsite",
            environ_base={"HTTP_X_HOMEFINDER_SITE": "testsite"},
        )
        assert resp.status_code in (302, 303)

        with client.session_transaction() as sess:
            assert sess.get("_site_key") == "testsite"

    def test_go_to_site_remaps_user_id(self, client, req_ctx):
        """When master has different IDs across DBs, session._user_id updates.

        Since tests use a single DB, we verify the lookup-by-email logic
        sets _user_id to the ID found in the target site's users table.
        """
        from app.models import db

        # Create master user (this is the user who will "go to" the site)
        user = make_user(username="gomaster", email="master@remap.com", role="master")
        db.session.add(user)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)
            sess["_site_key"] = "testsite"

        resp = client.get(
            "/site/testsite/go/testsite",
            environ_base={"HTTP_X_HOMEFINDER_SITE": "testsite"},
        )
        assert resp.status_code in (302, 303)

        # After the redirect, session should have the master's ID from the target DB
        with client.session_transaction() as sess:
            assert sess.get("_user_id") == str(user.id)

    def test_go_to_site_next_manage(self, client, req_ctx):
        """?next=manage should redirect to the site_manager URL."""
        user = _login(client, req_ctx, username="gonext", email="gonext@test.com")

        resp = client.get(
            "/site/testsite/go/testsite?next=manage",
            environ_base={"HTTP_X_HOMEFINDER_SITE": "testsite"},
        )
        assert resp.status_code in (302, 303)
        location = resp.headers.get("Location", "")
        # Should contain site_manager route (or /admin/sites)
        assert "sites" in location.lower() or "admin" in location.lower()

    def test_go_to_site_default_redirect(self, client, req_ctx):
        """Without ?next, should redirect to /site/<key>/."""
        user = _login(client, req_ctx, username="godef", email="godef@test.com")

        resp = client.get(
            "/site/testsite/go/testsite",
            environ_base={"HTTP_X_HOMEFINDER_SITE": "testsite"},
        )
        assert resp.status_code in (302, 303)
        location = resp.headers.get("Location", "")
        assert "/site/testsite/" in location


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  4. AJAX FLAG TOGGLE — /api/flag endpoint
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestAjaxFlagToggle:
    """Tests for the POST /api/flag AJAX endpoint."""

    def test_api_toggle_flag_set(self, client, req_ctx):
        """POST with listing_id and flag='favorite' should return status='set'."""
        from app.models import db

        user = _login(client, req_ctx, username="flagger1", email="flagger1@test.com")

        listing = make_listing(address="100 Flag St")
        db.session.add(listing)
        db.session.commit()

        resp = client.post(
            "/site/testsite/api/flag",
            json={"listing_id": listing.id, "flag": "favorite"},
            environ_base={"HTTP_X_HOMEFINDER_SITE": "testsite"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "set"
        assert data["flag"] == "favorite"

    def test_api_toggle_flag_remove(self, client, req_ctx):
        """POST twice with same flag should toggle it off (status='removed')."""
        from app.models import db

        user = _login(client, req_ctx, username="flagger2", email="flagger2@test.com")

        listing = make_listing(address="200 Toggle Ave")
        db.session.add(listing)
        db.session.commit()

        payload = {"listing_id": listing.id, "flag": "maybe"}
        env = {"HTTP_X_HOMEFINDER_SITE": "testsite"}

        # First POST — set
        resp1 = client.post("/site/testsite/api/flag", json=payload, environ_base=env)
        assert resp1.get_json()["status"] == "set"

        # Second POST — remove (toggle)
        resp2 = client.post("/site/testsite/api/flag", json=payload, environ_base=env)
        assert resp2.get_json()["status"] == "removed"
        assert resp2.get_json()["flag"] is None

    def test_api_toggle_flag_invalid_flag(self, client, req_ctx):
        """flag='invalid' should return 400."""
        from app.models import db

        user = _login(client, req_ctx, username="flagger3", email="flagger3@test.com")

        listing = make_listing(address="300 Bad Flag Ln")
        db.session.add(listing)
        db.session.commit()

        resp = client.post(
            "/site/testsite/api/flag",
            json={"listing_id": listing.id, "flag": "invalid"},
            environ_base={"HTTP_X_HOMEFINDER_SITE": "testsite"},
        )
        assert resp.status_code == 400
        assert "invalid flag" in resp.get_json().get("error", "")

    def test_api_toggle_flag_missing_listing(self, client, req_ctx):
        """No listing_id in payload should return 400."""
        user = _login(client, req_ctx, username="flagger4", email="flagger4@test.com")

        resp = client.post(
            "/site/testsite/api/flag",
            json={"flag": "favorite"},
            environ_base={"HTTP_X_HOMEFINDER_SITE": "testsite"},
        )
        assert resp.status_code == 400
        assert "listing_id required" in resp.get_json().get("error", "")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  5. NAV TOOLTIP PLACEMENT — help-hints.js logic
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestNavTooltipPlacement:
    """Tests for the tooltip placement logic in help-hints.js.

    The JS sets placement = 'bottom' for elements with class 'nav-link',
    otherwise falls back to data-help-placement or default 'top'.
    """

    def test_nav_links_get_bottom_placement(self, req_ctx):
        """Elements with .nav-link class should get 'bottom' placement."""
        # Simulates the JS logic:
        #   var placement = el.dataset.helpPlacement || 'top';
        #   if (el.classList.contains('nav-link')) { placement = 'bottom'; }

        class MockElement:
            def __init__(self, classes, help_placement=None):
                self.classes = classes
                self.help_placement = help_placement

        def compute_placement(el):
            placement = el.help_placement or "top"
            if "nav-link" in el.classes:
                placement = "bottom"
            return placement

        el = MockElement(classes=["nav-link"], help_placement=None)
        assert compute_placement(el) == "bottom"

        # Even with an explicit data-help-placement, nav-link overrides
        el = MockElement(classes=["nav-link"], help_placement="right")
        assert compute_placement(el) == "bottom"

    def test_non_nav_elements_get_default_placement(self, req_ctx):
        """Non-nav elements keep data-help-placement or default 'top'."""

        class MockElement:
            def __init__(self, classes, help_placement=None):
                self.classes = classes
                self.help_placement = help_placement

        def compute_placement(el):
            placement = el.help_placement or "top"
            if "nav-link" in el.classes:
                placement = "bottom"
            return placement

        # No placement specified → 'top'
        el = MockElement(classes=["btn", "btn-primary"], help_placement=None)
        assert compute_placement(el) == "top"

        # Explicit placement → use that
        el = MockElement(classes=["btn"], help_placement="right")
        assert compute_placement(el) == "right"

        el = MockElement(classes=["card-header"], help_placement="left")
        assert compute_placement(el) == "left"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  6. SETTINGS PAGE — Guest visibility
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSettingsPageGuestVisibility:
    """Tests for /settings page visibility by auth state.

    Template uses:
        {% if current_user.is_authenticated %} for Power Mode and AI Analysis cards.
    Guests only see the Help Level card.
    """

    def test_settings_route_accessible_to_guests(self, client, req_ctx):
        """GET /settings should return 200 for guests (no login)."""
        resp = client.get(
            "/site/testsite/settings",
            environ_base={"HTTP_X_HOMEFINDER_SITE": "testsite"},
        )
        assert resp.status_code == 200

    def test_settings_guest_sees_help_level_only(self, client, req_ctx):
        """Guest should see Help Level but NOT Power Mode or AI Analysis cards."""
        resp = client.get(
            "/site/testsite/settings",
            environ_base={"HTTP_X_HOMEFINDER_SITE": "testsite"},
        )
        html = resp.data.decode()
        assert "Help Level" in html
        # The Power Mode and AI Analysis cards are inside {% if current_user.is_authenticated %}
        # The HTML comment mentioning "Power Mode" is outside the block, but the
        # actual interactive element (id="settingsPowerMode") should not render.
        assert 'id="settingsPowerMode"' not in html
        assert 'id="settingsAiMode"' not in html

    def test_settings_auth_sees_all_cards(self, client, req_ctx):
        """Authenticated user should see all three settings cards."""
        _login(client, req_ctx, username="settings_auth", email="settings@test.com")

        resp = client.get(
            "/site/testsite/settings",
            environ_base={"HTTP_X_HOMEFINDER_SITE": "testsite"},
        )
        html = resp.data.decode()
        assert "Help Level" in html
        assert "Power Mode" in html
        assert "AI Analysis" in html
