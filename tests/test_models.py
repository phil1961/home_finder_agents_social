# ─────────────────────────────────────────────
# File: tests/test_models.py
# App Version: 2026.03.12 | File Version: 1.0.0
# Last Modified: 2026-03-13
# ─────────────────────────────────────────────
"""Regression tests for ORM models: User, Listing, AgentProfile, DealScore."""
import json
import pytest
from tests.conftest import make_user, make_listing, make_agent_profile


class TestUserModel:
    """Test User model basics: password, roles, prefs."""

    def test_password_hashing(self, req_ctx):
        from app.models import db
        user = make_user()
        db.session.add(user)
        db.session.commit()
        assert user.check_password("testpass123") is True
        assert user.check_password("wrongpass") is False

    def test_default_role_is_client(self, req_ctx):
        from app.models import db
        user = make_user()
        assert user.role == "client"
        assert user.is_client is True
        assert user.is_agent is False
        assert user.is_owner is False
        assert user.is_master is False

    def test_role_hierarchy(self, req_ctx):
        from app.models import db
        master = make_user(username="m", email="m@t.com", role="master")
        owner = make_user(username="o", email="o@t.com", role="owner")
        agent = make_user(username="a", email="a@t.com", role="agent")

        assert master.is_master is True
        assert master.is_owner is True  # master can do everything owner can
        assert owner.is_owner is True
        assert owner.is_master is False
        assert agent.is_agent is True
        assert agent.is_admin is True

    def test_get_prefs_returns_defaults(self, req_ctx):
        from app.models import db
        user = make_user()
        prefs = user.get_prefs()
        assert "max_price" in prefs
        assert "imp_price" in prefs
        assert prefs["max_price"] == 600000

    def test_set_prefs_only_stores_diff(self, req_ctx):
        from app.models import db
        user = make_user()
        db.session.add(user)
        db.session.commit()

        prefs = user.get_prefs()
        prefs["max_price"] = 800000
        user.set_prefs(prefs)
        db.session.commit()

        stored = json.loads(user.preferences_json)
        assert stored["max_price"] == 800000
        # Default values should NOT be in stored json
        assert "imp_price" not in stored

    def test_principal_has_agent(self, req_ctx):
        from app.models import db
        agent_user = make_user(username="ag", email="ag@t.com", role="agent")
        db.session.add(agent_user)
        db.session.commit()

        profile = make_agent_profile(agent_user)
        db.session.add(profile)
        db.session.commit()

        principal = make_user(username="pr", email="pr@t.com", role="principal")
        principal.agent_id = profile.id
        db.session.add(principal)
        db.session.commit()

        assert principal.assigned_agent is not None
        assert principal.assigned_agent.full_name == "Test Agent"


class TestAgentProfile:
    """Test AgentProfile model."""

    def test_create_agent_profile(self, req_ctx):
        from app.models import db
        user = make_user(username="agent1", email="agent1@t.com", role="agent")
        db.session.add(user)
        db.session.commit()

        profile = make_agent_profile(user, brand_color="#ff5500")
        db.session.add(profile)
        db.session.commit()

        assert profile.is_approved is True
        assert profile.brand_color == "#ff5500"
        assert profile.user.username == "agent1"

    def test_pending_agent_not_approved(self, req_ctx):
        from app.models import db
        user = make_user(username="agent2", email="agent2@t.com", role="agent")
        db.session.add(user)
        db.session.commit()

        profile = make_agent_profile(user, status="pending")
        db.session.add(profile)
        db.session.commit()

        assert profile.is_approved is False

    def test_client_count(self, req_ctx):
        from app.models import db
        agent_user = make_user(username="agent3", email="agent3@t.com", role="agent")
        db.session.add(agent_user)
        db.session.commit()

        profile = make_agent_profile(agent_user)
        db.session.add(profile)
        db.session.commit()

        # Add two clients
        c1 = make_user(username="c1", email="c1@t.com", role="client")
        c1.agent_id = profile.id
        c2 = make_user(username="c2", email="c2@t.com", role="client")
        c2.agent_id = profile.id
        db.session.add_all([c1, c2])
        db.session.commit()

        assert profile.client_count == 2


class TestListingModel:
    """Test Listing model."""

    def test_create_listing(self, req_ctx):
        from app.models import db
        listing = make_listing()
        db.session.add(listing)
        db.session.commit()

        assert listing.id is not None
        assert listing.status == "active"
        assert listing.price == 350000

    def test_listing_first_seen_auto_set(self, req_ctx):
        from app.models import db
        listing = make_listing()
        db.session.add(listing)
        db.session.commit()
        assert listing.first_seen is not None


class TestUserFlag:
    """Test flagging system."""

    def test_create_and_query_flag(self, req_ctx):
        from app.models import db, UserFlag
        user = make_user(username="flagger", email="f@t.com")
        db.session.add(user)
        listing = make_listing()
        db.session.add(listing)
        db.session.commit()

        flag = UserFlag(user_id=user.id, listing_id=listing.id, flag="favorite")
        db.session.add(flag)
        db.session.commit()

        found = UserFlag.query.filter_by(user_id=user.id, flag="favorite").all()
        assert len(found) == 1

    def test_flag_count_for_milestones(self, req_ctx):
        """Verify we can count favorites for progressive nudge milestones."""
        from app.models import db, UserFlag
        user = make_user(username="counter", email="cnt@t.com")
        db.session.add(user)
        db.session.commit()

        for i in range(5):
            listing = make_listing(address=f"{i} Test St")
            db.session.add(listing)
            db.session.commit()
            flag = UserFlag(user_id=user.id, listing_id=listing.id, flag="favorite")
            db.session.add(flag)

        db.session.commit()

        count = UserFlag.query.filter_by(user_id=user.id, flag="favorite").count()
        assert count == 5
