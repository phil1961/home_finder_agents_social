# ─────────────────────────────────────────────
# File: app/routes/ai_routes.py
# App Version: 2026.03.14 | File Version: 1.6.0
# Last Modified: 2026-03-18
# ─────────────────────────────────────────────
"""
app/routes/ai_routes.py — AI analysis routes.
"""
from flask import request, jsonify
from flask_login import login_required, current_user

from app.models import db, Listing, DealScore, UserFlag, User
from app.routes.dashboard_helpers import dashboard_bp


@dashboard_bp.route("/listing/<int:listing_id>/analyze", methods=["POST"])
@login_required
def analyze_listing(listing_id):
    """Generate an AI Deal Brief for a listing via Claude API."""
    listing = Listing.query.get_or_404(listing_id)

    # ── Quota check ───────────────────────────────────────────────
    from flask import g
    _site = getattr(g, "site", None)
    if _site:
        from app.services.billing import check_quota
        allowed, reason = check_quota(_site["site_key"], "anthropic_deal")
        if not allowed:
            return jsonify({"error": reason}), 429

    try:
        from app.services.deal_analyst import analyze_listing as run_analysis

        prefs = current_user.get_prefs()
        from app.models import PromptOverride
        _agent_id = current_user.agent_id
        _prompt = PromptOverride.resolve("deal", _agent_id)
        result = run_analysis(listing, listing.deal_score, prefs, system_prompt=_prompt)

        from app.models import ApiCallLog, CachedAnalysis
        meta = result.pop("_meta", {})
        ApiCallLog.log("anthropic_deal", user_id=current_user.id,
                       detail=listing.address, success="error" not in result,
                       response_time_ms=meta.get("response_time_ms"),
                       http_status=meta.get("http_status"))

        if "error" in result:
            return jsonify({"error": result["error"]}), 500

        CachedAnalysis.save(current_user.id, "deal", result,
                            listing_id=listing_id)
        return jsonify(result)

    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {e}"}), 500


# ── Portfolio / Set Analysis ────────────────────────────────────

@dashboard_bp.route("/analyze-portfolio", methods=["POST"])
@login_required
def analyze_portfolio_route():
    """Generate a big-picture AI analysis across a set of flagged listings."""
    # ── Quota check ───────────────────────────────────────────────
    from flask import g
    _site = getattr(g, "site", None)
    if _site:
        from app.services.billing import check_quota
        allowed, reason = check_quota(_site["site_key"], "anthropic_portfolio")
        if not allowed:
            return jsonify({"error": reason}), 429

    flag = request.form.get("flag", "favorite")
    if flag not in ("favorite", "maybe", "hidden"):
        return jsonify({"error": "Invalid flag filter."}), 400

    flag_labels = {"favorite": "Favorites", "maybe": "Maybes", "hidden": "Hidden"}

    # Get flagged listings for this user
    flagged = (
        Listing.query
        .join(UserFlag, (UserFlag.listing_id == Listing.id) & (UserFlag.user_id == current_user.id))
        .filter(UserFlag.flag == flag, Listing.status == "active")
        .outerjoin(DealScore)
        .all()
    )

    if not flagged:
        return jsonify({"error": f"No {flag_labels[flag].lower()} listings to analyze."}), 400

    if len(flagged) > 20:
        flagged = flagged[:20]  # Cap to avoid token overflow

    # Compute per-user composites
    user_prefs = current_user.get_prefs()
    user_composites = {}
    for listing in flagged:
        if listing.deal_score:
            user_composites[listing.id] = listing.deal_score.compute_user_composite(user_prefs)
        else:
            user_composites[listing.id] = 0

    # Sort by composite descending for the AI
    flagged.sort(key=lambda l: user_composites.get(l.id, 0), reverse=True)

    try:
        from app.services.deal_analyst import analyze_portfolio

        from app.models import PromptOverride
        _agent_id = current_user.agent_id
        _prompt = PromptOverride.resolve("portfolio", _agent_id)
        result = analyze_portfolio(flagged, user_composites, user_prefs,
                                   flag_label=flag_labels[flag], system_prompt=_prompt)

        from app.models import ApiCallLog, CachedAnalysis
        meta = result.pop("_meta", {})
        ApiCallLog.log("anthropic_portfolio", user_id=current_user.id,
                       detail=f"{flag} ({len(flagged)} listings)",
                       success="error" not in result,
                       response_time_ms=meta.get("response_time_ms"),
                       http_status=meta.get("http_status"))

        if "error" in result:
            return jsonify({"error": result["error"]}), 500

        CachedAnalysis.save(current_user.id, f"portfolio_{flag}", result)
        return jsonify(result)

    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Portfolio analysis failed: {e}"}), 500


# ── AI Preferences Coach ────────────────────────────────────────

@dashboard_bp.route("/analyze-preferences", methods=["POST"])
@login_required
def analyze_preferences():
    """AI analysis of the user's scoring preferences configuration."""
    # ── Quota check ───────────────────────────────────────────────
    from flask import g
    _site = getattr(g, "site", None)
    if _site:
        from app.services.billing import check_quota
        allowed, reason = check_quota(_site["site_key"], "anthropic_prefs")
        if not allowed:
            return jsonify({"error": reason}), 429

    imp_keys = [k for k in User.DEFAULT_PREFS if k.startswith("imp_")]

    # Read current slider values from the POST (may differ from saved prefs)
    prefs = {
        "min_price": int(request.form.get("min_price", 200000)),
        "max_price": int(request.form.get("max_price", 600000)),
        "min_beds": int(request.form.get("min_beds", 4)),
        "min_baths": float(request.form.get("min_baths", 3)),
        "must_have_garage": request.form.get("must_have_garage") == "on",
        "must_have_porch": request.form.get("must_have_porch") == "on",
        "must_have_patio": request.form.get("must_have_patio") == "on",
    }
    for k in imp_keys:
        prefs[k] = int(request.form.get(k, User.DEFAULT_PREFS.get(k, 5)))

    # Include buyer profile from saved prefs (managed via Settings > Tune)
    saved_prefs = current_user.get_prefs()
    prefs["buyer_profile"] = saved_prefs.get("buyer_profile", {})

    try:
        from app.services.deal_analyst import analyze_preferences as run_prefs_analysis

        from app.models import PromptOverride
        _agent_id = current_user.agent_id
        _prompt = PromptOverride.resolve("preferences", _agent_id)
        result = run_prefs_analysis(prefs, User.DEFAULT_PREFS, system_prompt=_prompt)

        from app.models import ApiCallLog, CachedAnalysis
        meta = result.pop("_meta", {})
        ApiCallLog.log("anthropic_prefs", user_id=current_user.id,
                       detail="preferences analysis", success="error" not in result,
                       response_time_ms=meta.get("response_time_ms"),
                       http_status=meta.get("http_status"))

        if "error" in result:
            return jsonify({"error": result["error"]}), 500

        CachedAnalysis.save(current_user.id, "prefs", result)
        return jsonify(result)

    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Preferences analysis failed: {e}"}), 500
