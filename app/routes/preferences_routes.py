# ─────────────────────────────────────────────
# File: app/routes/preferences_routes.py
# App Version: 2026.03.14 | File Version: 1.3.0
# Last Modified: 2026-03-14
# ─────────────────────────────────────────────
"""
app/routes/preferences_routes.py — Preferences and API endpoints.
"""
from flask import render_template, request, flash, jsonify
from flask_login import login_required, current_user

from app.models import db, Listing, UserFlag, User
from app.routes.dashboard_helpers import (
    dashboard_bp, _guest_prefs, _get_site_target_areas, _site_redirect,
)


@dashboard_bp.route("/preferences", methods=["GET", "POST"])
def preferences():
    """View and update scoring/search preferences."""
    from flask import session, g as _prefs_g

    is_auth = current_user.is_authenticated
    _site = getattr(_prefs_g, "site", None)

    # Principals can now edit their own scoring weights (agents may also
    # update them via the agent dashboard — last save wins).

    if request.method == "POST":
        section = request.form.get("_section", "scoring")

        try:
            # Load existing prefs so we only update what this section controls
            existing_prefs = current_user.get_prefs() if is_auth else _guest_prefs()

            if section == "scoring":
                # ── Section 1: Scoring sliders + search criteria ──────
                imp_keys = [k for k in User.DEFAULT_PREFS if k.startswith("imp_")]

                prefs = dict(existing_prefs)  # keep areas/POI intact
                prefs.update({
                    "min_price": int(request.form.get("min_price", 200000)),
                    "max_price": int(request.form.get("max_price", 600000)),
                    "min_beds": int(request.form.get("min_beds", 4)),
                    "min_baths": float(request.form.get("min_baths", 3)),
                    "must_have_garage": request.form.get("must_have_garage") == "on",
                    "must_have_porch": request.form.get("must_have_porch") == "on",
                    "must_have_patio": request.form.get("must_have_patio") == "on",
                    "great_deal_threshold": int(request.form.get("great_deal_threshold", 75)),
                })

                for k in imp_keys:
                    prefs[k] = int(request.form.get(k, User.DEFAULT_PREFS.get(k, 5)))

                # Proximity POI: selected landmark coords
                prefs["proximity_poi_name"] = request.form.get("proximity_poi_name", "")
                prefs["proximity_poi_lat"] = float(request.form.get("proximity_poi_lat", 0) or 0)
                prefs["proximity_poi_lng"] = float(request.form.get("proximity_poi_lng", 0) or 0)

                # Preserve user_landmarks (managed via separate AJAX route)
                prefs["user_landmarks"] = existing_prefs.get("user_landmarks", [])

                msg = "Scoring preferences saved!"

            elif section == "areas":
                # ── Section 2: Target areas + avoid areas ─────────────
                prefs = dict(existing_prefs)  # keep scoring intact

                # Avoid areas — owner+ may change
                if is_auth and current_user.is_owner:
                    prefs["avoid_areas"] = [
                        a.strip() for a in request.form.get("avoid_areas", "").split(",") if a.strip()
                    ]

                # target_areas — owner+ can label areas; master can also add/remove zips
                if is_auth and current_user.is_owner and _site:
                    import json as _json
                    target_areas = {}
                    area_names = request.form.getlist("area_name")
                    area_zips  = request.form.getlist("area_zips")
                    for name, zips in zip(area_names, area_zips):
                        name = name.strip()
                        if name:
                            zip_list = [z.strip() for z in zips.split(",") if z.strip()]
                            if zip_list:
                                target_areas[name] = zip_list

                    new_all_zips = sorted({z for zips in target_areas.values() for z in zips})

                    if current_user.is_master:
                        # Master can change the zip set — add/remove freely
                        from app.services import registry as _reg
                        _reg.update_site(
                            _site["site_key"],
                            target_areas_json=_json.dumps(target_areas),
                            zip_codes_json=_json.dumps(new_all_zips),
                        )
                    else:
                        # Owner can only reorganize existing zips into areas
                        # Cannot add zips not in the master's zip_codes_json
                        existing_zips = set()
                        try:
                            existing_zips = set(_json.loads(_site.get("zip_codes_json", "[]") or "[]"))
                        except (ValueError, TypeError):
                            pass

                        # Filter: owner can only use zips that master already allocated
                        for area_name in target_areas:
                            target_areas[area_name] = [z for z in target_areas[area_name] if z in existing_zips]
                        # Remove empty areas after filtering
                        target_areas = {k: v for k, v in target_areas.items() if v}

                        from app.services import registry as _reg
                        _reg.update_site(
                            _site["site_key"],
                            target_areas_json=_json.dumps(target_areas),
                            # zip_codes_json stays unchanged — owner can't expand the zip set
                        )

                    updated = _reg.get_site(_site["site_key"])
                    if updated:
                        _site = updated

                msg = "Target areas saved!"

            else:
                prefs = existing_prefs
                msg = "Preferences saved!"

            is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

            if is_auth:
                current_user.set_prefs(prefs)
                db.session.commit()
                if is_ajax:
                    return jsonify({"ok": True, "message": msg})
                flash(msg, "success")
            else:
                session["guest_prefs"] = prefs
                session.modified = True
                if is_ajax:
                    return jsonify({"ok": True, "message": msg})
                return _site_redirect("dashboard.preferences", saved="guest")

        except (ValueError, TypeError) as e:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"ok": False, "message": f"Invalid input: {e}"}), 400
            flash(f"Invalid input: {e}", "danger")

        return _site_redirect("dashboard.preferences")

    # ── GET — load prefs from user account or session ──────────────────────────
    if is_auth:
        prefs = current_user.get_prefs()
    else:
        prefs = _guest_prefs()

    # target_areas always come from registry (site-wide, not per-user)
    prefs["target_areas"] = _get_site_target_areas()

    cached_prefs_analysis = None
    if is_auth:
        from app.models import CachedAnalysis
        cached_prefs_analysis = CachedAnalysis.load(current_user.id, "prefs")

    # Load landmarks from registry for POI proximity dropdown
    landmarks = []
    if _site and _site.get("landmarks_json"):
        import json as _json_lm
        try:
            landmarks = _json_lm.loads(_site["landmarks_json"])
        except (ValueError, TypeError):
            pass

    return render_template("dashboard/preferences.html",
                           prefs=prefs,
                           prefs_defaults=User.DEFAULT_PREFS,
                           cached_prefs_analysis=cached_prefs_analysis,
                           landmarks=landmarks,
                           user=current_user)


# ── Census place names for Avoid Areas autocomplete ──────────────

@dashboard_bp.route("/api/places")
def api_places():
    """Return sorted list of Census place names for the current site's area."""
    try:
        from app.services.place_geocoder import get_area_places, is_available
        from flask import g
        site = getattr(g, "site", None)
        bounds = None
        if site and site.get("map_bounds_json"):
            import json as _json
            try:
                bounds = _json.loads(site["map_bounds_json"])
            except (ValueError, TypeError):
                pass
        if is_available():
            places = get_area_places(bounds)
        else:
            # Fallback: derive from zip codes in registry
            places = []
        return jsonify(places)
    except Exception as exc:
        return jsonify([])


# ── API endpoint for AJAX flag toggling ──────────────────────────

@dashboard_bp.route("/api/flag", methods=["POST"])
@login_required
def api_toggle_flag():
    """JSON API for flag toggling (for JS-based UI updates)."""
    data = request.get_json(silent=True) or {}
    listing_id = data.get("listing_id")
    new_flag = data.get("flag", "favorite")

    if not listing_id:
        return jsonify({"error": "listing_id required"}), 400
    if new_flag not in ("favorite", "maybe", "hidden"):
        return jsonify({"error": "invalid flag"}), 400

    listing = Listing.query.get(listing_id)
    if not listing:
        return jsonify({"error": "listing not found"}), 404

    uf = UserFlag.query.filter_by(
        user_id=current_user.id, listing_id=listing_id
    ).first()

    if uf and uf.flag == new_flag:
        db.session.delete(uf)
        db.session.commit()
        return jsonify({"status": "removed", "flag": None})

    if uf:
        uf.flag = new_flag
    else:
        uf = UserFlag(user_id=current_user.id, listing_id=listing_id, flag=new_flag)
        db.session.add(uf)

    db.session.commit()
    return jsonify({"status": "set", "flag": new_flag})


# ── Owner: Landmark management for POI proximity scoring ─────

@dashboard_bp.route("/admin/landmarks", methods=["POST"])
@login_required
def admin_landmarks():
    """Owner: add/remove landmarks for POI proximity scoring."""
    from flask import g as _lm_g
    import json as _json_lm

    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if not current_user.is_owner:
        if is_ajax:
            return jsonify({"ok": False, "error": "Access denied."}), 403
        flash("Only owners can manage landmarks.", "danger")
        return _site_redirect("dashboard.preferences")

    _site = getattr(_lm_g, "site", None)
    if not _site:
        if is_ajax:
            return jsonify({"ok": False, "error": "No site context."}), 400
        flash("No site context.", "danger")
        return _site_redirect("dashboard.preferences")

    # Load current landmarks
    try:
        landmarks = _json_lm.loads(_site.get("landmarks_json") or "[]")
    except (ValueError, TypeError):
        landmarks = []

    action = request.form.get("landmark_action", "add")

    if action == "add":
        name = request.form.get("landmark_name", "").strip()
        try:
            lat = float(request.form.get("landmark_lat", 0) or 0)
            lng = float(request.form.get("landmark_lng", 0) or 0)
        except (ValueError, TypeError):
            if is_ajax:
                return jsonify({"ok": False, "error": "Invalid coordinates."})
            flash("Invalid coordinates.", "danger")
            return _site_redirect("dashboard.preferences")

        if not name or not lat or not lng:
            if is_ajax:
                return jsonify({"ok": False, "error": "Name and valid coordinates are required."})
            flash("Landmark name and valid coordinates are required.", "danger")
            return _site_redirect("dashboard.preferences")

        # Check for duplicate name
        if any(lm.get("name") == name for lm in landmarks):
            if is_ajax:
                return jsonify({"ok": False, "error": f"'{name}' already exists."})
            flash(f"A landmark named '{name}' already exists.", "warning")
            return _site_redirect("dashboard.preferences")

        landmarks.append({"name": name, "lat": lat, "lng": lng})
        if not is_ajax:
            flash(f"Landmark '{name}' added.", "success")

    elif action == "delete":
        del_name = request.form.get("landmark_name", "").strip()
        landmarks = [lm for lm in landmarks if lm.get("name") != del_name]
        if not is_ajax:
            flash(f"Landmark '{del_name}' removed.", "success")

    from app.services import registry as _reg
    _reg.update_site(_site["site_key"], landmarks_json=_json_lm.dumps(landmarks))

    if is_ajax:
        return jsonify({"ok": True, "landmarks": landmarks})

    return _site_redirect("dashboard.preferences")


# ── User: Personal landmark management ──────────────────────

MAX_USER_LANDMARKS = 3

@dashboard_bp.route("/my-landmarks", methods=["POST"])
@login_required
def user_landmarks():
    """User adds/removes personal landmarks (stored in preferences_json)."""
    import json as _json_ul

    prefs = current_user.get_prefs()
    user_lms = prefs.get("user_landmarks", [])

    action = request.form.get("landmark_action", "add")

    if action == "add":
        if len(user_lms) >= MAX_USER_LANDMARKS:
            return jsonify({"ok": False, "error": f"Maximum {MAX_USER_LANDMARKS} personal landmarks allowed."}), 400

        name = request.form.get("landmark_name", "").strip()
        try:
            lat = float(request.form.get("landmark_lat", 0) or 0)
            lng = float(request.form.get("landmark_lng", 0) or 0)
        except (ValueError, TypeError):
            return jsonify({"ok": False, "error": "Invalid coordinates."}), 400

        if not name or not lat or not lng:
            return jsonify({"ok": False, "error": "Name and coordinates are required."}), 400

        if any(lm.get("name") == name for lm in user_lms):
            return jsonify({"ok": False, "error": f"'{name}' already exists."}), 400

        user_lms.append({"name": name, "lat": lat, "lng": lng})

    elif action == "delete":
        del_name = request.form.get("landmark_name", "").strip()
        user_lms = [lm for lm in user_lms if lm.get("name") != del_name]

    prefs["user_landmarks"] = user_lms
    current_user.set_prefs(prefs)
    db.session.commit()

    return jsonify({"ok": True, "user_landmarks": user_lms})
