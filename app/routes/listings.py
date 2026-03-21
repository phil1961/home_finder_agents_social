# ─────────────────────────────────────────────
# File: app/routes/listings.py
# App Version: 2026.03.14 | File Version: 1.8.0
# Last Modified: 2026-03-14
# ─────────────────────────────────────────────
"""
app/routes/listings.py — Public listing browsing routes.
"""
from datetime import datetime, timezone
from flask import render_template, request, redirect, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc

from app.models import db, Listing, DealScore, UserFlag, User
from app.routes.dashboard_helpers import (
    dashboard_bp, _guest_prefs, _get_flags, _get_site_target_areas,
    _GuestFlag, _parse_detail_sections, _site_redirect,
)
from app.utils import site_url as _site_url


@dashboard_bp.route("/welcome")
def welcome():
    """Site-selector landing page.

    Shows all active HomeFinder markets so visitors can pick their city.
    Authenticated users who already have a site context go straight to
    the dashboard; unauthenticated visitors (or those arriving at the
    root /welcome URL with no site key) always see the chooser.
    """
    from flask import request as _req, g
    from app.services.registry import get_all_sites

    # If the user is already in a site context AND authenticated, skip the chooser
    # ?chooser=1 forces the market picker (used by the "All Markets" globe icon)
    site = getattr(g, "site", None)
    if current_user.is_authenticated and site and not _req.args.get("chooser"):
        return _site_redirect("dashboard.index")

    sites = [s for s in get_all_sites() if s.get("active")]
    script = _req.script_root or ""
    return render_template(
        "dashboard/welcome.html",
        sites=sites,
        script_root=script,
        user=current_user,
    )


@dashboard_bp.route("/go/<site_key>")
def go_to_site(site_key):
    """Redirect master to a specific site instance.

    Looks up the master user in the target site's DB by email (since user
    IDs differ across site databases) and rebinds the session to that user.
    """
    from flask import request as _req, session as _sess

    # Must have an active session
    if "_user_id" not in _sess:
        return redirect(_req.script_root or "/")

    # Get the current user's email before switching
    current_email = None
    if current_user.is_authenticated:
        current_email = current_user.email
    else:
        # Try to load from current site DB
        try:
            user = db.session.get(User, int(_sess["_user_id"]))
            if user:
                current_email = user.email
        except Exception:
            pass

    if not current_email:
        return redirect(_req.script_root or "/")

    # Switch to the target site's DB and find the master user by email
    from app.services.registry import get_site
    from app import _get_site_engine
    target_site = get_site(site_key)
    if not target_site:
        return redirect(_req.script_root or "/")

    from sqlalchemy import text
    target_engine = _get_site_engine(target_site["db_path"])
    with target_engine.connect() as conn:
        row = conn.execute(
            text("SELECT id FROM users WHERE email = :email AND role = 'master' LIMIT 1"),
            {"email": current_email},
        ).fetchone()

    if not row:
        # Master doesn't exist in target site — fall back to dashboard
        return redirect(f"{_req.script_root or ''}/site/{site_key}/")

    # Rebind session to the target site's master user ID
    _sess["_user_id"] = str(row[0])
    _sess["_site_key"] = site_key
    _sess.modified = True

    script = _req.script_root or ""
    if _req.args.get("next") == "manage":
        from flask import url_for
        return redirect(url_for("site_manager.sites_list"))
    return redirect(f"{script}/site/{site_key}/")


@dashboard_bp.route("/")
def index():
    """Main dashboard with filters and user-specific deal scores."""
    is_auth = current_user.is_authenticated
    area = request.args.get("area", "all")
    sort_by = request.args.get("sort", "score")
    flag_filter = request.args.get("flag", "all")
    source_filter = request.args.get("source", "all")
    min_score = request.args.get("min_score", 0, type=int)
    max_distance = request.args.get("max_distance", 0, type=float)

    # Compute user prefs early — needed for avoid_areas filter and scoring
    user_prefs = current_user.get_prefs() if is_auth else _guest_prefs()

    query = (
        Listing.query
        .outerjoin(DealScore)
        .filter(Listing.status == "active")
    )

    # ── Site zip floor — never show listings outside this site's registered zips ──
    from flask import g as _g
    import json as _json
    _site = getattr(_g, "site", None)
    _site_zips = []
    if _site and _site.get("zip_codes_json"):
        try:
            _site_zips = _json.loads(_site["zip_codes_json"])
            if _site_zips:
                query = query.filter(Listing.zip_code.in_(_site_zips))
        except (ValueError, TypeError):
            pass

    # ── Target areas come from registry (site-wide), not per-user prefs ──────────
    site_target_areas = _get_site_target_areas()

    if area != "all":
        area_zip_codes = site_target_areas.get(area, [])
        if area_zip_codes:
            query = query.filter(Listing.zip_code.in_(area_zip_codes))
        else:
            query = query.filter(db.false())  # area in nav but has no zips
    if source_filter != "all":
        query = query.filter(Listing.source == source_filter)

    # Exclude avoided zip codes using user's avoid_areas matched against target_areas
    # (avoid_areas stores names, not zips — skip name-based filtering on listings)

    # Get flags (DB for auth, session for guest)
    all_user_flags = _get_flags(is_auth)
    # Convert string keys back to int for session-based flags
    all_user_flags = {int(k): v for k, v in all_user_flags.items()}

    # Per-user flag filtering (works for both auth and guest)
    if flag_filter != "all" and flag_filter in ("favorite", "maybe", "hidden"):
        if is_auth:
            query = query.join(
                UserFlag,
                (UserFlag.listing_id == Listing.id) & (UserFlag.user_id == current_user.id)
            ).filter(UserFlag.flag == flag_filter)
        else:
            # Guest: filter by session flags in Python after query
            pass
    elif is_auth:
        # Exclude listings the current user has hidden
        hidden_ids = (
            db.session.query(UserFlag.listing_id)
            .filter_by(user_id=current_user.id, flag="hidden")
            .scalar_subquery()
        )
        query = query.filter(~Listing.id.in_(hidden_ids))
    else:
        # Guest: exclude hidden from session flags
        hidden_ids = [lid for lid, f in all_user_flags.items() if f == "hidden"]
        if hidden_ids:
            query = query.filter(~Listing.id.in_(hidden_ids))

    # Load all matching listings — must fetch all before scoring/sorting
    # so the top 100 by user-composite are correct (not just the first 200 by DB order)
    listings = query.all()

    # Guest flag filtering (can't do in SQL without UserFlag rows)
    if not is_auth and flag_filter != "all" and flag_filter in ("favorite", "maybe", "hidden"):
        flagged_ids = {int(lid) for lid, f in all_user_flags.items() if f == flag_filter}
        listings = [l for l in listings if l.id in flagged_ids]

    # Compute composite scores using user's weights (already computed above)
    user_composites = {}
    for listing in listings:
        if listing.deal_score:
            user_composites[listing.id] = listing.deal_score.compute_user_composite(user_prefs)
        else:
            user_composites[listing.id] = 0

    # Filter by min score (using user's composite)
    if min_score > 0:
        listings = [l for l in listings if user_composites.get(l.id, 0) >= min_score]

    # Sort
    if sort_by == "score":
        listings.sort(key=lambda l: user_composites.get(l.id, 0), reverse=True)
    elif sort_by == "price_asc":
        listings.sort(key=lambda l: l.price or 0)
    elif sort_by == "price_desc":
        listings.sort(key=lambda l: l.price or 0, reverse=True)
    elif sort_by == "newest":
        listings.sort(key=lambda l: l.first_seen or l.last_seen or l.id, reverse=True)
    elif sort_by == "yard":
        listings.sort(key=lambda l: l.lot_sqft or 0, reverse=True)
    else:
        listings.sort(key=lambda l: user_composites.get(l.id, 0), reverse=True)

    # ── POI distance computation + filtering ────────────────────
    poi_distances = {}
    poi_filter_name = None
    _poi_lat = user_prefs.get("proximity_poi_lat")
    _poi_lng = user_prefs.get("proximity_poi_lng")
    _poi_name = user_prefs.get("proximity_poi_name")
    if _poi_lat and _poi_lng and _poi_name:
        poi_filter_name = _poi_name
        try:
            from app.scraper.scorer import _haversine_miles
            for l in listings:
                if l.latitude and l.longitude:
                    poi_distances[l.id] = round(_haversine_miles(
                        l.latitude, l.longitude, _poi_lat, _poi_lng
                    ), 1)
        except Exception:
            pass

        # Filter by max distance if set
        if max_distance > 0:
            listings = [l for l in listings if poi_distances.get(l.id, 999) <= max_distance]

    listings = listings[:100]

    # Flags already loaded above
    user_flags = all_user_flags

    display_areas = list(site_target_areas.keys())

    # Load cached portfolio results for all flag types
    cached_portfolio = {}
    if is_auth:
        from app.models import CachedAnalysis
        for ft in ("favorite", "maybe", "hidden"):
            r = CachedAnalysis.load(current_user.id, f"portfolio_{ft}")
            if r:
                cached_portfolio[ft] = r

    # Street Watch widget: get active watches for current user/guest
    watched_streets = []
    from app.services.street_watch import get_user_watches as _get_watches
    if is_auth:
        watched_streets = _get_watches(user_id=current_user.id)
    else:
        from flask import session as _session
        _sw_email = _session.get("watch_email")
        if _sw_email:
            watched_streets = _get_watches(email=_sw_email)

    # ── "Since your last visit" stats ─────────────────────────────
    since_stats = None
    _gdt = user_prefs.get("great_deal_threshold", 75)
    _great_count = sum(1 for s in user_composites.values() if s >= _gdt)
    if is_auth and current_user.last_login:
        _ll = current_user.last_login
        _new = Listing.query.filter(
            Listing.status == "active",
            Listing.first_seen > _ll,
        )
        _drops = Listing.query.filter(
            Listing.status == "active",
            Listing.last_seen > _ll,
            Listing.price_change_pct < 0,
        )
        if _site_zips:
            _new = _new.filter(Listing.zip_code.in_(_site_zips))
            _drops = _drops.filter(Listing.zip_code.in_(_site_zips))
        since_stats = {
            "new_count": _new.count(),
            "drop_count": _drops.count(),
            "last_login": _ll,
            "total_scored": len(listings),
            "top_score": max(user_composites.values()) if user_composites else 0,
            "great_deal_count": _great_count,
        }
    elif not is_auth:
        # Guests see total stats to demonstrate value
        since_stats = {
            "total_scored": len(listings),
            "top_score": max(user_composites.values()) if user_composites else 0,
            "great_deal_count": _great_count,
        }

    # ── Most Shared This Week (top 5) ────────────────────────────
    most_shared_week = []
    try:
        from sqlalchemy import func as _func
        from datetime import timedelta as _td
        from app.models_social import SocialShare
        _week_ago = datetime.now(timezone.utc) - _td(days=7)
        most_shared_week = db.session.query(
            Listing,
            _func.count(SocialShare.id).label("share_count"),
        ).join(SocialShare, SocialShare.listing_id == Listing.id
        ).filter(SocialShare.created_at >= _week_ago
        ).group_by(Listing.id
        ).order_by(_func.count(SocialShare.id).desc()
        ).limit(5).all()
    except Exception:
        pass

    # ── Share counts for listing cards ────────────────────────────
    share_counts = {}
    try:
        from sqlalchemy import func as _func
        from app.models_social import SocialShare
        _sc_rows = db.session.query(
            SocialShare.listing_id,
            _func.count(SocialShare.id),
        ).filter(
            SocialShare.listing_id.in_([l.id for l in listings]),
        ).group_by(SocialShare.listing_id).all()
        share_counts = {row[0]: row[1] for row in _sc_rows}
    except Exception:
        pass

    # ── Active friend-listed homes matching site zips ─────────────
    friend_listings_active = []
    try:
        from app.models_social import FriendListing
        _fl_q = FriendListing.query.filter_by(status="active")
        if _site_zips:
            _fl_q = _fl_q.filter(FriendListing.zip_code.in_(_site_zips))
        friend_listings_active = _fl_q.order_by(FriendListing.created_at.desc()).limit(5).all()
    except Exception:
        pass

    return render_template(
        "dashboard/index.html",
        listings=listings,
        user_composites=user_composites,
        user_flags=user_flags,
        areas=display_areas,
        current_area=area,
        current_sort=sort_by,
        current_flag=flag_filter,
        current_source=source_filter,
        current_min_score=min_score,
        great_deal_threshold=user_prefs.get("great_deal_threshold", 75),
        cached_portfolio=cached_portfolio,
        watched_streets=watched_streets,
        since_stats=since_stats,
        most_shared_week=most_shared_week,
        share_counts=share_counts,
        friend_listings_active=friend_listings_active,
        poi_distances=poi_distances,
        poi_filter_name=poi_filter_name,
        current_max_distance=max_distance,
        user=current_user,
    )


@dashboard_bp.route("/listing/<int:listing_id>")
def listing_detail(listing_id):
    """Detail view for a single listing."""
    listing = Listing.query.get_or_404(listing_id)
    is_auth = current_user.is_authenticated
    user_flag = None
    if is_auth:
        user_flag_obj = UserFlag.query.filter_by(
            user_id=current_user.id, listing_id=listing_id
        ).first()
        user_flag = user_flag_obj
    else:
        from flask import session
        guest_flags = session.get("guest_flags", {})
        guest_flag_val = guest_flags.get(str(listing_id))
        if guest_flag_val:
            user_flag = _GuestFlag(guest_flag_val)
    user_prefs = current_user.get_prefs() if is_auth else _guest_prefs()
    user_composite = 0
    user_scores = {}
    if listing.deal_score:
        user_composite = listing.deal_score.compute_user_composite(user_prefs)
        user_scores = listing.deal_score.get_user_scores(user_prefs)

    # Detail enrichment is now AJAX — see /listing/<id>/enrich route below

    listing_note = None
    cached_deal  = None
    if is_auth:
        from app.models import ListingNote, CachedAnalysis
        listing_note = ListingNote.query.filter_by(
            user_id=current_user.id, listing_id=listing_id
        ).first()
        cached_deal = CachedAnalysis.load(current_user.id, "deal",
                                          listing_id=listing_id)

    # Street Watch: extract street name for the sidebar card
    from app.services.street_watch import extract_street_name
    _sw_normalised, _sw_display = extract_street_name(listing.address)

    # Check if current user/guest already watches this street
    _sw_watching = None
    if _sw_normalised:
        from app.models import StreetWatch
        if current_user.is_authenticated:
            _sw_watching = StreetWatch.query.filter_by(
                user_id=current_user.id, street_name=_sw_normalised,
                zip_code=listing.zip_code, is_active=True
            ).first()
        else:
            from flask import session as _session
            _sw_email = _session.get("watch_email")
            if _sw_email:
                _sw_watching = StreetWatch.query.filter_by(
                    email=_sw_email, street_name=_sw_normalised,
                    zip_code=listing.zip_code, is_active=True
                ).first()

    # ── Reaction summary for this listing's shares ─────────────────
    reaction_summary = []
    try:
        from sqlalchemy import func as _func
        from app.models_social import SocialShare, SocialReaction, REACTION_TYPES
        _r_rows = db.session.query(
            SocialReaction.reaction_type,
            _func.count(SocialReaction.id),
        ).join(SocialShare, SocialReaction.share_id == SocialShare.id
        ).filter(SocialShare.listing_id == listing_id
        ).group_by(SocialReaction.reaction_type).all()
        _rt_map = {r[0]: r for r in REACTION_TYPES}
        for rtype, count in _r_rows:
            info = _rt_map.get(rtype)
            if info:
                reaction_summary.append((rtype, info[2], info[1], info[3], count))
    except Exception:
        pass

    # ── Load landmarks for detail map ──────────────────────────────
    detail_landmarks = []
    from flask import g as _detail_g
    import json as _detail_json
    _detail_site = getattr(_detail_g, "site", None)
    if _detail_site and _detail_site.get("landmarks_json"):
        try:
            detail_landmarks = _detail_json.loads(_detail_site["landmarks_json"])
        except (ValueError, TypeError):
            pass
    # Merge user landmarks
    user_lms = user_prefs.get("user_landmarks", [])
    if user_lms:
        detail_landmarks = detail_landmarks + user_lms

    # ── POI proximity distance for detail display ──────────────────
    poi_distance_miles = None
    poi_name = None
    if listing.latitude and listing.longitude:
        poi_lat = user_prefs.get("proximity_poi_lat")
        poi_lng = user_prefs.get("proximity_poi_lng")
        poi_name = user_prefs.get("proximity_poi_name")
        if poi_lat and poi_lng and poi_name:
            try:
                from app.scraper.scorer import _haversine_miles
                poi_distance_miles = _haversine_miles(
                    listing.latitude, listing.longitude, poi_lat, poi_lng
                )
            except Exception:
                pass

    return render_template("dashboard/detail.html",
                           listing=listing, user_flag=user_flag,
                           user_composite=user_composite,
                           user_scores=user_scores, user=current_user,
                           listing_note=listing_note,
                           cached_deal=cached_deal,
                           detail_sections=_parse_detail_sections(listing),
                           street_name=_sw_display,
                           street_name_normalised=_sw_normalised,
                           street_watching=_sw_watching,
                           reaction_summary=reaction_summary,
                           poi_distance_miles=poi_distance_miles,
                           poi_name=poi_name,
                           landmarks=detail_landmarks)


@dashboard_bp.route("/listing/<int:listing_id>/enrich", methods=["POST"])
def enrich_listing(listing_id):
    """AJAX: fetch detail data from source API for a listing."""
    import time as _time
    from flask import current_app as _ca, g as _g_enrich, jsonify
    from app.models import ApiCallLog

    listing = db.session.get(Listing, listing_id)
    if not listing:
        return jsonify({"error": "Listing not found"}), 404

    if listing.details_fetched:
        return jsonify({"ok": True, "already_fetched": True,
                        "description": listing.description or ""})

    # Quota check
    _site_enrich = getattr(_g_enrich, "site", None)
    if _site_enrich:
        from app.services.billing import check_quota as _bq_check
        allowed, reason = _bq_check(
            _site_enrich["site_key"],
            f"{listing.source or 'zillow'}_detail",
        )
        if not allowed:
            return jsonify({"error": reason}), 429

    try:
        from app.scraper.zillow import TransientAPIError as _ZillowTransient
        from app.scraper.realtor import TransientAPIError as _RealtorTransient
        enrichment = None
        _enrich_source = listing.source or "unknown"
        raw_id = listing.source_id or ""
        bare_id = raw_id.split("_", 1)[1] if "_" in raw_id else raw_id

        _t0 = _time.time()
        if listing.source == "zillow" and bare_id:
            from app.scraper.zillow import fetch_zillow_detail
            enrichment = fetch_zillow_detail(bare_id, listing.url or "", listing.address or "")
        elif listing.source == "realtor" and bare_id:
            from app.scraper.realtor import fetch_realtor_detail
            enrichment = fetch_realtor_detail(bare_id)
        _elapsed_ms = int((_time.time() - _t0) * 1000)

        _enrich_ok = False
        applied_keys = []
        if enrichment:
            ENRICHABLE = {
                "details_json", "description", "year_built", "hoa_monthly",
                "has_garage", "has_porch", "has_patio", "stories",
                "is_single_story", "has_community_pool",
                "property_tax_annual", "flood_zone",
                "above_flood_plain", "photo_urls_json",
            }
            applied = {k: v for k, v in enrichment.items() if k in ENRICHABLE and v is not None}
            for field, value in applied.items():
                setattr(listing, field, value)
            applied_keys = sorted(applied.keys())
            _enrich_ok = True

        _user_id = current_user.id if current_user.is_authenticated else None
        ApiCallLog.log(
            f"{_enrich_source}_detail",
            user_id=_user_id,
            detail=listing.address or f"listing #{listing_id}",
            success=_enrich_ok,
            response_time_ms=_elapsed_ms,
            zip_code=listing.zip_code,
        )

        listing.details_fetched = True
        db.session.commit()

        return jsonify({
            "ok": True,
            "description": listing.description or "",
            "response_time_ms": _elapsed_ms,
            "fields_updated": applied_keys,
        })

    except (_ZillowTransient, _RealtorTransient) as _transient:
        _elapsed_ms = int((_time.time() - _t0) * 1000)
        _user_id = current_user.id if current_user.is_authenticated else None
        ApiCallLog.log(
            f"{_enrich_source}_detail", user_id=_user_id,
            detail=f"{listing.address} (transient)", success=False,
            response_time_ms=_elapsed_ms, zip_code=listing.zip_code,
        )
        return jsonify({"error": "Source API temporarily unavailable. Try again in a moment."}), 503

    except Exception as exc:
        _elapsed_ms = int((_time.time() - _t0) * 1000) if '_t0' in dir() else 0
        _ca.logger.warning(f"[ENRICH] listing {listing_id} — EXCEPTION: {exc}", exc_info=True)
        _user_id = current_user.id if current_user.is_authenticated else None
        ApiCallLog.log(
            f"{listing.source or 'unknown'}_detail", user_id=_user_id,
            detail=f"{listing.address} (error)", success=False,
            response_time_ms=_elapsed_ms, zip_code=listing.zip_code,
        )
        return jsonify({"error": "Failed to fetch details. Please try again."}), 500


@dashboard_bp.route("/listing/<int:listing_id>/flag", methods=["POST"])
def toggle_flag(listing_id):
    """Set or update a per-user flag on a listing (favorite / maybe / hidden)."""
    from flask import session
    Listing.query.get_or_404(listing_id)
    new_flag = request.form.get("flag", "favorite")
    if new_flag not in ("favorite", "maybe", "hidden"):
        flash("Invalid flag type.", "danger")
        return redirect(request.referrer or _site_redirect("dashboard.index").location)

    is_auth = current_user.is_authenticated

    if is_auth:
        note = request.form.get("note", "").strip() or None
        uf = UserFlag.query.filter_by(
            user_id=current_user.id, listing_id=listing_id
        ).first()

        if uf:
            if uf.flag == new_flag:
                db.session.delete(uf)
                flash("Flag removed.", "info")
            else:
                uf.flag = new_flag
                uf.note = note
                flash(f"Flag updated to {new_flag}.", "success")
        else:
            uf = UserFlag(user_id=current_user.id, listing_id=listing_id,
                          flag=new_flag, note=note)
            db.session.add(uf)
            flash(f"Listing flagged as {new_flag}.", "success")

        db.session.commit()

        # ── Progressive nudges after flagging milestones ────────
        fav_count = UserFlag.query.filter_by(
            user_id=current_user.id, flag="favorite"
        ).count()
        agent = current_user.assigned_agent
        agent_first = agent.full_name.split(" ")[0] if agent else None

        if new_flag == "favorite" and fav_count == 1:
            flash("Great first pick! Keep starring listings you like.", "info")
        elif new_flag == "favorite" and fav_count == 3:
            tip = f" {agent_first} can see your picks and help prioritize." if agent else ""
            flash(f"3 favorites — try <strong>AI Portfolio Analysis</strong> "
                  f"to compare them side-by-side.{tip}", "info")
        elif new_flag == "favorite" and fav_count == 5:
            if agent:
                flash(f"5 favorites — {agent_first} has enough to start "
                      f"planning showings. Ready for a tour?", "info")
            else:
                flash("5 favorites — head to <strong>Tour</strong> "
                      "to plan your visits.", "info")

    else:
        # Guest: store in session
        guest_flags = session.get("guest_flags", {})
        lid_key = str(listing_id)  # session JSON keys are strings
        if guest_flags.get(lid_key) == new_flag:
            del guest_flags[lid_key]
            flash("Flag removed.", "info")
        else:
            guest_flags[lid_key] = new_flag
            flash(f"Listing flagged as {new_flag}.", "success")

            # Guest milestone — nudge toward account creation
            guest_fav_count = sum(1 for f in guest_flags.values() if f == "favorite")
            if new_flag == "favorite" and guest_fav_count == 1:
                flash("Nice pick! Your flags are saved in this browser session.", "info")
            elif new_flag == "favorite" and guest_fav_count == 3:
                flash('<a href="' + _site_url("auth.register") + '">Create a free account</a> '
                      "to keep your favorites permanently and unlock AI analysis.", "info")

        session["guest_flags"] = guest_flags
        session.modified = True

    return redirect(request.referrer or _site_redirect("dashboard.index").location)


@dashboard_bp.route("/map")
def map_view():
    """Map view of all active listings."""
    is_auth = current_user.is_authenticated
    listings = (
        Listing.query
        .outerjoin(DealScore)
        .filter(Listing.status == "active")
        .filter(Listing.latitude.isnot(None))
        .all()
    )
    user_prefs = current_user.get_prefs() if is_auth else _guest_prefs()
    user_composites = {}
    for listing in listings:
        if listing.deal_score:
            user_composites[listing.id] = listing.deal_score.compute_user_composite(user_prefs)
        else:
            user_composites[listing.id] = 0
    user_flags = _get_flags(is_auth)
    user_flags = {int(k): v for k, v in user_flags.items()}
    _map_target_areas = _get_site_target_areas()

    # Load landmarks for map display
    landmarks = []
    from flask import g as _map_g
    import json as _map_json
    _map_site = getattr(_map_g, "site", None)
    if _map_site and _map_site.get("landmarks_json"):
        try:
            landmarks = _map_json.loads(_map_site["landmarks_json"])
        except (ValueError, TypeError):
            pass

    return render_template("dashboard/map.html",
                           listings=listings, user_composites=user_composites,
                           user_flags=user_flags, target_areas=_map_target_areas,
                           landmarks=landmarks,
                           user=current_user)


@dashboard_bp.route("/digest")
def digest():
    """Full tabular listing view with CSV export support."""
    from datetime import datetime, timedelta, timezone
    is_auth = current_user.is_authenticated
    user_prefs = current_user.get_prefs() if is_auth else _guest_prefs()

    # Days filter (for "New" tab)
    days_back = request.args.get("days", 3, type=int)
    since     = datetime.now(timezone.utc) - timedelta(days=days_back)
    since_naive = since.replace(tzinfo=None)  # SQLite datetimes are naive

    # Flag filter
    flag_filter = request.args.get("flag", "all")   # all, favorite, maybe, hidden, new
    area_filter = request.args.get("area", "")

    # Resolve user flags
    if is_auth:
        user_flags_map = {
            f.listing_id: f.flag
            for f in UserFlag.query.filter_by(user_id=current_user.id).all()
        }
    else:
        from flask import session
        user_flags_map = {
            int(k): v for k, v in session.get("guest_flags", {}).items()
        }

    # Base query — all active listings with scores
    q = Listing.query.outerjoin(DealScore).filter(Listing.status == "active")

    # Target areas from registry (site-wide)
    _digest_target_areas = _get_site_target_areas()

    if area_filter:
        area_zip_codes = _digest_target_areas.get(area_filter, [])
        if area_zip_codes:
            q = q.filter(Listing.zip_code.in_(area_zip_codes))

    all_listings = q.order_by(Listing.first_seen.desc()).all()

    # Apply flag filter in Python
    if flag_filter == "new":
        listings = [l for l in all_listings if l.first_seen and l.first_seen >= since_naive]
    elif flag_filter in ("favorite", "maybe", "hidden"):
        listings = [l for l in all_listings if user_flags_map.get(l.id) == flag_filter]
    else:
        listings = [l for l in all_listings if user_flags_map.get(l.id) != "hidden"]

    # Compute per-user composites
    user_composites = {}
    for l in listings:
        if l.deal_score:
            user_composites[l.id] = round(l.deal_score.compute_user_composite(user_prefs), 1)
        else:
            user_composites[l.id] = 0

    # Distinct areas for filter buttons — from site registry
    areas = sorted(_digest_target_areas.keys())

    # CSV export
    if request.args.get("export") == "csv":
        import csv, io
        from flask import Response
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Address","Area","Price","Beds","Baths","Sqft","Lot Sqft","Year Built",
            "Score","Flood Zone","Above Flood Plain","HOA/mo","Tax/yr","Days on Market",
            "Price Change %","Garage","Porch","Patio","Pool","Single Story",
            "Source","Status","First Seen","Flag"
        ])
        for l in listings:
            score = user_composites.get(l.id, "")
            writer.writerow([
                l.address, l.area_name, l.price, l.beds, l.baths, l.sqft, l.lot_sqft,
                l.year_built, score, l.flood_zone,
                "Yes" if l.above_flood_plain else ("No" if l.above_flood_plain is not None else ""),
                l.hoa_monthly, l.property_tax_annual, l.days_on_market,
                l.price_change_pct,
                "Yes" if l.has_garage else "",
                "Yes" if l.has_porch  else "",
                "Yes" if l.has_patio  else "",
                "Yes" if l.has_community_pool else "",
                "Yes" if l.is_single_story    else "",
                l.source, l.status,
                l.first_seen.strftime("%Y-%m-%d") if l.first_seen else "",
                user_flags_map.get(l.id, ""),
            ])
        csv_data = output.getvalue()
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=homefinder_listings.csv"}
        )

    # Price-change listings for the "New" summary strip
    new_listings    = [l for l in all_listings if l.first_seen and l.first_seen >= since_naive]
    price_changes   = [l for l in all_listings
                       if l.price_history_json and l.price_history_json != "[]"
                       and l.last_seen and l.last_seen >= since_naive]

    return render_template(
        "dashboard/digest.html",
        listings=listings,
        new_listings=new_listings,
        price_changes=price_changes,
        user_composites=user_composites,
        user_flags_map=user_flags_map,
        days_back=days_back,
        flag_filter=flag_filter,
        area_filter=area_filter,
        areas=areas,
        user=current_user,
    )
