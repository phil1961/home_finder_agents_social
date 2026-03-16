# v20260309-1
"""Geocode addresses using free Nominatim (OpenStreetMap) service."""
import logging
import time

import requests

log = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "HomeFinder/1.0 (personal-project)"}

# Simple in-memory cache to avoid re-geocoding same addresses
_cache: dict[str, tuple] = {}


def geocode(address: str, zip_code: str = "", state: str = "SC") -> tuple:
    """
    Geocode an address. Returns (lat, lng) or (None, None).
    Rate-limited to 1 req/sec per Nominatim policy.
    """
    query = address
    if zip_code:
        query += f", {zip_code}"
    if state and state.upper() not in query.upper():
        query += f", {state}"

    # Check cache
    cache_key = query.lower().strip()
    if cache_key in _cache:
        return _cache[cache_key]

    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1, "countrycodes": "us"},
            headers=HEADERS,
            timeout=10,
        )
        results = resp.json()
        if results:
            lat = float(results[0]["lat"])
            lon = float(results[0]["lon"])
            _cache[cache_key] = (lat, lon)
            return (lat, lon)
    except Exception as e:
        log.debug(f"Geocode failed for '{query}': {e}")

    _cache[cache_key] = (None, None)
    return (None, None)


def geocode_listing(data: dict) -> dict:
    """
    If a listing dict is missing lat/lng, attempt to geocode from address.
    Modifies and returns the dict.
    """
    if data.get("latitude") and data.get("longitude"):
        return data

    lat, lng = geocode(
        data.get("address", ""),
        data.get("zip_code", ""),
    )
    if lat and lng:
        data["latitude"] = lat
        data["longitude"] = lng
        log.debug(f"Geocoded: {data['address']} → ({lat}, {lng})")
    else:
        log.debug(f"Geocode failed: {data['address']}")

    # Nominatim rate limit
    time.sleep(1.1)
    return data
