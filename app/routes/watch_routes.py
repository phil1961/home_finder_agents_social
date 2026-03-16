# ─────────────────────────────────────────────
# File: app/routes/watch_routes.py
# App Version: 2026.03.12 | File Version: 1.6.0
# Last Modified: 2026-03-12
# ─────────────────────────────────────────────
"""
app/routes/watch_routes.py — Street Watch routes (AJAX + pages).
"""
import json as _json
import logging

from flask import render_template, request, redirect, flash, jsonify, session, g, current_app
from flask_login import current_user

from app.models import db, Listing
from app.routes.dashboard_helpers import dashboard_bp, _site_redirect
from app.services.street_watch import (
    create_watch, deactivate_watch, deactivate_by_token,
    get_user_watches, extract_street_name,
)

log = logging.getLogger(__name__)


def _site_zips() -> list[str]:
    """Return the list of zip codes for the current site."""
    site = getattr(g, "site", None)
    if site and site.get("zip_codes_json"):
        try:
            return _json.loads(site["zip_codes_json"])
        except (ValueError, TypeError):
            pass
    return []


@dashboard_bp.route("/watch/quick", methods=["POST"])
def watch_quick_add():
    """AJAX: create a street watch. Requires authentication."""
    from flask_login import login_required as _lr

    if not current_user.is_authenticated:
        return jsonify({"ok": False, "error": "Please create a free account to use Street Watch."}), 401

    street_name = request.form.get("street_name", "").strip()
    zip_code = request.form.get("zip_code", "").strip()
    email = current_user.email
    user_id = current_user.id
    if not street_name:
        return jsonify({"ok": False, "error": "Street name is required."}), 400
    if not zip_code:
        return jsonify({"ok": False, "error": "Zip code is required."}), 400

    # Validate zip is in this site's supported zips
    allowed = _site_zips()
    if allowed and zip_code not in allowed:
        return jsonify({"ok": False, "error": f"Zip code {zip_code} is not in this market."}), 400

    watch, created = create_watch(email, street_name, zip_code, user_id=user_id)

    return jsonify({
        "ok": True,
        "created": created,
        "watch_id": watch.id,
        "label": watch.label,
        "message": "Watching!" if created else "Already watching this street.",
    })


@dashboard_bp.route("/watch/streets", methods=["GET"])
def watch_street_search():
    """AJAX: autocomplete street names via Geoapify.

    Query params:
        q   — partial street name (min 2 chars)
        zip — optional zip code to bias results
    Returns JSON list of {street, zip_code, city}.
    """
    import requests as _requests

    q = request.args.get("q", "").strip()
    zip_filter = request.args.get("zip", "").strip()

    if len(q) < 2:
        return jsonify([])

    api_key = current_app.config.get("GEOAPIFY_KEY", "")
    if not api_key:
        # Fallback: search local listings if no Geoapify key configured
        return _local_street_search(q, zip_filter)

    # Build Geoapify autocomplete request
    # Circle filter: 25 km around site map center for fast, relevant results
    search_text = f"{q} {zip_filter}" if zip_filter else q
    site = getattr(g, "site", None) or {}
    lat = site.get("map_center_lat", 0)
    lon = site.get("map_center_lon", 0)
    geo_filter = f"circle:{lon},{lat},25000" if lat and lon else "countrycode:us"

    params = {
        "text": search_text,
        "type": "street",
        "filter": geo_filter,
        "format": "json",
        "limit": 10,
        "apiKey": api_key,
    }

    try:
        resp = _requests.get(
            "https://api.geoapify.com/v1/geocode/autocomplete",
            params=params,
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        log.warning(f"Geoapify autocomplete failed: {exc}")
        return _local_street_search(q, zip_filter)

    # Parse results — deduplicate by street+zip
    allowed = set(_site_zips())
    seen = set()
    results = []
    for feature in data.get("results", []):
        street = feature.get("street", "")
        postcode = feature.get("postcode", "")
        city = feature.get("city", "")

        if not street:
            continue
        # Only include streets in this site's zip codes
        if allowed and postcode not in allowed:
            continue

        dedup_key = (street.upper(), postcode)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        # Normalise the street name for storage
        normalised, display = extract_street_name(f"1 {street}")
        if not normalised:
            normalised = street.upper()
            display = street

        results.append({
            "street": street,
            "normalised": normalised,
            "display": display,
            "zip_code": postcode,
            "city": city,
        })

    return jsonify(results)


def _local_street_search(q, zip_filter):
    """Fallback: search local listings for street names (used when no Geoapify key)."""
    q_upper = q.upper()
    allowed = _site_zips()
    query = db.session.query(Listing.address, Listing.zip_code)
    if allowed:
        query = query.filter(Listing.zip_code.in_(allowed))
    if zip_filter:
        query = query.filter(Listing.zip_code == zip_filter)

    rows = query.all()

    from collections import Counter
    street_counts = Counter()
    street_labels = {}
    for address, zip_code in rows:
        normalised, display = extract_street_name(address)
        if normalised and q_upper in normalised:
            key = (normalised, zip_code)
            street_counts[key] += 1
            street_labels[key] = display

    results = []
    for (normalised, zip_code), count in street_counts.most_common(10):
        results.append({
            "street": street_labels[(normalised, zip_code)],
            "normalised": normalised,
            "display": street_labels[(normalised, zip_code)],
            "zip_code": zip_code,
            "city": "",
        })
    return jsonify(results)


@dashboard_bp.route("/watch/remove/<int:watch_id>", methods=["POST"])
def watch_remove(watch_id):
    """Deactivate a street watch."""
    if not current_user.is_authenticated:
        flash("Please sign in to manage watches.", "info")
        return _site_redirect("auth.login")
    success = deactivate_watch(watch_id, user_id=current_user.id)

    # If AJAX, return JSON
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": success})

    if success:
        flash("Street watch removed.", "info")
    else:
        flash("Could not remove that watch.", "warning")
    return redirect(request.referrer or _site_redirect("dashboard.watch_manage").location)


@dashboard_bp.route("/watch")
def watch_manage():
    """Street Watch management page."""
    if current_user.is_authenticated:
        watches = get_user_watches(user_id=current_user.id)
    else:
        watches = []

    # Get alert counts per watch
    from app.models import StreetWatchAlert
    alert_counts = {}
    for w in watches:
        alert_counts[w.id] = StreetWatchAlert.query.filter_by(watch_id=w.id).count()

    # Site zip codes for the dropdown
    site_zips = sorted(_site_zips())

    # Map center for Geoapify circle bias
    site = getattr(g, "site", None) or {}
    map_lat = site.get("map_center_lat", 0)
    map_lon = site.get("map_center_lon", 0)

    return render_template(
        "dashboard/watch.html",
        watches=watches,
        alert_counts=alert_counts,
        site_zips=site_zips,
        geoapify_key=current_app.config.get("GEOAPIFY_KEY", ""),
        map_center_lat=map_lat,
        map_center_lon=map_lon,
        user=current_user,
    )


@dashboard_bp.route("/watch/unsubscribe/<token>")
def watch_unsubscribe(token):
    """One-click email unsubscribe."""
    success = deactivate_by_token(token)
    if success:
        flash("You've been unsubscribed from this street watch.", "success")
    else:
        flash("That unsubscribe link is invalid or the watch was already removed.", "warning")
    return _site_redirect("dashboard.index")
