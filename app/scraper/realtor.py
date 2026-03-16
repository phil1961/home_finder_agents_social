# v20260309-1
"""Fetch listings from Realtor.com via the realty-in-us RapidAPI endpoint."""
import json
import logging
import os
import time

import requests

log = logging.getLogger(__name__)

class TransientAPIError(Exception):
    """Raised when a detail fetch fails with a 5xx / server error.
    The caller should NOT set details_fetched=True so the fetch is retried next view."""


REALTOR_HOST = "realty-in-us.p.rapidapi.com"
REALTOR_SEARCH_URL = f"https://{REALTOR_HOST}/properties/v3/list"


def _headers():
    key = os.environ.get("RAPIDAPI_KEY", "")
    if not key:
        raise RuntimeError("RAPIDAPI_KEY not set in environment.")
    return {
        "X-RapidAPI-Key": key,
        "X-RapidAPI-Host": REALTOR_HOST,
        "Content-Type": "application/json",
    }


def search_realtor(zip_code: str, **filters) -> list[dict]:
    """
    Search Realtor.com for properties in a given zip code.
    Uses the properties/v3/list POST endpoint.
    """
    payload = {
        "limit": 50,
        "offset": 0,
        "postal_code": zip_code,
        "status": ["for_sale"],
        "sort": {
            "direction": "desc",
            "field": "list_date",
        },
        "beds_min": filters.get("min_beds", 4),
        "baths_min": filters.get("min_baths", 3),
        "price_max": filters.get("max_price", 600000),
        "type": ["single_family"],
    }

    log.info(f"Realtor search: zip={zip_code}")

    t0 = time.time()
    try:
        resp = requests.post(REALTOR_SEARCH_URL, headers=_headers(),
                             json=payload, timeout=30)
        elapsed_ms = int((time.time() - t0) * 1000)
        quota = resp.headers.get("X-RateLimit-Requests-Remaining")
        quota_remaining = int(quota) if quota else None

        _log_api_call("realtor", zip_code, resp.status_code, elapsed_ms,
                      quota_remaining, success=resp.ok)

        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        elapsed_ms = int((time.time() - t0) * 1000)
        _log_api_call("realtor", zip_code, getattr(e.response, 'status_code', 0) if hasattr(e, 'response') and e.response else 0,
                      elapsed_ms, None, success=False)
        log.error(f"Realtor API error for {zip_code}: {e}")
        return []

    # Response structure: data -> home_search -> results
    results = []
    if "data" in data:
        home_search = data["data"].get("home_search", {})
        results = home_search.get("results", [])
    elif "properties" in data:
        results = data["properties"]
    elif isinstance(data, list):
        results = data

    # Update log entry with results count
    _update_last_results_count("realtor", zip_code, len(results))

    log.info(f"Realtor: {len(results)} results for {zip_code} ({elapsed_ms}ms)")
    return results


def _log_api_call(call_type, zip_code, http_status, response_time_ms,
                  quota_remaining, success=True):
    """Log an individual API call to ApiCallLog. Silently fails."""
    try:
        from app.models import ApiCallLog
        ApiCallLog.log(
            call_type, zip_code=zip_code,
            http_status=http_status, response_time_ms=response_time_ms,
            quota_remaining=quota_remaining, success=success,
            detail=f"zip={zip_code}",
        )
    except Exception:
        pass


def _update_last_results_count(call_type, zip_code, count):
    """Update the most recent matching log entry with results_count."""
    try:
        from app.models import ApiCallLog, db
        entry = (ApiCallLog.query
                 .filter_by(call_type=call_type, zip_code=zip_code)
                 .order_by(ApiCallLog.id.desc()).first())
        if entry:
            entry.results_count = count
            db.session.commit()
    except Exception:
        pass


def normalize_realtor(raw: dict) -> dict:
    """
    Convert a raw Realtor API property dict into our standard schema.

    Actual API response structure (from debug):
      primary_photo.href  -> photo URL
      photo_count         -> number of photos
      href                -> listing URL on realtor.com
      list_price          -> price
      property_id         -> unique ID
      listing_id          -> MLS listing ID
      location.address.line/city/postal_code  -> address
      location.coordinate.lat/lon  -> coordinates
      description.beds/baths/sqft/lot_sqft/year_built/type/text -> property details
      flags               -> is_price_reduced, is_new_construction, etc.
      status              -> for_sale
      estimate.estimate   -> estimated value
    """
    # ── Address ──────────────────────────────────────────────
    location = raw.get("location", {}) or {}
    address_obj = location.get("address", {}) or {}
    address_line = address_obj.get("line", "")
    city = address_obj.get("city", "")
    zip_code = address_obj.get("postal_code", "")

    # ── Coordinates (try multiple paths) ────────────────────
    lat = None
    lng = None

    # Path 1: location.coordinate.lat / lon
    coord = location.get("coordinate", {}) or {}
    if coord:
        lat = coord.get("lat") or coord.get("latitude")
        lng = coord.get("lon") or coord.get("lng") or coord.get("longitude")

    # Path 2: location.address.coordinate
    if not lat:
        addr_coord = address_obj.get("coordinate", {}) or {}
        lat = addr_coord.get("lat") or addr_coord.get("latitude")
        lng = addr_coord.get("lon") or addr_coord.get("lng") or addr_coord.get("longitude")

    # Path 3: top-level lat/lon
    if not lat:
        lat = raw.get("latitude") or raw.get("lat")
        lng = raw.get("longitude") or raw.get("lon") or raw.get("lng")

    # Path 4: location.lat / location.lon directly
    if not lat:
        lat = location.get("lat") or location.get("latitude")
        lng = location.get("lon") or location.get("lng") or location.get("longitude")

    # ── Description / details ────────────────────────────────
    desc_obj = raw.get("description", {}) or {}
    if isinstance(desc_obj, str):
        desc_text = desc_obj
        beds = baths = sqft = lot_sqft = year_built = 0
    else:
        desc_text = desc_obj.get("text", "") or ""
        beds = desc_obj.get("beds") or 0
        baths = desc_obj.get("baths") or 0
        sqft = desc_obj.get("sqft") or 0
        lot_sqft = desc_obj.get("lot_sqft")
        year_built = desc_obj.get("year_built")

    # ── Price ────────────────────────────────────────────────
    price = raw.get("list_price") or 0

    # ── IDs ──────────────────────────────────────────────────
    property_id = raw.get("property_id", "") or raw.get("listing_id", "")

    # ── Photo: primary_photo.href ────────────────────────────
    primary_photo = raw.get("primary_photo", {}) or {}
    photo_href = primary_photo.get("href", "")

    # Try to get larger image by modifying the URL suffix
    # Realtor URLs often end in 's.jpg' for small; change to 'od.jpg' for original
    photo_urls = []
    if photo_href:
        # Keep original and also try a larger version
        large_photo = photo_href.replace("-m3647035753s.jpg", "-m3647035753od.jpg")
        if large_photo == photo_href:
            # Generic approach: replace trailing 's.jpg' pattern
            large_photo = photo_href
        photo_urls.append(large_photo)

    photo_count = raw.get("photo_count", 0) or 0

    # ── URL (the href field, NOT permalink) ──────────────────
    url = raw.get("href", "")

    # ── Feature detection ────────────────────────────────────
    tags = [t.lower() for t in (raw.get("tags") or [])]
    desc_lower = desc_text.lower()
    combined = " ".join(tags) + " " + desc_lower

    # ── Stories / single story ────────────────────────────────
    stories = desc_obj.get("stories") if isinstance(desc_obj, dict) else None
    is_single_story = None
    if stories == 1:
        is_single_story = True
    elif stories and stories > 1:
        is_single_story = False
    elif "single story" in combined or "one story" in combined or "1 story" in combined or "ranch" in combined:
        is_single_story = True
        stories = 1
    elif "two story" in combined or "2 story" in combined or "two-story" in combined:
        is_single_story = False
        stories = stories or 2

    # ── HOA ───────────────────────────────────────────────────
    hoa_monthly = None
    hoa_data = raw.get("hoa", {}) or {}
    if isinstance(hoa_data, dict) and hoa_data.get("value"):
        hoa_val = float(hoa_data["value"])
        hoa_period = (hoa_data.get("period") or "monthly").lower()
        if "year" in hoa_period:
            hoa_monthly = hoa_val / 12
        elif "quarter" in hoa_period:
            hoa_monthly = hoa_val / 3
        else:
            hoa_monthly = hoa_val
    elif "no hoa" in combined or "no_hoa" in combined:
        hoa_monthly = 0

    # ── List date / days on market ───────────────────────────
    list_date_str = raw.get("list_date", "")
    list_date_val = None
    days_on_market = None
    if list_date_str:
        try:
            list_date_val = list_date_str  # pass string, pipeline parses
        except Exception:
            pass

    # ── Property tax ─────────────────────────────────────────
    property_tax = None
    tax_data = raw.get("tax_record") or raw.get("property_taxes") or {}
    if isinstance(tax_data, dict):
        property_tax = tax_data.get("total") or tax_data.get("amount")

    # ── Community pool ───────────────────────────────────────
    has_pool = ("community_pool" in combined or "pool" in " ".join(tags)
                or "clubhouse" in combined or "community center" in combined)

    # ── Structured property details (Interior/Exterior/etc.) ──
    raw_details = raw.get("details") or []
    details = []
    if isinstance(raw_details, list):
        for section in raw_details:
            if not isinstance(section, dict):
                continue
            cat = section.get("category") or section.get("name") or ""
            text = section.get("text") or section.get("values") or []
            if cat and text:
                details.append({"category": cat, "text": list(text)})

    # ── Year built ───────────────────────────────────────────
    yb = year_built
    if not yb and isinstance(desc_obj, dict):
        yb = desc_obj.get("year_built")

    return {
        "source": "realtor",
        "source_id": f"realtor_{property_id}",
        "url": url,
        "address": f"{address_line}, {city}" if address_line else "Unknown",
        "city": city,
        "zip_code": str(zip_code),
        "price": int(price) if price else 0,
        "beds": int(beds or 0),
        "baths": float(baths or 0),
        "sqft": int(sqft or 0),
        "lot_sqft": int(lot_sqft) if lot_sqft else None,
        "year_built": int(yb) if yb else None,
        "latitude": float(lat) if lat else None,
        "longitude": float(lng) if lng else None,
        "has_garage": "garage" in combined,
        "has_porch": "porch" in combined or "screened" in combined,
        "has_patio": "patio" in combined or "deck" in combined,
        # New fields
        "stories": stories,
        "is_single_story": is_single_story,
        "hoa_monthly": hoa_monthly,
        "list_date": list_date_val,
        "days_on_market": days_on_market,
        "property_tax_annual": float(property_tax) if property_tax else None,
        "has_community_pool": has_pool,
        "description": desc_text[:2000] if desc_text else "",
        "details_json": json.dumps(details) if details else None,
        "photo_urls_json": json.dumps(photo_urls),
        "photo_count": photo_count,
    }




REALTOR_DETAIL_URL = f"https://{REALTOR_HOST}/properties/v3/detail"


def fetch_realtor_detail(property_id: str) -> dict | None:
    """
    Fetch full property details for a single Realtor listing by property_id.
    Called lazily on first detail page view; result stored in details_json.

    Returns a dict of enrichment fields, or None on failure.
    """
    if not property_id:
        return None
    try:
        resp = requests.get(
            REALTOR_DETAIL_URL,
            headers=_headers(),
            params={"property_id": property_id},
            timeout=30,
        )
        if resp.status_code != 200:
            if resp.status_code >= 500:
                raise TransientAPIError(
                    f"Realtor detail API {resp.status_code} (transient) for {property_id}"
                )
            log.warning(f"Realtor detail API {resp.status_code} for {property_id}: {resp.text[:200]}")
            return None

        data = resp.json()
        # Response: data.home or data.home_search.results[0]
        raw = None
        if "data" in data:
            raw = (data["data"].get("home") or
                   ((data["data"].get("home_search") or {}).get("results") or [{}])[0])
        elif isinstance(data, dict):
            raw = data

        if not raw:
            log.warning(f"Realtor detail: no data for property_id={property_id}")
            return None

        log.info(f"Realtor detail fetched for property_id={property_id}")
        return _parse_realtor_detail(raw)

    except TransientAPIError:
        raise  # let dashboard.py catch this and skip details_fetched=True
    except Exception as e:
        log.error(f"Realtor detail fetch error for {property_id}: {e}")
        return None


def _parse_realtor_detail(raw: dict) -> dict:
    """
    Parse a Realtor detail response into enrichment fields.
    Mirrors normalize_realtor but focused on the richer detail-only fields.
    """
    result = {}

    desc_obj = raw.get("description", {}) or {}

    # ── Structured details sections ───────────────────────────
    raw_details = raw.get("details") or []
    details = []
    if isinstance(raw_details, list):
        for section in raw_details:
            if not isinstance(section, dict):
                continue
            cat = section.get("category") or section.get("name") or ""
            text = section.get("text") or section.get("values") or []
            if cat and text:
                details.append({"category": cat, "text": list(text)})
    if details:
        result["details_json"] = json.dumps(details)

    # ── Description text ──────────────────────────────────────
    desc_text = (desc_obj.get("text") if isinstance(desc_obj, dict) else None) or ""
    if desc_text:
        result["description"] = desc_text[:3000]

    # ── Year built ────────────────────────────────────────────
    yb = desc_obj.get("year_built") if isinstance(desc_obj, dict) else None
    if yb:
        try:
            result["year_built"] = int(yb)
        except (ValueError, TypeError):
            pass

    # ── Stories ───────────────────────────────────────────────
    stories = desc_obj.get("stories") if isinstance(desc_obj, dict) else None
    if stories:
        try:
            s = int(stories)
            result["stories"] = s
            result["is_single_story"] = (s == 1)
        except (ValueError, TypeError):
            pass

    # ── HOA ───────────────────────────────────────────────────
    hoa_data = raw.get("hoa", {}) or {}
    if isinstance(hoa_data, dict) and hoa_data.get("value"):
        try:
            hoa_val = float(hoa_data["value"])
            period = (hoa_data.get("period") or "monthly").lower()
            if "year" in period:
                hoa_val /= 12
            elif "quarter" in period:
                hoa_val /= 3
            result["hoa_monthly"] = round(hoa_val, 2)
        except (ValueError, TypeError):
            pass

    # ── Property tax ──────────────────────────────────────────
    tax_data = raw.get("tax_record") or raw.get("property_taxes") or {}
    if isinstance(tax_data, dict):
        tax = tax_data.get("total") or tax_data.get("amount")
        if tax:
            try:
                result["property_tax_annual"] = float(tax)
            except (ValueError, TypeError):
                pass

    # ── Features from tags + description ─────────────────────
    tags = [t.lower() for t in (raw.get("tags") or [])]
    desc_lower = desc_text.lower()
    combined = " ".join(tags) + " " + desc_lower

    if "garage" in combined:
        result["has_garage"] = True
    if "porch" in combined or "screened" in combined:
        result["has_porch"] = True
    if "patio" in combined or "deck" in combined:
        result["has_patio"] = True
    if "community_pool" in combined or "pool" in " ".join(tags) or "clubhouse" in combined:
        result["has_community_pool"] = True

    # ── Photos (detail may have more) ─────────────────────────
    photos_raw = raw.get("photos") or []
    if photos_raw and isinstance(photos_raw, list):
        urls = []
        for p in photos_raw[:30]:
            href = (p.get("href") or "") if isinstance(p, dict) else str(p)
            if href:
                urls.append(href)
        if urls:
            result["photo_urls_json"] = json.dumps(urls)

    return result

def fetch_all_realtor(zip_codes: list[str], **filters) -> list[dict]:
    """Fetch and normalize listings from Realtor.com for all target zip codes."""
    all_listings = []
    for zc in zip_codes:
        raw_list = search_realtor(zc, **filters)
        for raw in raw_list:
            try:
                normalized = normalize_realtor(raw)
                all_listings.append(normalized)
            except Exception as e:
                log.warning(f"Failed to normalize Realtor listing: {e}")
        time.sleep(1)

    log.info(f"Realtor total: {len(all_listings)} normalized listings")
    return all_listings
