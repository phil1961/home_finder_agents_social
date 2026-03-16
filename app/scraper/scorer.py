# ─────────────────────────────────────────────
# File: app/scraper/scorer.py
# App Version: 2026.03.14 | File Version: 1.1.0
# Last Modified: 2026-03-14
# ─────────────────────────────────────────────
"""
Score listings on how well they match retirement home criteria.

18 scoring factors, each producing a 0-100 sub-score.
Weights use an importance scale (0-10) that gets normalized to percentages.
"""
import logging
import math
from datetime import datetime, timezone

log = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ORIGINAL 5 SCORING FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def score_price(price: int, max_price: int = 600000, min_price: int = 200000) -> float:
    """Lower price = higher score. Sweet spot is min to ~70% of max."""
    if price <= 0:
        return 0
    if price < min_price:
        return 60  # suspiciously cheap — might be lot/land only
    if price <= max_price * 0.7:
        return 100 - (price / max_price) * 30  # 70-100 range
    if price <= max_price:
        return 50 + (max_price - price) / (max_price * 0.3) * 20
    # Over budget
    over = price - max_price
    penalty = min(over / max_price * 100, 50)
    return max(50 - penalty, 0)


def score_size(sqft: int) -> float:
    """Bigger house = better, diminishing returns above 2500."""
    if sqft <= 0:
        return 20
    if sqft >= 3000:
        return 100
    if sqft >= 2000:
        return 70 + (sqft - 2000) / 1000 * 30
    if sqft >= 1200:
        return 30 + (sqft - 1200) / 800 * 40
    return max(sqft / 1200 * 30, 5)


def score_yard(lot_sqft: int | None) -> float:
    """Larger yard = higher score. Target: ≥10,000 sqft lot."""
    if not lot_sqft or lot_sqft <= 0:
        return 10
    if lot_sqft >= 20000:
        return 100
    if lot_sqft >= 10000:
        return 75 + (lot_sqft - 10000) / 10000 * 25
    if lot_sqft >= 5000:
        return 40 + (lot_sqft - 5000) / 5000 * 35
    return max(lot_sqft / 5000 * 40, 5)


def score_features(has_garage: bool, has_porch: bool, has_patio: bool,
                   beds: int = 0, baths: float = 0) -> float:
    """Garage + Porch + Patio = 60pts. Beds ≥ 4 = +20, Baths ≥ 3 = +20."""
    s = 0
    if has_garage:
        s += 20
    if has_porch:
        s += 20
    if has_patio:
        s += 20
    if beds >= 4:
        s += 20
    elif beds == 3:
        s += 10
    if baths >= 3:
        s += 20
    elif baths >= 2.5:
        s += 10
    return min(s, 100)


def score_flood(above_flood_plain: bool | None, flood_zone: str | None) -> float:
    """Above flood plain = best. Unknown = middle."""
    if above_flood_plain is True:
        return 100
    if above_flood_plain is False:
        return 20
    if flood_zone:
        zone = flood_zone.upper()
        if zone.startswith("X") or zone.startswith("C"):
            return 85
        elif zone.startswith("B") or zone.startswith("D"):
            return 50
        else:
            return 25
    return 50


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NEW 12 SCORING FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def score_year_built(year_built: int | None) -> float:
    """Newer = less maintenance. 2020+ → 100, 1960 → ~30."""
    if not year_built or year_built <= 0:
        return 30  # unknown
    now = datetime.now().year
    age = now - year_built
    if age <= 5:
        return 100
    if age <= 15:
        return 85 + (15 - age) / 10 * 15
    if age <= 30:
        return 60 + (30 - age) / 15 * 25
    if age <= 50:
        return 35 + (50 - age) / 20 * 25
    return max(15, 35 - (age - 50) / 30 * 20)


def score_single_story(is_single_story: bool | None, stories: int | None) -> float:
    """Single story is ideal for retirement living."""
    if is_single_story is True:
        return 100
    if stories == 1:
        return 100
    if stories == 2:
        return 40  # doable but not ideal
    if stories and stories >= 3:
        return 15
    if is_single_story is False:
        return 35
    return 50  # unknown


def score_price_per_sqft(price: int, sqft: int, *,
                         low: int = 120, mid_low: int = 150,
                         mid_high: int = 200, high: int = 275) -> float:
    """Lower $/sqft = better value. Breakpoints default to Charleston benchmarks."""
    if not price or not sqft or sqft <= 0:
        return 50
    pps = price / sqft
    if pps <= low:
        return 100
    if pps <= mid_low:
        return 85 + (mid_low - pps) / (mid_low - low) * 15
    if pps <= mid_high:
        return 60 + (mid_high - pps) / (mid_high - mid_low) * 25
    if pps <= high:
        return 30 + (high - pps) / (high - mid_high) * 30
    return max(5, 30 - (pps - high) / 100 * 25)


def score_days_on_market(days: int | None, list_date=None) -> float:
    """Longer on market = more negotiation leverage. 60+ days = best."""
    if days is None and list_date:
        if isinstance(list_date, str):
            try:
                list_date = datetime.fromisoformat(list_date.replace("Z", "+00:00"))
            except Exception:
                return 50
        try:
            days = (datetime.now(timezone.utc) - list_date).days
        except Exception:
            return 50
    if days is None:
        return 50
    if days >= 90:
        return 100  # very motivated seller
    if days >= 60:
        return 80 + (days - 60) / 30 * 20
    if days >= 30:
        return 50 + (days - 30) / 30 * 30
    if days >= 7:
        return 20 + (days - 7) / 23 * 30
    return 10  # brand new listing, little leverage


def score_hoa(hoa_monthly: float | None) -> float:
    """No HOA or low HOA = best. $500+/mo = low score."""
    if hoa_monthly is None:
        return 70  # unknown, likely no HOA
    if hoa_monthly == 0:
        return 100
    if hoa_monthly <= 50:
        return 90
    if hoa_monthly <= 150:
        return 70 + (150 - hoa_monthly) / 100 * 20
    if hoa_monthly <= 300:
        return 40 + (300 - hoa_monthly) / 150 * 30
    if hoa_monthly <= 500:
        return 15 + (500 - hoa_monthly) / 200 * 25
    return 5


def score_proximity_medical(miles: float | None) -> float:
    """Closer to hospital = better. <2mi = great, >15mi = poor."""
    if miles is None:
        return 40  # unknown
    if miles <= 2:
        return 100
    if miles <= 5:
        return 75 + (5 - miles) / 3 * 25
    if miles <= 10:
        return 40 + (10 - miles) / 5 * 35
    if miles <= 15:
        return 15 + (15 - miles) / 5 * 25
    return 5


def score_proximity_grocery(miles: float | None) -> float:
    """Closer to grocery = better. <1mi = great, >10mi = poor."""
    if miles is None:
        return 40  # unknown
    if miles <= 1:
        return 100
    if miles <= 3:
        return 75 + (3 - miles) / 2 * 25
    if miles <= 5:
        return 50 + (5 - miles) / 2 * 25
    if miles <= 10:
        return 20 + (10 - miles) / 5 * 30
    return 5


def score_community_pool(has_pool: bool | None) -> float:
    """Community pool/clubhouse nearby = great for retirement."""
    if has_pool is True:
        return 100
    if has_pool is False:
        return 20
    return 40  # unknown


def score_property_tax(annual_tax: float | None, price: int = 0) -> float:
    """Lower tax rate = better. SC avg ~0.5-0.6% of value."""
    if annual_tax is None or annual_tax <= 0:
        if price > 0:
            # Estimate: SC average ~0.55% of market value
            annual_tax = price * 0.0055
        else:
            return 50  # unknown
    if price <= 0:
        return 50
    rate = annual_tax / price * 100  # as percentage
    if rate <= 0.3:
        return 100
    if rate <= 0.5:
        return 80 + (0.5 - rate) / 0.2 * 20
    if rate <= 0.7:
        return 55 + (0.7 - rate) / 0.2 * 25
    if rate <= 1.0:
        return 30 + (1.0 - rate) / 0.3 * 25
    return max(5, 30 - (rate - 1.0) / 0.5 * 25)


def score_lot_ratio(lot_sqft: int | None, sqft: int | None) -> float:
    """Higher lot-to-house ratio = more yard relative to house. 4:1+ = great."""
    if not lot_sqft or not sqft or sqft <= 0:
        return 40  # unknown
    ratio = lot_sqft / sqft
    if ratio >= 6:
        return 100
    if ratio >= 4:
        return 80 + (ratio - 4) / 2 * 20
    if ratio >= 2.5:
        return 55 + (ratio - 2.5) / 1.5 * 25
    if ratio >= 1.5:
        return 30 + (ratio - 1.5) / 1 * 25
    return max(10, ratio / 1.5 * 30)


def score_price_trend(change_pct: float | None) -> float:
    """Price dropping = opportunity. -10%+ = great, rising = lower score."""
    if change_pct is None:
        return 50  # no price history
    if change_pct <= -10:
        return 100
    if change_pct <= -5:
        return 80 + (-5 - change_pct) / 5 * 20
    if change_pct <= 0:
        return 60 + (-change_pct) / 5 * 20
    if change_pct <= 5:
        return 40 + (5 - change_pct) / 5 * 20
    if change_pct <= 10:
        return 20 + (10 - change_pct) / 5 * 20
    return max(5, 20 - (change_pct - 10) / 10 * 15)


def score_walkability(walk_score: float | None) -> float:
    """Higher walkability = better. 0-100 scale passthrough with floors."""
    if walk_score is None:
        return 40  # unknown — Charleston suburbs aren't very walkable
    return max(min(walk_score, 100), 0)


def _haversine_miles(lat1, lon1, lat2, lon2) -> float:
    """Calculate the great-circle distance in miles between two lat/lng points."""
    R = 3958.8  # Earth radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def score_proximity_poi(listing_lat, listing_lng, poi_lat, poi_lng,
                        max_miles: float = 15.0) -> float:
    """Score based on distance to a point of interest.

    Closer = higher score. Uses Haversine formula.
    Returns 0-100 score.
      0-1 miles:  100
      1-5 miles:  linear 100 -> 70
      5-10 miles: linear 70 -> 30
      10-15 miles: linear 30 -> 0
      15+ miles:  0
    """
    if not listing_lat or not listing_lng or not poi_lat or not poi_lng:
        return 50  # unknown / not configured
    try:
        dist = _haversine_miles(float(listing_lat), float(listing_lng),
                                float(poi_lat), float(poi_lng))
    except (TypeError, ValueError):
        return 50
    if dist <= 1.0:
        return 100.0
    if dist <= 5.0:
        return 100.0 - (dist - 1.0) / 4.0 * 30.0  # 100 -> 70
    if dist <= 10.0:
        return 70.0 - (dist - 5.0) / 5.0 * 40.0   # 70 -> 30
    if dist <= max_miles:
        return 30.0 - (dist - 10.0) / 5.0 * 30.0   # 30 -> 0
    return 0.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  COMPOSITE SCORING ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Default importance weights (0-10) — canonical values live in config.py
from config import DEFAULT_IMPORTANCE

# Map each sub-score key to its importance key (without imp_ prefix).
# Single source of truth — also used by DealScore in models.py.
SCORE_TO_IMP = {
    "price_score": "price", "size_score": "size", "yard_score": "yard",
    "feature_score": "features", "flood_score": "flood",
    "year_built_score": "year_built", "single_story_score": "single_story",
    "price_per_sqft_score": "price_per_sqft",
    "days_on_market_score": "days_on_market", "hoa_score": "hoa",
    "proximity_medical_score": "proximity_medical",
    "proximity_grocery_score": "proximity_grocery",
    "community_pool_score": "community_pool",
    "property_tax_score": "property_tax", "lot_ratio_score": "lot_ratio",
    "price_trend_score": "price_trend", "walkability_score": "walkability",
    "proximity_poi_score": "proximity_poi",
}


def compute_deal_score(listing_data: dict, importance: dict | None = None) -> dict:
    """
    Compute all 17 sub-scores and weighted composite.

    Args:
        listing_data: dict with listing fields
        importance: dict of factor -> 0-10 importance weight (optional)

    Returns dict with all score keys + composite_score.
    """
    imp = dict(DEFAULT_IMPORTANCE)
    if importance:
        imp.update(importance)

    # Compute all 17 sub-scores
    scores = {}

    # Original 5
    scores["price_score"] = score_price(
        listing_data.get("price", 0),
        listing_data.get("max_price", 600000),
        listing_data.get("min_price", 200000),
    )
    scores["size_score"] = score_size(listing_data.get("sqft", 0))
    scores["yard_score"] = score_yard(listing_data.get("lot_sqft"))
    scores["feature_score"] = score_features(
        listing_data.get("has_garage", False),
        listing_data.get("has_porch", False),
        listing_data.get("has_patio", False),
        listing_data.get("beds", 0),
        listing_data.get("baths", 0),
    )
    scores["flood_score"] = score_flood(
        listing_data.get("above_flood_plain"),
        listing_data.get("flood_zone"),
    )

    # New 12
    scores["year_built_score"] = score_year_built(listing_data.get("year_built"))
    scores["single_story_score"] = score_single_story(
        listing_data.get("is_single_story"),
        listing_data.get("stories"),
    )
    scores["price_per_sqft_score"] = score_price_per_sqft(
        listing_data.get("price", 0),
        listing_data.get("sqft", 0),
    )
    scores["days_on_market_score"] = score_days_on_market(
        listing_data.get("days_on_market"),
        listing_data.get("list_date"),
    )
    scores["hoa_score"] = score_hoa(listing_data.get("hoa_monthly"))
    scores["proximity_medical_score"] = score_proximity_medical(
        listing_data.get("nearest_hospital_miles"),
    )
    scores["proximity_grocery_score"] = score_proximity_grocery(
        listing_data.get("nearest_grocery_miles"),
    )
    scores["community_pool_score"] = score_community_pool(
        listing_data.get("has_community_pool"),
    )
    scores["property_tax_score"] = score_property_tax(
        listing_data.get("property_tax_annual"),
        listing_data.get("price", 0),
    )
    scores["lot_ratio_score"] = score_lot_ratio(
        listing_data.get("lot_sqft"),
        listing_data.get("sqft"),
    )
    scores["price_trend_score"] = score_price_trend(
        listing_data.get("price_change_pct"),
    )
    scores["walkability_score"] = score_walkability(
        listing_data.get("walkability"),
    )
    scores["proximity_poi_score"] = score_proximity_poi(
        listing_data.get("latitude"),
        listing_data.get("longitude"),
        listing_data.get("poi_lat"),
        listing_data.get("poi_lng"),
    )

    # ── Weighted composite ───────────────────────────────────
    # Normalize importance to weights summing to 1.0
    total_imp = sum(imp.get(k, 0) for k in SCORE_TO_IMP.values())
    if total_imp <= 0:
        total_imp = 1  # avoid division by zero

    composite = 0
    for score_key, imp_key in SCORE_TO_IMP.items():
        weight = imp.get(imp_key, 0) / total_imp
        composite += scores.get(score_key, 50) * weight

    # Round everything
    for k in scores:
        scores[k] = round(scores[k], 1)
    scores["composite_score"] = round(composite, 1)

    return scores
