# v20260309-1
"""
Fetch Zillow listings via the "Real-Time Real-Estate Data" API on RapidAPI.
Provider: OpenWeb Ninja (real-time-real-estate-data.p.rapidapi.com)

Endpoints used:
  GET /search             — search by city/zip
  GET /property-details   — full detail for a single listing (lazy, on first view)
"""
import json
import logging
import os
import time

import requests

log = logging.getLogger(__name__)

MODULE_VERSION = "2026.03.07"


class TransientAPIError(Exception):
    """Raised when a detail fetch fails with a 5xx / server error.
    The caller should NOT set details_fetched=True so the fetch is retried next view."""


HOST = "real-time-real-estate-data.p.rapidapi.com"
BASE = f"https://{HOST}"

# Search returns 41 results per page; assume more pages if we got a full page
PAGE_SIZE = 41


def _headers() -> dict:
    key = os.environ.get("RAPIDAPI_KEY", "")
    if not key:
        raise RuntimeError("RAPIDAPI_KEY not set in environment.")
    return {
        "X-RapidAPI-Key":  key,
        "X-RapidAPI-Host": HOST,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SEARCH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def search_zillow(zip_code: str, page: int = 1, **filters) -> tuple[list[dict], bool]:
    """
    Search Zillow via Real-Time Real-Estate Data API.

    Returns: (list_of_raw_dicts, has_more)
    """
    params = {
        "location":     zip_code,
        "home_status":  "FOR_SALE",
        "home_type":    "HOUSES",
        "sort":         "DEFAULT",
        "listing_type": "BY_AGENT",
        "page":         page,
    }
    min_price = filters.get("min_price", 0)
    max_price = filters.get("max_price")
    if max_price:
        params["list_price_range"] = f"{min_price},{max_price}"
    if filters.get("min_beds"):
        params["beds_min"] = str(filters["min_beds"])

    try:
        log.debug(f"Zillow REQUEST  zip={zip_code} page={page}")

        t0 = time.time()
        resp = requests.get(
            f"{BASE}/search",
            headers=_headers(),
            params=params,
            timeout=30,
        )
        elapsed_ms = int((time.time() - t0) * 1000)

        quota = resp.headers.get("X-RateLimit-Requests-Remaining")
        quota_remaining = int(quota) if quota else None

        # Log this API call to ApiCallLog
        _log_api_call("zillow", zip_code, page, resp.status_code,
                       elapsed_ms, quota_remaining, success=(resp.status_code == 200))

        if resp.status_code != 200:
            log.warning(f"Zillow API returned {resp.status_code} for {zip_code}: "
                        f"{resp.text[:200]}")
            return [], False

        data = resp.json()
        if data.get("status") != "OK":
            log.warning(f"Zillow API returned status={data.get('status')!r} for {zip_code}")
            return [], False

        results = data.get("data") or []
        if not isinstance(results, list):
            results = []

        # Update the log entry with results count
        _update_last_results_count("zillow", zip_code, page, len(results))

        # has_more: assume more pages if we got a full page
        has_more = len(results) >= PAGE_SIZE

        log.info(f"Zillow: {len(results)} results for {zip_code} "
                 f"(page {page}, {elapsed_ms}ms)")
        return results, has_more

    except Exception as e:
        log.error(f"Zillow search error for {zip_code}: {e}")
        return [], False


def _log_api_call(call_type, zip_code, page, http_status, response_time_ms,
                  quota_remaining, success=True, results_count=None):
    """Log an individual API call to ApiCallLog. Silently fails."""
    try:
        from app.models import ApiCallLog
        ApiCallLog.log(
            call_type, zip_code=zip_code, page_number=page,
            http_status=http_status, response_time_ms=response_time_ms,
            quota_remaining=quota_remaining, results_count=results_count,
            success=success, detail=f"zip={zip_code} page={page}",
        )
    except Exception:
        pass  # don't let logging failures break the pipeline


def _update_last_results_count(call_type, zip_code, page, count):
    """Update the most recent matching log entry with results_count."""
    try:
        from app.models import ApiCallLog, db
        entry = (ApiCallLog.query
                 .filter_by(call_type=call_type, zip_code=zip_code, page_number=page)
                 .order_by(ApiCallLog.id.desc()).first())
        if entry:
            entry.results_count = count
            db.session.commit()
    except Exception:
        pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NORMALIZE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def normalize_zillow(raw: dict) -> dict:
    """
    Convert a raw Real-Time Real-Estate Data search result into our standard schema.

    Response fields of note:
      zpid, address, streetAddress, city, state, zipcode,
      latitude, longitude,
      price, beds, baths, area (sqft),
      imgSrc, detailUrl,
      hdpData.homeInfo: { daysOnZillow, zestimate, lotAreaValue, lotAreaUnit,
                          taxAssessedValue, priceChange, homeType, livingArea },
      carouselPhotosComposable: { baseUrl, photoData: [{photoKey}] }
    """
    zpid    = str(raw.get("zpid", ""))
    address = raw.get("address", "Unknown")
    city    = raw.get("city", "")
    zip_code = raw.get("zipcode", "")
    price   = raw.get("price", 0) or 0
    beds    = raw.get("beds", 0) or 0
    baths   = raw.get("baths", 0) or 0
    sqft    = raw.get("area", 0) or 0

    url = raw.get("detailUrl", "")
    if url and not url.startswith("http"):
        url = f"https://www.zillow.com{url}"

    lat = raw.get("latitude")
    lng = raw.get("longitude")
    # fallback: latLong dict (older response shape)
    if lat is None:
        lat_long = raw.get("latLong") or {}
        lat = lat_long.get("latitude")
        lng = lat_long.get("longitude")

    # ── Photos ───────────────────────────────────────────────
    photos = []
    img_src = raw.get("imgSrc", "")
    if img_src:
        photos.append(img_src)

    carousel = raw.get("carouselPhotosComposable") or {}
    base_url  = carousel.get("baseUrl", "")
    photo_data = carousel.get("photoData") or []
    if base_url and photo_data:
        for pd in photo_data[:20]:
            key = pd.get("photoKey", "")
            if key:
                full_url = base_url.replace("{photoKey}", key)
                if full_url not in photos:
                    photos.append(full_url)

    # ── HDP rich data ────────────────────────────────────────
    hdp = (raw.get("hdpData") or {}).get("homeInfo") or {}

    lot_value = hdp.get("lotAreaValue")
    lot_unit  = hdp.get("lotAreaUnit", "")
    lot_sqft  = None
    if lot_value:
        if "acre" in str(lot_unit).lower():
            lot_sqft = int(float(lot_value) * 43560)
        else:
            lot_sqft = int(float(lot_value))

    year_built = hdp.get("yearBuilt")
    days_on    = hdp.get("daysOnZillow")
    zestimate  = hdp.get("zestimate") or raw.get("zestimate")

    tax_assessed = hdp.get("taxAssessedValue")
    property_tax_annual = None
    if tax_assessed:
        property_tax_annual = round(float(tax_assessed) * 0.0055, 2)

    price_change = hdp.get("priceChange")
    price_change_pct = None
    if price_change and price:
        price_change_pct = round((price_change / price) * 100, 2)

    home_type = hdp.get("homeType", "")
    living_area = hdp.get("livingArea")
    if living_area and int(living_area) > 0:
        sqft = int(living_area)

    is_single_story = None
    stories = None
    desc_lower = str(raw.get("statusText", "")).lower()
    if "ranch" in desc_lower or "single story" in desc_lower or "one story" in desc_lower:
        is_single_story = True
        stories = 1

    return {
        "source":     "zillow",
        "source_id":  f"zillow_{zpid}" if zpid else f"zillow_{hash(address)}",
        "url":        url,
        "address":    address,
        "city":       city,
        "zip_code":   zip_code,
        "price":      int(price),
        "beds":       int(beds),
        "baths":      float(baths),
        "sqft":       int(sqft),
        "lot_sqft":   lot_sqft,
        "year_built": int(year_built) if year_built else None,
        "latitude":   float(lat) if lat else None,
        "longitude":  float(lng) if lng else None,
        "has_garage": False,
        "has_porch":  False,
        "has_patio":  False,
        "stories":    stories,
        "is_single_story":     is_single_story,
        "hoa_monthly":         None,
        "days_on_market":      int(days_on) if days_on else None,
        "property_tax_annual": property_tax_annual,
        "has_community_pool":  False,
        "price_change_pct":    price_change_pct,
        "description":         "",
        "photo_urls_json":     json.dumps(photos),
        "photo_count":         len(photos),
        "zestimate":           int(zestimate) if zestimate else None,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  FETCH ALL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MAX_PAGES = 5  # 5 × 41 = ~200 listings per zip


def fetch_all_zillow(zip_codes: list[str], **filters) -> list[dict]:
    """Fetch and normalize Zillow listings for all target zip codes."""
    all_listings = []
    seen_zpids   = set()

    for zc in zip_codes:
        page = 1
        while page <= MAX_PAGES:
            results, has_more = search_zillow(zc, page=page, **filters)

            for raw in results:
                try:
                    normalized = normalize_zillow(raw)
                    sid = normalized["source_id"]
                    if sid not in seen_zpids:
                        seen_zpids.add(sid)
                        all_listings.append(normalized)
                except Exception as e:
                    log.warning(f"Failed to normalize Zillow listing: {e}")

            if not has_more or not results:
                break

            page += 1
            time.sleep(1)

        time.sleep(1)

    log.info(f"Zillow total: {len(all_listings)} unique listings "
             f"from {len(zip_codes)} zip codes")
    return all_listings


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DETAIL ENRICHMENT  (called lazily on first detail page view)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def fetch_zillow_detail(zpid: str, listing_url: str = "", address: str = "") -> dict | None:
    """
    Fetch full property details for a single listing.
    Uses GET /property-details endpoint.

    Returns a dict of enrichment fields, or None on failure.
    """
    if not zpid or not zpid.strip():
        log.warning("fetch_zillow_detail: empty zpid, skipping")
        return None

    zpid = zpid.strip()
    log.info(f"[v{MODULE_VERSION}] Zillow property-details fetch: zpid={zpid!r}")

    try:
        resp = requests.get(
            f"{BASE}/property-details",
            headers=_headers(),
            params={"zpid": zpid},
            timeout=30,
        )

        if resp.status_code != 200:
            if resp.status_code >= 500:
                raise TransientAPIError(
                    f"Zillow detail API {resp.status_code} (transient) for zpid={zpid}"
                )
            log.warning(f"Zillow property-details {resp.status_code} for zpid={zpid}: "
                        f"{resp.text[:200]}")
            return None

        data = resp.json()
        if data.get("status") != "OK":
            log.warning(f"Zillow property-details status={data.get('status')!r} "
                        f"for zpid={zpid}")
            return None

        raw = data.get("data") or {}
        if not raw:
            log.warning(f"Zillow property-details: empty data for zpid={zpid}")
            return None

        log.info(f"[v{MODULE_VERSION}] Zillow detail enrichment fetched for zpid={zpid}")
        return _parse_zillow_detail(zpid, raw)

    except TransientAPIError:
        raise
    except Exception as e:
        log.error(f"Zillow detail fetch error for zpid={zpid}: {e}")
        return None


def _parse_zillow_detail(zpid: str, raw: dict) -> dict:
    """
    Parse /property-details response into enrichment fields.

    Key paths:
      raw.resoFacts.*        — structured property attributes
      raw.description        — listing narrative
      raw.yearBuilt          — year built (also in resoFacts)
      raw.price              — list price
    """
    result = {}
    reso   = raw.get("resoFacts") or {}

    # ── details_json sections ─────────────────────────────────
    SECTION_MAP = [
        ("Interior", [
            ("interiorFeatures", "Interior Features"),
            ("appliances",       "Appliances"),
            ("flooring",         "Flooring"),
            ("laundryFeatures",  "Laundry"),
            ("fireplaces",       "Fireplaces"),
            ("fireplaceFeatures","Fireplace"),
        ]),
        ("Bedrooms & Bathrooms", [
            ("bedroomCount",   "Bedrooms"),
            ("bathroomsFull",  "Full Baths"),
            ("bathroomsHalf",  "Half Baths"),
        ]),
        ("Heating & Cooling", [
            ("heating", "Heating"),
            ("cooling", "Cooling"),
        ]),
        ("Exterior & Lot", [
            ("exteriorFeatures",       "Exterior Features"),
            ("patioAndPorchFeatures",  "Patio/Porch"),
            ("roofType",               "Roof"),
            ("constructionMaterials",  "Construction"),
            ("lotFeatures",            "Lot Features"),
            ("waterfrontFeatures",     "Waterfront"),
        ]),
        ("Parking & Garage", [
            ("parkingFeatures", "Parking"),
            ("garageSpaces",    "Garage Spaces"),
            ("hasGarage",       "Garage"),
        ]),
        ("Community & HOA", [
            ("communityFeatures",    "Community"),
            ("associationFee",       "HOA Fee"),
            ("associationAmenities", "Amenities"),
        ]),
        ("Utilities", [
            ("sewer",       "Sewer"),
            ("waterSource", "Water"),
            ("utilities",   "Utilities"),
        ]),
        ("Financial", [
            ("taxAnnualAmount", "Annual Tax"),
            ("floodZone",       "Flood Zone"),
        ]),
    ]

    details = []
    for section_name, fields in SECTION_MAP:
        items = []
        for reso_key, label in fields:
            val = reso.get(reso_key)
            if val is None or val == "" or val is False:
                continue
            if isinstance(val, list):
                for v in val:
                    if v:
                        items.append(f"{label}: {v}")
            elif isinstance(val, bool):
                items.append(f"{label}: Yes")
            else:
                items.append(f"{label}: {val}")
        if items:
            details.append({"category": section_name, "text": items})

    if details:
        result["details_json"] = json.dumps(details)

    # ── Scalar fields ─────────────────────────────────────────
    description = raw.get("description") or raw.get("overview") or ""
    if description:
        result["description"] = description[:3000]

    year_built = raw.get("yearBuilt") or reso.get("yearBuilt")
    if year_built:
        try:
            result["year_built"] = int(year_built)
        except (ValueError, TypeError):
            pass

    # HOA
    hoa = raw.get("monthlyHoaFee") or reso.get("associationFee")
    if hoa is not None:
        try:
            hoa_val = float(str(hoa).replace("$", "").replace(",", "").strip())
            period  = (reso.get("associationFeeFrequency") or "monthly").lower()
            if "year" in period:
                hoa_val /= 12
            elif "quarter" in period:
                hoa_val /= 3
            result["hoa_monthly"] = round(hoa_val, 2)
        except (ValueError, TypeError):
            pass

    # Stories
    stories = reso.get("stories") or reso.get("levels")
    if stories:
        try:
            s = int(float(str(stories).split()[0]))
            result["stories"]       = s
            result["is_single_story"] = (s == 1)
        except (ValueError, TypeError):
            pass

    # Garage
    has_garage    = reso.get("hasGarage")
    parking       = reso.get("parkingFeatures") or []
    garage_spaces = reso.get("garageSpaces")
    if has_garage or garage_spaces or any(
        "garage" in str(p).lower() for p in (parking if isinstance(parking, list) else [parking])
    ):
        result["has_garage"] = True
    elif has_garage is False:
        result["has_garage"] = False

    # Porch / patio
    porch_features = reso.get("patioAndPorchFeatures") or []
    if isinstance(porch_features, str):
        porch_features = [porch_features]
    combined_porch = " ".join(porch_features).lower()
    if "porch" in combined_porch or "screened" in combined_porch:
        result["has_porch"] = True
    if "patio" in combined_porch or "deck" in combined_porch:
        result["has_patio"] = True

    # Community pool
    community = reso.get("communityFeatures") or []
    if isinstance(community, str):
        community = [community]
    if any("pool" in str(c).lower() for c in community):
        result["has_community_pool"] = True

    # Property tax
    tax = reso.get("taxAnnualAmount")
    if tax:
        try:
            result["property_tax_annual"] = float(str(tax).replace(",", "").replace("$", ""))
        except (ValueError, TypeError):
            pass

    # Flood zone
    flood_zone = reso.get("floodZone")
    if flood_zone and str(flood_zone).strip():
        result["flood_zone"]       = str(flood_zone).strip()
        result["above_flood_plain"] = str(flood_zone).strip().upper().startswith("X")

    return result
