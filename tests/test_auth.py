# ─────────────────────────────────────────────
# File: tests/test_auth.py
# App Version: 2026.03.12 | File Version: 1.0.0
# Last Modified: 2026-03-13
# ─────────────────────────────────────────────
"""Regression tests for auth: registration, login, verification, agent guards."""
import pytest
from tests.conftest import make_user, make_agent_profile


class TestRegistration:
    """Test user registration flow."""

    def test_register_creates_user(self, req_ctx):
        from app.models import db, User
        user = make_user(username="newuser", email="new@test.com")
        db.session.add(user)
        db.session.commit()

        found = User.query.filter_by(username="newuser").first()
        assert found is not None
        assert found.email == "new@test.com"
        assert found.is_verified is True  # test helper sets this

    def test_duplicate_username_prevented(self, req_ctx):
        from app.models import db, User
        from sqlalchemy.exc import IntegrityError
        user1 = make_user(username="dupe", email="dupe1@test.com")
        db.session.add(user1)
        db.session.commit()

        user2 = make_user(username="dupe", email="dupe2@test.com")
        db.session.add(user2)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_registration_links_watches(self, req_ctx):
        """Registration should link existing guest watches to the new user."""
        from app.models import db
        from app.services.street_watch import create_watch, link_watches_to_user

        # Create a guest watch
        watch, _ = create_watch("linkme@test.com", "Oak Dr", "29401")
        assert watch.user_id is None

        # Register user with same email
        user = make_user(username="linkme", email="linkme@test.com")
        db.session.add(user)
        db.session.commit()

        link_watches_to_user("linkme@test.com", user.id)
        db.session.expire_all()
        assert watch.user_id == user.id


class TestLogin:
    """Test login flow."""

    def test_correct_password_succeeds(self, req_ctx):
        from app.models import db
        user = make_user(username="login1", email="login1@test.com")
        db.session.add(user)
        db.session.commit()

        assert user.check_password("testpass123") is True

    def test_wrong_password_fails(self, req_ctx):
        from app.models import db
        user = make_user(username="login2", email="login2@test.com")
        db.session.add(user)
        db.session.commit()

        assert user.check_password("wrongpassword") is False

    def test_unverified_user_flag(self, req_ctx):
        from app.models import db
        user = make_user(username="unv", email="unv@test.com", verified=False)
        db.session.add(user)
        db.session.commit()

        assert user.is_verified is False


class TestAgentProfileGuards:
    """Regression: agent routes must not 500 when AgentProfile is missing."""

    def test_agent_without_profile(self, req_ctx):
        """An agent user without AgentProfile should not crash role checks."""
        from app.models import db
        agent = make_user(username="noprofile", email="noprofile@test.com", role="agent")
        db.session.add(agent)
        db.session.commit()

        # agent_profile should be None, not raise an error
        assert agent.agent_profile is None
        assert agent.is_agent is True

    def test_agent_with_profile(self, req_ctx):
        """An agent with a proper profile should work normally."""
        from app.models import db
        agent = make_user(username="withprofile", email="wp@test.com", role="agent")
        db.session.add(agent)
        db.session.commit()

        profile = make_agent_profile(agent, brand_color="#123456",
                                     brand_tagline="Test Tagline")
        db.session.add(profile)
        db.session.commit()

        assert agent.agent_profile is not None
        assert agent.agent_profile.brand_color == "#123456"
        assert agent.agent_profile.brand_tagline == "Test Tagline"


class TestMasquerade:
    """Test masquerade (agent-as-client) system."""

    def test_principal_has_assigned_agent(self, req_ctx):
        """Principal should see agent branding via assigned_agent relationship."""
        from app.models import db
        agent = make_user(username="masq_ag", email="masq_ag@t.com", role="agent")
        db.session.add(agent)
        db.session.commit()

        profile = make_agent_profile(agent, full_name="Masq Agent",
                                     brand_color="#ff0000")
        db.session.add(profile)
        db.session.commit()

        principal = make_user(username="masq_pr", email="masq_pr@t.com", role="principal")
        principal.agent_id = profile.id
        db.session.add(principal)
        db.session.commit()

        # Principal branding check — same logic as base.html
        assert principal.assigned_agent is not None
        assert principal.assigned_agent.brand_color == "#ff0000"

    def test_regular_user_no_agent(self, req_ctx):
        """Regular client without agent_id should have no assigned_agent."""
        from app.models import db
        user = make_user(username="no_ag", email="no_ag@t.com")
        db.session.add(user)
        db.session.commit()

        assert user.assigned_agent is None


class TestCloseAccount:
    """Test account closure logic."""

    def test_close_account_scrambles_credentials(self, req_ctx):
        from app.models import db
        user = make_user(username="closer", email="closer@test.com")
        db.session.add(user)
        db.session.commit()

        uid = user.id
        user.username = f"closed_{uid}_{user.username}"
        user.email = f"closed_{uid}_{user.email}"
        user.is_verified = False
        user.password_hash = "ACCOUNT_CLOSED"
        db.session.commit()

        assert user.username.startswith("closed_")
        assert user.email.startswith("closed_")
        assert user.check_password("testpass123") is False
