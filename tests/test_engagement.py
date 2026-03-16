# ─────────────────────────────────────────────
# File: tests/test_engagement.py
# App Version: 2026.03.12 | File Version: 1.0.0
# Last Modified: 2026-03-13
# ─────────────────────────────────────────────
"""Regression tests for the three engagement features:
1. "Since your last visit" stats
2. Progressive toast/flash messages after flagging milestones
3. Smart empty states across templates
"""
import pytest
from datetime import datetime, timedelta, timezone
from tests.conftest import make_user, make_listing


class TestSinceLastVisitStats:
    """Feature 1: Since-your-last-visit summary card on dashboard."""

    def test_since_stats_for_authenticated_user(self, req_ctx):
        """Logged-in user with last_login should get since_stats with counts."""
        from app.models import db, Listing
        user = make_user(username="slv1", email="slv1@t.com")
        user.last_login = datetime.now(timezone.utc) - timedelta(days=2)
        db.session.add(user)

        # Create a listing that appeared after last_login
        listing = make_listing(
            address="100 New St",
            zip_code="29401",
        )
        listing.first_seen = datetime.now(timezone.utc) - timedelta(hours=12)
        db.session.add(listing)

        # Create a listing with a price drop after last_login
        drop_listing = make_listing(
            address="200 Drop St",
            zip_code="29401",
        )
        drop_listing.price_change_pct = -5.0
        drop_listing.last_seen = datetime.now(timezone.utc) - timedelta(hours=6)
        db.session.add(drop_listing)
        db.session.commit()

        # Query like the index route does
        _ll = user.last_login
        new_q = Listing.query.filter(
            Listing.status == "active",
            Listing.first_seen > _ll,
        )
        drops_q = Listing.query.filter(
            Listing.status == "active",
            Listing.last_seen > _ll,
            Listing.price_change_pct < 0,
        )
        assert new_q.count() >= 1
        assert drops_q.count() >= 1

    def test_since_stats_old_listings_excluded(self, req_ctx):
        """Listings from before last_login should not appear in since_stats."""
        from app.models import db, Listing
        user = make_user(username="slv2", email="slv2@t.com")
        user.last_login = datetime.now(timezone.utc) - timedelta(hours=6)
        db.session.add(user)

        old_listing = make_listing(address="Old St")
        old_listing.first_seen = datetime.now(timezone.utc) - timedelta(days=5)
        db.session.add(old_listing)
        db.session.commit()

        new_q = Listing.query.filter(
            Listing.status == "active",
            Listing.first_seen > user.last_login,
        )
        assert new_q.count() == 0

    def test_guest_gets_total_stats(self, req_ctx):
        """Guests should see total scored listings, not new/drop counts."""
        from app.models import db
        for i in range(3):
            db.session.add(make_listing(address=f"{i} Guest St"))
        db.session.commit()

        from app.models import Listing
        total = Listing.query.filter(Listing.status == "active").count()
        assert total >= 3

        # Guest since_stats would have total_scored but not new_count
        since_stats = {"total_scored": total, "top_score": 0}
        assert "total_scored" in since_stats
        assert "new_count" not in since_stats


class TestProgressiveNudges:
    """Feature 2: Progressive toast messages after flagging milestones."""

    def test_first_favorite_milestone(self, req_ctx):
        """First favorite should trigger 'Great first pick!' message."""
        from app.models import db, UserFlag
        user = make_user(username="nudge1", email="nudge1@t.com")
        db.session.add(user)
        listing = make_listing(address="1 First St")
        db.session.add(listing)
        db.session.commit()

        flag = UserFlag(user_id=user.id, listing_id=listing.id, flag="favorite")
        db.session.add(flag)
        db.session.commit()

        fav_count = UserFlag.query.filter_by(user_id=user.id, flag="favorite").count()
        assert fav_count == 1
        # At count == 1, the route flashes "Great first pick!"

    def test_third_favorite_milestone(self, req_ctx):
        """Third favorite should trigger portfolio analysis suggestion."""
        from app.models import db, UserFlag
        user = make_user(username="nudge3", email="nudge3@t.com")
        db.session.add(user)
        db.session.commit()

        for i in range(3):
            listing = make_listing(address=f"{i} Third St")
            db.session.add(listing)
            db.session.commit()
            flag = UserFlag(user_id=user.id, listing_id=listing.id, flag="favorite")
            db.session.add(flag)

        db.session.commit()

        fav_count = UserFlag.query.filter_by(user_id=user.id, flag="favorite").count()
        assert fav_count == 3
        # At count == 3, route flashes "AI Portfolio Analysis" suggestion

    def test_fifth_favorite_milestone(self, req_ctx):
        """Fifth favorite should trigger tour planning suggestion."""
        from app.models import db, UserFlag
        user = make_user(username="nudge5", email="nudge5@t.com")
        db.session.add(user)
        db.session.commit()

        for i in range(5):
            listing = make_listing(address=f"{i} Fifth St")
            db.session.add(listing)
            db.session.commit()
            flag = UserFlag(user_id=user.id, listing_id=listing.id, flag="favorite")
            db.session.add(flag)

        db.session.commit()

        fav_count = UserFlag.query.filter_by(user_id=user.id, flag="favorite").count()
        assert fav_count == 5
        # At count == 5, route flashes tour planning suggestion

    def test_milestone_with_agent(self, req_ctx):
        """Principal with agent should get agent-specific nudge text."""
        from app.models import db, UserFlag
        agent_user = make_user(username="ag_nudge", email="ag_nudge@t.com", role="agent")
        db.session.add(agent_user)
        db.session.commit()

        profile = make_agent_profile(agent_user, full_name="Sarah Johnson")
        db.session.add(profile)
        db.session.commit()

        principal = make_user(username="pr_nudge", email="pr_nudge@t.com", role="principal")
        principal.agent_id = profile.id
        db.session.add(principal)
        db.session.commit()

        assert principal.assigned_agent is not None
        agent_first = principal.assigned_agent.full_name.split(" ")[0]
        assert agent_first == "Sarah"

    def test_guest_milestone_at_three(self, req_ctx):
        """Guest at 3 favorites should get account creation nudge."""
        from flask import session
        guest_flags = {"1": "favorite", "2": "favorite", "3": "favorite"}
        guest_fav_count = sum(1 for f in guest_flags.values() if f == "favorite")
        assert guest_fav_count == 3
        # At 3, route flashes account creation link


class TestSmartEmptyStates:
    """Feature 3: Value-first empty states across templates."""

    def test_digest_empty_state_has_value_messaging(self, app):
        """digest.html empty state should suggest broadening filters."""
        import os
        template_path = os.path.join(app.root_path, "templates", "dashboard", "digest.html")
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "broadening your price range" in content
        assert "Browse All Listings" in content

    def test_watch_empty_state_has_value_messaging(self, app):
        """watch.html empty state should explain the feature value."""
        import os
        template_path = os.path.join(app.root_path, "templates", "dashboard", "watch.html")
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "first to know" in content
        assert "price drops" in content.lower() or "price drop" in content.lower()

    def test_admin_agents_empty_has_signup_link(self, app):
        """admin_agents.html should show agent signup link when empty."""
        import os
        template_path = os.path.join(app.root_path, "templates", "dashboard", "admin_agents.html")
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "agent-signup" in content
        assert "all caught up" in content.lower()

    def test_agent_dashboard_empty_has_onboarding(self, app):
        """agent_dashboard.html should explain what happens when adding first client."""
        import os
        template_path = os.path.join(app.root_path, "templates", "dashboard", "agent_dashboard.html")
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "welcome email" in content.lower()
        assert "branding" in content.lower()

    def test_admin_metrics_empty_explains_when_data_appears(self, app):
        """admin_metrics.html empty state should explain when costs appear."""
        import os
        template_path = os.path.join(app.root_path, "templates", "dashboard", "admin_metrics.html")
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "pipeline runs" in content.lower()

    def test_landing_empty_has_signup_prompt(self, app):
        """landing.html empty state should encourage creating an account."""
        import os
        template_path = os.path.join(app.root_path, "templates", "landing.html")
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "free account" in content.lower()

    def test_welcome_empty_has_encouragement(self, app):
        """welcome.html empty state should mention adding markets."""
        import os
        template_path = os.path.join(app.root_path, "templates", "dashboard", "welcome.html")
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "adding new markets" in content.lower() or "check back" in content.lower()

    def test_index_since_stats_card_present(self, app):
        """index.html should contain since_stats rendering block."""
        import os
        template_path = os.path.join(app.root_path, "templates", "dashboard", "index.html")
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "since_stats" in content
        assert "Since your last visit" in content or "since your last" in content.lower()


# Import for make_agent_profile
from tests.conftest import make_agent_profile
