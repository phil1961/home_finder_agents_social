# ─────────────────────────────────────────────
# File: tests/test_street_watch.py
# App Version: 2026.03.12 | File Version: 1.0.0
# Last Modified: 2026-03-13
# ─────────────────────────────────────────────
"""Regression tests for Street Watch service: extraction, CRUD, linking."""
import pytest
from tests.conftest import make_user, make_listing


class TestExtractStreetName:
    """Test street name extraction and normalisation."""

    def test_basic_address(self, req_ctx):
        from app.services.street_watch import extract_street_name
        norm, display = extract_street_name("123 Oak Dr, Charleston, SC 29414")
        assert norm == "OAK DR"
        assert display == "Oak DR"

    def test_full_suffix_normalised(self, req_ctx):
        from app.services.street_watch import extract_street_name
        norm, _ = extract_street_name("456 Elm Street, Town, SC")
        assert norm == "ELM ST"

    def test_directional_prefix_preserved(self, req_ctx):
        from app.services.street_watch import extract_street_name
        norm, display = extract_street_name("789 N Main Blvd, City, SC")
        assert norm == "N MAIN BLVD"
        assert "N" in display

    def test_empty_address_returns_none(self, req_ctx):
        from app.services.street_watch import extract_street_name
        norm, display = extract_street_name("")
        assert norm is None
        assert display is None

    def test_none_address_returns_none(self, req_ctx):
        from app.services.street_watch import extract_street_name
        norm, display = extract_street_name(None)
        assert norm is None
        assert display is None

    def test_address_with_unit(self, req_ctx):
        from app.services.street_watch import extract_street_name
        norm, _ = extract_street_name("100A Pine Lane, Town")
        assert norm == "PINE LN"

    def test_multiple_suffixes(self, req_ctx):
        """All known suffixes should normalise correctly."""
        from app.services.street_watch import extract_street_name
        cases = [
            ("1 Test Drive", "TEST DR"),
            ("2 Test Road", "TEST RD"),
            ("3 Test Avenue", "TEST AVE"),
            ("4 Test Court", "TEST CT"),
            ("5 Test Circle", "TEST CIR"),
            ("6 Test Place", "TEST PL"),
            ("7 Test Terrace", "TEST TER"),
            ("8 Test Parkway", "TEST PKWY"),
            ("9 Test Highway", "TEST HWY"),
            ("10 Test Way", "TEST WAY"),
            ("11 Test Trail", "TEST TRL"),
        ]
        for addr, expected in cases:
            norm, _ = extract_street_name(addr)
            assert norm == expected, f"Failed for {addr!r}: got {norm!r}"


class TestCreateWatch:
    """Test watch creation, deduplication, and reactivation."""

    def test_create_new_watch(self, req_ctx):
        from app.services.street_watch import create_watch
        from app.models import db
        user = make_user(username="watcher1", email="w1@test.com")
        db.session.add(user)
        db.session.commit()

        watch, created = create_watch("w1@test.com", "Oak Dr", "29401", user_id=user.id)
        assert created is True
        assert watch.email == "w1@test.com"
        assert watch.zip_code == "29401"
        assert watch.is_active is True
        assert watch.unsubscribe_token is not None

    def test_duplicate_watch_returns_existing(self, req_ctx):
        from app.services.street_watch import create_watch
        from app.models import db
        user = make_user(username="watcher2", email="w2@test.com")
        db.session.add(user)
        db.session.commit()

        watch1, created1 = create_watch("w2@test.com", "Oak Dr", "29401", user_id=user.id)
        watch2, created2 = create_watch("w2@test.com", "Oak Dr", "29401", user_id=user.id)
        assert created1 is True
        assert created2 is False
        assert watch1.id == watch2.id

    def test_reactivate_deactivated_watch(self, req_ctx):
        from app.services.street_watch import create_watch, deactivate_watch
        from app.models import db
        user = make_user(username="watcher3", email="w3@test.com")
        db.session.add(user)
        db.session.commit()

        watch, _ = create_watch("w3@test.com", "Elm St", "29401", user_id=user.id)
        deactivate_watch(watch.id, user_id=user.id)
        assert watch.is_active is False

        watch2, created = create_watch("w3@test.com", "Elm St", "29401", user_id=user.id)
        assert created is True
        assert watch2.is_active is True
        assert watch2.id == watch.id

    def test_link_watch_to_user_on_create(self, req_ctx):
        """When a watch exists without user_id, create_watch with user_id links it."""
        from app.services.street_watch import create_watch
        from app.models import db
        user = make_user(username="watcher4", email="w4@test.com")
        db.session.add(user)
        db.session.commit()

        # Create watch without user_id (guest)
        watch1, _ = create_watch("w4@test.com", "Pine Rd", "29401")
        assert watch1.user_id is None

        # Re-call with user_id — should link
        watch2, created = create_watch("w4@test.com", "Pine Rd", "29401", user_id=user.id)
        assert created is False
        assert watch2.user_id == user.id


class TestDeactivateWatch:
    """Test watch deactivation with ownership checks."""

    def test_deactivate_by_user_id(self, req_ctx):
        from app.services.street_watch import create_watch, deactivate_watch
        from app.models import db
        user = make_user(username="deact1", email="d1@test.com")
        db.session.add(user)
        db.session.commit()

        watch, _ = create_watch("d1@test.com", "Oak Dr", "29401", user_id=user.id)
        result = deactivate_watch(watch.id, user_id=user.id)
        assert result is True
        assert watch.is_active is False

    def test_deactivate_by_email(self, req_ctx):
        from app.services.street_watch import create_watch, deactivate_watch
        from app.models import db

        watch, _ = create_watch("guest@test.com", "Oak Dr", "29403")
        result = deactivate_watch(watch.id, email="guest@test.com")
        assert result is True

    def test_deactivate_wrong_owner_fails(self, req_ctx):
        from app.services.street_watch import create_watch, deactivate_watch
        from app.models import db
        user = make_user(username="deact2", email="d2@test.com")
        db.session.add(user)
        db.session.commit()

        watch, _ = create_watch("d2@test.com", "Oak Dr", "29401", user_id=user.id)
        result = deactivate_watch(watch.id, user_id=9999)
        assert result is False
        assert watch.is_active is True

    def test_deactivate_nonexistent_watch(self, req_ctx):
        from app.services.street_watch import deactivate_watch
        result = deactivate_watch(99999, user_id=1)
        assert result is False


class TestDeactivateByToken:
    """Test token-based unsubscribe."""

    def test_deactivate_by_valid_token(self, req_ctx):
        from app.services.street_watch import create_watch, deactivate_by_token
        from app.models import db

        watch, _ = create_watch("token@test.com", "Maple Ave", "29401")
        token = watch.unsubscribe_token
        result = deactivate_by_token(token)
        assert result is True
        assert watch.is_active is False

    def test_deactivate_by_invalid_token(self, req_ctx):
        from app.services.street_watch import deactivate_by_token
        result = deactivate_by_token("totally-fake-token")
        assert result is False


class TestLinkWatchesToUser:
    """Test linking guest watches to a newly registered user."""

    def test_link_watches_to_user(self, req_ctx):
        from app.services.street_watch import create_watch, link_watches_to_user
        from app.models import db

        # Create guest watches (no user_id)
        w1, _ = create_watch("link@test.com", "Oak Dr", "29401")
        w2, _ = create_watch("link@test.com", "Elm St", "29403")
        assert w1.user_id is None
        assert w2.user_id is None

        user = make_user(username="linker", email="link@test.com")
        db.session.add(user)
        db.session.commit()

        link_watches_to_user("link@test.com", user.id)

        # Refresh
        db.session.expire_all()
        assert w1.user_id == user.id
        assert w2.user_id == user.id


class TestGetUserWatches:
    """Test fetching watches for dashboard widget."""

    def test_get_by_user_id(self, req_ctx):
        from app.services.street_watch import create_watch, get_user_watches
        from app.models import db
        user = make_user(username="getter1", email="g1@test.com")
        db.session.add(user)
        db.session.commit()

        create_watch("g1@test.com", "Oak Dr", "29401", user_id=user.id)
        create_watch("g1@test.com", "Elm St", "29403", user_id=user.id)

        watches = get_user_watches(user_id=user.id)
        assert len(watches) == 2

    def test_get_by_email(self, req_ctx):
        from app.services.street_watch import create_watch, get_user_watches
        from app.models import db

        create_watch("g2@test.com", "Pine Rd", "29401")
        watches = get_user_watches(email="g2@test.com")
        assert len(watches) == 1

    def test_inactive_watches_excluded(self, req_ctx):
        from app.services.street_watch import create_watch, deactivate_watch, get_user_watches
        from app.models import db
        user = make_user(username="getter3", email="g3@test.com")
        db.session.add(user)
        db.session.commit()

        w, _ = create_watch("g3@test.com", "Oak Dr", "29401", user_id=user.id)
        deactivate_watch(w.id, user_id=user.id)

        watches = get_user_watches(user_id=user.id)
        assert len(watches) == 0
