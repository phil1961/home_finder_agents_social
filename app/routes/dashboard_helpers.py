# v20260310-1
"""
app/routes/dashboard_helpers.py — Shared helpers and blueprint definition.

All dashboard sub-modules import dashboard_bp from here.
"""
from flask import Blueprint, session
from flask_login import current_user

from app.models import db, UserFlag, User
from app.utils import site_redirect as _site_redirect  # noqa: F401

dashboard_bp = Blueprint("dashboard", __name__)


def _guest_prefs() -> dict:
    """Return preferences for anonymous visitors — session overrides defaults."""
    defaults = dict(User.DEFAULT_PREFS)
    guest = session.get("guest_prefs")
    if guest:
        defaults.update(guest)
    # target_areas always come from registry, not session
    ta = _get_site_target_areas()
    if ta:
        defaults["target_areas"] = ta
    return defaults


def _get_flags(is_auth: bool) -> dict:
    """Return {listing_id: flag} for the current user or guest session."""
    if is_auth:
        return {
            uf.listing_id: uf.flag
            for uf in UserFlag.query.filter_by(user_id=current_user.id).all()
        }
    return session.get("guest_flags", {})


def _get_site_target_areas():
    """Return {area_name: [zip_codes]} from g.site registry entry.
    Falls back to {display_name: all_zips} if target_areas_json is absent."""
    import json as _json
    from flask import g
    _site = getattr(g, "site", None)
    if not _site:
        return {}
    if _site.get("target_areas_json"):
        try:
            ta = _json.loads(_site["target_areas_json"])
            if ta:
                return ta
        except (ValueError, TypeError):
            pass
    # Fallback: group all zips under display name
    if _site.get("zip_codes_json"):
        try:
            zips = _json.loads(_site["zip_codes_json"])
            if zips:
                return {_site.get("display_name", "All Areas"): zips}
        except (ValueError, TypeError):
            pass
    return {}


class _GuestFlag:
    """Lightweight stand-in for UserFlag when the visitor has no account."""
    def __init__(self, flag):
        self.flag = flag
        self.note = None


def _parse_detail_sections(listing) -> list:
    """Return parsed details_json as list of {category, text} dicts, or []."""
    import json as _j
    if not listing.details_json:
        return []
    try:
        sections = _j.loads(listing.details_json)
        return sections if isinstance(sections, list) else []
    except (ValueError, TypeError):
        return []
