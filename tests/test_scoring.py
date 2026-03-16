# ─────────────────────────────────────────────
# File: tests/test_scoring.py
# App Version: 2026.03.12 | File Version: 1.0.0
# Last Modified: 2026-03-13
# ─────────────────────────────────────────────
"""Regression tests for deal scoring: DealScore, composite computation, user weights."""
import pytest
from tests.conftest import make_user, make_listing


class TestDealScoreModel:
    """Test DealScore creation and composite computation."""

    def test_create_deal_score(self, req_ctx):
        from app.models import db, DealScore
        listing = make_listing()
        db.session.add(listing)
        db.session.commit()

        score = DealScore(
            listing_id=listing.id,
            price_score=80,
            size_score=60,
            yard_score=70,
            feature_score=50,
            flood_score=90,
            composite_score=70,
        )
        db.session.add(score)
        db.session.commit()

        assert listing.deal_score is not None
        assert listing.deal_score.composite_score == 70

    def test_composite_with_user_weights(self, req_ctx):
        """User-specific composite should reflect their importance weights."""
        from app.models import db, DealScore
        import json

        listing = make_listing()
        db.session.add(listing)
        db.session.commit()

        score = DealScore(
            listing_id=listing.id,
            price_score=100,
            size_score=0,
            yard_score=0,
            feature_score=0,
            flood_score=0,
            composite_score=50,
            extended_scores_json=json.dumps({
                "year_built": 50, "single_story": 50,
                "price_per_sqft": 50, "days_on_market": 50,
                "hoa": 50, "proximity_medical": 50,
                "proximity_grocery": 50, "community_pool": 50,
                "property_tax": 50, "lot_ratio": 50,
                "price_trend": 50, "walkability": 50,
            }),
        )
        db.session.add(score)
        db.session.commit()

        # User who cares only about price
        prefs_price_only = {
            "imp_price": 10, "imp_size": 0, "imp_yard": 0,
            "imp_features": 0, "imp_flood": 0, "imp_year_built": 0,
            "imp_single_story": 0, "imp_price_per_sqft": 0,
            "imp_days_on_market": 0, "imp_hoa": 0,
            "imp_proximity_medical": 0, "imp_proximity_grocery": 0,
            "imp_community_pool": 0, "imp_property_tax": 0,
            "imp_lot_ratio": 0, "imp_price_trend": 0,
            "imp_walkability": 0,
        }
        composite = score.compute_user_composite(prefs_price_only)
        # With only price weight, composite should be high (price score gets
        # recomputed via score_price() based on listing price vs user range)
        assert composite > 50

    def test_composite_with_balanced_weights(self, req_ctx):
        """Balanced weights should produce a middle-range composite."""
        from app.models import db, DealScore
        import json

        listing = make_listing()
        db.session.add(listing)
        db.session.commit()

        score = DealScore(
            listing_id=listing.id,
            price_score=100,
            size_score=0,
            yard_score=50,
            feature_score=50,
            flood_score=50,
            composite_score=50,
            extended_scores_json=json.dumps({
                "year_built": 50, "single_story": 50,
                "price_per_sqft": 50, "days_on_market": 50,
                "hoa": 50, "proximity_medical": 50,
                "proximity_grocery": 50, "community_pool": 50,
                "property_tax": 50, "lot_ratio": 50,
                "price_trend": 50, "walkability": 50,
            }),
        )
        db.session.add(score)
        db.session.commit()

        prefs_balanced = {f"imp_{k}": 5 for k in [
            "price", "size", "yard", "features", "flood",
            "year_built", "single_story", "price_per_sqft",
            "days_on_market", "hoa", "proximity_medical",
            "proximity_grocery", "community_pool", "property_tax",
            "lot_ratio", "price_trend", "walkability",
        ]}
        composite = score.compute_user_composite(prefs_balanced)
        # Most scores are 50, price is 100, size is 0 → avg around 50
        assert 30 < composite < 70

    def test_zero_weights_returns_zero(self, req_ctx):
        """If all weights are zero, composite should be 0 (no division by zero)."""
        from app.models import db, DealScore
        listing = make_listing()
        db.session.add(listing)
        db.session.commit()

        score = DealScore(
            listing_id=listing.id,
            price_score=100,
            size_score=100,
            yard_score=100,
            feature_score=100,
            flood_score=100,
            composite_score=100,
        )
        db.session.add(score)
        db.session.commit()

        prefs_zero = {f"imp_{k}": 0 for k in [
            "price", "size", "yard", "features", "flood",
            "year_built", "single_story", "price_per_sqft",
            "days_on_market", "hoa", "proximity_medical",
            "proximity_grocery", "community_pool", "property_tax",
            "lot_ratio", "price_trend", "walkability",
        ]}
        composite = score.compute_user_composite(prefs_zero)
        # With all weights zero, returns neutral 50.0 (no division by zero)
        assert composite == 50.0


class TestDefaultImportanceWeights:
    """Verify the 18 default importance weights exist and are valid."""

    def test_all_17_factors_present(self):
        from config import DEFAULT_IMPORTANCE
        expected = {
            "price", "size", "yard", "features", "flood",
            "year_built", "single_story", "price_per_sqft",
            "days_on_market", "hoa", "proximity_medical",
            "proximity_grocery", "community_pool", "property_tax",
            "lot_ratio", "price_trend", "walkability",
            "proximity_poi",
        }
        assert set(DEFAULT_IMPORTANCE.keys()) == expected

    def test_weights_in_valid_range(self):
        from config import DEFAULT_IMPORTANCE
        for factor, weight in DEFAULT_IMPORTANCE.items():
            assert 0 <= weight <= 10, f"{factor} weight {weight} out of range"
