# ─────────────────────────────────────────────
# File: app/routes/admin_routes.py
# App Version: 2026.03.14 | File Version: 1.7.0
# Last Modified: 2026-03-14
# ─────────────────────────────────────────────
"""
app/routes/admin_routes.py — Owner-level admin routes.
"""
from flask import render_template, request, flash, jsonify
from flask_login import login_required, current_user

from app.models import db, User
from app.routes.dashboard_helpers import dashboard_bp, _site_redirect


@dashboard_bp.route("/fetch-now", methods=["POST"])
@login_required
def fetch_now():
    """Manually trigger the scraper pipeline. Returns JSON with captured log."""
    import logging
    import time
    from flask import current_app, g
    from app.scraper.pipeline import run_pipeline

    if not (current_user.is_owner or current_user.is_agent):
        return jsonify({"error": "Permission denied"}), 403

    site_key = g.site["site_key"] if hasattr(g, "site") and g.site else None

    # ── Quota check before fetch ──────────────────────────────────
    if site_key:
        from app.services.billing import check_quota
        allowed, reason = check_quota(site_key, "zillow")
        if not allowed:
            return jsonify({"status": "error", "summary": reason, "elapsed": "0s", "log": []}), 429

    # Capture log output during pipeline run
    log_lines = []
    start_time = time.time()

    class _LogCapture(logging.Handler):
        def emit(self, record):
            elapsed = time.time() - start_time
            log_lines.append({
                "time": f"{elapsed:.1f}s",
                "level": record.levelname,
                "message": self.format(record),
            })

    handler = _LogCapture()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(message)s"))

    # Attach to pipeline and scraper loggers, ensuring they emit INFO+
    # We disable propagation temporarily so messages don't also bubble up
    # to the app logger and get captured twice.
    loggers = []
    saved_levels = {}
    saved_propagate = {}
    for name in ("pipeline", "app.scraper.pipeline", "app.scraper.zillow",
                  "app.scraper.realtor", "app.scraper.geocoder", "app.scraper.scorer"):
        _log = logging.getLogger(name)
        saved_levels[name] = _log.level
        saved_propagate[name] = _log.propagate
        if _log.level == logging.NOTSET or _log.level > logging.DEBUG:
            _log.setLevel(logging.DEBUG)
        _log.propagate = False
        _log.addHandler(handler)
        loggers.append(_log)

    # Check for zip codes before running
    import json as _fetch_json
    _fetch_site = g.site if hasattr(g, "site") and g.site else {}
    _fetch_zips = []
    try:
        _fetch_zips = _fetch_json.loads(_fetch_site.get("zip_codes_json", "[]") or "[]")
    except (ValueError, TypeError):
        pass
    if not _fetch_zips:
        return jsonify({
            "status": "error",
            "summary": "No zip codes configured for this site. Go to Preferences → Target Areas and add zip codes before fetching.",
            "elapsed": "0s",
            "log": [{"time": "0s", "level": "ERROR", "message": "No zip codes configured. Add target areas with zip codes first."}],
        })

    try:
        count = run_pipeline(current_app._get_current_object(), site_key=site_key)
        # Individual API calls are now logged by the scraper modules themselves
        elapsed = time.time() - start_time
        status = "success" if count > 0 else "warning"
        summary = (f"Fetch complete — {count} listings processed in {elapsed:.1f}s."
                   if count > 0 else
                   "Fetch ran but returned no listings. Check your API key and subscriptions.")
    except Exception as e:
        elapsed = time.time() - start_time
        status = "error"
        summary = f"Fetch failed: {e}"
        log_lines.append({"time": f"{elapsed:.1f}s", "level": "ERROR", "message": str(e)})
    finally:
        # Clean up handlers and restore original levels + propagation
        for _log in loggers:
            _log.removeHandler(handler)
        for name, lvl in saved_levels.items():
            logging.getLogger(name).setLevel(lvl)
            logging.getLogger(name).propagate = saved_propagate.get(name, True)

    return jsonify({
        "status": status,
        "summary": summary,
        "elapsed": f"{elapsed:.1f}s",
        "log": log_lines,
    })


# ── Owner: Toggle scheduled fetcher ──────────────────────────────

@dashboard_bp.route("/toggle-scheduler", methods=["POST"])
@login_required
def toggle_scheduler():
    """Pause or resume the nightly scheduled pipeline for the current site."""
    if not current_user.is_owner:
        return jsonify({"error": "Permission denied"}), 403

    from flask import g
    from app.services.registry import get_site_any, update_site

    site_key = g.site["site_key"] if hasattr(g, "site") and g.site else None
    if not site_key:
        return jsonify({"error": "No site context"}), 400

    site = get_site_any(site_key)

    # If master has locked the scheduler, owner can't resume it
    if bool(site.get("scheduler_locked")) and not current_user.is_master:
        return jsonify({
            "error": "Scheduler is locked by the master administrator. Contact them to unlock it.",
        }), 403

    currently_paused = bool(site.get("scheduler_paused"))
    new_state = not currently_paused
    update_site(site_key, scheduler_paused=int(new_state))

    return jsonify({
        "paused": new_state,
        "message": f"Scheduler {'paused' if new_state else 'resumed'} for {site.get('display_name', site_key)}.",
    })


# ── Owner: API Diagnostics ───────────────────────────────────────

@dashboard_bp.route("/admin/diagnostics")
@login_required
def admin_diagnostics():
    """Owner-only: per-call API diagnostics — response times, HTTP status, quota."""
    if not current_user.is_owner:
        flash("Owner access required.", "danger")
        return _site_redirect("dashboard.index")

    from app.models import ApiCallLog
    from datetime import datetime, timezone, timedelta

    # Last 200 paid API calls (scrapers, detail enrichment, AI analysis)
    calls = (ApiCallLog.query
             .filter(ApiCallLog.call_type.in_(list(ApiCallLog.COST_MAP.keys())))
             .order_by(ApiCallLog.called_at.desc())
             .limit(200).all())

    # Aggregate stats
    last_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    recent = [c for c in calls if c.called_at and
              c.called_at.replace(tzinfo=c.called_at.tzinfo or timezone.utc) >= last_24h]

    def _avg_ms(entries):
        times = [e.response_time_ms for e in entries if e.response_time_ms]
        return int(sum(times) / len(times)) if times else 0

    def _error_rate(entries):
        if not entries:
            return 0
        fails = sum(1 for e in entries if not e.success)
        return round(fails / len(entries) * 100, 1)

    summary = {
        "total_calls": len(recent),
        "avg_response_ms": _avg_ms(recent),
        "error_rate": _error_rate(recent),
        "zillow_calls": sum(1 for c in recent if c.call_type == "zillow"),
        "realtor_calls": sum(1 for c in recent if c.call_type == "realtor"),
        "min_quota": min((c.quota_remaining for c in recent if c.quota_remaining is not None), default=None),
    }

    return render_template("dashboard/admin_diagnostics.html",
                           calls=calls, summary=summary)


# ── Owner: API Usage Metrics ─────────────────────────────────────

@dashboard_bp.route("/admin/metrics")
@login_required
def admin_metrics():
    """Owner-only: API call usage and cost breakdown by user."""
    if not current_user.is_owner:
        flash("Owner access required.", "danger")
        return _site_redirect("dashboard.index")

    from app.models import ApiCallLog
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import func

    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    # All-time totals per user per call_type
    alltime = (
        db.session.query(
            ApiCallLog.user_id,
            ApiCallLog.call_type,
            func.count(ApiCallLog.id).label("cnt")
        )
        .group_by(ApiCallLog.user_id, ApiCallLog.call_type)
        .all()
    )

    # Last 30 days totals per user per call_type
    recent = (
        db.session.query(
            ApiCallLog.user_id,
            ApiCallLog.call_type,
            func.count(ApiCallLog.id).label("cnt")
        )
        .filter(ApiCallLog.called_at >= thirty_days_ago)
        .group_by(ApiCallLog.user_id, ApiCallLog.call_type)
        .all()
    )

    # Build a lookup of user_id -> User
    user_ids = set(r.user_id for r in alltime + recent)
    users = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()}

    # Aggregate into per-user dicts
    COST_MAP = ApiCallLog.COST_MAP
    CALL_TYPES = list(ApiCallLog.COST_MAP.keys())

    def build_user_rows(rows):
        data = {}  # user_id -> {call_type: count}
        for r in rows:
            uid = r.user_id or 0
            if uid not in data:
                data[uid] = {ct: 0 for ct in CALL_TYPES}
                data[uid]["_total_cost"] = 0.0
            data[uid][r.call_type] = data[uid].get(r.call_type, 0) + r.cnt
            data[uid]["_total_cost"] += r.cnt * COST_MAP.get(r.call_type, 0)
        return data

    alltime_data = build_user_rows(alltime)
    recent_data  = build_user_rows(recent)

    # Grand totals
    grand_alltime = sum(v["_total_cost"] for v in alltime_data.values())
    grand_recent  = sum(v["_total_cost"] for v in recent_data.values())

    # Pre-compute summary card numbers (Jinja2 can't map over dict keys)
    def col_sum(data, *keys):
        return sum(data[uid].get(k, 0) for uid in data for k in keys)

    def col_totals(data):
        """Per-call-type column totals for the footer row."""
        return {ct: sum(data[uid].get(ct, 0) for uid in data) for ct in CALL_TYPES}

    summary = {
        "alltime_ai":      col_sum(alltime_data, "anthropic_deal","anthropic_portfolio","anthropic_prefs"),
        "alltime_fetches": col_sum(alltime_data, "zillow","realtor"),
        "alltime_col_totals": col_totals(alltime_data),
        "recent_col_totals":  col_totals(recent_data),
    }

    # Most recent 50 calls for the activity log
    recent_calls = (
        ApiCallLog.query
        .order_by(ApiCallLog.called_at.desc())
        .limit(50)
        .all()
    )

    return render_template(
        "dashboard/admin_metrics.html",
        alltime_data=alltime_data,
        recent_data=recent_data,
        users=users,
        call_types=CALL_TYPES,
        cost_map=COST_MAP,
        grand_alltime=grand_alltime,
        grand_recent=grand_recent,
        recent_calls=recent_calls,
        summary=summary,
        user=current_user,
    )



@dashboard_bp.route("/admin/metrics/refresh")
@login_required
def admin_metrics_refresh():
    """AJAX: return fresh Recent Activity rows + summary card numbers."""
    if not current_user.is_owner:
        return jsonify(error="Owner access required."), 403

    from app.models import ApiCallLog
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import func

    COST_MAP = ApiCallLog.COST_MAP

    # Summary card values
    alltime_rows = (
        db.session.query(ApiCallLog.call_type, func.count(ApiCallLog.id).label("cnt"))
        .group_by(ApiCallLog.call_type).all()
    )
    alltime_by_type = {r.call_type: r.cnt for r in alltime_rows}
    alltime_ai = sum(alltime_by_type.get(k, 0) for k in ("anthropic_deal", "anthropic_portfolio", "anthropic_prefs"))
    alltime_fetches = sum(alltime_by_type.get(k, 0) for k in ("zillow", "realtor", "zillow_detail", "realtor_detail"))
    grand_alltime = sum(cnt * COST_MAP.get(ct, 0) for ct, cnt in alltime_by_type.items())

    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    recent_rows = (
        db.session.query(ApiCallLog.call_type, func.count(ApiCallLog.id).label("cnt"))
        .filter(ApiCallLog.called_at >= thirty_days_ago)
        .group_by(ApiCallLog.call_type).all()
    )
    recent_by_type = {r.call_type: r.cnt for r in recent_rows}
    grand_recent = sum(cnt * COST_MAP.get(ct, 0) for ct, cnt in recent_by_type.items())

    # Recent activity (last 50)
    calls = ApiCallLog.query.order_by(ApiCallLog.called_at.desc()).limit(50).all()
    user_ids = set(c.user_id for c in calls if c.user_id)
    users = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}

    activity_rows = []
    for c in calls:
        u = users.get(c.user_id)
        activity_rows.append({
            "when": c.called_at.strftime("%b %d %H:%M") if c.called_at else "—",
            "user": u.username if u else "system",
            "trigger": c.trigger or "",
            "site_key": c.site_key or "—",
            "zip_code": c.zip_code or "—",
            "call_type": c.call_type or "",
            "results_count": c.results_count,
            "response_time_ms": c.response_time_ms,
            "detail": c.detail or "—",
            "success": c.success,
        })

    return jsonify(
        summary={
            "alltime_ai": alltime_ai,
            "alltime_fetches": alltime_fetches,
            "grand_alltime": f"{grand_alltime:.2f}",
            "grand_recent": f"{grand_recent:.2f}",
        },
        activity=activity_rows,
    )


@dashboard_bp.route("/admin/agents")
@login_required
def admin_agents():
    """Owner-only page to view and manage agent applications."""
    if not current_user.is_owner:
        flash("Access denied.", "danger")
        return _site_redirect("dashboard.index")

    from app.models import AgentProfile
    agents = (
        AgentProfile.query
        .join(User, AgentProfile.user_id == User.id)
        .order_by(AgentProfile.status, AgentProfile.created_at.desc())
        .all()
    )
    from app.models import OwnerAgentNote
    owner_notes = {n.agent_id: n for n in OwnerAgentNote.query.all()}
    return render_template("dashboard/admin_agents.html",
                           agents=agents, owner_notes=owner_notes, user=current_user)


@dashboard_bp.route("/admin/agents/<int:agent_profile_id>/action", methods=["POST"])
@login_required
def admin_agent_action(agent_profile_id):
    """Approve or suspend an agent. Owner only."""
    from datetime import datetime, timezone
    from app.models import AgentProfile

    if not current_user.is_owner:
        flash("Access denied.", "danger")
        return _site_redirect("dashboard.index")

    profile = AgentProfile.query.get_or_404(agent_profile_id)
    action = request.form.get("action")

    if action == "approve":
        profile.status = "approved"
        profile.approved_at = datetime.now(timezone.utc)
        db.session.commit()
        flash(f"{profile.full_name} has been approved. They can now log in.", "success")
    elif action == "suspend":
        profile.status = "suspended"
        db.session.commit()
        flash(f"{profile.full_name} has been suspended.", "warning")
    elif action == "reactivate":
        profile.status = "approved"
        db.session.commit()
        flash(f"{profile.full_name} has been reactivated.", "success")
    else:
        flash("Unknown action.", "danger")

    return _site_redirect("dashboard.admin_agents")


@dashboard_bp.route("/admin/agents/<int:agent_profile_id>/notes", methods=["POST"])
@login_required
def admin_agent_notes(agent_profile_id):
    """Save owner notes and checkboxes for an agent. Returns JSON."""
    if not current_user.is_owner:
        return jsonify({"error": "Access denied"}), 403

    from app.models import AgentProfile, OwnerAgentNote
    profile = AgentProfile.query.get(agent_profile_id)
    if not profile:
        return jsonify({"error": "Agent not found"}), 404

    note = OwnerAgentNote.for_agent(agent_profile_id)
    note.notes              = request.form.get("notes", "").strip()
    note.contract_signed    = request.form.get("contract_signed") == "on"
    note.background_checked = request.form.get("background_checked") == "on"
    note.mls_verified       = request.form.get("mls_verified") == "on"

    try:
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ── Prompt editor — owner (global) ──────────────────────────────
@dashboard_bp.route("/admin/prompts", methods=["GET", "POST"])
@login_required
def admin_prompts():
    """Owner edits global default prompts."""
    if not current_user.is_owner:
        flash("Access denied.", "danger")
        return _site_redirect("dashboard.index")

    from app.models import PromptOverride
    from config import DEFAULT_PROMPTS

    if request.method == "POST":
        for ptype in ("deal", "portfolio", "preferences"):
            text = request.form.get(f"prompt_{ptype}", "").strip()
            if text:
                PromptOverride.upsert(ptype, text, agent_id=None)
            else:
                PromptOverride.delete(ptype, agent_id=None)
        db.session.commit()
        flash("Global prompts saved.", "success")
        return _site_redirect("dashboard.admin_prompts")

    overrides = {}
    for ptype in ("deal", "portfolio", "preferences"):
        row = PromptOverride.get_for_edit(ptype, agent_id=None)
        overrides[ptype] = row.system_prompt if row else ""

    return render_template("dashboard/admin_prompts.html",
                           overrides=overrides, defaults=DEFAULT_PROMPTS,
                           user=current_user)


# ── Prompt Validation & Preview ──────────────────────────────────

# Required JSON keys per prompt type
_PROMPT_REQUIRED_KEYS = {
    "deal": {"summary", "strengths", "concerns", "negotiation", "verdict"},
    "portfolio": {"headline", "ranking", "patterns", "strategy", "dark_horse", "bottom_line"},
    "preferences": {"headline", "strengths", "blind_spots", "tweaks", "local_insight", "bottom_line"},
}

# Sample listing data for test previews
_SAMPLE_LISTING_CONTEXT = (
    "Property: 742 Evergreen Terrace, Springfield\n"
    "Price: $385,000\n"
    "Beds: 4  |  Baths: 2.5  |  Sqft: 2,100\n"
    "Lot size: 8,712 sqft (0.20 acres)\n"
    "Year built: 1989\n"
    "Price per sqft: $183\n"
    "Days on market: 34\n"
    "HOA: None\n"
    "Estimated annual property tax: $4,200\n"
    "Single story: No\n"
    "Stories: 2\n"
    "Price has dropped 3.5%\n"
    "Features: garage, porch, patio\n"
    "Flood zone: X (minimal risk)\n"
    "Above flood plain: Yes\n"
    "Deal score: 72/100\n"
    "Score breakdown: price 78, size 65, yard 58, features 85, flood 90\n"
    "Source: Zillow\n"
    "Market: Charleston, SC"
)

_SAMPLE_PORTFOLIO_CONTEXT = (
    "Buyer's favorites (3 properties):\n\n"
    "1. 742 Evergreen Terrace — $385,000 | 4bd/2.5ba | 2,100 sqft | Score: 72\n"
    "   Garage, porch, patio. Year built 1989. Price dropped 3.5%.\n\n"
    "2. 15 Oak Lane — $420,000 | 4bd/3ba | 2,450 sqft | Score: 81\n"
    "   Garage, single story. Year built 2005. HOA $125/mo.\n\n"
    "3. 303 Palmetto Dr — $349,000 | 3bd/2ba | 1,850 sqft | Score: 68\n"
    "   Porch, patio. Year built 1975. No flood zone. Price dropped 6.1%.\n\n"
    "Market: Charleston, SC"
)

_SAMPLE_PREFERENCES_CONTEXT = (
    "Buyer's scoring preferences:\n"
    "  Price importance: 8/10\n"
    "  Size importance: 5/10\n"
    "  Yard importance: 7/10\n"
    "  Features importance: 8/10\n"
    "  Flood risk importance: 6/10\n"
    "  Year built importance: 5/10\n"
    "  Single story importance: 7/10\n"
    "  Price per sqft importance: 4/10\n"
    "  HOA importance: 6/10\n"
    "  Tax importance: 5/10\n"
    "  Days on market importance: 3/10\n"
    "  Community pool importance: 2/10\n"
    "Price range: $200,000 - $600,000\n"
    "Min beds: 4  |  Min baths: 3\n"
    "Must have: garage, porch, patio\n"
    "Market: Charleston, SC"
)

_SAMPLE_CONTEXTS = {
    "deal": _SAMPLE_LISTING_CONTEXT,
    "portfolio": _SAMPLE_PORTFOLIO_CONTEXT,
    "preferences": _SAMPLE_PREFERENCES_CONTEXT,
}


@dashboard_bp.route("/admin/prompts/validate", methods=["POST"])
@login_required
def prompt_validate():
    """Validate a prompt for syntax and required structure. Returns JSON."""
    if not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    ptype = request.form.get("ptype", "deal")
    prompt_text = request.form.get("prompt_text", "").strip()

    if not prompt_text:
        return jsonify({"valid": False, "issues": ["Prompt is empty."]})

    issues = []
    required_keys = _PROMPT_REQUIRED_KEYS.get(ptype, set())

    # Check that prompt mentions JSON
    text_lower = prompt_text.lower()
    if "json" not in text_lower:
        issues.append("Prompt should instruct the AI to respond with JSON. Missing keyword 'JSON'.")

    # Check that all required keys are mentioned
    missing_keys = []
    for key in required_keys:
        if key not in text_lower:
            missing_keys.append(key)
    if missing_keys:
        issues.append(f"Missing required JSON keys: {', '.join(sorted(missing_keys))}. "
                      f"The AI response must include these keys.")

    # Check for markdown fence instruction (common mistake — we want NO fences)
    if "no markdown" not in text_lower and "no fences" not in text_lower and "no ```" not in text_lower:
        if "markdown" not in text_lower:
            issues.append("Consider adding 'no markdown fences' instruction. "
                          "Without it, the AI may wrap JSON in ```json blocks, breaking parsing.")

    # Length checks
    if len(prompt_text) < 50:
        issues.append(f"Prompt is very short ({len(prompt_text)} chars). "
                      "It may not give the AI enough context to produce good results.")
    if len(prompt_text) > 4000:
        issues.append(f"Prompt is very long ({len(prompt_text)} chars). "
                      "Consider trimming — longer prompts increase cost and latency.")

    # Check for role/persona
    has_role = any(w in text_lower for w in ["you are", "act as", "your role", "your job"])
    if not has_role:
        issues.append("Consider starting with a role instruction (e.g., 'You are a real estate analyst...'). "
                      "This improves output quality.")

    return jsonify({
        "valid": len(issues) == 0,
        "issues": issues,
        "keys_found": sorted(required_keys - set(missing_keys)) if missing_keys else sorted(required_keys),
        "keys_missing": sorted(missing_keys) if missing_keys else [],
    })


@dashboard_bp.route("/admin/prompts/preview", methods=["POST"])
@login_required
def prompt_preview():
    """Send a prompt with sample data to Claude and return the result. Returns JSON."""
    if not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    ptype = request.form.get("ptype", "deal")
    prompt_text = request.form.get("prompt_text", "").strip()

    if not prompt_text:
        return jsonify({"error": "Prompt is empty."})

    # Use custom sample context from modal if provided, else defaults
    custom_context = request.form.get("sample_context", "").strip()
    sample_context = custom_context if custom_context else _SAMPLE_CONTEXTS.get(ptype, _SAMPLE_LISTING_CONTEXT)

    try:
        from app.services.deal_analyst import _call_anthropic
        result = _call_anthropic(
            system_prompt=prompt_text,
            user_message=sample_context,
            max_tokens=1024,
            timeout=30,
        )

        # Log the test call
        from app.models import ApiCallLog
        meta = result.pop("_meta", {})
        ApiCallLog.log(
            f"anthropic_{ptype}",
            user_id=current_user.id,
            detail=f"prompt_preview ({ptype})",
            success="error" not in result,
            response_time_ms=meta.get("response_time_ms"),
            http_status=meta.get("http_status"),
        )

        if "error" in result:
            return jsonify({"error": result["error"]})

        return jsonify({
            "ok": True,
            "result": result,
            "response_time_ms": meta.get("response_time_ms"),
            "sample_context": sample_context,
        })
    except Exception as exc:
        return jsonify({"error": str(exc)})


# ── User Management (Owner / Master) ────────────────────────────

@dashboard_bp.route("/admin/users")
@login_required
def admin_users():
    """Owner/master: view and manage all user accounts."""
    if not current_user.is_owner:
        flash("Access denied.", "danger")
        return _site_redirect("dashboard.index")

    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("dashboard/admin_users.html",
                           users=users, user=current_user)


@dashboard_bp.route("/admin/users/<int:user_id>/action", methods=["POST"])
@login_required
def admin_user_action(user_id):
    """Suspend, reactivate, or delete a user account."""
    if not current_user.is_owner:
        flash("Access denied.", "danger")
        return _site_redirect("dashboard.index")

    target = db.session.get(User, user_id)
    if not target:
        flash("User not found.", "danger")
        return _site_redirect("dashboard.admin_users")

    # Never allow modifying master accounts (unless you ARE the master)
    if target.role == "master" and not current_user.is_master:
        flash("Cannot modify master accounts.", "danger")
        return _site_redirect("dashboard.admin_users")

    # Never allow modifying your own account via this route
    if target.id == current_user.id:
        flash("You cannot modify your own account here.", "warning")
        return _site_redirect("dashboard.admin_users")

    action = request.form.get("action")

    if action == "suspend":
        reason = request.form.get("reason", "").strip()
        target.is_suspended = True
        target.suspended_reason = reason or None
        db.session.commit()
        flash(f"{target.username} has been suspended.", "warning")

    elif action == "reactivate":
        target.is_suspended = False
        target.suspended_reason = None
        db.session.commit()
        flash(f"{target.username} has been reactivated.", "success")

    elif action == "delete":
        if target.role in ("owner", "master"):
            flash("Cannot delete owner or master accounts.", "danger")
            return _site_redirect("dashboard.admin_users")
        username = target.username
        # Rename to free email/username, then mark as closed
        target.username = f"deleted_{target.id}_{target.username}"
        target.email = f"deleted_{target.id}_{target.email}"
        target.is_verified = False
        target.is_suspended = True
        target.suspended_reason = "Account deleted by admin"
        target.password_hash = "ACCOUNT_DELETED"
        db.session.commit()
        flash(f"Account '{username}' has been deleted.", "info")

    else:
        flash("Unknown action.", "danger")

    return _site_redirect("dashboard.admin_users")


# ── Owner: Billing Settings ──────────────────────────────────────

@dashboard_bp.route("/admin/billing", methods=["GET", "POST"])
@login_required
def admin_billing():
    """Owner-only: view and update billing plan, limits, and budget."""
    if not current_user.is_owner:
        flash("Owner access required.", "danger")
        return _site_redirect("dashboard.index")

    from flask import g
    from app.services.billing import get_billing_info, PLAN_DEFAULTS
    from app.services.registry import update_site

    site_key = g.site["site_key"] if hasattr(g, "site") and g.site else None
    if not site_key:
        flash("No site context.", "danger")
        return _site_redirect("dashboard.index")

    if request.method == "POST":
        plan = request.form.get("billing_plan", "free")
        if plan not in PLAN_DEFAULTS:
            plan = "free"

        defaults = PLAN_DEFAULTS[plan]

        # Use plan defaults or custom overrides
        monthly_limit_ai = int(request.form.get("monthly_limit_ai",
                                                 defaults["monthly_limit_ai"]))
        monthly_limit_fetch = int(request.form.get("monthly_limit_fetch",
                                                    defaults["monthly_limit_fetch"]))
        monthly_budget = float(request.form.get("monthly_budget",
                                                 defaults["monthly_budget"]))
        billing_email = request.form.get("billing_email", "").strip()
        billing_cycle_start = int(request.form.get("billing_cycle_start", 1))
        billing_cycle_start = max(1, min(billing_cycle_start, 28))

        update_site(
            site_key,
            billing_plan=plan,
            monthly_limit_ai=monthly_limit_ai,
            monthly_limit_fetch=monthly_limit_fetch,
            monthly_budget=monthly_budget,
            billing_email=billing_email,
            billing_cycle_start=billing_cycle_start,
        )
        flash(f"Billing updated to '{plan}' plan.", "success")
        return _site_redirect("dashboard.admin_billing")

    info = get_billing_info(site_key)
    return render_template("dashboard/admin_billing.html",
                           billing=info, plans=PLAN_DEFAULTS,
                           user=current_user)
