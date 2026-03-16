# ─────────────────────────────────────────────
# File: pipeline.py
# App Version: 2026.03.14 | File Version: 1.3.0
# Last Modified: 2026-03-14
# ─────────────────────────────────────────────
"""
Pipeline: fetch from both APIs → deduplicate → upsert to DB → score.

Call run_pipeline(app) from the scheduler or manually.
"""
import json
import logging
from datetime import datetime, timezone

from app.models import db, Listing, DealScore
from app.scraper.zillow import fetch_all_zillow
from app.scraper.realtor import fetch_all_realtor
from app.scraper.scorer import compute_deal_score

log = logging.getLogger(__name__)


def _all_zip_codes(site=None) -> list[str]:
    """Collect zip codes from site registry entry, falling back to config."""
    if site and site.get("zip_codes_json"):
        import json as _json
        try:
            return sorted(_json.loads(site["zip_codes_json"]))
        except (ValueError, TypeError):
            pass
    try:
        from config import TARGET_AREAS
        zips = set()
        for area_info in TARGET_AREAS.values():
            zips.update(area_info.get("zip_codes", []))
        return sorted(zips)
    except ImportError:
        return []


def _zip_to_area(zip_code: str, site=None) -> str | None:
    """Map a zip code to an area name, or None."""
    if site:
        return site.get("display_name")
    try:
        from config import TARGET_AREAS
        for area_name, info in TARGET_AREAS.items():
            if zip_code in info.get("zip_codes", []):
                return area_name
    except ImportError:
        pass
    return None


def _upsert_listing(data: dict, site=None, existing=None) -> Listing:
    """
    Insert a new listing or update an existing one (matched by source_id).

    Args:
        data:     dict of listing fields (must include source_id)
        site:     registry site dict (for area name lookup)
        existing: pre-loaded Listing instance if already fetched, or None.
                  When None, falls back to a DB query (legacy path).

    Returns the Listing object.
    """
    if existing is None:
        existing = Listing.query.filter_by(source_id=data["source_id"]).first()

    if existing:
        # Update mutable fields
        if data.get("price") and data["price"] != existing.price:
            # Track price change
            history = json.loads(existing.price_history_json or "[]")
            history.append({
                "price": existing.price,
                "date": existing.last_seen.isoformat() if existing.last_seen else
                        datetime.now(timezone.utc).isoformat(),
                "event": "reduced" if data["price"] < existing.price else "increased",
            })
            existing.price_history_json = json.dumps(history)
            existing.price = data["price"]

        existing.status = "active"
        existing.last_seen = datetime.now(timezone.utc)
        # Update URL if existing is empty
        if data.get("url") and not existing.url:
            existing.url = data["url"]
        # Backfill coordinates if missing
        if data.get("latitude") and not existing.latitude:
            existing.latitude = data["latitude"]
            existing.longitude = data.get("longitude")
        # Update description if we got a better one
        if data.get("description") and len(data["description"]) > len(existing.description or ""):
            existing.description = data["description"]
        # Update features if newly detected
        if data.get("has_garage"):
            existing.has_garage = True
        if data.get("has_porch"):
            existing.has_porch = True
        if data.get("has_patio"):
            existing.has_patio = True
        if data.get("lot_sqft") and not existing.lot_sqft:
            existing.lot_sqft = data["lot_sqft"]
        if data.get("photo_urls_json") and data["photo_urls_json"] != "[]":
            # Always update if existing has no photos, or new has more
            existing_empty = existing.photo_urls_json in (None, "[]", "")
            if existing_empty:
                existing.photo_urls_json = data["photo_urls_json"]
            else:
                # Keep whichever has more photos
                try:
                    new_count = len(json.loads(data["photo_urls_json"]))
                    old_count = len(json.loads(existing.photo_urls_json or "[]"))
                    if new_count > old_count:
                        existing.photo_urls_json = data["photo_urls_json"]
                except Exception:
                    pass

        return existing

    # New listing
    area_name = _zip_to_area(data.get("zip_code", ""), site=site)

    # Parse list_date if string
    list_date = data.get("list_date")
    if isinstance(list_date, str):
        try:
            list_date = datetime.fromisoformat(list_date.replace("Z", "+00:00"))
        except Exception:
            list_date = None

    # Calculate days on market
    days_on_market = data.get("days_on_market")
    if days_on_market is None and list_date:
        try:
            days_on_market = (datetime.now(timezone.utc) - list_date).days
        except Exception:
            pass

    listing = Listing(
        source=data["source"],
        source_id=data["source_id"],
        url=data.get("url", ""),
        address=data["address"],
        city=data.get("city", ""),
        zip_code=data.get("zip_code", ""),
        area_name=area_name,
        price=data.get("price", 0),
        beds=data.get("beds", 0),
        baths=data.get("baths", 0),
        sqft=data.get("sqft", 0),
        lot_sqft=data.get("lot_sqft"),
        year_built=data.get("year_built"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        has_garage=data.get("has_garage", False),
        has_porch=data.get("has_porch", False),
        has_patio=data.get("has_patio", False),
        flood_zone=data.get("flood_zone"),
        above_flood_plain=data.get("above_flood_plain"),
        # New fields
        stories=data.get("stories"),
        is_single_story=data.get("is_single_story"),
        hoa_monthly=data.get("hoa_monthly"),
        list_date=list_date,
        days_on_market=days_on_market,
        property_tax_annual=data.get("property_tax_annual"),
        has_community_pool=data.get("has_community_pool", False),
        nearest_hospital_miles=data.get("nearest_hospital_miles"),
        nearest_grocery_miles=data.get("nearest_grocery_miles"),
        walkability_score=data.get("walkability_score"),
        price_change_pct=data.get("price_change_pct"),
        description=data.get("description", ""),
        photo_urls_json=data.get("photo_urls_json", "[]"),
        price_history_json=json.dumps([{
            "price": data.get("price", 0),
            "date": datetime.now(timezone.utc).isoformat(),
            "event": "listed",
        }]) if data.get("price") else "[]",
    )
    db.session.add(listing)
    return listing


def _score_listing(listing: Listing, importance: dict | None = None,
                   min_price: int = None, max_price: int = None):
    """Compute and save/update the DealScore for a listing.

    Args:
        listing: Listing model instance
        importance: optional dict of factor -> 0-10 importance weight
                    (keys: price, size, yard, features, flood, etc.)
        min_price: optional user min price preference
        max_price: optional user max price preference
    """
    from config import MAX_PRICE
    data = {
        # Original 5
        "price": listing.price,
        "max_price": max_price or MAX_PRICE,
        "min_price": min_price or 200000,
        "sqft": listing.sqft,
        "lot_sqft": listing.lot_sqft,
        "has_garage": listing.has_garage,
        "has_porch": listing.has_porch,
        "has_patio": listing.has_patio,
        "beds": listing.beds,
        "baths": listing.baths,
        "above_flood_plain": listing.above_flood_plain,
        "flood_zone": listing.flood_zone,
        # New 12
        "year_built": listing.year_built,
        "is_single_story": listing.is_single_story,
        "stories": listing.stories,
        "hoa_monthly": listing.hoa_monthly,
        "days_on_market": listing.days_on_market,
        "list_date": listing.list_date,
        "nearest_hospital_miles": listing.nearest_hospital_miles,
        "nearest_grocery_miles": listing.nearest_grocery_miles,
        "has_community_pool": listing.has_community_pool,
        "property_tax_annual": listing.property_tax_annual,
        "price_change_pct": listing.price_change_pct,
        "walkability": listing.walkability_score,
        # POI proximity — lat/lng passed for completeness; poi_lat/poi_lng
        # intentionally omitted (per-user, recomputed in compute_user_composite)
        "latitude": listing.latitude,
        "longitude": listing.longitude,
    }
    scores = compute_deal_score(data, importance=importance)

    # Separate original 5 (columns) from extended 12 (JSON)
    original_keys = ["price_score", "size_score", "yard_score",
                     "feature_score", "flood_score", "composite_score"]
    extended = {k: v for k, v in scores.items() if k not in original_keys}

    if listing.deal_score:
        for k in original_keys:
            setattr(listing.deal_score, k, scores.get(k, 0))
        listing.deal_score.extended_scores = extended
        listing.deal_score.scored_at = datetime.now(timezone.utc)
    else:
        ds = DealScore(
            listing=listing,
            price_score=scores.get("price_score", 0),
            size_score=scores.get("size_score", 0),
            yard_score=scores.get("yard_score", 0),
            feature_score=scores.get("feature_score", 0),
            flood_score=scores.get("flood_score", 0),
            composite_score=scores.get("composite_score", 0),
        )
        ds.extended_scores = extended
        db.session.add(ds)


def run_pipeline(app=None, site_key=None):
    """
    Full pipeline: fetch → upsert → score → commit.

    Args:
        app:      Flask app instance (optional — creates one if omitted)
        site_key: registry site key (e.g. "charleston", "bathwv").
                  If None, uses the default site.
    """
    from config import MAX_PRICE, MIN_BEDS, MIN_BATHS

    def _execute():
        # ── Resolve site and bind engine ──────────────────────────
        from app.services.registry import get_site, get_default_site_key
        from app import _get_site_engine
        import flask

        _key = site_key or get_default_site_key()
        site = get_site(_key)
        if not site:
            log.error(f"Site '{_key}' not found in registry. Aborting.")
            return 0

        log.info(f"Pipeline running for site '{_key}' → {site['db_path']}")

        # Push site engine into Flask g so _SiteRoutedSession uses it
        ctx = flask.has_app_context()
        if ctx:
            flask.g.site = site
            flask.g.site_engine = _get_site_engine(site["db_path"])
            # Ensure schema exists
            db.metadata.create_all(flask.g.site_engine)
        else:
            log.warning("No app context — DB routing may use default engine")

        zip_codes = _all_zip_codes(site)
        log.info(f"Pipeline starting — {len(zip_codes)} zip codes: {zip_codes}")

        filters = {
            "max_price": MAX_PRICE,
            "min_beds":  MIN_BEDS,
            "min_baths": MIN_BATHS,
        }

        # Fetch from both sources
        zillow_listings = []
        realtor_listings = []

        try:
            zillow_listings = fetch_all_zillow(zip_codes, **filters)
        except Exception as e:
            log.error(f"Zillow fetch failed: {e}")

        try:
            realtor_listings = fetch_all_realtor(zip_codes, **filters)
        except Exception as e:
            log.error(f"Realtor fetch failed: {e}")

        all_listings = zillow_listings + realtor_listings
        log.info(f"Fetched {len(all_listings)} total "
                 f"({len(zillow_listings)} Zillow + {len(realtor_listings)} Realtor)")

        if not all_listings:
            log.warning("No listings fetched. Check your RAPIDAPI_KEY and API subscriptions.")
            return 0

        # Geocode any listings missing coordinates
        from app.scraper.geocoder import geocode_listing
        needs_geocode = [d for d in all_listings if not d.get("latitude")]
        if needs_geocode:
            log.info(f"Geocoding {len(needs_geocode)} listings missing coordinates...")
            for data in needs_geocode:
                geocode_listing(data)
            geocoded = sum(1 for d in needs_geocode if d.get("latitude"))
            log.info(f"Geocoded {geocoded}/{len(needs_geocode)} successfully")

        # Batch-preload existing listings to avoid N+1 queries
        all_source_ids = [d["source_id"] for d in all_listings if d.get("source_id")]
        existing_map = {
            l.source_id: l
            for l in Listing.query.filter(Listing.source_id.in_(all_source_ids)).all()
        }
        log.info(f"Pre-loaded {len(existing_map)} existing listings for upsert")

        # Upsert and score
        new_count = 0
        update_count = 0
        for data in all_listings:
            pre_existing = existing_map.get(data.get("source_id"))
            listing = _upsert_listing(data, site=site, existing=pre_existing)
            db.session.flush()  # ensure listing.id is set
            _score_listing(listing)
            if pre_existing is None:
                new_count += 1
            else:
                update_count += 1

        db.session.commit()
        log.info(f"Pipeline complete: {new_count} new, {update_count} updated")

        # Build per-area breakdown for logging
        area_counts = {}
        for data in all_listings:
            area = _zip_to_area(data.get("zip_code", ""), site=site) or "Unknown"
            area_counts[area] = area_counts.get(area, 0) + 1
        run_pipeline.last_area_counts = area_counts

        # Update registry with run timestamp and listing count
        try:
            from app.services.registry import set_pipeline_ran
            set_pipeline_ran(_key, new_count + update_count)
        except Exception as e:
            log.warning(f"Could not update registry pipeline stats: {e}")

        return new_count + update_count

    if app:
        with app.app_context():
            return _execute()
    else:
        return _execute()


if __name__ == "__main__":
    import argparse
    import sys
    import os

    # Load .env so RAPIDAPI_KEY and other secrets are available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # python-dotenv not installed — rely on env vars being set externally

    parser = argparse.ArgumentParser(description="HomeFinder listing pipeline")
    parser.add_argument("--site", default=None,
                        help="Site key from registry (e.g. charleston, bathwv). "
                             "Defaults to the first active site.")
    parser.add_argument("--rescore", action="store_true",
                        help="Re-score all existing listings without fetching new ones.")
    args = parser.parse_args()

    # Bootstrap Flask app
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app import create_app
    _app = create_app()

    with _app.app_context():
        if args.rescore:
            log.info("Re-scoring all listings...")
            count = rescore_all_listings()
            print(f"Re-scored {count} listings.")
        else:
            count = run_pipeline(app=_app, site_key=args.site)
            print(f"Pipeline complete: {count} listings processed.")


def prefs_to_importance(prefs: dict) -> dict:
    """Convert user preference keys (imp_price, imp_size, ...) to
    scorer importance keys (price, size, ...)."""
    importance = {}
    for key, val in prefs.items():
        if key.startswith("imp_"):
            factor_name = key[4:]  # strip "imp_" prefix
            importance[factor_name] = int(val)
    return importance


def rescore_all_listings(importance: dict | None = None,
                        min_price: int = None, max_price: int = None):
    """Re-score all active listings with the given importance weights.
    Must be called within an app context.

    Args:
        importance: dict of factor -> 0-10 importance weight
                    e.g. {"price": 8, "size": 5, "yard": 7, ...}
        min_price: optional user min price preference
        max_price: optional user max price preference

    Returns: count of listings re-scored.
    """
    listings = Listing.query.filter_by(status="active").all()
    count = 0
    for listing in listings:
        try:
            _score_listing(listing, importance=importance,
                           min_price=min_price, max_price=max_price)
            count += 1
        except Exception as e:
            log.warning(f"Re-score failed for listing {listing.id}: {e}")
    db.session.commit()
    log.info(f"Re-scored {count} listings")
    return count
